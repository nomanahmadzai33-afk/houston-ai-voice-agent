from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RESERVATIONS_PATH = DATA_DIR / "reservations.json"
LEADS_PATH = DATA_DIR / "leads.json"
TRANSFERS_PATH = DATA_DIR / "transfers.json"


def _ensure_file(path: Path) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]\n", encoding="utf-8")


def load_records(path: Path) -> list[dict]:
    _ensure_file(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_records(path: Path, records: list[dict]) -> None:
    _ensure_file(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2)
        handle.write("\n")


def append_record(path: Path, record: dict) -> dict:
    records = load_records(path)
    records.append(record)
    save_records(path, records)
    return record


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
