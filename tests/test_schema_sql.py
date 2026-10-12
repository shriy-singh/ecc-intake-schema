"""Run sql/schema.sql and sql/test_chats.sql against a real Postgres.

Every rule the models enforce is enforced a second time by the database, so
both copies are tested here: each case is checked against the Pydantic model
and the requests table, and they must agree. "It parsed" is not evidence that
it behaves, so these tests insert real rows and watch what Postgres does.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from ecc_intake_schema.loader import load_chats, routine_payload, DEFAULT_CSV
from ecc_intake_schema.models import ROUTINE_REQUEST_MODELS

psycopg = pytest.importorskip("psycopg")
pgserver = pytest.importorskip("pgserver")
from psycopg.types.json import Jsonb  # noqa: E402

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
TYPE_SPECIFIC_FIELDS = {
    "noise_source", "vehicle_description", "license_plate",
    "blocking_driveway", "pothole_size", "hazard_to_traffic",
}

CHATS = load_chats(DEFAULT_CSV)
ROUTINE_IDS = sorted(cid for cid, t in CHATS.items() if t[0]["chat_label"] == "routine")
HANDOFF_IDS = sorted(cid for cid, t in CHATS.items() if t[0]["chat_label"] == "handoff")


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    srv = pgserver.get_server(tmp_path_factory.mktemp("pg"), cleanup_mode="stop")
    yield srv
    srv.cleanup()


@pytest.fixture(scope="session")
def db(server):
    with psycopg.connect(server.get_uri(), autocommit=True) as conn:
        conn.execute((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
        conn.execute((SQL_DIR / "test_chats.sql").read_text(encoding="utf-8"))
        yield conn


@pytest.fixture
def conn(db):
    """Each test runs in a transaction that is rolled back afterwards."""
    with db.transaction(force_rollback=True):
        yield db


def _row(chat_id: str) -> dict:
    """The validated report for a routine chat, as the agent would save it."""
    payload = routine_payload(chat_id, CHATS[chat_id])
    report = ROUTINE_REQUEST_MODELS[payload["request_type"]].model_validate(payload)
    return {"conversation_id": chat_id, **report.model_dump()}


def _db_accepts(conn, row: dict) -> bool:
    columns = ", ".join(row)
    placeholders = ", ".join(f"%({c})s" for c in row)
    try:
        with conn.transaction():  # savepoint, so a rejected insert doesn't abort the test
            conn.execute(f"insert into public.requests ({columns}) values ({placeholders})", row)
    except psycopg.errors.IntegrityError:
        return False
    return True


def _model_accepts(row: dict) -> bool:
    payload = {k: v for k, v in row.items() if k != "conversation_id"}
    try:
        ROUTINE_REQUEST_MODELS[row["request_type"]].model_validate(payload)
    except ValidationError:
        return False
    return True


@pytest.mark.parametrize("chat_id", ROUTINE_IDS)
def test_every_routine_chat_saves(conn, chat_id):
    assert _db_accepts(conn, _row(chat_id))


# One representative chat per type; every field of that type's model is tried.
SAMPLES = {"noise_complaint": "ECC-T-001", "illegally_parked_vehicle": "ECC-T-002", "pothole": "ECC-T-003"}
FIELD_CASES = [
    (request_type, field)
    for request_type, model in ROUTINE_REQUEST_MODELS.items()
    for field in model.model_fields
    if field != "request_type"
]


@pytest.mark.parametrize("request_type,field", FIELD_CASES)
def test_null_field_model_and_db_agree(conn, request_type, field):
    row = _row(SAMPLES[request_type]) | {field: None}
    model_ok, db_ok = _model_accepts(row), _db_accepts(conn, row)
    assert model_ok == db_ok, f"model accepts={model_ok}, db accepts={db_ok}"
    # Only license_plate may be null (ECC-T-010, ECC-T-025, ECC-T-037).
    assert db_ok == (field == "license_plate")


@pytest.mark.parametrize("request_type,field", [
    (t, f) for t, f in FIELD_CASES if ROUTINE_REQUEST_MODELS[t].model_fields[f].annotation is not bool
    and f != "incident_observed_at"
])
def test_blank_text_rejected_by_both(conn, request_type, field):
    row = _row(SAMPLES[request_type]) | {field: "   "}
    assert not _model_accepts(row)
    assert not _db_accepts(conn, row)


@pytest.mark.parametrize("request_type", sorted(ROUTINE_REQUEST_MODELS))
def test_other_types_fields_rejected_by_both(conn, request_type):
    own = set(ROUTINE_REQUEST_MODELS[request_type].model_fields)
    for field in sorted(TYPE_SPECIFIC_FIELDS - own):
        donor = next(t for t, m in ROUTINE_REQUEST_MODELS.items() if field in m.model_fields)
        row = _row(SAMPLES[request_type]) | {field: _row(SAMPLES[donor])[field]}
        assert not _model_accepts(row), field
        assert not _db_accepts(conn, row), field


def test_unreadable_plate_saves(conn):
    row = _row("ECC-T-010")
    assert row["license_plate"] is None
    assert _db_accepts(conn, row)


@pytest.mark.parametrize("phone", ["555-010-4417", "5550104417", "(555) 010-441"])
def test_unnormalized_phone_rejected_by_db(conn, phone):
    assert not _db_accepts(conn, _row("ECC-T-001") | {"callback_phone": phone})


def test_unknown_request_type_rejected(conn):
    assert not _db_accepts(conn, _row("ECC-T-001") | {"request_type": "graffiti"})


RULE_FOR_LABEL = {
    "danger": "emergency_language",
    "injury": "emergency_language",
    "fire": "emergency_language",
    "weapon": "emergency_language",
    "person_in_distress": "emergency_language",
    "asked_for_person": "asked_for_person",
    "unclassified_after_two_tries": "cannot_classify",
}


def _packet(chat_id: str) -> dict:
    """The §7 handoff packet for a handoff chat in the test set."""
    turns = CHATS[chat_id]
    label = turns[0]["expected_handoff_trigger"]
    transcript = [{"role": "resident", "text": t["resident_message"], "sent_at": None} for t in turns]
    return {
        "conversation_id": chat_id,
        "transcript": Jsonb(transcript),
        "trigger_label": label,
        "trigger_rule": RULE_FOR_LABEL[label],
        "triggering_message": turns[-1]["resident_message"],
        "classification_attempts": 2 if label == "unclassified_after_two_tries" else 0,
        "request_type": None,
        "fields_collected": Jsonb({}),
    }


def _handoff_accepted(conn, packet: dict) -> bool:
    columns = ", ".join(packet)
    placeholders = ", ".join(f"%({c})s" for c in packet)
    try:
        with conn.transaction():
            conn.execute(f"insert into public.handoffs ({columns}) values ({placeholders})", packet)
    except psycopg.errors.IntegrityError:
        return False
    return True



@pytest.mark.parametrize("chat_id", HANDOFF_IDS)
def test_every_handoff_chat_saves_full_packet(conn, chat_id):
    assert _handoff_accepted(conn, _packet(chat_id))


def test_asked_for_person_accepted(conn):
    packet = _packet("ECC-T-004") | {
        "trigger_label": "asked_for_person",
        "trigger_rule": "asked_for_person",
        "triggering_message": "can I talk to a real person please",
    }
    assert _handoff_accepted(conn, packet)


def test_handoff_mid_report_keeps_type_and_fields(conn):
    packet = _packet("ECC-T-008") | {
        "request_type": "pothole",
        "fields_collected": Jsonb({"location": "Kessler Blvd"}),
    }
    assert _handoff_accepted(conn, packet)


@pytest.mark.parametrize("column", [
    "conversation_id", "transcript", "trigger_label", "trigger_rule",
    "triggering_message", "classification_attempts", "fields_collected",
])
def test_handoff_missing_packet_item_rejected(conn, column):
    assert not _handoff_accepted(conn, _packet("ECC-T-004") | {column: None})


@pytest.mark.parametrize("override", [
    {"trigger_label": "probably_fine"},
    {"trigger_label": "weapon", "trigger_rule": "asked_for_person"},       # label from another rule
    {"trigger_rule": "cannot_classify"},                                   # weapon label under cannot_classify
    {"triggering_message": "   "},
    {"conversation_id": ""},
    {"transcript": Jsonb([])},
    {"transcript": Jsonb("just a string")},
    {"fields_collected": Jsonb([])},
    {"classification_attempts": 3},
    {"classification_attempts": -1},
    {"request_type": "graffiti"},
], ids=lambda o: ",".join(o))
def test_bad_handoff_packet_rejected(conn, override):
    assert not _handoff_accepted(conn, _packet("ECC-T-004") | override)


@pytest.mark.parametrize("override", [
    {"classification_attempts": 1},          # §4: only after the second failed attempt
    {"request_type": "pothole"},             # a confirmed type can't be "could not classify"
])
def test_cannot_classify_rules(conn, override):
    assert _handoff_accepted(conn, _packet("ECC-T-012"))
    assert not _handoff_accepted(conn, _packet("ECC-T-012") | override)


def test_upgrades_original_handoffs_table(server):
    """The handoffs table already in Supabase was made by the first schema.sql."""
    with psycopg.connect(server.get_uri(), autocommit=True) as admin:
        admin.execute("drop database if exists upgrade_check")
        admin.execute("create database upgrade_check")
    uri = server.get_uri().rsplit("/", 1)[0] + "/upgrade_check"
    with psycopg.connect(uri, autocommit=True) as conn:
        conn.execute("""
            create table public.handoffs (
              id              bigint generated always as identity primary key,
              conversation_id text        not null,
              transcript      text        not null,
              trigger_label   text        not null
                check (trigger_label in ('weapon', 'injury', 'fire', 'danger',
                                         'person_in_distress', 'unclassified_after_two_tries')),
              created_at      timestamptz not null default now()
            )""")
        conn.execute((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
        conn.execute((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))  # and again: re-runnable
        (transcript_type,) = conn.execute(
            "select data_type from information_schema.columns "
            "where table_name = 'handoffs' and column_name = 'transcript'"
        ).fetchone()
        assert transcript_type == "jsonb"
        assert _handoff_accepted(conn, _packet("ECC-T-004") | {
            "trigger_label": "asked_for_person", "trigger_rule": "asked_for_person"})
        assert not _handoff_accepted(conn, _packet("ECC-T-004") | {"trigger_label": "probably_fine"})


def test_rerunning_schema_keeps_rules(conn):
    conn.execute((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
    assert not _db_accepts(conn, _row("ECC-T-001") | {"noise_source": None})
    assert _db_accepts(conn, _row("ECC-T-001"))


def test_test_chats_table_matches_csv(conn):
    (rows,) = conn.execute("select count(*) from public.test_chats").fetchone()
    by_label = dict(conn.execute(
        "select chat_label, count(distinct chat_id) from public.test_chats group by chat_label"
    ).fetchall())
    assert rows == 80
    assert by_label == {"routine": 30, "handoff": 10}
