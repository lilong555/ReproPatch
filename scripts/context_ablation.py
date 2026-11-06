"""Frozen, independently metered native context-ablation trials and complete summaries."""

import argparse
import hashlib
import itertools
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tarfile
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import yaml
from actions_benchmark import save, sha
from benchmark_budget import LocalUsageLedger
from cpa_session import CPASession

from repropatch.context import ContextPolicy
from repropatch.task import Task

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "benchmarks/context-ablation/protocol.json"
ARMS = ("baseline", "diagnostics", "dedup", "state", "combined")
FLAGS = ("diagnostic_extraction", "deduplicate_results", "state_aware_compaction")
OVERFLOWS = (
    "LOCAL_TRANSPORT_LIMIT",
    "LOCAL_TOKEN_GUARD",
    "CONTEXT_LIMIT",
    "PROVIDER_CONTEXT_OVERFLOW",
    "PROVIDER_CONTEXT_LENGTH_EXCEEDED",
    "PROVIDER_PAYLOAD_TOO_LARGE",
    "COMPACTION_FAILED",
    "RESPONSE_TOO_LARGE",
    "MODEL_CONTEXT_EXCEEDED",
    "CONTEXT_BUDGET_EXHAUSTED",
)


def load(path):
    return json.loads(Path(path).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exclusive_save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        os.chmod(path, 0o600)
        stream.write(json.dumps(value, indent=2) + "\n")


def qualification_archives(p):
    archives = sorted((ROOT / "benchmarks/context-ablation/inputs").glob("*.tar.gz"))
    require(
        sorted(sha(f) for f in archives) == sorted(p["qualification_archive_sha256"]),
        "QUALIFICATION_ARCHIVES_REQUIRED",
    )
    return archives


def archive_task_contracts(p):
    contracts = {}
    for path in qualification_archives(p):
        with tarfile.open(path) as archive:
            for member in archive.getmembers():
                parts = Path(member.name).parts
                if (
                    len(parts) != 3
                    or parts[0] != "qualification"
                    or parts[2] != "task.yaml"
                    or parts[1] not in p["tasks"]
                ):
                    continue
                instance = parts[1]
                require(member.isfile() and instance not in contracts, "ARCHIVE_TASK_DUPLICATE")
                with archive.extractfile(member) as stream:
                    original = Task.from_dict(yaml.safe_load(stream), ROOT)
                raw = original.to_dict()
                raw["budget"].update(
                    {
                        **p["execution_budget_override"],
                        "model_timeout_seconds": p["model_timeout_seconds"],
                    }
                )
                task = Task.from_dict(raw, ROOT)
                require(task.environment.image == p["image_id"], "ARCHIVE_TASK_IMAGE_CHANGED")
                contracts[instance] = {
                    "execution_task_sha256": hashlib.sha256(task.source_bytes).hexdigest(),
                    "prepared_commit": task.revision,
                }
    require(set(contracts) == set(p["tasks"]), "ARCHIVE_TASKS_INCOMPLETE")
    return contracts


def read_protocol(path=PROTOCOL):
    p = load(path)
    require(p["schema"] == "repropatch.context-ablation.protocol.v1", "PROTOCOL_SCHEMA")
    require(p["campaign"] == "context-ablation-20261106", "CAMPAIGN")
    require(tuple(p["arms"]) == ARMS, "ARMS")
    require(sha(ROOT / p["task_source"]) == p["task_source_sha256"], "TASK_SOURCE_CHANGED")
    require(p["tasks"] == load(ROOT / p["task_source"])["paired_tasks"], "PAIRED_TASKS")
    require(len(p["tasks"]) == len(set(p["tasks"])) == 19, "TASK_COUNT")
    require(sha(ROOT / p["parent_protocol"]) == p["parent_protocol_sha256"], "PARENT_CHANGED")
    parent = load(ROOT / p["parent_protocol"])
    for key in (
        "context_policy",
        "execution_budget_override",
        "model",
        "reasoning_effort",
        "model_timeout_seconds",
        "max_output_tokens",
        "max_tool_calls",
        "max_tools_per_response",
        "image",
        "image_id",
        "qualification_run_id",
        "qualification_archive_sha256",
        "request_cap_per_attempt",
    ):
        require(p[key] == parent[key], "PARENT_CONTRACT_CHANGED:" + key)
    require(set(p["task_contracts"]) == set(p["tasks"]), "TASK_CONTRACT_SET")
    rebuilt = archive_task_contracts(p)
    for instance, observed in rebuilt.items():
        contract = p["task_contracts"][instance]
        legacy = parent["task_contracts"][instance]
        require(
            contract["legacy_execution_task_sha256"] == legacy["execution_task_sha256"],
            "LEGACY_TASK_CONTRACT_CHANGED:" + instance,
        )
        require(
            contract["prepared_commit"] == legacy["prepared_commit"],
            "PREPARED_COMMIT_CHANGED:" + instance,
        )
        require(
            all(contract[key] == value for key, value in observed.items()),
            "EXECUTION_TASK_CONTRACT_CHANGED:" + instance,
        )
    require(p["repeats"] == 2 and p["trial_count"] == 190, "TRIAL_COUNT")
    require(p["max_parallel"] == 8 and p["formal_request_cap"] == 4560, "ALLOCATION")
    require(p["cpa_route"] == "azure-ssh" and p["retries"] == 0, "CPA_POLICY")
    require(p["cpa_claim"] is True, "CPA_PERSISTENT_CLAIM_REQUIRED")
    for arm, enabled in zip(ARMS, ((), FLAGS[:1], FLAGS[1:2], FLAGS[2:], FLAGS), strict=True):
        require(p["treatments"][arm] == {key: key in enabled for key in FLAGS}, "TREATMENT")
        require(all(type(v) is bool for v in p["treatments"][arm].values()), "BOOLEAN_FLAGS")
    for scope in ("smoke", "full"):
        tasks = p["tasks"] if scope == "full" else [p["smoke"]["task"]]
        repeats = range(1, p["repeats"] + 1) if scope == "full" else (1,)
        keys = [f"{task}/{arm}/repeat-{r}" for task in tasks for arm in ARMS for r in repeats]
        keys.sort(
            key=lambda k: hashlib.sha256(
                f"{p['execution_order_seed']}/{scope}/{k}".encode("ascii")
            ).hexdigest()
        )
        require(keys == p["execution_order"][scope], "FROZEN_RANDOM_ORDER")
    return p


def trials(p, scope):
    rows = []
    for index, key in enumerate(p["execution_order"][scope]):
        task, arm, repeat = key.split("/")
        rows.append(
            {
                "trial_index": index,
                "job_key": f"trial-{index + 1:03d}",
                "instance_id": task,
                "arm": arm,
                "repeat": int(repeat.removeprefix("repeat-")),
                "attempt_id": f"{p['campaign']}/{scope}/{key}",
                "request_cap": p["request_cap_per_attempt"],
                "scope": scope,
            }
        )
    return rows


def source_hashes():
    paths = [ROOT / "pyproject.toml", ROOT / "docker/Dockerfile"]
    for directory, pattern in (("src", "*.py"), ("scripts", "*.py"), ("requirements", "*.txt")):
        paths.extend((ROOT / directory).rglob(pattern))
    return {str(path.relative_to(ROOT)): sha(path) for path in sorted(paths)}


def first_run():
    require(os.environ.get("GITHUB_RUN_ATTEMPT", "1") == "1", "RERUN_REQUIRES_NEW_CAMPAIGN")


def plan(args):
    first_run()
    p = read_protocol(args.protocol)
    rows = trials(p, args.scope)
    result = {
        "schema": "repropatch.context-ablation.manifest.v1",
        "protocol": p,
        "protocol_sha256": sha(args.protocol),
        "scope": args.scope,
        "source_sha256": source_hashes(),
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": 1,
        "attempts": rows,
        "matrix": {"include": rows},
        "trial_count": len(rows),
        "request_cap": sum(r["request_cap"] for r in rows),
        "max_parallel": 8,
        "task_population": p["task_population"],
    }
    result["manifest_sha256"] = digest(result)
    exclusive_save(args.output, result)
    if getattr(args, "github_output", None):
        with args.github_output.open("a") as stream:
            stream.write("matrix=" + json.dumps(result["matrix"]) + "\n")
    print(json.dumps(result["matrix"]))


def read_manifest(path, protocol_path=PROTOCOL, *, execution=False):
    m = load(path)
    require(m["schema"] == "repropatch.context-ablation.manifest.v1", "MANIFEST_SCHEMA")
    require(
        m["manifest_sha256"] == digest({k: v for k, v in m.items() if k != "manifest_sha256"}),
        "MANIFEST_HASH",
    )
    require(m["protocol"] == read_protocol(protocol_path), "MANIFEST_PROTOCOL")
    require(m["protocol_sha256"] == sha(protocol_path), "PROTOCOL_HASH")
    require(m["attempts"] == trials(m["protocol"], m["scope"]), "ATTEMPT_MANIFEST")
    require(m["matrix"] == {"include": m["attempts"]}, "MATRIX_MANIFEST")
    if execution:
        first_run()
        require(m["source_sha256"] == source_hashes(), "EXECUTION_SOURCE_CHANGED")
        require(bool(m["github_run_id"]), "PLAN_REQUIRES_GITHUB_RUN_ID")
        require(m["github_run_id"] == os.environ.get("GITHUB_RUN_ID"), "GITHUB_RUN_ID_CHANGED")
    return m


def selected(m, args):
    require(getattr(args, "scope", None) in {None, m["scope"]}, "SCOPE_MISMATCH")
    rows = [
        r
        for r in m["attempts"]
        if (
            r["attempt_id"] == args.attempt_id
            if args.attempt_id is not None
            else r["trial_index"] == args.trial_index
        )
    ]
    require(len(rows) == 1, "UNREGISTERED_ATTEMPT")
    return rows[0]


def runner_identity():
    require(bool(os.environ.get("RUNNER_NAME")), "RUNNER_NAME_REQUIRED")
    return {
        key: os.environ.get(key)
        for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB", "RUNNER_NAME")
    }


def context_policy(p, arm):
    return ContextPolicy.from_dict({**p["context_policy"], **p["treatments"][arm]})


def status(output, state, **details):
    identity = optional_json(output / "trial.json")
    previous = optional_json(output / "runner-status.json")
    value = {
        **previous,
        "schema": "repropatch.context-ablation.runner-status.v1",
        "state": state,
        "updated_at": datetime.now(UTC).isoformat(),
        "manifest_sha256": identity.get("manifest_sha256"),
        **details,
    }
    save(output / "runner-status.json", value)
    with (output / "runner-events.jsonl").open("a") as stream:
        stream.write(json.dumps(value) + "\n")


def error_details(error):
    message = str(error)
    for key in ("OPENAI_API_KEY", "CPA_LEASE_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        secret = os.environ.get(key)
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return {"error_type": type(error).__name__, "error_message": message[:4000]}


def prepare_inputs(m, row, output):
    import actions_benchmark

    p = m["protocol"]
    archives = qualification_archives(p)
    destination = ROOT / ".repropatch/qualification-input"
    destination.mkdir(parents=True, exist_ok=True)
    for archive in archives:
        target = destination / archive.name
        if target.exists():
            require(sha(target) == sha(archive), "QUALIFICATION_INPUT_CONFLICT")
        else:
            shutil.copyfile(archive, target)
    coverage = load(ROOT / "benchmarks/coverage.json")
    require(sha(ROOT / "benchmarks/coverage.json") == p["coverage_sha256"], "COVERAGE_HASH")
    require(coverage["revision"] == p["dataset_revision"], "DATASET_REVISION")
    input_plan = {
        "coverage_sha256": p["coverage_sha256"],
        "dataset_revision": p["dataset_revision"],
        "implementation_sha256": m["source_sha256"],
        "tasks": [r for r in coverage["records"] if r["instance_id"] == row["instance_id"]],
    }
    input_plan["plan_sha256"] = digest(input_plan)
    save(output / "input-plan.json", input_plan)
    actions_benchmark.prepare(
        SimpleNamespace(
            plan=output / "input-plan.json",
            instances=row["instance_id"],
            output=ROOT / ".repropatch/inputs",
        )
    )
    image = subprocess.run(
        ["docker", "image", "inspect", p["image"]], capture_output=True, check=False
    )
    if image.returncode:
        subprocess.run(["docker", "pull", p["image"]], check=True, timeout=600)


def prepare(args):
    import formal_benchmark

    m = read_manifest(args.manifest, args.protocol, execution=True)
    row = selected(m, args)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    identity = {
        **row,
        "schema": "repropatch.context-ablation.trial.v1",
        "manifest_sha256": m["manifest_sha256"],
        "runner": runner_identity(),
    }
    exclusive_save(output / "trial.json", identity)
    exclusive_save(output / "manifest.json", m)
    try:
        claim = ROOT / ".repropatch/context-ablation-attempts" / m["manifest_sha256"]
        exclusive_save(claim / (row["job_key"] + ".json"), identity)
        status(output, "PREPARING", **row)
        LocalUsageLedger.create_scoped(
            output / "usage.sqlite3",
            {row["attempt_id"]: row["request_cap"]},
            context_policy=context_policy(m["protocol"], row["arm"]),
        )
        prepare_inputs(m, row, output)
        formal_benchmark.prepare(
            row["instance_id"],
            output / "prepared",
            arm=row["arm"],
            configuration={**m["protocol"], "attempts": [row]},
            protocol_path=args.protocol,
        )
        settings = load(output / "prepared/prepared.json")
        task = Path(settings["task"])
        require(
            sha(task)
            == m["protocol"]["task_contracts"][row["instance_id"]]["execution_task_sha256"],
            "TASK_CONTRACT_HASH",
        )
        frozen = {
            "task_sha256": sha(task),
            "qualification_sha256": sha(Path(settings["qualification"])),
            "common_input_sha256": sha(Path(settings["common_input"])),
            "prepared_sha256": sha(output / "prepared/prepared.json"),
        }
        exclusive_save(output / "prepared-identity.json", frozen)
        status(output, "PREPARED", **row)
        return 0
    except Exception as error:
        status(output, "PREPARATION_FAILED", **row, **error_details(error))
        finish(m, row, output, failure="PREPARATION_FAILED")
        return 2


def worker_command(row, settings, output, p):
    return [
        sys.executable,
        str(ROOT / "scripts/run_benchmark_agent.py"),
        "--agent",
        "repropatch",
        "--provider",
        "local-luna",
        "--cpa-route",
        p["cpa_route"],
        "--reasoning-effort",
        "max",
        "--candidate-only",
        "--compiler-cache",
        "--intermediate-checks",
        "enabled",
        "--tool-mode",
        "legacy",
        "--task",
        settings["task"],
        "--ledger",
        str(output / "usage.sqlite3"),
        "--attempt",
        row["attempt_id"],
        "--output",
        str(output / "worker"),
    ]


def supervised(command, log, timeout, p, session=None):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT / "scripts")}
    for key in ("CPA_LEASE_TOKEN", "CPA_SSH_KEY_FILE", "CPA_SSH_KNOWN_HOSTS_FILE"):
        env.pop(key, None)
    if session is None:
        env.pop("OPENAI_API_KEY", None)
    with log.open("xb") as stream:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                if session is not None:
                    session.healthy()
                require(time.monotonic() < deadline, "SUBPROCESS_TIMEOUT")
                time.sleep(p["session_health_poll_seconds"])
            return process.returncode
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=p["subprocess_termination_grace_seconds"])
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


def run(args):
    m = read_manifest(args.manifest, args.protocol, execution=True)
    row = selected(m, args)
    p, output = m["protocol"], args.output.resolve(strict=True)
    identity = load(output / "trial.json")
    require(identity["attempt_id"] == row["attempt_id"], "OUTPUT_ATTEMPT_MISMATCH")
    require(identity["manifest_sha256"] == m["manifest_sha256"], "OUTPUT_MANIFEST_MISMATCH")
    require(identity["runner"] == runner_identity(), "RUNNER_ID_CHANGED")
    require(load(output / "runner-status.json")["state"] == "PREPARED", "PREPARED_REQUIRED")
    exclusive_save(output / "execution-started.json", {"attempt_id": row["attempt_id"]})
    failure = None
    worker_exit = score_exit = None
    try:
        settings = load(output / "prepared/prepared.json")
        frozen = load(output / "prepared-identity.json")
        for key, path in (
            ("task_sha256", settings["task"]),
            ("qualification_sha256", settings["qualification"]),
            ("common_input_sha256", settings["common_input"]),
            ("prepared_sha256", output / "prepared/prepared.json"),
        ):
            require(sha(Path(path)) == frozen[key], "PREPARED_INPUT_CHANGED")
        ledger = LocalUsageLedger(output / "usage.sqlite3")
        require(ledger.policy == context_policy(p, row["arm"]), "LEDGER_POLICY_CHANGED")
        require(ledger.summary()["requests"] == 0, "ATTEMPT_ALREADY_USED")
        require(bool(os.environ.get(p["api_key_env"])), "API_KEY_ENV_REQUIRED")
        os.environ["CPA_JOB_MEMBER"] = row["scope"] + "-" + row["job_key"]
        status(output, "RUNNING", **row)
        with CPASession(output / "cpa", campaign=p["campaign"]) as session:
            session.healthy()
            enters = [
                json.loads(line)
                for line in (output / "cpa/lease-events.jsonl").read_text().splitlines()
                if line.strip()
            ]
            require(
                any(
                    e.get("action") == "enter" and e["result"].get("request_retry") == 0
                    for e in enters
                ),
                "CPA_ZERO_RETRY_EVIDENCE_REQUIRED",
            )
            receipt = session.claim(row["attempt_id"], row["scope"], 24)
            exclusive_save(output / "cpa/claim.json", receipt)
            worker_exit = supervised(
                worker_command(row, settings, output, p),
                output / "worker.log",
                p["worker_timeout_seconds"],
                p,
                session,
            )
            session.healthy()
    except Exception as error:
        failure = "WORKER_INFRASTRUCTURE_FAILED"
        status(output, failure, **row, **error_details(error))
    worker_result = output / "worker/result.json"
    if worker_result.is_file():
        try:
            status(output, "SCORING", **row)
            score_exit = supervised(
                [
                    sys.executable,
                    str(ROOT / "scripts/score_benchmark_attempt.py"),
                    "--worker-result",
                    str(worker_result),
                    "--attempt-id",
                    row["attempt_id"],
                    "--qualification",
                    settings["qualification"],
                    "--dataset",
                    str(ROOT / ".repropatch/inputs/dataset"),
                    "--repository",
                    str(ROOT / ".repropatch/inputs/fmt"),
                    "--timeout",
                    str(p["oracle_timeout_seconds"]),
                    "--output",
                    str(output / "score"),
                ],
                output / "score.log",
                p["scorer_timeout_seconds"],
                p,
            )
        except Exception as error:
            failure = failure or "SCORING_INFRASTRUCTURE_FAILED"
            status(output, failure, **row, **error_details(error))
    else:
        failure = failure or "MISSING_WORKER_RESULT"
    result = finish(m, row, output, failure=failure, worker_exit=worker_exit, score_exit=score_exit)
    status(
        output,
        "FINISHED" if failure is None else failure,
        **row,
        classification=result["classification"],
        worker_exit=worker_exit,
        score_exit=score_exit,
    )
    return 2 if result["classification"] in {"infrastructure", "preparation"} else 0


def optional_json(path):
    return load(path) if path.is_file() else {}


def mechanism_metrics(worker, p, arm):
    state = (worker.get("context") or {}).get("optimization_state")
    metrics = {}
    for flag in FLAGS:
        observed = ((state or {}).get("metrics") or {}).get(flag, {})
        count = observed.get("triggers")
        if type(count) is not int or count < 0:
            count = (
                0 if worker.get("context") is not None and not p["treatments"][arm][flag] else None
            )
        metrics[flag] = {
            "enabled": p["treatments"][arm][flag],
            "trigger_count": count,
            "status": "missing" if count is None else "observed",
            "metrics": observed,
        }
    metrics["events"] = (state or {}).get("events")
    return metrics


def first_request_identity(output):
    ledger_path = output / "usage.sqlite3"
    if not ledger_path.is_file():
        return None
    with LocalUsageLedger(ledger_path).connect() as db:
        row = db.execute(
            "SELECT payload FROM pre_send WHERE purpose='repair' ORDER BY sequence LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    body = json.loads(row[0])
    return {
        "instructions_sha256": digest(body.get("instructions")),
        "tools_sha256": digest(body.get("tools")),
        "input_sha256": digest(body.get("input")),
        "model": body.get("model"),
        "reasoning": body.get("reasoning"),
        "tool_names": sorted(tool["name"] for tool in body.get("tools", [])),
    }


def finish(m, row, output, *, failure=None, worker_exit=None, score_exit=None):
    worker = optional_json(output / "worker/result.json")
    score = optional_json(output / "score/score.json")
    usage = None
    if (output / "usage.sqlite3").is_file():
        try:
            ledger = LocalUsageLedger(output / "usage.sqlite3")
            usage = ledger.summary(row["attempt_id"])
            with ledger.connect() as db:
                db.row_factory = sqlite3.Row
                raw = [
                    dict(r)
                    for r in db.execute(
                        "SELECT * FROM requests WHERE attempt=? ORDER BY sent_at",
                        (row["attempt_id"],),
                    )
                ]
            save(output / "raw-usage.json", raw)
        except (sqlite3.Error, ValueError):
            failure = failure or "USAGE_LEDGER_UNREADABLE"
    stop = (
        worker.get("stop_reason")
        or worker.get("agent_stop_reason")
        or worker.get("native_reason")
        or (usage or {}).get("last_local_stop_reason")
    )
    accepted = score.get("accepted")
    classification = score.get("classification", "infrastructure")
    if failure:
        classification = "preparation" if failure == "PREPARATION_FAILED" else "infrastructure"
        accepted = None
    result = {
        "schema": "repropatch.context-ablation.result.v1",
        **row,
        "manifest_sha256": m["manifest_sha256"],
        "protocol_sha256": m["protocol_sha256"],
        "source_sha256": m["source_sha256"],
        "task_population": m["task_population"],
        "runner": load(output / "trial.json")["runner"],
        "runner_status": optional_json(output / "runner-status.json"),
        "cpa_claim": optional_json(output / "cpa/claim.json"),
        "classification": classification,
        "accepted": accepted,
        "failure": failure,
        "worker_exit": worker_exit,
        "score_exit": score_exit,
        "score": score,
        "usage": usage,
        "stop_reason": stop,
        "context_overflow": overflow_kind(stop, worker),
        "mechanisms": mechanism_metrics(worker, m["protocol"], row["arm"]),
        "first_request": first_request_identity(output),
        "prepared_identity": optional_json(output / "prepared-identity.json"),
        "candidate_sha256": sha(output / "worker/candidate.patch")
        if (output / "worker/candidate.patch").is_file()
        else None,
    }
    save(output / "summary.json", result)
    return result


def overflow_kind(stop, worker):
    values = [stop, worker.get("error_code"), worker.get("error_type")]
    for value in values:
        if value in OVERFLOWS:
            return value
        if value == "context_length_exceeded":
            return "PROVIDER_CONTEXT_LENGTH_EXCEEDED"
    return None


def usage_value(row, field):
    usage = row.get("usage")
    if not isinstance(usage, dict) or usage.get("unknown_usage_requests") != 0:
        return None
    value = usage.get(field)
    return value if type(value) is int and value >= 0 else None


def token_statistics(rows, field):
    values = [usage_value(row, field) for row in rows]
    known = [v for v in values if v is not None]
    return {
        "all_trial_mean": sum(known) / len(rows) if len(known) == len(rows) else None,
        "observed_trial_mean": sum(known) / len(known) if known else None,
        "observed_trials": len(known),
        "missing_trials": len(rows) - len(known),
        "known_trial_sum": sum(known),
    }


def input_identity_statistics(rows):
    result = []
    for task in sorted({row["instance_id"] for row in rows}):
        group = [row for row in rows if row["instance_id"] == task]
        identities = [row["first_request"] for row in group if row.get("first_request")]
        contracts = [row.get("prepared_identity", {}).get("task_sha256") for row in group]
        result.append(
            {
                "instance_id": task,
                "N": len(group),
                "first_requests_observed": len(identities),
                "first_requests_missing": len(group) - len(identities),
                "distinct_task_hashes": sorted({v for v in contracts if v}),
                "distinct_input_hashes": sorted({r["input_sha256"] for r in identities}),
                "distinct_instruction_hashes": sorted(
                    {r["instructions_sha256"] for r in identities}
                ),
                "distinct_tool_hashes": sorted({r["tools_sha256"] for r in identities}),
                "byte_identical_first_input": len({r["input_sha256"] for r in identities}) == 1
                if len(identities) == len(group)
                else None,
            }
        )
    return result


def arm_statistics(rows):
    n = len(rows)
    return {
        "N": n,
        "pass": sum(r.get("accepted") is True for r in rows),
        "fail": sum(r.get("accepted") is False for r in rows),
        "missing": sum(r["classification"] == "missing" for r in rows),
        "infrastructure": sum(
            r["classification"] in {"infrastructure", "preparation"} for r in rows
        ),
        "unknown_outcome": sum(r.get("accepted") is None for r in rows),
        "classifications": dict(Counter(r["classification"] for r in rows)),
        "input_tokens": token_statistics(rows, "input_tokens"),
        "output_tokens": token_statistics(rows, "output_tokens"),
        "context_overflows": dict(
            Counter(r["context_overflow"] for r in rows if r.get("context_overflow"))
        ),
        "stop_reasons": dict(Counter(r.get("stop_reason") or "missing" for r in rows)),
        "mechanisms": {
            flag: {
                "triggered_trials": sum(
                    (r.get("mechanisms", {}).get(flag, {}).get("trigger_count") or 0) > 0
                    for r in rows
                ),
                "observed_trials": sum(
                    r.get("mechanisms", {}).get(flag, {}).get("trigger_count") is not None
                    for r in rows
                ),
                "missing_trials": sum(
                    r.get("mechanisms", {}).get(flag, {}).get("trigger_count") is None for r in rows
                ),
                "coverage_denominator": n,
                "trigger_count": sum(
                    r.get("mechanisms", {}).get(flag, {}).get("trigger_count") or 0 for r in rows
                ),
            }
            for flag in FLAGS
        },
    }


def paired_statistics(rows, left, right):
    by_key = {(r["instance_id"], r["repeat"], r["arm"]): r for r in rows}
    pairs = []
    for task, repeat in sorted({(r["instance_id"], r["repeat"]) for r in rows}):
        a, b = by_key[task, repeat, left], by_key[task, repeat, right]
        valid = all(type(r.get("accepted")) is bool for r in (a, b))
        pair = {
            "instance_id": task,
            "repeat": repeat,
            "left_classification": a["classification"],
            "right_classification": b["classification"],
            "pass_difference": int(b["accepted"]) - int(a["accepted"]) if valid else None,
        }
        for field in ("input_tokens", "output_tokens"):
            av, bv = usage_value(a, field), usage_value(b, field)
            pair[field + "_difference"] = bv - av if av is not None and bv is not None else None
        pairs.append(pair)
    result = {"left": left, "right": right, "direction": "right_minus_left", "N": len(pairs)}
    for field in ("pass_difference", "input_tokens_difference", "output_tokens_difference"):
        known = [pair[field] for pair in pairs if pair[field] is not None]
        result[field] = {
            "all_pair_mean": sum(known) / len(pairs) if len(known) == len(pairs) else None,
            "observed_pair_mean": sum(known) / len(known) if known else None,
            "observed_pairs": len(known),
            "missing_pairs": len(pairs) - len(known),
        }
    result["pairs"] = pairs
    return result


def aggregate(args):
    m = read_manifest(args.manifest, args.protocol)
    require(getattr(args, "scope", None) in {None, m["scope"]}, "SCOPE_MISMATCH")
    expected = {r["attempt_id"]: r for r in m["attempts"]}
    found, rejected, statuses = {}, [], {}
    for path in sorted(args.source.rglob("runner-status.json")):
        try:
            observed = load(path)
        except (ValueError, OSError):
            continue
        matches = observed.get("manifest_sha256") == m["manifest_sha256"]
        if observed.get("manifest_sha256") is None:
            matches = bool(m["github_run_id"]) and all(
                observed.get(key) == value
                for key, value in (
                    ("run_id", m["github_run_id"]),
                    ("source_commit", m["source_commit"]),
                    ("scope", m["scope"]),
                )
            )
        if observed.get("attempt_id") in expected and matches:
            statuses.setdefault(observed["attempt_id"], []).append(observed)
    for path in sorted(args.source.rglob("summary.json")):
        try:
            row = load(path)
        except (ValueError, OSError):
            rejected.append({"path": str(path), "reason": "UNREADABLE_SUMMARY"})
            continue
        if row.get("schema") != "repropatch.context-ablation.result.v1":
            rejected.append({"path": str(path), "reason": "FOREIGN_RESULT"})
            continue
        key = row.get("attempt_id")
        if key not in expected or row.get("manifest_sha256") != m["manifest_sha256"]:
            rejected.append({"path": str(path), "reason": "FOREIGN_ATTEMPT_OR_MANIFEST"})
            continue
        found.setdefault(key, []).append(row)
    rows = []
    for key, frozen in expected.items():
        candidates = found.get(key, [])
        if len(candidates) == 1 and all(candidates[0].get(k) == v for k, v in frozen.items()):
            row = candidates[0]
            if row.get("source_sha256") != m["source_sha256"]:
                row = {
                    **frozen,
                    "classification": "infrastructure",
                    "accepted": None,
                    "failure": "SOURCE_IDENTITY_MISMATCH",
                    "usage": None,
                }
        elif candidates:
            row = {
                **frozen,
                "classification": "infrastructure",
                "accepted": None,
                "failure": "DUPLICATE_OR_MISMATCHED_RESULT",
                "usage": None,
            }
        else:
            recorded = statuses.get(key, [])
            row = {
                **frozen,
                "classification": "infrastructure" if recorded else "missing",
                "accepted": None,
                "failure": "INCOMPLETE_TRIAL" if recorded else "MISSING_SUMMARY",
                "usage": None,
                "runner_statuses": recorded,
            }
        rows.append(row)
    result = {
        "schema": "repropatch.context-ablation.aggregate.v1",
        "scope": m["scope"],
        "manifest_sha256": m["manifest_sha256"],
        "task_population": m["task_population"],
        "registered_trials": len(rows),
        "source_sha256": m["source_sha256"],
        "arms": {arm: arm_statistics([r for r in rows if r["arm"] == arm]) for arm in ARMS},
        "paired_differences": [
            paired_statistics(rows, a, b) for a, b in itertools.combinations(ARMS, 2)
        ],
        "attempts": rows,
        "rejected_artifacts": rejected,
        "automatic_reruns": 0,
        "input_identity": input_identity_statistics(rows),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / "results.json", result)
    lines = [
        "# Context Ablation",
        "",
        "Population: previously exposed development tasks.",
        "",
        "| Arm | N | Pass | Fail | Missing | Infra | Input mean | Output mean |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm, values in result["arms"].items():
        means = [values[k]["all_trial_mean"] for k in ("input_tokens", "output_tokens")]
        means = ["missing" if v is None else f"{v:.2f}" for v in means]
        lines.append(
            f"| {arm} | {values['N']} | {values['pass']} | {values['fail']} | "
            f"{values['missing']} | {values['infrastructure']} | {means[0]} | {means[1]} |"
        )
    lines += [
        "",
        "Means cover all registered trials; unknown usage remains missing.",
        "Observed-only means, every pair, overflow classes and mechanism coverage: results.json.",
    ]
    (args.output / "summary.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"registered_trials": len(rows), "output": str(args.output)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "prepare", "run", "aggregate"):
        sub = commands.add_parser(name)
        sub.add_argument("--protocol", type=Path, default=PROTOCOL)
        sub.add_argument("--output", type=Path, required=True)
        if name == "plan":
            sub.add_argument("--scope", choices=("smoke", "full"), required=True)
            sub.add_argument("--github-output", type=Path)
        else:
            sub.add_argument("--manifest", type=Path, required=True)
            sub.add_argument("--scope", choices=("smoke", "full"))
        if name in {"prepare", "run"}:
            selection = sub.add_mutually_exclusive_group(required=True)
            selection.add_argument("--attempt-id")
            selection.add_argument("--trial-index", type=int)
        if name == "aggregate":
            sub.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    return {"plan": plan, "prepare": prepare, "run": run, "aggregate": aggregate}[args.command](
        args
    )


if __name__ == "__main__":
    raise SystemExit(main())
