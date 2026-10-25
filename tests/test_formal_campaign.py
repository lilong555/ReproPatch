"""正式批次的首批准入条件。"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from formal_benchmark import ROOT, completed_pilot_gate, completion_gate, pilot_gate


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


@pytest.mark.parametrize("changed", [None, "started_arm", "over_cap"])
def test_completion_uses_only_untouched_arms_and_remaining_budget(pilot, changed):
    p = json.loads((ROOT / "benchmarks/formal-max-completion-protocol.json").read_text())
    for row in pilot["attempts"]:
        usage = row["score"]["worker_usage"]
        if row["arm"] in {"mini", "codex"}:
            usage["requests"] = 0
            row["score"]["oracle_executed"] = False
        elif row["arm"] == "no-checks":
            usage.update(
                requests=10 if row["instance_id"].endswith("3727") else 11,
                unknown_usage_requests=1,
            )
    if changed == "started_arm":
        pilot["attempts"][2]["score"]["worker_usage"]["requests"] = 1
    elif changed == "over_cap":
        p["formal_request_cap"] = 52
    if changed:
        with pytest.raises(AssertionError):
            completion_gate(pilot, p)
    else:
        completion_gate(pilot, p)


@pytest.mark.parametrize("changed", [None, "completion_failure", "completion_usage_unknown"])
def test_full_campaign_preserves_prior_timeouts_and_requires_measured_completion(pilot, changed):
    p = json.loads((ROOT / "benchmarks/formal-max-full-v2-protocol.json").read_text())
    config = json.loads((ROOT / "benchmarks/formal-max-completion-protocol.json").read_text())
    for row in pilot["attempts"]:
        score = row["score"]
        if row["arm"] in {"mini", "codex"}:
            score["worker_usage"]["requests"] = 0
            score["oracle_executed"] = False
        elif row["arm"] == "no-checks":
            score.update(
                native_reason="MODEL_REQUEST_TIMEOUT",
                classification="infrastructure",
                accepted=None,
            )
            score["worker_usage"].update(
                requests=10 if row["instance_id"].endswith("3727") else 11,
                unknown_usage_requests=1,
            )
    completion = {
        "protocol_sha256": p["completion_protocol_sha256"],
        "attempts": [
            {
                **a,
                "score": {
                    "classification": "candidate",
                    "accepted": False,
                    "worker_usage": {"requests": 12, "unknown_usage_requests": 0},
                },
            }
            for a in config["attempts"]
        ],
    }
    if changed == "completion_failure":
        completion["attempts"][0]["score"].update(classification="infrastructure", accepted=None)
    elif changed == "completion_usage_unknown":
        completion["attempts"][0]["score"]["worker_usage"]["unknown_usage_requests"] = 1
    if changed:
        with pytest.raises(AssertionError):
            completed_pilot_gate(pilot, completion, p)
    else:
        rows = completed_pilot_gate(pilot, completion, p)
        assert len(rows) == 8
        assert sum(r["score"]["worker_usage"]["unknown_usage_requests"] for r in rows) == 2
