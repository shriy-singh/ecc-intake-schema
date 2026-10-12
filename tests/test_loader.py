import csv
from pathlib import Path

import pytest

from ecc_intake_schema.loader import (
    DEFAULT_CSV,
    ChatDataError,
    chat_label,
    load_chats,
    main,
    routine_payload,
)


def test_groups_rows_by_chat_in_turn_order():
    chats = load_chats(DEFAULT_CSV)
    assert len(chats) == 40
    assert sum(len(t) for t in chats.values()) == 80
    assert all([int(r["turn_number"]) for r in t] == [1, 2] for t in chats.values())


def test_main_reports_counts_and_passes(capsys):
    assert main([str(DEFAULT_CSV)]) == 0
    out = capsys.readouterr().out
    assert "80 rows -> 40 chats" in out
    assert "routine: 30" in out
    assert "handoff: 10" in out
    assert "Routine chats valid against their model: 30/30" in out


def _write_variant(tmp_path: Path, edit) -> Path:
    with DEFAULT_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames, rows = reader.fieldnames, list(reader)
    edit(rows)
    out = tmp_path / "variant.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return out


def test_main_fails_on_missing_required_field(tmp_path, capsys):
    def blank_phone(rows):
        for r in rows:
            if r["chat_id"] == "ECC-T-001":
                r["expected_callback_phone"] = ""

    assert main([str(_write_variant(tmp_path, blank_phone))]) == 1
    out = capsys.readouterr().out
    assert "29/30" in out
    assert "FAIL ECC-T-001 (noise_complaint): callback_phone" in out


def test_turns_that_disagree_are_flagged():
    turns = [dict(r) for r in load_chats(DEFAULT_CSV)["ECC-T-002"]]
    turns[1]["expected_license_plate"] = "OTHER1"
    with pytest.raises(ChatDataError, match="expected_license_plate"):
        routine_payload("ECC-T-002", turns)


def test_unknown_label_is_flagged():
    turns = [dict(r, chat_label="maybe") for r in load_chats(DEFAULT_CSV)["ECC-T-001"]]
    with pytest.raises(ChatDataError, match="unknown chat_label"):
        chat_label("ECC-T-001", turns)
