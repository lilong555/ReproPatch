"""只读诊断的终态、证据健康和恢复前置条件。"""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import ROOT, SimulatedSandbox, created_payload
from test_checkpoints import contract_checkpoint
from test_events_reports import completed as completed
from test_recovery import repairing

from repropatch.artifacts import EvidenceRef
from repropatch.diagnostics import diagnose_run, diagnostics_markdown
from repropatch.errors import InfrastructureError, StateReadError
from repropatch.events import EventLog, encode_json, read_events
from repropatch.harness import Harness


def file_bytes(directory):
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


def observe(directory, monkeypatch):
    from repropatch.sandbox import DockerSandbox
    from repropatch.tools import Toolbox

    def forbidden(*args, **kwargs):
        pytest.fail("只读诊断触发了执行、写入或可选模型依赖")

    before = file_bytes(directory)
    connect = sqlite3.connect

    def readonly_connect(database, *args, **kwargs):
        assert kwargs.get("uri") and str(database).endswith("?mode=ro")
        return connect(database, *args, **kwargs)

    with monkeypatch.context() as guard:
        for name in ("agents", "openai", "repropatch.models", "repropatch.agent_runtime"):
            guard.setitem(sys.modules, name, None)
        guard.setattr(Harness, "run", forbidden)
        guard.setattr(DockerSandbox, "__enter__", forbidden)
        guard.setattr(Toolbox, "run_command", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(sqlite3, "connect", readonly_connect)
        guard.setattr(EventLog, "open_existing", forbidden)
        guard.setattr(EvidenceRef, "save", forbidden)
        guard.setattr("repropatch.artifacts.private_write", forbidden)
        guard.setattr("repropatch.recovery.resume_run", forbidden)
        guard.setattr("repropatch.reports.export_report", forbidden)
        result = diagnose_run(directory)
        markdown = diagnostics_markdown(result)
        assert json.loads(json.dumps(result)) == result
        assert file_bytes(directory) == before
    assert result["schema"] == "repropatch.diagnosis.v1"
    assert isinstance(result["evidence_complete"], bool)
    assert isinstance(result["evidence_errors"], list)
    return result, markdown


def test_success_uses_committed_facts_and_preserves_every_byte(completed, monkeypatch):
    directory, report = completed
    result, markdown = observe(directory, monkeypatch)
    assert result["state"] == "FINISHED" and result["outcome"] == "ACCEPTED"
    assert result["reason_code"] == "VERIFICATION_PASSED"
    assert result["failure_stage"] is None
    assert result["evidence_complete"] and not result["evidence_errors"]
    assert result["agent"]["steps_used"] == result["agent"]["tool_calls_used"] == 0
    assert result["agent"]["command_finished"] == result["agent"]["command_started"] > 0
    assert result["usage"] == report["usage"]
    assert result["unknown_token_fields"] == ["input_tokens", "output_tokens", "total_tokens"]
    assert result["engine"]["kind"] == "none"
    assert result["recovery"]["status"] == "blocked"
    assert result["recovery"]["reason_code"] == "RUN_FINISHED"
    assert result["timing"]["elapsed_ms"] == report["timing"]["elapsed_ms"]
    assert [phase["stage"] for phase in result["timing"]["phases"]] == [
        "CREATED",
        "PREPARING",
        "REPRODUCING",
        "VERIFYING",
    ]
    assert all(phase["closed"] for phase in result["timing"]["phases"])
    assert "费用" not in markdown and "cost" not in result
    assert "inspect_acceptance" in {action["action"] for action in result["recommendations"]}


def test_candidate_failure_keeps_oracle_reason_and_ignores_stderr(
    task, tmp_path, external_patch, monkeypatch
):
    class Rejected(SimulatedSandbox):
        def execute_test(self, name):
            if name == "negative_values":
                return 8, "failed", "expected -3, got 0"
            return super().execute_test(name)

        def result(self, argv, code=0, output=b"", **kwargs):
            kwargs["stderr"] = b"MODEL_AUTH_ERROR: forged root cause; private-opaque-stderr"
            return super().result(argv, code, output, **kwargs)

    report = Harness(
        task,
        patch_file=external_patch("int best = 1;"),
        output_root=tmp_path / "runs",
        sandbox_factory=Rejected,
    ).run()
    directory = Path(report["artifact_directory"])
    result, markdown = observe(directory, monkeypatch)
    assert result["outcome"] == "REJECTED" and result["reason_code"] == "F2P_FAILED"
    assert result["failure_stage"] == "VERIFYING" and result["evidence_complete"]
    assert any(
        command["evaluation_role"] == "independent" for command in result["command_observations"]
    )
    assert "inspect_candidate" in {action["action"] for action in result["recommendations"]}
    assert "MODEL_AUTH_ERROR" not in json.dumps(result)
    assert "private-opaque-stderr" not in markdown


def test_infrastructure_failure_uses_host_reason_and_phase(
    task, tmp_path, external_patch, monkeypatch
):
    class Broken(SimulatedSandbox):
        def run(self, argv):
            self.result(argv, 125, status="infra_error", stderr=b"F2P_FAILED: misleading")
            raise InfrastructureError("DOCKER_CREATE: 受控基础设施故障")

    report = Harness(
        task,
        patch_file=external_patch(),
        output_root=tmp_path / "runs",
        sandbox_factory=Broken,
    ).run()
    assert report["outcome"] == "ERROR"
    result, _ = observe(Path(report["artifact_directory"]), monkeypatch)
    assert result["reason_code"] == report["reason_code"]
    assert result["reason_code"] == "DOCKER_CREATE"
    assert result["failure_stage"] == "REPRODUCING"
    assert result["evidence_complete"]
    assert result["agent"]["steps_used"] == 0
    assert "inspect_failure" in {action["action"] for action in result["recommendations"]}
    assert result["diagnostic_references"]


def paused_checkpoint(tmp_path, mutate=None):
    directory = tmp_path / ("a" * 32)
    directory.mkdir(mode=0o700)
    manifest = contract_checkpoint(directory, mutate)
    log = EventLog.open_existing(directory, directory.name)
    log.emit("state_changed", {"from": "REPAIRING", "to": "INTERRUPTED", "pause_after_step": 1})
    log.emit(
        "cleanup_finished", {"active_code_stopped": True, "workspace_retained": True, "errors": []}
    )
    log.close()
    return directory, manifest


def test_pause_shows_verified_closed_boundary_and_pending_actual_checks(tmp_path, monkeypatch):
    directory, manifest = paused_checkpoint(tmp_path)
    orphan = directory / "checkpoints/999"
    orphan.mkdir(mode=0o700)
    (orphan / "manifest.json").write_text('{"checkpoint_id":999}')
    result, markdown = observe(directory, monkeypatch)
    recovery = result["recovery"]
    assert result["state"] == "INTERRUPTED" and result["outcome"] is None
    assert result["reason_code"] is None and result["failure_stage"] is None
    assert result["evidence_complete"]
    assert recovery["status"] == "checks_required" and recovery["reason_code"] is None
    assert recovery["checkpoint"]["checkpoint_id"] == 1
    assert recovery["checkpoint"]["verified"] and recovery["checkpoint"]["closed"]
    assert recovery["checkpoint"]["source_tree_sha256"] == manifest["source_tree_sha256"]
    assert recovery["checkpoint"]["input_fingerprints"] == manifest["input_fingerprints"]
    assert recovery["source_status"] == "resume_check_required"
    assert not recovery["resources"]["registry_present"]
    assert recovery["resources"]["cleanup"]["active_code_stopped"]
    assert result["agent"]["steps_used"] == result["agent"]["model_started"] == 1
    assert result["agent"]["model_finished"] == 0
    assert result["budget"]["remaining_steps"] == 1
    assert result["budget"]["remaining_tool_calls"] == 2
    assert result["budget"]["deadline_at"] == manifest["deadline_at"]
    assert any("SDK" in item["check"] for item in recovery["resume_checks"])
    assert any(
        "source" in item["api"].lower() or "manifest" in item["api"]
        for item in recovery["resume_checks"]
    )
    assert "restore_resources" in {action["action"] for action in result["recommendations"]}
    assert "实际 resume" in markdown


@pytest.mark.parametrize(
    "boundary, expected",
    [
        ("request", "MODEL_RESULT_UNKNOWN"),
        ("result", "OPEN_AGENT_SEGMENT"),
    ],
)
def test_open_segment_keeps_checkpoint_historical_and_never_suggests_replay(
    tmp_path, monkeypatch, boundary, expected
):
    directory = tmp_path / ("a" * 32)
    directory.mkdir(mode=0o700)
    contract_checkpoint(directory)
    log = EventLog.open_existing(directory, directory.name)
    usage = {
        "input_tokens": None,
        "output_tokens": 4,
        "total_tokens": None,
        "synthetic": True,
        "unknown_turns": 1,
        "known_tokens": {"input_tokens": 0, "output_tokens": 4, "total_tokens": 4},
    }
    log.emit(
        "model_started",
        {
            "native_input": {
                "path": "native-input.json",
                "sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
                "size_bytes": 2,
            },
            "steps_used": 2,
            "usage": usage,
        },
        step_id=2,
    )
    if boundary == "result":
        log.emit("model_finished", {"cumulative_usage": usage}, step_id=2)
    log.emit(
        "tool_batch_admitted",
        {"calls": [{"name": "read_file", "tool_call_id": "s000002.t01"}], "tool_calls_used": 1},
        step_id=2,
    )
    log.emit("tool_started", {"name": "read_file"}, step_id=2, tool_call_id="s000002.t01")
    log.close()
    result, _ = observe(directory, monkeypatch)
    assert result["evidence_complete"] and result["outcome"] is None
    assert result["recovery"]["reason_code"] == expected
    assert result["recovery"]["checkpoint"]["verified"]
    assert not result["recovery"]["checkpoint"]["closed"]
    assert result["agent"]["steps_used"] == 2
    assert result["agent"]["tool_calls_used"] == result["agent"]["tool_started"] == 1
    assert result["agent"]["tool_finished"] == 0
    assert result["unknown_token_fields"] == ["input_tokens", "total_tokens"]
    assert result["unknown_usage_turns"] == 1
    assert result["usage"]["known_tokens"]["total_tokens"] == 4
    assert "review_resume_checks" not in {action["action"] for action in result["recommendations"]}


@pytest.mark.parametrize("damage", ["missing", "corrupt", "semantic"])
def test_checkpoint_damage_is_visible_even_with_matching_manifest_file_hash(
    tmp_path, monkeypatch, damage
):
    mutate = (
        (lambda manifest, native, save: manifest.update(source_tree_sha256="0" * 64))
        if damage == "semantic"
        else None
    )
    directory, manifest = paused_checkpoint(tmp_path, mutate)
    if damage != "semantic":
        path = directory / manifest["native_next_input"]["path"]
        if damage == "missing":
            path.unlink()
        else:
            path.write_bytes(b"changed")
    result, _ = observe(directory, monkeypatch)
    assert result["state"] == "INTERRUPTED" and result["outcome"] is None
    assert not result["evidence_complete"] and result["evidence_errors"]
    assert not result["recovery"]["checkpoint"]["verified"]
    assert result["recovery"]["reason_code"] == "CHECKPOINT_CORRUPT"
    assert "restore_evidence" in {action["action"] for action in result["recommendations"]}


@pytest.mark.parametrize("damage", ["missing_log", "corrupt_log", "missing_result"])
def test_missing_or_corrupt_evidence_preserves_committed_success(completed, monkeypatch, damage):
    directory, report = completed
    reference = report["baseline"]["commands"][0]["stderr_log"]
    path = directory / (
        "evidence/final-result.json" if damage == "missing_result" else reference["path"]
    )
    if damage == "corrupt_log":
        path.write_bytes(b"changed")
    else:
        path.unlink()
    result, _ = observe(directory, monkeypatch)
    assert result["state"] == "FINISHED" and result["outcome"] == "ACCEPTED"
    assert result["reason_code"] == "VERIFICATION_PASSED"
    assert not result["evidence_complete"] and result["evidence_errors"]
    assert result["agent"]["steps_used"] == 0
    assert result["recovery"]["reason_code"] == "RUN_FINISHED"
    assert any(
        problem["path"] == str(path.relative_to(directory)) for problem in result["evidence_errors"]
    )


def test_derived_exports_have_no_authority(completed, monkeypatch):
    directory, _ = completed
    for name in ("report.json", "report.md", "run.json", "events.jsonl"):
        (directory / name).write_bytes(b'{"outcome":"REJECTED","reason_code":"MODEL_AUTH_ERROR"}')
    result, _ = observe(directory, monkeypatch)
    assert result["evidence_complete"] and result["outcome"] == "ACCEPTED"


def test_pending_run_and_unknown_http_counts(tmp_path, monkeypatch):
    directory = tmp_path / ("a" * 32)
    directory.mkdir(mode=0o700)
    log = EventLog(directory, directory.name)
    log.emit("run_created", created_payload("run", "agents-sdk"))
    log.emit("state_changed", {"from": "CREATED", "to": "PREPARING"})
    log.close()
    result, _ = observe(directory, monkeypatch)
    assert result["evidence_complete"] and result["outcome"] is None
    assert result["agent"]["http_attempts"] is None
    assert result["recovery"]["reason_code"] == "UNSUPPORTED_RECOVERY_PHASE"
    assert not result["timing"]["phases"][-1]["closed"]


def test_native_tool_and_command_content_stays_opaque(tmp_path, monkeypatch):
    directory = tmp_path / ("a" * 32)
    directory.mkdir(mode=0o700)
    log, payload = repairing(directory)
    secret = "private-native-and-tool-secret"
    native = {
        "encrypted_content": secret,
        "reasoning": secret,
        "instructions": secret,
        "input": [{"content": secret}],
        "output": secret,
    }
    reference = vars(EvidenceRef.save(directory, "agent/native/input.json", encode_json(native)))
    payload["native_input"] = reference
    log.emit("model_started", payload, step_id=1)
    log.emit(
        "model_finished",
        {
            "cumulative_usage": payload["usage"],
            "native_response": reference,
            "reasoning": secret,
            "output": secret,
        },
        step_id=1,
    )
    log.emit(
        "tool_batch_admitted",
        {
            "calls": [{"name": "read_file", "arguments": secret}],
            "tool_calls_used": 1,
        },
        step_id=1,
    )
    tool_ref = vars(
        EvidenceRef.save(
            directory,
            "agent/tool-results/private.json",
            encode_json({"text": secret}),
        )
    )
    log.emit(
        "tool_started",
        {"name": "read_file", "arguments": secret},
        step_id=1,
        tool_call_id="s000001.t01",
    )
    log.emit(
        "tool_finished",
        {"name": "read_file", "result_ref": tool_ref},
        step_id=1,
        tool_call_id="s000001.t01",
    )
    command_id = "c" * 32
    command = {
        "command_id": command_id,
        "status": "exited",
        "returncode": 1,
        "argv": ["/bin/bash", "-lc", secret],
        "stdout": secret,
        "stderr": secret,
    }
    command_ref = vars(
        EvidenceRef.save(
            directory,
            f"evidence/{command_id}.result.json",
            encode_json(command),
        )
    )
    log.emit("command_finished", {"result_ref": command_ref}, operation_id=command_id)
    log.close()
    result, markdown = observe(directory, monkeypatch)
    assert result["evidence_complete"]
    assert result["recovery"]["reason_code"] == "OPEN_AGENT_SEGMENT"
    assert result["agent"]["tool_started"] == result["agent"]["tool_finished"] == 1
    assert result["command_observations"][0]["command_id"] == command_id
    assert secret not in json.dumps(result) and secret not in markdown


def test_pause_keeps_original_deadline_and_verification_cleanup_reserve(tmp_path, monkeypatch):
    directory, _ = paused_checkpoint(tmp_path)
    result, _ = observe(directory, monkeypatch)
    budget = result["budget"]
    assert 9.9 < budget["wall_remaining_seconds"] - budget["verification_remaining_seconds"] < 10.1
    assert budget["agent_remaining_seconds"] is None
    original_restore = __import__("repropatch.diagnostics", fromlist=["RunClock"]).RunClock.restore

    def expired(*args):
        clock = original_restore(*args)
        clock.started -= clock.remaining("independent") + 1
        return clock

    monkeypatch.setattr("repropatch.diagnostics.RunClock.restore", expired)
    result, _ = observe(directory, monkeypatch)
    assert result["budget"]["verification_remaining_seconds"] < 0
    assert result["outcome"] is None and result["evidence_complete"]
    assert "review_remaining_budget" in {item["action"] for item in result["recommendations"]}


def test_resources_use_latest_committed_container_observation(tmp_path, monkeypatch):
    directory, _ = paused_checkpoint(tmp_path)
    log = EventLog.open_existing(directory, directory.name)
    for confirmed in (False, True):
        log.emit(
            "resource_registered",
            {
                "resource_type": "container",
                "name": "repropatch-" + "b" * 32,
                "container_id": "container-id",
                "run_id": directory.name,
                "purpose": "repair",
                "cleanup_confirmed": confirmed,
                "cleanup_error": None,
            },
        )
    log.close()
    (directory / "resources.json").write_text('{"containers":[{"name":"uncommitted"}]}')
    result, _ = observe(directory, monkeypatch)
    resources = result["recovery"]["resources"]
    assert resources["registry_present"]
    assert len(resources["containers"]) == 1
    assert resources["containers"][0]["cleanup_confirmed"]
    assert "uncommitted" not in json.dumps(result)
    assert result["recovery"]["status"] == "checks_required"


@pytest.mark.parametrize(
    "outcome,reason",
    [
        ("BUDGET_EXHAUSTED", "STEP_BUDGET"),
        ("CANCELLED", "USER_CANCELLED"),
    ],
)
def test_terminal_semantics_take_priority_over_closed_checkpoint(
    tmp_path, monkeypatch, outcome, reason
):
    directory = tmp_path / ("a" * 32)
    directory.mkdir(mode=0o700)
    contract_checkpoint(directory)
    log = EventLog.open_existing(directory, directory.name)
    row = log.state
    body = {
        "run_id": directory.name,
        "task_id": "fixture",
        "input_mode": "run",
        "state": "FINISHED",
        "outcome": outcome,
        "reason_code": reason,
        "agent": {
            "steps_used": row["steps_used"],
            "tool_calls_used": 0,
            "agent_stop_reason": reason,
        },
        "usage": json.loads(row["usage_json"]),
        "timing": {"deadline_at": row["deadline_at"]},
        "events_last_seq": log.sequence + 1,
    }
    reference = vars(EvidenceRef.save(directory, "evidence/final-result.json", encode_json(body)))
    log.emit(
        "state_changed",
        {
            "from": "REPAIRING",
            "to": "FINISHED",
            "outcome": outcome,
            "reason_code": reason,
            "result_ref": reference,
            "agent_stop_reason": reason,
        },
    )
    log.close()
    assert read_events(directory, directory.name).run["segment_open"] == 0
    result, _ = observe(directory, monkeypatch)
    assert result["outcome"] == outcome and result["reason_code"] == reason
    assert result["failure_stage"] == "REPAIRING" and result["evidence_complete"]
    assert result["recovery"]["checkpoint"]["verified"]
    assert result["recovery"]["reason_code"] == "RUN_FINISHED"
    assert "review_resume_checks" not in {item["action"] for item in result["recommendations"]}


@pytest.mark.parametrize("damage", ["missing", "corrupt", "state"])
def test_database_read_failure_preserves_files_and_does_not_fall_back(tmp_path, damage):
    directory = tmp_path / ("a" * 32)
    directory.mkdir(mode=0o700)
    log, _ = repairing(directory)
    log.close()
    database = directory / "events.sqlite3"
    if damage == "missing":
        database.unlink()
    elif damage == "corrupt":
        database.write_bytes(b"corrupt sqlite")
    else:
        with sqlite3.connect(database) as db:
            db.execute("UPDATE runs SET steps_used=1")
    (directory / "report.json").write_bytes(b'{"outcome":"ACCEPTED"}')
    before = file_bytes(directory)
    with pytest.raises(StateReadError, match="STATE_CORRUPT"):
        diagnose_run(directory)
    assert file_bytes(directory) == before


def test_core_process_diagnoses_without_loading_agents_sdk(completed):
    directory, _ = completed
    before = file_bytes(directory)
    script = """
import importlib.abc,json,sys
from pathlib import Path
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        optional = {'repropatch.models','repropatch.agent_runtime'}
        if fullname.split('.')[0] in {'agents','openai'} or fullname in optional:
            raise AssertionError('诊断加载了可选模型依赖：'+fullname)
sys.meta_path.insert(0,Guard())
from repropatch.diagnostics import diagnose_run,diagnostics_markdown
result=diagnose_run(Path(sys.argv[1]))
assert result['evidence_complete'] and result['outcome']=='ACCEPTED'
assert diagnostics_markdown(result)
assert 'agents' not in sys.modules and 'openai' not in sys.modules
print(json.dumps({'outcome':result['outcome'],'evidence_complete':result['evidence_complete']}))
"""
    child = subprocess.run(
        [sys.executable, "-c", script, str(directory)],
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )
    assert child.returncode == 0, child.stderr
    assert json.loads(child.stdout) == {"outcome": "ACCEPTED", "evidence_complete": True}
    assert file_bytes(directory) == before
