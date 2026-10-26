"""正式批次的首批准入条件。"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from formal_benchmark import ROOT, completed_pilot_gate, completion_gate, pilot_gate, registry_gate


def test_comparison_matrix_matches_shell_tasks_and_budget(monkeypatch):
    import formal_benchmark as campaign

    monkeypatch.setattr(campaign, "PROTOCOL", ROOT / "benchmarks/comparison-full-24-protocol.json")
    p = campaign.protocol()
    shell = json.loads((ROOT / "benchmarks/shell-only-full-protocol.json").read_text())
    matrix = campaign.execution_matrix(p)
    assert p["tasks"] == shell["tasks"]
    assert p["execution_budget_override"] == shell["execution_budget_override"]
    assert len(p["attempts"]) == len(matrix) == 84
    assert len({a["attempt_id"] for a in p["attempts"]}) == 84
    assert sum(a["request_cap"] for a in p["attempts"]) == 2016
    assert {a["arm"] for a in matrix} == {"full", "no-checks", "mini", "codex"}
    assert len({(a["instance"], a["suffix"]) for a in matrix}) == 84
    assert len(campaign.execution_matrix(shell)) == 21


@pytest.mark.parametrize("arm", ["full", "no-checks", "mini", "codex"])
def test_matrix_job_executes_only_selected_arm(monkeypatch, tmp_path, arm):
    import formal_benchmark as campaign

    monkeypatch.setattr(campaign, "PROTOCOL", ROOT / "benchmarks/comparison-full-24-protocol.json")
    output = tmp_path / "output"
    output.mkdir()
    settings = {
        "task": "task.yaml",
        "qualification": "result.json",
        "common_input": "common-input.json",
        "mini_source": "mini-source",
        "agent_seconds": 5900,
    }
    (output / "prepared.json").write_text(json.dumps(settings))
    commands, preparations = [], []

    def run(command, log):
        commands.append(command)
        if command[1] == "scripts/score_benchmark_attempt.py":
            target = Path(command[command.index("--output") + 1])
            target.mkdir()
            (target / "score.json").write_text(
                json.dumps({"status": "EMPTY_CANDIDATE", "accepted": False})
            )
        return 0

    monkeypatch.setattr(campaign, "run", run)
    monkeypatch.setattr(
        campaign.subprocess, "run", lambda command, **kw: preparations.append(command)
    )
    campaign.execute("fmtlib__fmt-1171", output, arm)
    assert len(commands) == 2
    assert len(preparations) == int(arm in {"mini", "codex"})
    expected_script = (
        "scripts/run_codex_benchmark.py" if arm == "codex" else "scripts/run_benchmark_agent.py"
    )
    assert commands[0][1] == expected_script
    result = json.loads((output / "summary.json").read_text())
    assert len(result["attempts"]) == 1
    assert result["attempts"][0]["arm"] == arm
    assert result["attempts"][0]["usage"]["requests"] == 0
    ledger = campaign.LocalUsageLedger(output / "ledgers" / (arm + ".sqlite3"))
    assert ledger.request_cap(result["attempts"][0]["attempt_id"]) == 24


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


@pytest.mark.parametrize("changed", [None, "issued_mini", "new_unknown_usage"])
def test_registry_completes_only_zero_request_trials(pilot, changed):
    p = json.loads((ROOT / "benchmarks/formal-max-mini-protocol.json").read_text())
    for row in pilot["attempts"]:
        score = row["score"]
        if row["arm"] in {"mini", "codex"}:
            score["worker_usage"]["requests"] = 0
        elif row["arm"] == "no-checks":
            score.update(native_reason="MODEL_REQUEST_TIMEOUT", classification="infrastructure")
            score["worker_usage"].update(
                requests=10 if row["instance_id"].endswith("3727") else 11,
                unknown_usage_requests=1,
            )
    rows = list(pilot["attempts"])
    completion = json.loads((ROOT / "benchmarks/formal-max-completion-protocol.json").read_text())
    for attempt in completion["attempts"]:
        rows.append(
            {
                **attempt,
                "score": {
                    "classification": "candidate",
                    "accepted": False,
                    "worker_usage": {
                        "requests": 0
                        if attempt["arm"] == "mini"
                        else 5
                        if attempt["instance_id"].endswith("3727")
                        else 11,
                        "unknown_usage_requests": 0,
                    },
                },
            }
        )
    if changed == "issued_mini":
        rows[-2]["score"]["worker_usage"]["requests"] = 1
    elif changed == "new_unknown_usage":
        rows[-1]["score"]["worker_usage"]["unknown_usage_requests"] = 1
    if changed:
        with pytest.raises(AssertionError):
            registry_gate(rows, p)
    else:
        result = registry_gate(rows, p)
        assert result["prior_model_requests"] == 61
