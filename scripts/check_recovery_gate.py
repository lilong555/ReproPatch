"""运行少量恢复故障边界，保存对应 Run 并单列安全恢复、明确失败和控制器拒绝。"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

SCENARIOS = (
    (
        "controlled-pause",
        "test_resume_preserves_native_input_counters_and_uses_remaining_script",
        "ACCEPTED",
        "VERIFICATION_PASSED",
    ),
    (
        "closed-checkpoint",
        "test_process_death_only_resumes_closed_checkpoint[closed_checkpoint]",
        "ACCEPTED",
        "VERIFICATION_PASSED",
    ),
    (
        "model-result-unknown",
        "test_process_death_only_resumes_closed_checkpoint[model_started]",
        "RECOVERY_FAILED",
        "MODEL_RESULT_UNKNOWN",
    ),
    (
        "response-before-tools",
        "test_process_death_only_resumes_closed_checkpoint[model_finished]",
        "RECOVERY_FAILED",
        "OPEN_AGENT_SEGMENT",
    ),
    (
        "edit-before-checkpoint",
        "test_process_death_only_resumes_closed_checkpoint[edit_finished]",
        "RECOVERY_FAILED",
        "OPEN_AGENT_SEGMENT",
    ),
    (
        "checkpoint-files-only",
        "test_process_death_only_resumes_closed_checkpoint[checkpoint_files]",
        "RECOVERY_FAILED",
        "OPEN_AGENT_SEGMENT",
    ),
    (
        "final-response-only",
        "test_process_death_only_resumes_closed_checkpoint[final_response]",
        "RECOVERY_FAILED",
        "OPEN_AGENT_SEGMENT",
    ),
    (
        "corrupt-checkpoint",
        "test_resume_rejects_divergence_without_model_or_overwriting_source[checkpoint]",
        "RECOVERY_FAILED",
        "CHECKPOINT_CORRUPT",
    ),
    (
        "diverged-workspace",
        "test_resume_rejects_divergence_without_model_or_overwriting_source[source]",
        "RECOVERY_FAILED",
        "WORKSPACE_DIVERGED",
    ),
    (
        "cleanup-uncertain",
        "test_uncertain_cleanup_refuses_safe_candidate_without_model_call",
        "RECOVERY_FAILED",
        "OWNED_RESOURCE_UNCONFIRMED",
    ),
    (
        "recovery-interrupted",
        "test_process_death_during_recovery_does_not_repeat_reconstruction",
        "RECOVERY_FAILED",
        "UNSUPPORTED_RECOVERY_PHASE",
    ),
    (
        "budget-consumed",
        "test_resume_budget_does_not_refund_and_verifies_only_with_remaining_time[agent_deadline]",
        "ACCEPTED",
        "VERIFICATION_PASSED",
    ),
    ("controller-held", "test_active_writer_cannot_be_taken_over", None, None),
)


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="尚不存在的证据目录")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = (args.output or root / ".repropatch/recovery-gates" / uuid.uuid4().hex).resolve()
    output.mkdir(parents=True)
    runtime = root / ".repropatch/recovery-gate-tests" / uuid.uuid4().hex
    runtime.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "gate": "T09-recovery",
        "status": "error",
        "started_at": datetime.now(UTC).isoformat(),
        "real_model_verified": False,
        "paid_requests_sent": 0,
        "scenarios": [],
    }
    code = 1
    try:
        from repropatch import __version__
        from repropatch.events import _json, encode_json, read_events
        from repropatch.harness import implementation_sha256
        from repropatch.models import prepare_sdk
        from repropatch.trace import replay_trace

        prepare_sdk()
        summary.update(product_version=__version__, implementation_sha256=implementation_sha256())
        paths = [
            p
            for directory in ("src/repropatch", "tests", "scripts", "requirements")
            for p in (root / directory).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        ]
        paths += [root / "pyproject.toml", root / "uv.lock"]
        write(
            output / "source-manifest.json",
            {
                str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(paths)
            },
        )
        argv = [
            sys.executable,
            "-I",
            "-m",
            "pytest",
            *(str(root / "tests/test_resume.py") + "::" + test for _, test, _, _ in SCENARIOS),
            "-v",
            f"--basetemp={runtime}",
            f"--junitxml={output / 'results.xml'}",
            "-o",
            "junit_family=legacy",
        ]
        with (output / "tests.log").open("wb") as log:
            result = subprocess.run(
                argv,
                cwd=root,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=180,
                env=dict(os.environ, REPROPATCH_RECOVERY_GATE="1", PYTEST_ADDOPTS=""),
            )
        summary["command"] = {"argv": argv, "returncode": result.returncode}
        cases = list(ET.parse(output / "results.xml").iter("testcase"))
        assert result.returncode == 0 and len(cases) == len(SCENARIOS)
        assert not any(
            child.tag in {"failure", "error", "skipped"} for case in cases for child in case
        )
        by_name = {case.get("name"): case for case in cases}
        for identifier, test, outcome, reason in SCENARIOS:
            case = by_name[test]
            properties = {
                p.get("name"): p.get("value") for p in case.findall("properties/property")
            }
            locations = json.loads(properties["recovery_runs"])
            assert len(locations) == 1, (identifier, locations)
            source = Path(locations[0])
            target = output / "runs" / identifier / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)
            database = target / "events.sqlite3"
            digest = hashlib.sha256(database.read_bytes()).hexdigest()
            assert digest == hashlib.sha256((source / "events.sqlite3").read_bytes()).hexdigest()
            snapshot = read_events(target, target.name)
            row = snapshot.run
            assert row["outcome"] == outcome and row["reason_code"] == reason, identifier
            recoveries = [e for e in snapshot.events if e["type"] == "recovery_started"]
            calls = [e for e in snapshot.events if e["type"] == "model_started"]
            starts_after = [e for e in calls if recoveries and e["seq"] > recoveries[0]["seq"]]
            tools = [e for e in snapshot.events if e["type"] == "tool_started"]
            assert len({e["tool_call_id"] for e in tools}) == len(tools)
            tools_after = [e for e in tools if recoveries and e["seq"] > recoveries[0]["seq"]]
            if outcome == "RECOVERY_FAILED":
                assert not starts_after and not tools_after, identifier
            if outcome is None:
                assert row["state"] == "INTERRUPTED" and not recoveries
            if identifier == "budget-consumed":
                assert not starts_after and not tools_after
            assert row["steps_used"] == len(calls)
            trace = replay_trace(target)
            write(target.parent / "trace.json", trace)
            assert hashlib.sha256(database.read_bytes()).hexdigest() == digest
            first = recoveries[0] if recoveries else None
            prefix_seq = first["seq"] - 3 if first else snapshot.last_seq
            assert row["deadline_at"] == snapshot.events[0]["payload"]["deadline_at"]
            prefix = b"".join(
                encode_json(e) + b"\n" for e in snapshot.events if e["seq"] <= prefix_seq
            )
            (target.parent / "unrecovered-prefix.jsonl").write_bytes(prefix)
            record = {
                "id": identifier,
                "test": test,
                "run_id": target.name,
                "database": str(database.relative_to(output)),
                "database_sha256": digest,
                "unrecovered_prefix": str(
                    (target.parent / "unrecovered-prefix.jsonl").relative_to(output)
                ),
                "prefix_is_independent_trial": False,
                "source_state": first["payload"]["source_state"] if first else row["state"],
                "state": row["state"],
                "outcome": outcome,
                "reason_code": reason,
                "recovery_attempts": row["recovery_attempt"],
                "steps_used": row["steps_used"],
                "steps_before_recovery": sum(e["seq"] <= prefix_seq for e in calls),
                "tool_calls_admitted": row["tool_calls_admitted"],
                "created_at": row["created_at"],
                "deadline_at": row["deadline_at"],
                "deadline_preserved": True,
                "usage": _json(row["usage_json"]),
                "new_model_turns_after_recovery": len(starts_after),
                "new_tool_invocations_after_recovery": len(tools_after),
                "evidence_complete": trace["evidence_complete"],
            }
            summary["scenarios"].append(record)
        summary.update(
            status="passed",
            tests_passed=len(cases),
            safe_recovery_runs=sum(r["outcome"] == "ACCEPTED" for r in summary["scenarios"]),
            explicit_recovery_failed_runs=sum(
                r["outcome"] == "RECOVERY_FAILED" for r in summary["scenarios"]
            ),
            controller_refused_runs=sum(r["outcome"] is None for r in summary["scenarios"]),
            unexpected_model_retries=0,
            limitations=[
                "ScriptedModel 恢复机制实验，不估计模型修复率。",
                "故障前缀来自同一 Run 的已提交事件，不是独立 baseline trial。",
                "真实 Docker 清理另由 Docker gate 验证。",
            ],
        )
        code = 0
    except Exception as exc:
        summary["error_type"] = type(exc).__name__
    summary["finished_at"] = datetime.now(UTC).isoformat()
    write(output / "summary.json", summary)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "evidence": str(output),
                "tests_passed": summary.get("tests_passed"),
                "safe_recovery_runs": summary.get("safe_recovery_runs"),
                "explicit_recovery_failed_runs": summary.get("explicit_recovery_failed_runs"),
                "controller_refused_runs": summary.get("controller_refused_runs"),
                "error_type": summary.get("error_type"),
            },
            ensure_ascii=False,
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
