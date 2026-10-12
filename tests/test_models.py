import pytest
from pydantic import ValidationError

from ecc_intake_schema.loader import (
    COMMON_COLUMNS,
    DEFAULT_CSV,
    TYPE_COLUMNS,
    load_chats,
    routine_payload,
)
from ecc_intake_schema.models import (
    ROUTINE_REQUEST_MODELS,
    IllegallyParkedVehicle,
    NoiseComplaint,
)

CHATS = load_chats(DEFAULT_CSV)
# Last row per routine chat (expected values repeat on every turn).
ROUTINE = {cid: turns[-1] for cid, turns in CHATS.items() if turns[0]["chat_label"] == "routine"}


def _payload(row: dict[str, str]) -> dict:
    return routine_payload(row["chat_id"], CHATS[row["chat_id"]])


def test_test_set_has_30_routine_chats():
    assert len(ROUTINE) == 30


@pytest.mark.parametrize("chat_id", sorted(ROUTINE))
def test_every_routine_chat_validates(chat_id):
    row = ROUTINE[chat_id]
    report = ROUTINE_REQUEST_MODELS[row["expected_request_type"]].model_validate(_payload(row))
    assert report.callback_phone == row["expected_callback_phone"]


@pytest.mark.parametrize("chat_id", sorted(ROUTINE))
def test_dropping_any_field_fails(chat_id):
    row = ROUTINE[chat_id]
    model = ROUTINE_REQUEST_MODELS[row["expected_request_type"]]
    payload = _payload(row)
    for field in payload:
        incomplete = {k: v for k, v in payload.items() if k != field}
        with pytest.raises(ValidationError):
            model.model_validate(incomplete)


def test_no_field_has_a_default():
    for model in ROUTINE_REQUEST_MODELS.values():
        assert all(f.is_required() for f in model.model_fields.values()), model.__name__


def _allows_none(field) -> bool:
    return type(None) in getattr(field.annotation, "__args__", ())


@pytest.mark.parametrize("request_type", sorted(ROUTINE_REQUEST_MODELS))
def test_nullable_fields_match_blanks_in_data(request_type):
    """A field may accept None only if a correct routine chat leaves it blank."""
    model = ROUTINE_REQUEST_MODELS[request_type]
    nullable = {name for name, f in model.model_fields.items() if _allows_none(f)}
    columns = {**COMMON_COLUMNS, **TYPE_COLUMNS[request_type]}
    blank_in_data = {
        field
        for row in ROUTINE.values()
        if row["expected_request_type"] == request_type
        for field, col in columns.items()
        if not row[col].strip()
    }
    assert nullable == blank_in_data


def test_unreadable_plate_must_be_explicit_none():
    payload = _payload(ROUTINE["ECC-T-010"])
    assert IllegallyParkedVehicle.model_validate(payload).license_plate is None
    payload.pop("license_plate")
    with pytest.raises(ValidationError):
        IllegallyParkedVehicle.model_validate(payload)


def test_phone_is_normalized():
    payload = _payload(ROUTINE["ECC-T-001"]) | {"callback_phone": "555 010 4417"}
    assert NoiseComplaint.model_validate(payload).callback_phone == "(555) 010-4417"


@pytest.mark.parametrize(
    "override",
    [
        {"location": "   "},
        {"callback_phone": "555-0104"},
        {"incident_observed_at": "2024-06-07T23:30:00"},  # no timezone
        {"request_type": "pothole"},
        {"extra_field": "x"},
    ],
)
def test_bad_values_rejected(override):
    with pytest.raises(ValidationError):
        NoiseComplaint.model_validate(_payload(ROUTINE["ECC-T-001"]) | override)
