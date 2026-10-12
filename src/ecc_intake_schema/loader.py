"""Load the ECC test-set CSV, group rows by chat, and validate routine chats.

Each chat spans several rows (one per resident turn). The expected values are
repeated on every turn, so the loader checks they agree before building the
report that the chat should produce.
"""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from ecc_intake_schema.models import ROUTINE_REQUEST_MODELS

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "data" / "palantir_ecc_intake_test_set_40_chats.csv"

LABELS = ("routine", "handoff")

COMMON_COLUMNS = {
    "location": "expected_location",
    "incident_observed_at": "incident_observed_at",
    "callback_phone": "expected_callback_phone",
}
TYPE_COLUMNS = {
    "noise_complaint": {"noise_source": "expected_noise_source"},
    "illegally_parked_vehicle": {
        "vehicle_description": "expected_vehicle_description",
        "license_plate": "expected_license_plate",
        "blocking_driveway": "expected_blocking_driveway",
    },
    "pothole": {
        "pothole_size": "expected_pothole_size",
        "hazard_to_traffic": "expected_hazard_to_traffic",
    },
}


class ChatDataError(ValueError):
    """The CSV rows for a chat contradict each other or use unknown labels."""


def load_chats(path: Path) -> dict[str, list[dict[str, str]]]:
    """Return {chat_id: rows}, with each chat's rows in turn order."""
    chats: dict[str, list[dict[str, str]]] = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            chats.setdefault(row["chat_id"], []).append(row)
    for turns in chats.values():
        turns.sort(key=lambda r: int(r["turn_number"]))
    return chats


def _single_value(chat_id: str, turns: list[dict[str, str]], column: str) -> str:
    values = {r[column].strip() for r in turns}
    if len(values) != 1:
        raise ChatDataError(f"{chat_id}: turns disagree on {column}: {sorted(values)}")
    return values.pop()


def chat_label(chat_id: str, turns: list[dict[str, str]]) -> str:
    label = _single_value(chat_id, turns, "chat_label")
    if label not in LABELS:
        raise ChatDataError(f"{chat_id}: unknown chat_label {label!r}")
    return label


def routine_payload(chat_id: str, turns: list[dict[str, str]]) -> dict:
    """Build the report a routine chat should save, from its expected_* columns."""
    request_type = _single_value(chat_id, turns, "expected_request_type")
    if request_type not in TYPE_COLUMNS:
        raise ChatDataError(f"{chat_id}: unknown expected_request_type {request_type!r}")
    columns = {**COMMON_COLUMNS, **TYPE_COLUMNS[request_type]}
    payload: dict = {field: _single_value(chat_id, turns, col) for field, col in columns.items()}
    payload["request_type"] = request_type
    if "license_plate" in payload:
        payload["license_plate"] = payload["license_plate"] or None
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", nargs="?", type=Path, default=DEFAULT_CSV, help="test-set CSV path")
    args = parser.parse_args(argv)

    chats = load_chats(args.csv)
    rows = sum(len(turns) for turns in chats.values())

    labels: dict[str, str] = {}
    failures: list[str] = []
    for chat_id, turns in chats.items():
        try:
            labels[chat_id] = chat_label(chat_id, turns)
        except ChatDataError as e:
            failures.append(str(e))

    label_counts = Counter(labels.values())
    print(f"Loaded {rows} rows -> {len(chats)} chats")
    print(f"  routine: {label_counts['routine']}")
    print(f"  handoff: {label_counts['handoff']}")

    routine_ids = [cid for cid, label in labels.items() if label == "routine"]
    valid_by_type: Counter[str] = Counter()
    for chat_id in routine_ids:
        try:
            payload = routine_payload(chat_id, chats[chat_id])
            ROUTINE_REQUEST_MODELS[payload["request_type"]].model_validate(payload)
        except ChatDataError as e:
            failures.append(str(e))
        except ValidationError as e:
            problems = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors())
            failures.append(f"{chat_id} ({payload['request_type']}): {problems}")
        else:
            valid_by_type[payload["request_type"]] += 1

    print(f"\nRoutine chats valid against their model: {sum(valid_by_type.values())}/{len(routine_ids)}")
    for request_type in ROUTINE_REQUEST_MODELS:
        print(f"  {request_type}: {valid_by_type[request_type]}")

    print(f"\nFailures: {len(failures)}")
    for failure in failures:
        print(f"  FAIL {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
