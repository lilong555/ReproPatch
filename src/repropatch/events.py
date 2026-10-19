"""Append-only audit records, not a resumable event-sourcing implementation."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class EventLog:
    def __init__(self, directory: Path, run_id: str):
        self.run_id = run_id
        self.db = sqlite3.connect(directory / "events.sqlite3")
        self.db.execute(
            "CREATE TABLE events (seq INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, "
            "run_id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)"
        )
        self.db.commit()
        self.stream = (directory / "events.jsonl").open("x", encoding="utf-8")
        self.sequence = 0

    def emit(self, kind: str, payload: dict):
        self.sequence += 1
        now = datetime.now(UTC).isoformat()
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        self.db.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            (self.sequence, now, self.run_id, kind, encoded),
        )
        self.db.commit()
        event = {
            "seq": self.sequence,
            "timestamp": now,
            "run_id": self.run_id,
            "kind": kind,
            "payload": payload,
        }
        self.stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
        self.stream.flush()

    def close(self):
        self.stream.close()
        self.db.close()
