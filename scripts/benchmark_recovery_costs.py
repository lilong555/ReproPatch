"""Audit committed recovery prefixes and register fresh paired recovery trials."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import statistics
import tarfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

SCHEMA = "repropatch.recovery-cost-evidence.v1"
CAMPAIGN = "recovery-costs-20261107-v1"
STEPS = (3, 6, 12)
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_SELECTED_BYTES = 256 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(data)
    return value.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def json_value(data):
    return json.loads(data)


def seconds(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


@contextmanager
def open_database(data):
    db = sqlite3.connect(":memory:")
    try:
        db.deserialize(data)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLITE_INTEGRITY_ERROR")
        yield db
    finally:
        db.close()


def safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError("UNSAFE_ARCHIVE_PATH")
    return str(path)


def read_members(path):
    selected = {}
    size = 0
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            name = safe_name(member.name)
            keep = (
                name in {"summary.json", "worker/result.json", "usage.sqlite3"}
                or (
                    name.startswith("worker/runs/")
                    and name.endswith((".sqlite3", ".json", ".jsonl", ".diff", ".yaml"))
                )
                or (name.startswith("worker/http-native/") and name.endswith("-response.json"))
            )
            if not keep:
                continue
            if not member.isfile() or member.size > MAX_MEMBER_BYTES:
                raise ValueError("INVALID_EVIDENCE_MEMBER")
            size += member.size
            if size > MAX_SELECTED_BYTES or name in selected:
                raise ValueError("ARCHIVE_EVIDENCE_LIMIT_OR_DUPLICATE")
            selected[name] = archive.extractfile(member).read()
    return selected


def verify_ref(members, prefix, ref):
    name = prefix + "/" + safe_name(ref["path"])
    data = members.get(name)
    return data is not None and len(data) == ref["size_bytes"] and sha(data) == ref["sha256"]


def usage_sum(rows):
    known = [json_value(row["usage"]) for row in rows if row["usage"] is not None]
    missing = len(rows) - len(known)
    incoming = sum(row["input_tokens"] for row in known)
    outgoing = sum(row["output_tokens"] for row in known)
    cached = sum((row.get("input_tokens_details") or {}).get("cached_tokens", 0) for row in known)
    return {
        "requests": len(rows),
        "input_tokens": None if missing else incoming,
        "output_tokens": None if missing else outgoing,
        "cached_input_tokens": None if missing else cached,
        "known_input_tokens": incoming,
        "known_output_tokens": outgoing,
        "unknown_usage_requests": missing,
        "request_purposes": dict(Counter(row["purpose"] for row in rows)),
    }


def interval_sum(events, cutoff, start_type, end_type, identity):
    starts, intervals = {}, []
    missing, negative = 0, 0
    for event in events:
        if event["seq"] > cutoff:
            break
        key = event.get(identity)
        if event["type"] == start_type:
            starts[key] = event
        elif event["type"] == end_type:
            first = starts.pop(key, None)
            if first is None:
                missing += 1
                continue
            left, right = seconds(first["timestamp"]), seconds(event["timestamp"])
            if right < left:
                negative += 1
            else:
                intervals.append((left, right))
    merged = []
    for left, right in sorted(intervals):
        if merged and left <= merged[-1][1]:
            merged[-1][1] = max(right, merged[-1][1])
        else:
            merged.append([left, right])
    return {
        "completed": len(intervals),
        "elapsed_sum_s": sum(right - left for left, right in intervals),
        "busy_wall_s": sum(right - left for left, right in merged),
        "unmatched_started": len(starts),
        "unmatched_finished": missing,
        "negative_intervals": negative,
        "clock_basis": "persisted_utc_event_timestamp_deltas",
    }


def prefix_record(members, prefix, run, checkpoint, events, requests, target_step):
    base = {"target_step": target_step, "reachable": checkpoint is not None}
    if checkpoint is None:
        return base
    ref = json_value(checkpoint["manifest_ref_json"])
    if not verify_ref(members, prefix, ref):
        raise ValueError("CHECKPOINT_MANIFEST_HASH_MISMATCH")
    manifest = json_value(members[prefix + "/" + ref["path"]])
    commit_event = next(event for event in events if event["seq"] == checkpoint["event_seq"])
    expected = [
        manifest[key] for key in ("baseline", "native_next_input", "patch", "source_manifest")
    ]
    expected.append(manifest["input_fingerprints"]["configuration"])
    if "context_state" in manifest:
        expected.append(manifest["context_state"])
    integrity = all(verify_ref(members, prefix, value) for value in expected)
    identity = (
        manifest["boundary"] == "model_input_ready"
        and manifest["step_id"] == checkpoint["step_id"]
        and manifest["counters"]["steps_used"] == checkpoint["step_id"]
        and manifest["deadline_at"] == run["deadline_at"]
        and commit_event["type"] == "checkpoint_committed"
        and commit_event["payload"]["manifest_ref"] == ref
        and commit_event["payload"]["counters"] == manifest["counters"]
    )
    cutoff = checkpoint["event_seq"]
    cutoff_time = seconds(checkpoint["created_at"])
    prefix_requests = [row for row in requests if seconds(row["sent_at"]) <= cutoff_time]
    accounted = usage_sum(prefix_requests)
    tool_intervals = interval_sum(events, cutoff, "tool_started", "tool_finished", "tool_call_id")
    model_intervals = interval_sum(events, cutoff, "model_started", "model_finished", "step_id")
    finished = [
        event for event in events if event["seq"] <= cutoff and event["type"] == "model_finished"
    ]
    cumulative = finished[-1]["payload"]["cumulative_usage"] if finished else {}
    accounting_matches = (
        accounted["unknown_usage_requests"] == 0
        and cumulative.get("input_tokens") == accounted["input_tokens"]
        and cumulative.get("output_tokens") == accounted["output_tokens"]
    )
    total = usage_sum(requests)
    first_model = next((event for event in events if event["type"] == "model_started"), None)
    return {
        **base,
        "checkpoint_id": checkpoint["checkpoint_id"],
        "checkpoint_event_seq": cutoff,
        "checkpoint_member": prefix + "/" + ref["path"],
        "checkpoint_sha256": ref["sha256"],
        "step_id": checkpoint["step_id"],
        "boundary": manifest["boundary"],
        "committed_at": checkpoint["created_at"],
        "reference_integrity_verified": integrity,
        "committed_identity_verified": identity,
        "input_source_payloads_complete": integrity and identity,
        "source_tree_sha256": manifest["source_tree_sha256"],
        "patch_sha256": manifest["patch"]["sha256"],
        "saved_input_bytes": manifest["native_next_input"]["size_bytes"],
        "counters": manifest["counters"],
        "usage": accounted,
        "usage_matches_native_cumulative": accounting_matches,
        "tool_intervals": tool_intervals,
        "model_intervals": model_intervals,
        "prefix_wall_s": cutoff_time - seconds(run["created_at"]),
        "initial_baseline_and_setup_wall_s": None
        if first_model is None
        else seconds(first_model["timestamp"]) - seconds(run["created_at"]),
        "remaining_original_deadline_s_at_checkpoint": seconds(run["deadline_at"]) - cutoff_time,
        "protected_prefix_input_fraction": None
        if not total["input_tokens"] or accounted["input_tokens"] is None
        else accounted["input_tokens"] / total["input_tokens"],
        "protected_prefix_request_fraction": accounted["requests"] / total["requests"]
        if total["requests"]
        else None,
    }


def audit_artifact(artifact, raw_root, now, selected_steps=STEPS):
    row = {
        "artifact_name": artifact["name"],
        "artifact_id": artifact["id"],
        "artifact_url": artifact["url"],
        "archive_zip_sha256": artifact["digest"].removeprefix("sha256:"),
        "status": "error",
    }
    try:
        folder = raw_root / artifact["name"]
        receipt = json.loads((folder / "download.json").read_text())
        if receipt["sha256"] != row["archive_zip_sha256"]:
            raise ValueError("DOWNLOAD_IDENTITY_MISMATCH")
        candidates = [m for m in receipt["members"] if m["path"].endswith(".tar.gz")]
        if len(candidates) != 1:
            raise ValueError("RAW_ARCHIVE_COUNT")
        archive_ref = candidates[0]
        archive = folder / safe_name(archive_ref["path"])
        if file_sha(archive) != archive_ref["sha256"]:
            raise ValueError("RAW_ARCHIVE_HASH_MISMATCH")
        members = read_members(archive)
        summary = json_value(members["summary.json"])
        worker = json_value(members["worker/result.json"])
        prefix = "worker/runs/" + worker["native_run_id"]
        events = [
            json_value(line) for line in members[prefix + "/events.jsonl"].splitlines() if line
        ]
        with open_database(members[prefix + "/events.sqlite3"]) as db:
            run = dict(db.execute("SELECT * FROM runs").fetchone())
            checkpoints = [
                dict(cp) for cp in db.execute("SELECT * FROM checkpoints ORDER BY event_seq")
            ]
            sqlite_events = [
                json_value(row[0])
                for row in db.execute("SELECT envelope_json FROM events ORDER BY seq")
            ]
            event_count = len(sqlite_events)
        if sqlite_events != events:
            raise ValueError("EVENT_PROJECTION_MISMATCH")
        if event_count != len(events) or [event["seq"] for event in events] != list(
            range(1, event_count + 1)
        ):
            raise ValueError("EVENT_SEQUENCE_MISMATCH")
        with open_database(members["usage.sqlite3"]) as db:
            requests = [
                dict(value)
                for value in db.execute(
                    "SELECT * FROM requests WHERE attempt=? ORDER BY sent_at,id",
                    (summary["attempt_id"],),
                )
            ]
        for request in requests:
            raw_response = members.get("worker/http-native/" + request["id"] + "-response.json")
            if raw_response is None or sha(raw_response) != request["response_sha256"]:
                raise ValueError("PROVIDER_RESPONSE_HASH_MISMATCH")
            expected_usage = json_value(raw_response).get("usage")
            if request["usage"] is not None and json_value(request["usage"]) != expected_usage:
                raise ValueError("PROVIDER_USAGE_MISMATCH")
        prefixes = []
        for target in selected_steps:
            checkpoint = next((cp for cp in checkpoints if cp["step_id"] >= target), None)
            prefixes.append(
                prefix_record(members, prefix, run, checkpoint, events, requests, target)
            )
        full = usage_sum(requests)
        closed = run["state"] == "FINISHED"
        expired = seconds(run["deadline_at"]) <= now
        return {
            **row,
            "status": "audited",
            "instance_id": summary["instance_id"],
            "arm": summary["arm"],
            "repeat": summary["repeat"],
            "attempt_id": summary["attempt_id"],
            "source_commit": "2597016d80ea47c8bbc06c93598093c307a24ee7",
            "run_id": run["run_id"],
            "run_state": run["state"],
            "outcome": run["outcome"],
            "stop_reason": summary["stop_reason"],
            "cold_accepted": summary["accepted"],
            "archive_tar_sha256": archive_ref["sha256"],
            "sqlite_sha256": sha(members[prefix + "/events.sqlite3"]),
            "usage_sqlite_sha256": sha(members["usage.sqlite3"]),
            "event_count": event_count,
            "checkpoint_count": len(checkpoints),
            "model_steps": run["steps_used"],
            "tool_calls": run["tool_calls_admitted"],
            "created_at": run["created_at"],
            "original_deadline_at": run["deadline_at"],
            "historical_run_terminal": closed,
            "historical_deadline_elapsed": expired,
            "archive_control_directory_identity": (
                "original_inode_identity_not_reproduced_by_unpacking"
            ),
            "direct_resume_admissible_now": False,
            "direct_resume_exclusion_reasons": (["terminal_run"] if closed else [])
            + (["original_deadline_elapsed"] if expired else [])
            + ["archived_control_directory_identity"],
            "usage": full,
            "usage_matches_published_summary": all(
                full[key] == summary["usage"][key]
                for key in ("requests", "input_tokens", "output_tokens", "cached_input_tokens")
            ),
            "prefixes": prefixes,
        }
    except Exception as exc:
        return {**row, "error_type": type(exc).__name__, "error": str(exc)}


def distribution(values):
    values = sorted(value for value in values if value is not None)
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "sum": sum(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": values[0],
        "max": values[-1],
    }


def aggregate(rows):
    valid = [row for row in rows if row["status"] == "audited"]
    result = {
        "expected": len(rows),
        "audited": len(valid),
        "errors": len(rows) - len(valid),
        "tasks": len({row["instance_id"] for row in valid}),
        "cold_accepted": sum(row["cold_accepted"] for row in valid),
        "usage_matches_published_summary": sum(
            row["usage_matches_published_summary"] for row in valid
        ),
        "direct_resume_admissible_now": sum(row["direct_resume_admissible_now"] for row in valid),
        "prefixes": {},
    }
    for field in ("requests", "input_tokens", "output_tokens", "cached_input_tokens"):
        result[field] = distribution([row["usage"][field] for row in valid])
    for step in STEPS:
        prefixes = [
            prefix
            for row in valid
            for prefix in row["prefixes"]
            if prefix["target_step"] == step and prefix["reachable"]
        ]
        result["prefixes"][str(step)] = {
            "reachable": len(prefixes),
            "payload_integrity_verified": sum(
                p["input_source_payloads_complete"] for p in prefixes
            ),
            "usage_matches_native_cumulative": sum(
                p["usage_matches_native_cumulative"] for p in prefixes
            ),
            **{
                field: distribution([p["usage"][field] for p in prefixes])
                for field in ("requests", "input_tokens", "output_tokens", "cached_input_tokens")
            },
            **{
                field: distribution([p[field] for p in prefixes])
                for field in (
                    "prefix_wall_s",
                    "protected_prefix_input_fraction",
                    "protected_prefix_request_fraction",
                    "remaining_original_deadline_s_at_checkpoint",
                )
            },
            "tool_elapsed_sum_s": distribution(
                [p["tool_intervals"]["elapsed_sum_s"] for p in prefixes]
            ),
        }
    return result


def write_records(path, rows):
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    )


def audit(args):
    index = json.loads(args.artifacts_index.read_text())
    artifacts = index["raw_artifacts"][: args.limit] if args.limit else index["raw_artifacts"]
    now = datetime.now(UTC)
    args.output.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(
            pool.map(lambda item: audit_artifact(item, args.raw_root, now.timestamp()), artifacts)
        )
    write_records(args.output / "attempts.jsonl", rows)
    flat = []
    for row in rows:
        for prefix in row.get("prefixes", []):
            record = {
                key: row[key]
                for key in (
                    "instance_id",
                    "arm",
                    "repeat",
                    "attempt_id",
                    "cold_accepted",
                    "artifact_url",
                )
            }
            record.update(
                {key: value for key, value in prefix.items() if not isinstance(value, (dict, list))}
            )
            record.update(
                {
                    "prefix_" + key: value
                    for key, value in prefix.get("usage", {}).items()
                    if not isinstance(value, (dict, list))
                }
            )
            flat.append(record)
    fields = sorted({key for row in flat for key in row})
    with (args.output / "prefixes.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(flat)
    summary = {
        "schema": SCHEMA,
        "kind": "historical_prefix_accounting",
        "source_run_id": index["run_id"],
        "source_commit": index["source_commit"],
        "generated_at": now.isoformat(),
        "script_sha256": file_sha(Path(__file__)),
        "index_sha256": file_sha(args.artifacts_index),
        "prefix_rule": "first committed model_input_ready checkpoint after model step 3, 6, or 12",
        "new_model_requests": 0,
        "historical_clock_basis": "persisted_utc_event_timestamp_deltas",
        "overall": aggregate(rows),
        "groups": {
            arm: aggregate([row for row in rows if row.get("arm") == arm])
            for arm in ("baseline", "diagnostics", "dedup", "state", "combined")
        },
        "errors": [row for row in rows if row["status"] != "audited"],
    }
    write_json(args.output / "summary.json", summary)
    print(
        json.dumps(
            {
                "expected": len(rows),
                "audited": summary["overall"]["audited"],
                "errors": summary["overall"]["errors"],
            }
        ),
        flush=True,
    )
    return int(bool(summary["errors"]))


def register(args):
    results = json.loads(args.results.read_text())
    rows = results.get("attempts", results.get("results", []))
    if not rows:
        raise ValueError("RESULT_ATTEMPTS_MISSING")
    tasks = sorted(
        {row["instance_id"] for row in rows}, key=lambda name: sha(("recovery-v1/" + name).encode())
    )
    selected = tasks[: args.tasks]
    pairs = [
        {
            "instance_id": task,
            "repeat": repeat,
            "pair_id": f"pair-{ordinal:02d}-r{repeat}",
            "resume_attempt": f"{CAMPAIGN}/full/{task}/resume/repeat-{repeat}",
            "restart_attempt": f"{CAMPAIGN}/full/{task}/restart/repeat-{repeat}",
        }
        for ordinal, task in enumerate(selected, 1)
        for repeat in (1, 2)
    ]
    root = Path(__file__).resolve().parents[1]
    sources = sorted((root / "src").rglob("*.py")) + sorted((root / "scripts").glob("*.py"))
    sources += [root / "pyproject.toml", root / "requirements/agent.txt"]
    manifest = {
        "schema": SCHEMA,
        "campaign": CAMPAIGN,
        "model": "gpt-6-luna",
        "reasoning_effort": "max",
        "source_commit": "1841f6e97ced42d9c914ac494b0e5ab8a0c388f5",
        "source_files_sha256": {str(path.relative_to(root)): file_sha(path) for path in sources},
        "preparation_protocol": "benchmarks/context-ablation/protocol.json",
        "preparation_protocol_sha256": file_sha(root / "benchmarks/context-ablation/protocol.json"),
        "selection": {
            "basis": "ascending SHA256('recovery-v1/' + task_id)",
            "all_tasks": tasks,
            "selected": selected,
        },
        "pairs": pairs,
        "local_concurrency": 1,
        "queue_after_run": 42335967622,
        "pause_after_step": 3,
        "request_cap": 24,
        "post_failure_request_cap": 21,
        "per_pair_max_actual_requests": 45,
        "tool_cap": 48,
        "restart_tool_cap_rule": "48 minus tools admitted at the committed checkpoint",
        "total_seconds": 7200,
        "model_timeout_seconds": 600,
        "cpa_allocation_per_attempt": 24,
        "cpa_max_reserved_requests": len(pairs) * 48,
        "max_actual_requests": len(pairs) * 45,
        "arm_execution_order": (
            "shared real prefix; resume in a fresh process immediately; "
            "restart in another fresh process; cold scoring after both terminate"
        ),
        "post_failure_time_rule": (
            "restart receives floor(original_deadline - checkpoint_commit_time) seconds; "
            "resume preserves original absolute deadline; its process startup delay is reported"
        ),
        "comparison": (
            "resume continues its original 24-request ledger after 3 requests; "
            "restart receives the same remaining 21-request allowance from the base source; "
            "report complete quality and cost pairs"
        ),
        "primary_metrics": [
            "cold_accepted",
            "post_failure_input_tokens",
            "post_failure_model_requests",
            "restore_to_model_admission_seconds",
            "post_failure_elapsed_seconds",
        ],
        "accounting": (
            "shared prefix reported once; actual post-failure requests and auxiliary usage summed; "
            "cached input included in input and also shown separately"
        ),
        "missing_checkpoint": "retain no_checkpoint with consumed cost",
        "source_results_sha256": file_sha(args.results),
    }
    write_json(args.output, manifest)
    print(
        json.dumps(
            {
                "campaign": CAMPAIGN,
                "tasks": selected,
                "pairs": len(pairs),
                "max_allocated_requests": len(pairs) * 48,
            }
        ),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("audit")
    p.add_argument("--artifacts-index", type=Path, required=True)
    p.add_argument("--raw-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--workers", type=int, choices=(1, 2, 3, 4), default=2)
    p.add_argument("--limit", type=int)
    p.set_defaults(handler=audit)
    p = sub.add_parser("register")
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--tasks", type=int, choices=(2,), default=2)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(handler=register)
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
