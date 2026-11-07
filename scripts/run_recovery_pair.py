"""Serial fresh-model checkpoint/restart pairs, with explicit remaining budgets."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter
from contextlib import asynccontextmanager, contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from benchmark_recovery_costs import CAMPAIGN, file_sha, write_json

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text())


def require(value, reason):
    if not value:
        raise ValueError(reason)


def selected_pairs(protocol, pair_id=None):
    pairs = [pair for pair in protocol["pairs"] if pair_id is None or pair["pair_id"] == pair_id]
    require(bool(pairs), "UNREGISTERED_PAIR")
    return pairs


def manifest(path):
    value = load(path)
    require(value["campaign"] == CAMPAIGN and value["local_concurrency"] == 1, "PROTOCOL_IDENTITY")
    require(
        value["pause_after_step"] == 3 and value["post_failure_request_cap"] == 21,
        "PROTOCOL_BUDGET",
    )
    for name, expected in value["source_files_sha256"].items():
        require(file_sha(ROOT / name) == expected, "SOURCE_CHANGED:" + name)
    require(
        file_sha(ROOT / value["preparation_protocol"]) == value["preparation_protocol_sha256"],
        "PREPARATION_PROTOCOL_CHANGED",
    )
    return value


def remaining_budget(run, checkpoint, original_budget):
    """Derive the restarted arm's fresh Task from the shared failure boundary."""
    require(run["deadline_at"] == checkpoint["deadline_at"], "CHECKPOINT_DEADLINE_CHANGED")
    require(run["steps_used"] == checkpoint["counters"]["steps_used"], "CHECKPOINT_STEPS_CHANGED")
    require(
        run["tool_calls_admitted"] == checkpoint["counters"]["tool_calls_admitted"],
        "CHECKPOINT_TOOLS_CHANGED",
    )
    remaining = original_budget["max_steps"] - checkpoint["counters"]["steps_used"]
    tools = original_budget["max_tool_calls"] - checkpoint["counters"]["tool_calls_admitted"]
    wall = math.floor(
        (
            datetime.fromisoformat(run["deadline_at"])
            - datetime.fromisoformat(checkpoint["committed_at"])
        ).total_seconds()
    )
    require(remaining > 0 and tools > 0, "NO_POST_FAILURE_BUDGET")
    require(wall > original_budget["verification_reserve_seconds"], "NO_POST_FAILURE_TIME")
    return {"max_steps": remaining, "max_tool_calls": tools, "wall_seconds": wall}


def subtract_usage(total, prefix):
    result = {}
    for key in (
        "requests",
        "input_tokens",
        "output_tokens",
        "cached_input_tokens",
        "unknown_usage_requests",
        "known_input_tokens",
        "known_output_tokens",
        "repair_requests",
        "compact_requests",
        "retry_requests",
    ):
        left, right = total.get(key), prefix.get(key)
        result[key] = None if left is None or right is None else left - right
        if result[key] is not None:
            require(result[key] >= 0, "NEGATIVE_CUMULATIVE_USAGE")
    return result


def pair_metrics(prefix, resumed, restarted):
    post_c = subtract_usage(resumed["usage"], prefix["usage"])
    post_r = restarted["usage"]
    delta = {}
    for key in ("requests", "input_tokens", "output_tokens", "cached_input_tokens"):
        a, b = post_r.get(key), post_c.get(key)
        delta[key] = None if a is None or b is None else a - b
    saved_fraction = (
        delta["input_tokens"] / post_r["input_tokens"]
        if delta["input_tokens"] is not None and post_r["input_tokens"]
        else None
    )
    return {
        "shared_prefix_usage": prefix["usage"],
        "resume_post_failure_usage": post_c,
        "restart_post_failure_usage": post_r,
        "restart_minus_resume_usage": delta,
        "post_failure_input_saved_fraction": saved_fraction,
        "resume_wall_seconds": resumed["measurement"]["elapsed_seconds"],
        "restart_wall_seconds": restarted["measurement"]["elapsed_seconds"],
        "restart_minus_resume_wall_seconds": restarted["measurement"]["elapsed_seconds"]
        - resumed["measurement"]["elapsed_seconds"],
    }


def ledger_snapshot(ledger, attempt):
    with ledger.connect() as db:
        rows = db.execute(
            "SELECT id,request_sha256,response_sha256,usage,status_code FROM requests "
            "WHERE attempt=? ORDER BY sent_at,id",
            (attempt,),
        ).fetchall()
    return {
        "path": str(ledger.path),
        "attempt": attempt,
        "request_cap": ledger.request_cap(attempt),
        "requests": [
            dict(
                zip(
                    ("id", "request_sha256", "response_sha256", "usage", "status_code"),
                    row,
                    strict=True,
                )
            )
            for row in rows
        ],
    }


@contextmanager
def metered_models(args, hooks):
    from run_benchmark_agent import responses_client

    import repropatch.models as models

    factory = models.responses_model

    @asynccontextmanager
    async def metered(*values, **options):
        async with responses_client(args, hooks) as client:
            async with factory(*values, **options, http_client=client) as model:
                yield model

    models.responses_model = metered
    try:
        yield
    finally:
        models.responses_model = factory


def export_result(report, task, output, attempt, usage, measurement):
    from run_benchmark_agent import attempt_identity, export_repropatch_candidate

    directory = Path(report["artifact_directory"])
    candidate = (
        export_repropatch_candidate(report, directory, output)
        if report["state"] == "FINISHED"
        else {"candidate_available": False, "candidate_bytes": 0, "candidate_sha256": None}
    )
    agent = report.get("agent", {})
    benchmark = report.get("benchmark", {})
    return {
        "schema": "repropatch.benchmark-attempt.v1",
        "agent": "repropatch",
        "attempt": attempt,
        "attempt_id": attempt,
        **attempt_identity(task, attempt),
        **candidate,
        "native_run_id": report["run_id"],
        "native_status": report["outcome"] or report["state"],
        "native_outcome": report["outcome"],
        "native_reason": report["reason_code"],
        "native_artifact_dir": str(directory),
        "native_image_id": report["provenance"]["image_id"],
        "native_task_sha256": report["provenance"]["task_sha256"],
        "baseline_eligible": report.get("reproduced"),
        "candidate_roundtrip_verified": report.get("candidate_roundtrip_verified"),
        "container_deleted": report.get("cleanup_confirmed"),
        "internal_verification_status": benchmark.get("internal_verification"),
        "internal_acceptance": report.get("verified"),
        "tool_calls": report.get("tool_calls", agent.get("tool_calls_used")),
        "model_steps": report.get("model_steps", agent.get("steps_used")),
        "agent_stop_reason": agent.get("agent_stop_reason"),
        "benchmark": benchmark,
        "usage": usage,
        "money": usage,
        "measurement": measurement,
    }


def stage(args):
    from benchmark_budget import BudgetHooks, LocalUsageLedger
    from run_benchmark_agent import provider

    from repropatch.events import EventLog, read_events
    from repropatch.harness import Harness
    from repropatch.models import ResponsesConfig
    from repropatch.recovery import read_checkpoint, resume_run
    from repropatch.task import Task

    ledger = LocalUsageLedger(args.ledger)
    task = Task.load(args.task)
    if args.stage == "resume":
        prior = load(args.output / "prefix.json")
        directory = Path(prior["native_artifact_dir"])
        old = read_events(directory, prior["native_run_id"])
    else:
        args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
        (args.output / "task.original.yaml").write_bytes(task.source_bytes)
        old = None
    hooks = BudgetHooks(
        ledger,
        args.attempt,
        args.output / "http-native" / args.stage,
        local_luna=True,
        route="azure-ssh",
    )
    settings = SimpleNamespace(provider="local-luna", cpa_route="azure-ssh", reasoning_effort="max")
    model_name, base_url, key_env, use_proxy = provider(settings)
    observation = {}
    original_emit = EventLog.emit

    def observe(log, event_type, payload, **options):
        result = original_emit(log, event_type, payload, **options)
        if event_type == "model_started" and "first_model_admission_ns" not in observation:
            observation["first_model_admission_ns"] = time.perf_counter_ns()
        if event_type == "recovery_finished" and payload.get("success"):
            observation["restore_ready_ns"] = time.perf_counter_ns()
        return result

    EventLog.emit = observe
    started_at, started = datetime.now(UTC), time.perf_counter_ns()
    try:
        with metered_models(settings, hooks):
            if args.stage == "resume":
                report = resume_run(directory, context_meter=hooks)
            else:
                harness = Harness(
                    task,
                    ResponsesConfig(model_name, base_url, key_env, True, use_proxy),
                    output_root=args.output / "runs",
                    candidate_only=True,
                    compiler_cache=True,
                    context_policy=ledger.policy,
                    context_meter=hooks,
                    pause_after_step=3 if args.stage == "prefix" else None,
                )
                report = harness.run()
    finally:
        EventLog.emit = original_emit
    elapsed = (time.perf_counter_ns() - started) / 1e9
    measurement = {
        "stage": args.stage,
        "pid": os.getpid(),
        "started_at": started_at.isoformat(),
        "elapsed_seconds": elapsed,
        "first_model_admission_seconds": (observation["first_model_admission_ns"] - started) / 1e9
        if "first_model_admission_ns" in observation
        else None,
        "restore_ready_seconds": (observation["restore_ready_ns"] - started) / 1e9
        if "restore_ready_ns" in observation
        else None,
    }
    result = export_result(
        report, task, args.output, args.attempt, ledger.summary(args.attempt), measurement
    )
    result["ledger"] = ledger_snapshot(ledger, args.attempt)
    result["http_trace_directory"] = str(args.output / "http-native" / args.stage)
    directory = Path(result["native_artifact_dir"])
    current = read_events(directory, result["native_run_id"])
    result["run_state"] = {
        key: current.run[key]
        for key in (
            "state",
            "steps_used",
            "tool_calls_admitted",
            "deadline_at",
            "created_at",
            "segment_open",
        )
    }
    if args.stage == "prefix" and report["state"] == "INTERRUPTED":
        cp, _ = read_checkpoint(directory, current)
        committed = next(
            event for event in reversed(current.events) if event["type"] == "checkpoint_committed"
        )
        result["checkpoint"] = {**cp, "committed_at": committed["timestamp"]}
        result["original_budget"] = asdict(task.budget)
        require(
            cp["counters"]["steps_used"] == 3 and result["usage"]["requests"] == 3,
            "PREFIX_BOUNDARY_MISMATCH",
        )
    if old is not None:
        result["recovery_checks"] = {
            "same_run": current.run_id == old.run_id,
            "deadline_preserved": current.run["deadline_at"] == old.run["deadline_at"],
            "event_prefix_preserved": current.events[: len(old.events)] == old.events,
            "counters_monotonic": current.run["steps_used"] >= old.run["steps_used"]
            and current.run["tool_calls_admitted"] >= old.run["tool_calls_admitted"],
            "same_ledger": result["ledger"]["path"] == prior["ledger"]["path"]
            and result["ledger"]["attempt"] == prior["ledger"]["attempt"]
            and result["ledger"]["request_cap"] == prior["ledger"]["request_cap"],
            "ledger_prefix_preserved": result["ledger"]["requests"][: prior["usage"]["requests"]]
            == prior["ledger"]["requests"],
            "model_step_cap_preserved": current.run["steps_used"] <= task.budget.max_steps,
            "tool_cap_preserved": current.run["tool_calls_admitted"] <= task.budget.max_tool_calls,
        }
        result["measurement"]["pause_to_resume_start_seconds"] = (
            started_at - datetime.fromisoformat(prior["checkpoint"]["committed_at"])
        ).total_seconds()
    write_json(args.output / ("prefix.json" if args.stage == "prefix" else "result.json"), result)
    write_json(args.output / (args.stage + "-report.json"), report)
    print(
        json.dumps(
            {
                "stage": args.stage,
                "state": report["state"],
                "requests": result["usage"]["requests"],
                "elapsed_seconds": elapsed,
            }
        ),
        flush=True,
    )


def command(arguments, logfile, protocol, session):
    from context_ablation import error_details, supervised

    start = time.perf_counter_ns()
    receipt = {"arguments": arguments, "started_at": datetime.now(UTC).isoformat()}
    try:
        receipt["exit_code"] = supervised(
            [sys.executable, str(Path(__file__)), *arguments],
            logfile,
            7500,
            protocol,
            session=session,
        )
        return receipt["exit_code"]
    except Exception as exc:
        receipt.update(error_details(exc))
        raise
    finally:
        receipt.update(
            supervisor_elapsed_seconds=(time.perf_counter_ns() - start) / 1e9,
            completion_poll_interval_seconds=protocol["session_health_poll_seconds"],
        )
        write_json(logfile.with_suffix(".process.json"), receipt)


def prepare(args):
    import context_ablation
    import formal_benchmark

    p = manifest(args.protocol)
    base = load(ROOT / p["preparation_protocol"])
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    pairs = selected_pairs(p, getattr(args, "pair", None))
    instances = list(dict.fromkeys(pair["instance_id"] for pair in pairs))
    for instance in instances:
        target = args.output / instance
        target.mkdir()
        row = {
            "instance_id": instance,
            "arm": "baseline",
            "attempt_id": CAMPAIGN + "/prepare/" + instance,
            "request_cap": 24,
        }
        context_ablation.prepare_inputs(
            {
                "protocol": base,
                "source_sha256": p["source_files_sha256"],
            },
            row,
            target,
        )
        formal_benchmark.prepare(
            instance,
            target / "prepared",
            arm="baseline",
            configuration={**base, "attempts": [row]},
            protocol_path=ROOT / p["preparation_protocol"],
        )
    write_json(
        args.output / "prepared-all.json",
        {"protocol_sha256": file_sha(args.protocol), "selected": instances},
    )


def score(worker, settings, attempt, output, timeout):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/score_benchmark_attempt.py"),
            "--worker-result",
            str(worker),
            "--attempt-id",
            attempt,
            "--qualification",
            settings["qualification"],
            "--dataset",
            str(ROOT / ".repropatch/inputs/dataset"),
            "--repository",
            str(ROOT / ".repropatch/inputs/fmt"),
            "--timeout",
            str(timeout),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=timeout + 300,
    )
    (output.parent / (output.name + ".log")).write_bytes(result.stdout + result.stderr)
    return {
        "exit_code": result.returncode,
        "score": load(output / "score.json") if (output / "score.json").is_file() else None,
    }


def run_pair(pair, target, settings, base, policy):
    from benchmark_budget import LocalUsageLedger
    from context_ablation import error_details
    from cpa_session import CPASession
    from formal_benchmark import prepare_execution_contract

    target.mkdir(mode=0o700)
    row = {**pair, "status": "started", "errors": []}
    write_json(target / "registered.json", row)
    arm_settings = {"resume": settings}
    try:
        os.environ["CPA_JOB_MEMBER"] = pair["pair_id"]
        with CPASession(target / "cpa", campaign=CAMPAIGN) as session:
            claim = session.claim(pair["resume_attempt"], "full", 24)
            write_json(target / "resume-claim.json", claim)
            resume_ledger = target / "resume-usage.sqlite3"
            LocalUsageLedger.create_scoped(
                resume_ledger, {pair["resume_attempt"]: 24}, context_policy=policy
            )
            common = [
                "--task",
                settings["task"],
                "--ledger",
                str(resume_ledger),
                "--attempt",
                pair["resume_attempt"],
                "--output",
                str(target / "resume"),
            ]
            row["prefix_exit"] = command(
                ["stage", "prefix", *common], target / "prefix.log", base, session
            )
            session.healthy()
            prefix = load(target / "resume/prefix.json")
            row["shared_prefix_usage"] = prefix["usage"]
            if "checkpoint" not in prefix:
                row.update(status="no_checkpoint", prefix=prefix)
            else:
                budget = remaining_budget(
                    prefix["run_state"], prefix["checkpoint"], prefix["original_budget"]
                )
                require(budget["max_steps"] == 21, "REMAINING_REQUEST_CAP_CHANGED")
                row["remaining_budget"] = budget
                row["resume_exit"] = command(
                    ["stage", "resume", *common], target / "resume.log", base, session
                )
                session.healthy()
                restart_contract = prepare_execution_contract(
                    Path(settings["task"]).parent, target / "restart-contract", 600, budget
                )
                arm_settings["restart"] = {
                    **settings,
                    "task": str(restart_contract / "task.yaml"),
                    "qualification": str(restart_contract / "result.json"),
                }
                write_json(target / "restart-settings.json", arm_settings["restart"])
                claim = session.claim(pair["restart_attempt"], "full", 24)
                write_json(target / "restart-claim.json", claim)
                restart_ledger = target / "restart-usage.sqlite3"
                LocalUsageLedger.create_scoped(
                    restart_ledger, {pair["restart_attempt"]: 21}, context_policy=policy
                )
                row["restart_exit"] = command(
                    [
                        "stage",
                        "restart",
                        "--task",
                        arm_settings["restart"]["task"],
                        "--ledger",
                        str(restart_ledger),
                        "--attempt",
                        pair["restart_attempt"],
                        "--output",
                        str(target / "restart"),
                    ],
                    target / "restart.log",
                    base,
                    session,
                )
                session.healthy()
    except Exception as exc:
        row["errors"].append({"stage": "model_execution", **error_details(exc)})
    row["attempt_usage"] = {}
    for arm in ("resume", "restart"):
        ledger_path = target / (arm + "-usage.sqlite3")
        if ledger_path.is_file():
            try:
                row["attempt_usage"][arm] = LocalUsageLedger(ledger_path).summary(
                    pair[arm + "_attempt"]
                )
            except Exception as exc:
                row["errors"].append({"stage": arm + "_ledger", **error_details(exc)})
        if (target / arm / "result.json").is_file() and arm in arm_settings:
            try:
                row[arm + "_score"] = score(
                    target / arm / "result.json",
                    arm_settings[arm],
                    pair[arm + "_attempt"],
                    target / (arm + "-score"),
                    base["oracle_timeout_seconds"],
                )
            except Exception as exc:
                row["errors"].append({"stage": arm + "_score", **error_details(exc)})
    if all((target / arm / "result.json").is_file() for arm in ("resume", "restart")):
        try:
            resumed, restarted = (
                load(target / "resume/result.json"),
                load(target / "restart/result.json"),
            )
            row.update(
                status="measured",
                metrics=pair_metrics(load(target / "resume/prefix.json"), resumed, restarted),
                recovery_checks=resumed.get("recovery_checks"),
                resume_measurement=resumed["measurement"],
                restart_measurement=restarted["measurement"],
            )
        except Exception as exc:
            row["errors"].append({"stage": "pair_metrics", **error_details(exc)})
    if row["errors"]:
        row["status"] = "error"
    row["processes"] = {
        phase: load(target / (phase + ".process.json"))
        for phase in ("prefix", "resume", "restart")
        if (target / (phase + ".process.json")).is_file()
    }
    write_json(target / "pair.json", row)
    return row


def summarize(protocol, rows):
    expected = {pair["pair_id"]: pair for pair in protocol["pairs"]}
    observed = {}
    for row in rows:
        key = row["pair_id"]
        require(key in expected and key not in observed, "DUPLICATE_OR_UNREGISTERED_PAIR")
        require(
            all(row.get(field) == expected[key][field] for field in expected[key]),
            "PAIR_IDENTITY_CHANGED",
        )
        observed[key] = row
    complete = [observed.get(key, {**pair, "status": "missing"}) for key, pair in expected.items()]
    costs = [
        row["metrics"]
        for row in complete
        if row.get("metrics", {}).get("resume_post_failure_usage", {}).get("input_tokens")
        is not None
        and row.get("metrics", {}).get("restart_post_failure_usage", {}).get("input_tokens")
        is not None
    ]
    c_input = sum(row["resume_post_failure_usage"]["input_tokens"] for row in costs)
    r_input = sum(row["restart_post_failure_usage"]["input_tokens"] for row in costs)
    usage = [item for row in complete for item in row.get("attempt_usage", {}).values()]
    return {
        "campaign": CAMPAIGN,
        "expected_pairs": len(expected),
        "status_counts": dict(Counter(row["status"] for row in complete)),
        "actual_requests_observed": sum(item["requests"] for item in usage),
        "usage_covered_attempts": len(usage),
        "cold_successes": {
            arm: sum(
                ((row.get(arm + "_score") or {}).get("score") or {}).get("accepted") is True
                for row in complete
            )
            for arm in ("resume", "restart")
        },
        "cold_score_status_counts": {
            arm: dict(
                Counter(
                    ((row.get(arm + "_score") or {}).get("score") or {}).get("status", "missing")
                    for row in complete
                )
            )
            for arm in ("resume", "restart")
        },
        "paired_input_cost": {
            "complete_pairs": len(costs),
            "resume_sum": c_input,
            "restart_sum": r_input,
            "restart_minus_resume_sum": r_input - c_input,
            "saved_fraction": (r_input - c_input) / r_input if r_input else None,
        },
        "pairs": complete,
    }


def execute(args):
    from context_ablation import context_policy

    p = manifest(args.protocol)
    require(
        load(args.prepared / "prepared-all.json")["protocol_sha256"] == file_sha(args.protocol),
        "PREPARED_PROTOCOL_CHANGED",
    )
    base = load(ROOT / p["preparation_protocol"])
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    policy = context_policy(base, "baseline")
    rows = []
    for pair in selected_pairs(p, getattr(args, "pair", None)):
        settings = load(args.prepared / pair["instance_id"] / "prepared/prepared.json")
        row = run_pair(pair, args.output / pair["pair_id"], settings, base, policy)
        rows.append(row)
        write_json(args.output / "results.json", summarize(p, rows))
    return int(any(row["status"] == "error" for row in rows))


def aggregate(args):
    p = manifest(args.protocol)
    rows = [load(path) for path in sorted(args.input.rglob("pair.json"))]
    result = summarize(p, rows)
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "results.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "pairs"}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "execute"):
        p = sub.add_parser(name)
        p.add_argument("--protocol", type=Path, required=True)
        p.add_argument("--output", type=Path, required=True)
        p.add_argument("--pair")
        if name == "execute":
            p.add_argument("--prepared", type=Path, required=True)
        p.set_defaults(handler=globals()[name])
    p = sub.add_parser("aggregate")
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(handler=aggregate)
    p = sub.add_parser("stage")
    p.add_argument("stage", choices=("prefix", "resume", "restart"))
    p.add_argument("--task", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--attempt", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(handler=stage)
    args = parser.parse_args()
    args.output = args.output.resolve()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
