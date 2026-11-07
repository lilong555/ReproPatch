"""Recovery cost accounting and production pause/resume measurement contracts."""

import copy
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import ROOT, SimulatedSandbox

from repropatch.events import read_events
from repropatch.harness import Harness
from repropatch.models import load_sdk_script
from repropatch.recovery import read_checkpoint
from repropatch.task import Task

sys.path.insert(0, str(ROOT / "scripts"))
import benchmark_recovery_costs as audit
import run_recovery_pair as live
from benchmark_budget import LocalUsageLedger


def usage(requests, incoming, outgoing=10, cached=0, unknown=0):
    return {
        "requests": requests,
        "input_tokens": incoming,
        "output_tokens": outgoing,
        "cached_input_tokens": cached,
        "unknown_usage_requests": unknown,
    }


def test_missing_provider_usage_preserves_missing_and_known_subtotal():
    rows = [
        {
            "usage": json.dumps({"input_tokens": 12, "output_tokens": 4}),
            "purpose": "repair",
        },
        {"usage": None, "purpose": "repair"},
    ]
    result = audit.usage_sum(rows)
    assert result["requests"] == 2
    assert result["input_tokens"] is None
    assert result["cached_input_tokens"] is None
    assert result["known_input_tokens"] == 12
    assert result["unknown_usage_requests"] == 1
    assert live.subtract_usage(usage(3, None), usage(1, 100))["input_tokens"] is None


def checkpoint_budget():
    run = {
        "deadline_at": "2026-11-07T02:00:00+00:00",
        "steps_used": 3,
        "tool_calls_admitted": 5,
    }
    checkpoint = {
        "deadline_at": run["deadline_at"],
        "committed_at": "2026-11-07T00:02:03.750000+00:00",
        "counters": {"steps_used": 3, "tool_calls_admitted": 5},
    }
    original = {"max_steps": 24, "max_tool_calls": 48, "verification_reserve_seconds": 1200}
    return run, checkpoint, original


def test_restart_allowance_is_exact_remaining_requests_tools_and_time():
    assert live.remaining_budget(*checkpoint_budget()) == {
        "max_steps": 21,
        "max_tool_calls": 43,
        "wall_seconds": 7076,
    }


@pytest.mark.parametrize("field", ["steps_used", "tool_calls_admitted", "deadline_at"])
def test_remaining_budget_requires_same_committed_boundary(field):
    run, checkpoint, original = checkpoint_budget()
    run[field] = "2026-11-07T03:00:00+00:00" if field == "deadline_at" else 7
    with pytest.raises(ValueError, match="CHECKPOINT_.*_CHANGED"):
        live.remaining_budget(run, checkpoint, original)


def test_pair_savings_subtract_prefix_once_and_keep_negative_values():
    result = live.pair_metrics(
        {"usage": usage(3, 1000)},
        {"usage": usage(8, 9000), "measurement": {"elapsed_seconds": 50}},
        {"usage": usage(6, 6000), "measurement": {"elapsed_seconds": 40}},
    )
    assert result["resume_post_failure_usage"]["input_tokens"] == 8000
    assert result["restart_minus_resume_usage"]["input_tokens"] == -2000
    assert result["post_failure_input_saved_fraction"] == pytest.approx(-1 / 3)
    assert result["restart_minus_resume_wall_seconds"] == -10


def test_cumulative_usage_regression_is_rejected():
    with pytest.raises(ValueError, match="NEGATIVE_CUMULATIVE_USAGE"):
        live.subtract_usage(usage(2, 10), usage(3, 20))


def test_both_post_failure_arms_enforce_twenty_one_requests(tmp_path):
    from benchmark_budget import BudgetLimit

    from repropatch.context import ContextPolicy, encoded

    payload = encoded(
        {
            "model": "gpt-6-luna",
            "max_output_tokens": 8192,
            "reasoning": {"effort": "max"},
            "input": [{"role": "user", "content": "offline budget check"}],
        }
    )
    policy = ContextPolicy(request_cap=24)
    ledgers = {}
    for arm, cap in (("resume", 24), ("restart", 21)):
        ledger = LocalUsageLedger.create_scoped(
            tmp_path / (arm + ".sqlite3"), {arm: cap}, context_policy=policy
        )
        for _ in range(cap):
            identity = ledger.reserve(arm, payload)
            ledger.settle(
                identity, encoded({"usage": {"input_tokens": 10, "output_tokens": 1}}), 200
            )
        with pytest.raises(BudgetLimit, match="BENCHMARK_REQUEST_LIMIT"):
            ledger.reserve(arm, payload)
        ledgers[arm] = ledger.summary(arm)
    assert ledgers["resume"]["requests"] - 3 == ledgers["restart"]["requests"] == 21
    assert sum(item["requests"] for item in ledgers.values()) == 45


def test_recovery_claims_are_limited_to_frozen_eight_attempts(tmp_path):
    import cpa_lease_server as server

    config = tmp_path / "config.yaml"
    config.write_text("request-retry: 2\n")
    manager = server.LeaseManager(config, tmp_path / "state", reload_probe=lambda _: None)
    for task_id in ("3732", "3727"):
        for arm in ("resume", "restart"):
            for repeat in (1, 2):
                request = {
                    "action": "claim",
                    "campaign": audit.CAMPAIGN,
                    "phase": "full",
                    "run_id": "123",
                    "request_cap": 24,
                    "attempt_id": (
                        f"{audit.CAMPAIGN}/full/fmtlib__fmt-{task_id}/{arm}/repeat-{repeat}"
                    ),
                }
                result = manager.rpc(request)
    assert result["allocated_phase_requests"] == 192
    with pytest.raises(ValueError, match="CPA_ATTEMPT_ALREADY_CLAIMED"):
        manager.rpc({**request, "run_id": "124"})
    for suffix in (
        "/full/fmtlib__fmt-1361/resume/repeat-1",
        "/full/fmtlib__fmt-3732/resume/repeat-3",
        "/full/fmtlib__fmt-3732/baseline/repeat-1",
    ):
        with pytest.raises(ValueError, match="CPA_ATTEMPT_CLAIM_INVALID"):
            manager.rpc({**request, "attempt_id": audit.CAMPAIGN + suffix})
    with pytest.raises(ValueError, match="CPA_CAMPAIGN_ALLOCATION_REJECTED"):
        manager.rpc({**request, "phase": "smoke"})
    assert config.read_text() == "request-retry: 2\n"


def test_aggregate_retains_failed_and_missing_pairs_and_negative_savings():
    pairs = [
        {"pair_id": "p1", "instance_id": "t1"},
        {"pair_id": "p2", "instance_id": "t2"},
    ]
    result = live.summarize(
        {"pairs": pairs},
        [
            {
                **pairs[0],
                "status": "error",
                "metrics": {
                    "resume_post_failure_usage": {"input_tokens": 120},
                    "restart_post_failure_usage": {"input_tokens": 100},
                    "post_failure_input_saved_fraction": -0.2,
                },
                "attempt_usage": {"resume": {"requests": 5}, "restart": {"requests": 2}},
            }
        ],
    )
    assert result["expected_pairs"] == 2
    assert result["status_counts"] == {"error": 1, "missing": 1}
    assert result["actual_requests_observed"] == 7
    assert result["paired_input_cost"]["saved_fraction"] == -0.2
    assert result["cold_successes"] == {"resume": 0, "restart": 0}
    with pytest.raises(ValueError, match="DUPLICATE_OR_UNREGISTERED_PAIR"):
        live.summarize({"pairs": pairs}, [pairs[0], pairs[0]])


def test_recovery_workflow_shares_existing_queue_and_serializes_complete_pairs():
    import yaml

    main = yaml.load(
        (ROOT / ".github/workflows/formal-benchmark.yml").read_text(), Loader=yaml.BaseLoader
    )
    workflow = yaml.load(
        (ROOT / ".github/workflows/recovery-costs.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert "recovery-costs" in main["on"]["workflow_dispatch"]["inputs"]["cross_stage"]["options"]
    assert "inputs.cross_stage == 'recovery-costs'" in main["concurrency"]["group"]
    assert "context-ablation-cpa-8" in main["concurrency"]["group"]
    assert main["concurrency"]["cancel-in-progress"] == "false"
    assert main["jobs"]["recovery-costs"]["uses"] == "./.github/workflows/recovery-costs.yml"
    assert workflow["jobs"]["pair"]["strategy"]["max-parallel"] == "1"
    assert workflow["jobs"]["pair"]["strategy"]["fail-fast"] == "false"
    steps = workflow["jobs"]["pair"]["steps"]
    execute = next(step for step in steps if step.get("id") == "execute")
    assert "secrets.CPA_API_KEY" in execute["env"]["OPENAI_API_KEY"]
    archives = [step for step in steps if "actions/upload-artifact@" in step.get("uses", "")]
    assert len(archives) == 2
    assert all(
        step["if"] == "always()" and step["with"]["retention-days"] == "30" for step in archives
    )


@pytest.fixture
def paused(task, tmp_path):
    source = (ROOT / "examples/models/fix-negative-maximum.json").read_bytes()
    script_path = tmp_path / "script.json"
    script_path.write_bytes(source)
    harness = Harness(
        task,
        load_sdk_script(script_path),
        script_source=source,
        pause_after_step=3,
        sandbox_factory=SimulatedSandbox,
    )
    report = harness.run()
    assert report["state"] == "INTERRUPTED"
    directory = Path(report["artifact_directory"])
    snapshot = read_events(directory, directory.name)
    with sqlite3.connect(directory / "events.sqlite3") as db:
        db.row_factory = sqlite3.Row
        checkpoint = dict(db.execute("SELECT * FROM checkpoints WHERE step_id=3").fetchone())
    prefix = "worker/runs/" + directory.name
    members = {
        prefix + "/" + str(path.relative_to(directory)): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }
    return members, prefix, snapshot.run, checkpoint, snapshot.events


@pytest.mark.sdk
@pytest.mark.parametrize("defect", ["none", "manifest_hash", "truncated_payload"])
def test_prefix_audit_detects_checkpoint_and_payload_corruption(paused, defect):
    members, prefix, run, checkpoint, events = paused
    ref = json.loads(checkpoint["manifest_ref_json"])
    name = prefix + "/" + ref["path"]
    if defect == "manifest_hash":
        members[name] += b" "
        with pytest.raises(ValueError, match="CHECKPOINT_MANIFEST_HASH_MISMATCH"):
            audit.prefix_record(members, prefix, run, checkpoint, events, [], 3)
        return
    if defect == "truncated_payload":
        manifest = json.loads(members[name])
        name = prefix + "/" + manifest["native_next_input"]["path"]
        members[name] = members[name][:-1]
    result = audit.prefix_record(members, prefix, run, checkpoint, events, [], 3)
    assert result["step_id"] == 3
    assert result["input_source_payloads_complete"] is (defect == "none")


@pytest.mark.sdk
def test_production_resume_uses_same_metered_ledger_and_preserves_budget(
    task, tmp_path, monkeypatch
):
    import httpx2
    import run_benchmark_agent as worker

    import repropatch.harness as harness_module
    import repropatch.recovery as recovery

    raw = task.to_dict()
    raw["budget"].update(max_steps=24, max_tool_calls=48, max_output_tokens=8192)
    task_path = tmp_path / "task.yaml"
    task_path.write_bytes(Task.from_dict(raw, tmp_path).source_bytes)
    outputs = json.loads((ROOT / "examples/models/fix-negative-maximum.json").read_bytes())["steps"]
    received = []

    def serve(request):
        received.append(json.loads(request.content))
        index = len(received) - 1
        return httpx2.Response(
            200,
            json={
                "id": "response-" + str(index),
                "object": "response",
                "created_at": 1,
                "model": "gpt-6-luna",
                "status": "completed",
                "output": outputs[index]["output"],
                "usage": {
                    "input_tokens": 1000 + 100 * index,
                    "output_tokens": 100,
                    "total_tokens": 1100 + 100 * index,
                    "input_tokens_details": {"cached_tokens": 100},
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
            },
        )

    client = worker.responses_client
    monkeypatch.setattr(
        worker,
        "responses_client",
        lambda args, hooks: client(args, hooks, transport=httpx2.MockTransport(serve)),
    )
    meters = []

    def simulated(*args, **kwargs):
        kwargs["sandbox_factory"] = SimulatedSandbox
        meters.append(kwargs.get("context_meter"))
        return Harness(*args, **kwargs)

    original_resume = recovery.resume_run
    monkeypatch.setattr(harness_module, "Harness", simulated)
    monkeypatch.setattr(
        recovery,
        "resume_run",
        lambda path, **kwargs: original_resume(path, sandbox_factory=SimulatedSandbox, **kwargs),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-only")
    ledger_path = tmp_path / "usage.sqlite3"
    from context_ablation import context_policy

    policy = context_policy(
        live.load(ROOT / "benchmarks/context-ablation/protocol.json"), "baseline"
    )
    LocalUsageLedger.create_scoped(ledger_path, {"offline-pair": 24}, context_policy=policy)
    args = SimpleNamespace(
        stage="prefix",
        task=task_path,
        ledger=ledger_path,
        attempt="offline-pair",
        output=tmp_path / "output",
    )
    live.stage(args)
    prefix = live.load(args.output / "prefix.json")
    assert len(received) == prefix["usage"]["requests"] == 3
    frozen = copy.deepcopy(prefix)
    args.stage = "resume"
    live.stage(args)
    result = live.load(args.output / "result.json")
    assert len(received) == result["usage"]["requests"] == 5
    assert result["usage"]["input_tokens"] == 6000
    assert result["run_state"]["steps_used"] == 5
    assert all(result["recovery_checks"].values())
    assert all(meter is not None and meter.ledger.path == ledger_path for meter in meters)
    assert meters[0] is not meters[-1]
    assert result["measurement"]["restore_ready_seconds"] is not None
    assert result["measurement"]["first_model_admission_seconds"] is not None
    assert live.subtract_usage(result["usage"], frozen["usage"])["input_tokens"] == 2700
    assert live.load(args.output / "prefix.json") == frozen
    checkpoint, _ = read_checkpoint(Path(result["native_artifact_dir"]))
    assert checkpoint["deadline_at"] == frozen["checkpoint"]["deadline_at"]
