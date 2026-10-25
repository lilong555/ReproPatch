"""正式批次的首批准入条件。"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from formal_benchmark import ROOT, pilot_gate


@pytest.fixture
def pilot():
    path = ROOT / "benchmarks/formal-max-protocol.json"
    config = json.loads(path.read_text())
    return {
        "protocol_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "attempts": [
            {
                **attempt,
                "score": {
                    "classification": "candidate",
                    "accepted": False,
                    "worker_usage": {"requests": 12, "unknown_usage_requests": 0},
                },
            }
            for attempt in config["attempts"]
        ],
    }


def test_complete_candidate_failures_are_valid_measured_attempts(pilot):
    p = json.loads((ROOT / "benchmarks/formal-max-full-protocol.json").read_text())
    pilot_gate(pilot, p)


@pytest.mark.parametrize(
    "issue", ["missing_attempt", "infrastructure", "unknown_usage", "over_cap"]
)
def test_incomplete_pilot_stops_full_campaign(pilot, issue):
    p = json.loads((ROOT / "benchmarks/formal-max-full-protocol.json").read_text())
    score = pilot["attempts"][0]["score"]
    if issue == "missing_attempt":
        pilot["attempts"].pop()
    elif issue == "infrastructure":
        score.update(classification="infrastructure", accepted=None)
    else:
        score["worker_usage"][
            "unknown_usage_requests" if issue == "unknown_usage" else "requests"
        ] = 1 if issue == "unknown_usage" else 13
    with pytest.raises(AssertionError):
        pilot_gate(pilot, p)
