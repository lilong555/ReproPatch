"""三臂原生对照的任务身份、开放请求账本与执行参数。"""

import copy
import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest
import yaml

from repropatch.context import admission_reason

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
campaign = importlib.import_module("cross_repo_campaign")
freeze = importlib.import_module("freeze_semantic_native")
formal = importlib.import_module("formal_benchmark")
analysis = importlib.import_module("analyze_cross_repo")


@pytest.fixture
def native_protocol(monkeypatch):
    sources = sorted((freeze.ROOT / "benchmarks/cross-repo").glob("formal-protocol-batch-*.json"))
    value = freeze.build_protocol(sources)
    value.update(
        status="FROZEN",
        execution_source_commit="a" * 40,
        execution_sha256="b" * 64,
        ci_run_id=123,
    )
    monkeypatch.setattr(campaign, "execution_fingerprint", lambda: "b" * 64)
    return value


def test_eight_tasks_reuse_identity_and_keep_native_executor_configuration(native_protocol):
    campaign.validate_protocol(native_protocol)
    assert native_protocol["tasks"] == freeze.TASKS
    assert len(native_protocol["attempts"]) == 24
    assert native_protocol["formal_request_cap"] is None
    assert native_protocol["batch_id"] == "semantic-state-native-20261101/r1"
    assert all(
        row["attempt_id"].startswith("semantic-state-native-20261101/r1/")
        for row in native_protocol["attempts"]
    )
    assert len({task.rsplit("-", 1)[0] for task in native_protocol["tasks"]}) == 7
    for task in native_protocol["tasks"]:
        source = next(
            json.loads(path.read_text())
            for path in (freeze.ROOT / "benchmarks/cross-repo").glob("formal-protocol-batch-*.json")
            if task in json.loads(path.read_text())["tasks"]
        )
        assert (
            native_protocol["qualification_contracts"][task]
            == source["qualification_contracts"][task]
        )
        assert campaign.task_environment(native_protocol, task) == campaign.task_environment(
            source, task
        )
        assert len(native_protocol["historical_reference"]["tasks"][task]["attempts"]) == 3
    assert campaign.arm_context_policy(native_protocol, "full").compaction_enabled
    assert not campaign.arm_context_policy(native_protocol, "mini").compaction_enabled
    assert not campaign.arm_context_policy(native_protocol, "codex").compaction_enabled
    assert all(row["request_cap"] is None for row in native_protocol["attempts"])


def test_native_transport_is_physical_high_water_without_local_token_admission(native_protocol):
    measurement = {
        "transport_bytes": 3 * 1024 * 1024,
        "estimated_input_tokens": 200_000,
        "opaque_attribution_unknown": True,
        "body_complete": True,
    }
    for arm in campaign.NATIVE_ARMS:
        policy = campaign.arm_context_policy(native_protocol, arm)
        assert policy.request_cap is None
        assert policy.transport_max_bytes == 64 * 1024 * 1024
        if arm in {"mini", "codex"}:
            assert admission_reason(policy, measurement) is None
            assert (
                admission_reason(
                    policy, {**measurement, "transport_bytes": policy.transport_max_bytes + 1}
                )
                == "LOCAL_TRANSPORT_LIMIT"
            )
    native_protocol["context_policy"]["transport_max_bytes"] = 2 * 1024 * 1024
    with pytest.raises(ValueError, match="CONTEXT_POLICY"):
        campaign.validate_protocol(native_protocol)


def test_attempt_namespace_matches_remote_campaign_contract(native_protocol):
    native_protocol["batch_id"] = "semantic-state-native-20261101-r1"
    for row in native_protocol["attempts"]:
        row["attempt_id"] = f"{native_protocol['batch_id']}/{row['instance_id']}/{row['arm']}/first"
    native_protocol["execution_order"] = copy.deepcopy(native_protocol["attempts"])
    with pytest.raises(ValueError, match="ATTEMPT_REGISTRY"):
        campaign.validate_protocol(native_protocol)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("status", "DRAFT", "FRAMEWORK"),
        ("request_cap_per_attempt", 24, "BUDGET"),
        ("formal_request_cap", 576, "BUDGET"),
        ("max_tool_calls", 48, "BUDGET"),
        ("max_parallel", 4, "BUDGET"),
        ("cpa_max_concurrent_requests", 4, "BUDGET"),
        ("execution_source_commit", None, "SOURCE"),
    ],
)
def test_native_protocol_refuses_ambiguous_or_limited_configuration(
    native_protocol, field, value, error
):
    native_protocol[field] = value
    with pytest.raises(ValueError, match=error):
        campaign.validate_protocol(native_protocol)


def test_native_protocol_retains_one_attempt_per_task_and_arm(native_protocol):
    native_protocol["attempts"][-1] = copy.deepcopy(native_protocol["attempts"][0])
    with pytest.raises(ValueError, match="ATTEMPT_REGISTRY"):
        campaign.validate_protocol(native_protocol)


def test_protocol_loader_accepts_real_null_budget_and_preserves_order(
    native_protocol, tmp_path, monkeypatch
):
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(native_protocol))
    monkeypatch.setattr(formal, "PROTOCOL", path)
    value = formal.protocol()
    matrix = formal.execution_matrix(value)
    assert len(matrix) == 24
    assert [(row["instance"], row["arm"]) for row in matrix] == [
        (row["instance_id"], row["arm"]) for row in value["attempts"]
    ]


@pytest.mark.parametrize("arm", ["full", "mini", "codex"])
def test_worker_uses_semantic_full_or_native_compaction_with_unlimited_ledger(
    native_protocol, monkeypatch, tmp_path, arm
):
    monkeypatch.setattr(formal, "protocol", lambda: native_protocol)
    monkeypatch.setattr(formal, "ATTEMPT_ID", None)
    output = tmp_path / "run"
    output.mkdir()
    (output / "prepared.json").write_text(
        json.dumps(
            {
                "task": "task.yaml",
                "qualification": "result.json",
                "common_input": "common-input.json",
                "mini_source": "mini-source",
                "agent_seconds": 10800,
            }
        )
    )
    commands = []

    def run(command, log):
        commands.append(command)
        if command[1] == "scripts/score_benchmark_attempt.py":
            target = Path(command[command.index("--output") + 1])
            target.mkdir()
            (target / "score.json").write_text(
                json.dumps({"status": "EMPTY_CANDIDATE", "accepted": False})
            )
        return 0

    monkeypatch.setattr(formal, "run", run)
    monkeypatch.setattr(formal.subprocess, "run", lambda *args, **kwargs: None)
    formal.execute(freeze.TASKS[0], output, arm)
    worker = commands[0]
    assert ("--semantic-state" in worker) is (arm == "full")
    assert ("--native-context" in worker) is (arm in {"mini", "codex"})
    ledger = formal.LocalUsageLedger(output / "ledgers" / (arm + ".sqlite3"))
    summary = json.loads((output / "summary.json").read_text())
    attempt = summary["attempts"][0]
    assert ledger.request_cap(attempt["attempt_id"]) is None
    assert ledger.policy.compaction_enabled is (arm == "full")
    assert attempt["executor_policy"] == native_protocol["executor_policies"][arm]
    assert attempt["usage"]["requests"] == 0


def test_native_analysis_compares_only_registered_three_arms(native_protocol):
    value = {
        "primary_pairs": native_protocol["primary_pairs"],
        "attempts": [
            {"instance_id": "repo__sample-1", "arm": arm, "score": {"accepted": arm == "full"}}
            for arm in native_protocol["arms"]
        ],
    }
    result = analysis.analyze(value)
    pairs = {(row["left"], row["right"]) for row in result["primary_comparisons"]}
    assert pairs == {("full", "mini"), ("full", "codex"), ("mini", "codex")}
    assert all(row["complete_pairs"] == 1 for row in result["primary_comparisons"])


def test_workflow_keeps_global_three_worker_group_and_explicit_native_stage():
    entry = yaml.safe_load((freeze.ROOT / ".github/workflows/formal-benchmark.yml").read_text())
    child = yaml.safe_load((freeze.ROOT / ".github/workflows/cross-repository.yml").read_text())
    assert "cross-cpa-model-3" in entry["concurrency"]["group"]
    assert entry["concurrency"]["cancel-in-progress"] is False
    assert child["jobs"]["paid-attempt"]["strategy"]["fail-fast"] is False
    assert child["jobs"]["paid-attempt"]["strategy"]["max-parallel"] == (
        "${{ fromJSON(needs.paid-plan.outputs.parallel) }}"
    )
    assert "native-trend" in child["jobs"]["paid-plan"]["if"]


def test_semantic_metrics_use_cumulative_counter_and_current_index(tmp_path):
    worker = {
        "semantic_state": True,
        "context": {
            "semantic_state": {
                "version": "cpp-evidence-state-v1",
                "queries_total": 300,
                "query_kinds": {"definitions": 200, "references": 100},
                "parse_count": 9,
                "cache_hits": 2,
                "indexed_bytes_total": 5120,
                "index_seconds_total": 0.4,
                "parse_seconds_total": 0.3,
                "sequence": 400,
                "observations": [
                    {"sequence": index, "tool": "query_code" if index > 390 else "read_file"}
                    for index in range(273, 401)
                ],
                "files": {
                    "src/a.cpp": {"parse_has_error": False},
                    "src/b.cpp": {"parse_has_error": True},
                },
                "changes": {"src/a.cpp": {"path": "src/a.cpp"}},
            }
        },
    }
    result = formal.attempt_metrics(worker, {}, {"accepted": False}, tmp_path)["metrics"][
        "semantic_state"
    ]
    assert result["enabled"] is True
    assert result["state_schema"] == "cpp-evidence-state-v1"
    assert result["counter_schema"] == "cpp-evidence-state-v1"
    assert result["query_code_calls"] == 300
    assert result["queries_total"] == 300
    assert result["query_kinds"] == {"definitions": 200, "references": 100}
    assert result["parse_count"] == 9
    assert result["cache_hits"] == 2
    assert result["indexed_bytes_total"] == 5120
    assert result["index_seconds_total"] == 0.4
    assert result["parse_seconds_total"] == 0.3
    assert result["query_code_calls_basis"] == "cumulative_query_invocations"
    assert result["observed_query_code_calls"] == 10
    assert result["observation_window_size"] == 128
    assert result["indexed_files"] == 2
    assert result["parse_error_files"] == 1
    assert result["state_sequence"] == 400
    assert result["changed_files"] == 1


def test_semantic_metrics_keep_truncated_history_counts_unknown():
    state = {
        "version": "cpp-evidence-state-v1",
        "sequence": 400,
        "observations": [{"sequence": 400, "tool": "query_code"}],
        "files": {"src/a.cpp": {}},
    }
    result = formal.semantic_metrics({"context": {"semantic_state": state}})
    assert result["enabled"] is True
    assert result["query_code_calls"] is None
    assert result["queries_total"] is None
    assert result["observed_query_code_calls"] == 1
    assert result["parse_error_files"] is None
    assert result["changed_files"] is None
    state["sequence"] = 1
    state["observations"][0]["sequence"] = 1
    result = formal.semantic_metrics({"context": {"semantic_state": state}})
    assert result["query_code_calls"] == 1
    assert result["query_code_calls_basis"] == "complete_observation_sequence"


def test_semantic_metrics_keep_missing_state_and_disabled_state_distinct():
    missing = formal.semantic_metrics({})
    disabled = formal.semantic_metrics({"semantic_state": False})
    assert missing["enabled"] is None
    assert disabled["enabled"] is False
    for field in (
        "state_schema",
        "query_code_calls",
        "indexed_files",
        "parse_error_files",
        "state_sequence",
        "changed_files",
    ):
        assert missing[field] is None
        assert disabled[field] is None


@pytest.fixture
def execution_evidence(native_protocol):
    ci = {
        "conclusion": "success",
        "head_sha": native_protocol["execution_source_commit"],
        "name": "CI",
    }
    calibration = json.dumps(
        {
            "schema": "repropatch.cross-network-calibration.v1",
            "status": "PASSED",
            "model": "gpt-6-luna",
            "reasoning_effort": "max",
            "model_timeout_seconds": 180,
            "usage": {"issued_requests": 12},
        }
    ).encode()
    native_protocol["network_calibration"]["sha256"] = hashlib.sha256(calibration).hexdigest()
    return native_protocol, ci, calibration


def test_native_paid_gate_uses_exact_ci_and_calibration_identity(execution_evidence):
    protocol, ci, calibration = execution_evidence
    campaign.validate_execution_evidence(protocol, ci, calibration)
    assert protocol["formal_request_cap"] is None
    assert all(row["request_cap"] is None for row in protocol["attempts"])
    with pytest.raises(ValueError, match="CALIBRATION_IDENTITY"):
        campaign.validate_execution_evidence(protocol, ci, calibration + b"\n")


@pytest.mark.parametrize(
    ("field", "value"),
    [("conclusion", "failure"), ("head_sha", "c" * 40), ("name", "Other workflow")],
)
def test_native_paid_gate_rejects_other_source_ci(execution_evidence, field, value):
    protocol, ci, calibration = execution_evidence
    ci[field] = value
    with pytest.raises(ValueError, match="CI_SOURCE_IDENTITY"):
        campaign.validate_execution_evidence(protocol, ci, calibration)


def test_native_paid_gate_checks_calibration_parameters_after_hash(execution_evidence):
    protocol, ci, calibration = execution_evidence
    value = json.loads(calibration)
    value["reasoning_effort"] = "medium"
    changed = json.dumps(value).encode()
    protocol["network_calibration"]["sha256"] = hashlib.sha256(changed).hexdigest()
    with pytest.raises(ValueError, match="CALIBRATION_REQUIRED"):
        campaign.validate_execution_evidence(protocol, ci, changed)
