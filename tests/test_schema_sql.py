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

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
TYPE_SPECIFIC_FIELDS = {
    "noise_source", "vehicle_description", "license_plate",
    "blocking_driveway", "pothole_size", "hazard_to_traffic",
}

CHATS = load_chats(DEFAULT_CSV)
ROUTINE_IDS = sorted(cid for cid, t in CHATS.items() if t[0]["chat_label"] == "routine")
HANDOFF_IDS = sorted(cid for cid, t in CHATS.items() if t[0]["chat_label"] == "handoff")


@pytest.fixture(scope="session")
def db(tmp_path_factory):
    server = pgserver.get_server(tmp_path_factory.mktemp("pg"), cleanup_mode="stop")
    with psycopg.connect(server.get_uri(), autocommit=True) as conn:
        conn.execute((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
        conn.execute((SQL_DIR / "test_chats.sql").read_text(encoding="utf-8"))
        yield conn
    server.cleanup()


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


@pytest.mark.parametrize("chat_id", HANDOFF_IDS)
def test_every_handoff_chat_saves(conn, chat_id):
    turns = CHATS[chat_id]
    conn.execute(
        "insert into public.handoffs (conversation_id, transcript, trigger_label) values (%s, %s, %s)",
        (chat_id, "\n".join(t["resident_message"] for t in turns), turns[0]["expected_handoff_trigger"]),
    )


def test_unknown_handoff_trigger_rejected(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        with conn.transaction():
            conn.execute(
                "insert into public.handoffs (conversation_id, transcript, trigger_label) "
                "values ('x', 'y', 'probably_fine')"
            )


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
