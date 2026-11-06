"""Recompute frozen evidence and exercise an isolated public runtime without paid models."""

from __future__ import annotations

import argparse
import copy
import csv
import gzip
import hashlib
import importlib.metadata
import io
import json
import platform
import re
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tarfile
import time
import traceback
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

COMMIT = "9cf01099206131ba6f984661a97f7aa65ee8b68a"
ARMS = ("full", "no-checks", "shell-only", "mini", "codex")
PACKAGE = Path(__file__).resolve().parents[1] / "benchmarks/runtime-evidence-20261106/public-inputs"
AUDIT = PACKAGE / "audit-index.json"
SOURCE_INPUTS = (
    "benchmarks/unified-context/final-results.json",
    "docs/evidence/context-unified-2026-10-27/final-campaign-verification.json",
    "benchmarks/context-formal-protocol.json",
    "benchmarks/actions-scale/cloud-results.json",
)
REQUEST = re.compile(r"(?:^|/)[0-9a-f]{32}-request\.json$")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def append(path, value):
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def table(path, rows):
    if not rows:
        Path(path).touch(exist_ok=False)
        return
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                    for k, v in row.items()
                }
            )


def source_identity(source):
    entries = {
        str(p.relative_to(source)): file_sha(p)
        for p in sorted((source / "src/repropatch").rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }
    return {"files": entries, "sha256": digest(json.dumps(entries, sort_keys=True).encode())}


def activate(source):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source / "src"))
    import repropatch.harness

    assert Path(repropatch.harness.__file__).resolve().is_relative_to(source.resolve())


def freeze(args):
    source = args.source
    manifest = {
        "frozen_at": datetime.now(UTC).isoformat(),
        "source_commit": COMMIT,
        "protocol_sha256": file_sha(args.output / "protocol.json"),
        "driver_sha256": file_sha(__file__),
        "source": source_identity(source),
        "inputs": {},
    }
    for path in (
        source / "benchmarks/unified-context/final-results.json",
        source / "docs/evidence/context-unified-2026-10-27/final-campaign-verification.json",
        source / "benchmarks/context-formal-protocol.json",
        source / "benchmarks/actions-scale/cloud-results.json",
        args.audit_index,
    ):
        manifest["inputs"][str(path)] = file_sha(path)
    save(args.output / "frozen-inputs.json", manifest)
    return manifest


def selected_rows(final):
    selected = [r for r in final["attempts"] if r["instance_id"] in final["paired_tasks"]]
    assert len(selected) == 95 and len(final["paired_tasks"]) == 19
    assert Counter(r["arm"] for r in selected) == dict.fromkeys(ARMS, 19)
    assert len({r["attempt_id"] for r in selected}) == 95
    return sorted(selected, key=lambda r: r["attempt_id"])


def observed_stage(score):
    status = score.get("status", "MISSING")
    return {
        "ORACLE_PASSED": "oracle_passed",
        "ORACLE_BUILD_FAILED": "oracle_build_failed",
        "ORACLE_TESTS_FAILED": "oracle_tests_failed",
    }.get(status, "other:" + status)


def coverage(values):
    known = [v for v in values if type(v) in (int, float)]
    return {
        "sum": sum(known),
        "n": len(known),
        "denominator": len(values),
        "median": statistics.median(known) if known else None,
    }


def aggregate(rows):
    result = {}
    for arm in ARMS:
        group = [r for r in rows if r["arm"] == arm]
        result[arm] = {
            "n": len(group),
            "tasks": len({r["instance_id"] for r in group}),
            "passed": sum(r["oracle_result"] == "PASS" for r in group),
            "stages": dict(Counter(r["observed_stage"] for r in group)),
            "stops": dict(Counter(r["stop_reason"] for r in group)),
            "versions": dict(Counter(r.get("execution_source_commit") or "unknown" for r in group)),
            "metrics": {
                key: coverage([r.get(key) for r in group])
                for key in (
                    "requests",
                    "input_tokens",
                    "output_tokens",
                    "unknown_usage_requests",
                    "tool_calls",
                    "worker_seconds",
                    "self_check_seconds",
                    "cold_oracle_seconds",
                    "compaction_count",
                    "compact_requests",
                )
            },
        }
    return result


def tar_bytes(tar, name):
    stream = tar.extractfile(name)
    if stream is None:
        raise ValueError(f"not a regular archive member: {name}")
    return stream.read()


def archive_path(index_path, reference):
    path = Path(reference.get("archive") or reference["local_paths"][0])
    return path if path.is_absolute() else (Path(index_path).resolve().parent / path).resolve()


def archive_index(args):
    return {r["attempt_id"]: r for r in load(args.audit_index)["fmt_paid_local_archives"]}


def history(args, out):
    final = load(args.source / "benchmarks/unified-context/final-results.json")
    selected = selected_rows(final)
    archives = archive_index(args)
    rows, contexts, models, tools, errors = [], [], [], [], []
    best = {}
    for ordinal, original in enumerate(selected, 1):
        arm, aid = original["arm"], original["attempt_id"]
        row = {
            "instance_id": original["instance_id"],
            "arm": arm,
            "attempt_id": aid,
            "original_attempt_id": original.get("original_attempt_id"),
            "split": "exposed-development",
            "stop_reason": original["stop_reason"],
            "oracle_result": original["oracle_result"],
            "score_status": original["score"]["status"],
            "observed_stage": observed_stage(original["score"]),
            "score": original["score"],
            "usage": original["usage"],
            "metrics": original["metrics"],
            **original["usage"],
            **original["metrics"],
        }
        for i, event in enumerate(original["metrics"].get("compactions", [])):
            contexts.append(
                {
                    "attempt_id": aid,
                    "arm": arm,
                    "event_index": i,
                    "source": "final-results.json attempts[].metrics.compactions",
                    **event,
                }
            )
        ref = archives[aid]
        path = archive_path(args.audit_index, ref)
        row.update(
            archive=str(path),
            archive_sha256=file_sha(path),
            archive_verified=file_sha(path) == ref["sha256"],
        )
        if ref.get("original_archive_sha256"):
            row["original_archive_sha256"] = ref["original_archive_sha256"]
        try:
            assert row["archive_verified"], "ARCHIVE_HASH_MISMATCH"
            with tarfile.open(path, "r:gz") as tar:
                members = {m.name: m for m in tar.getmembers() if m.isfile()}
                provenance = json.loads(tar_bytes(tar, "provenance.json"))
                row["provenance"] = provenance
                row["execution_source_commit"] = (
                    original.get("execution_source_commit")
                    or provenance.get("frozen_execution_commit")
                    or provenance.get("source_commit")
                )
                row["packaging_source_commit"] = provenance.get("source_commit")
                worker_bytes = tar_bytes(tar, f"{arm}/result.json")
                worker = json.loads(worker_bytes)
                row["worker_sha256"] = digest(worker_bytes)
                row["worker_hash_matches_score"] = digest(worker_bytes) == original["score"].get(
                    "worker_result_sha256"
                )
                row["native_run_id"] = worker.get("native_run_id")
                row["native_context"] = worker.get("context")
                native_events = []
                for member in members:
                    if member.startswith(f"{arm}/runs/") and member.endswith("/events.jsonl"):
                        for line in tar_bytes(tar, member).splitlines():
                            event = json.loads(line)
                            native_events.append(event)
                            if event["type"] in {"tool_started", "tool_finished"}:
                                tools.append(
                                    {"attempt_id": aid, "arm": arm, "member": member, **event}
                                )
                row["native_event_counts"] = dict(Counter(e["type"] for e in native_events))
                raw_requests = []
                for member in sorted(members):
                    if not member.startswith(f"{arm}/http-native/") or not REQUEST.search(member):
                        continue
                    body_bytes = tar_bytes(tar, member)
                    body = json.loads(body_bytes)
                    response_member = member.removesuffix("-request.json") + "-response.json"
                    response = (
                        json.loads(tar_bytes(tar, response_member))
                        if response_member in members
                        else {}
                    )
                    usage = response.get("usage") or {}
                    output = response.get("output") or []
                    calls = [
                        x for x in output if x.get("type") in ("function_call", "custom_tool_call")
                    ]
                    mr = {
                        "attempt_id": aid,
                        "arm": arm,
                        "request_id": Path(member).name.removesuffix("-request.json"),
                        "request_member": member,
                        "response_member": response_member,
                        "request_sha256": digest(body_bytes),
                        "request_bytes": len(body_bytes),
                        "model": body.get("model"),
                        "reasoning": body.get("reasoning"),
                        "input_tokens": usage.get("input_tokens"),
                        "output_tokens": usage.get("output_tokens"),
                        "cached_input_tokens": (usage.get("input_tokens_details") or {}).get(
                            "cached_tokens"
                        ),
                        "tool_calls_in_response": len(calls),
                        "tool_names": [x.get("name") for x in calls],
                    }
                    raw_requests.append(mr)
                    models.append(mr)
                    for idx, item in enumerate(body.get("input") or []):
                        if not isinstance(item, dict) or item.get("type") not in (
                            "function_call_output",
                            "custom_tool_call_output",
                        ):
                            continue
                        text = item.get("output")
                        if not isinstance(text, str) or len(text.encode()) <= 24576:
                            continue
                        sha = digest(text.encode())
                        key = (-len(text.encode()), aid, member, idx)
                        if sha in best and best[sha]["rank"] <= key:
                            continue
                        candidate = {
                            "rank": key,
                            "attempt_id": aid,
                            "arm": arm,
                            "archive": str(path),
                            "archive_sha256": ref["sha256"],
                            "request_member": member,
                            "request_sha256": digest(body_bytes),
                            "item_index": idx,
                            "output_sha256": sha,
                            "output_bytes": len(text.encode()),
                            "original_provider_usage": usage,
                            "body": body,
                        }
                        best[sha] = candidate
                        if len(best) > 6:
                            worst = max(best, key=lambda x: best[x]["rank"])
                            del best[worst]
                row["raw_request_count"] = len(raw_requests)
                row["raw_input_tokens"] = coverage([r["input_tokens"] for r in raw_requests])
                row["raw_output_tokens"] = coverage([r["output_tokens"] for r in raw_requests])
                row["raw_usage_matches"] = (
                    len(raw_requests) == row["requests"]
                    and row["raw_input_tokens"]["n"] == len(raw_requests)
                    and row["raw_output_tokens"]["n"] == len(raw_requests)
                    and row["raw_input_tokens"]["sum"] == row["input_tokens"]
                    and row["raw_output_tokens"]["sum"] == row["output_tokens"]
                )
        except Exception as exc:
            error = {"attempt_id": aid, "error": repr(exc), "traceback": traceback.format_exc()}
            errors.append(error)
            row["error"] = repr(exc)
        rows.append(row)
        append(out / "attempts.jsonl", row)
        print(f"history {ordinal}/95 {arm} {row['instance_id']}", flush=True)
    for event in contexts:
        event["execution_source_commit"] = next(
            r.get("execution_source_commit") for r in rows if r["attempt_id"] == event["attempt_id"]
        )
    for name, records in (("models", models), ("context-events", contexts), ("tools", tools)):
        for record in records:
            append(out / f"{name}.jsonl", record)
        table(out / f"{name}.csv", records)
    flat = [
        {
            k: v
            for k, v in r.items()
            if k not in {"score", "usage", "metrics", "provenance", "compactions", "native_context"}
        }
        for r in rows
    ]
    table(out / "attempts.csv", flat)
    table(out / "failures.csv", [r for r in flat if r["oracle_result"] != "PASS"])
    for idx, candidate in enumerate(sorted(best.values(), key=lambda r: r["rank"]), 1):
        save(out / "projection-inputs" / f"{idx:02d}.json", candidate)
    summary = {
        "selected_n": len(rows),
        "tasks": 19,
        "split": "exposed-development",
        "passed": sum(r["oracle_result"] == "PASS" for r in rows),
        "paid_history_n": len(final["campaign_paid_history"]),
        "paid_history_usage": final.get("campaign_usage"),
        "groups": aggregate(rows),
        "archive_verified_n": sum(r["archive_verified"] for r in rows),
        "raw_usage_matches_n": sum(r.get("raw_usage_matches", False) for r in rows),
        "worker_hash_matches_n": sum(r.get("worker_hash_matches_score", False) for r in rows),
        "raw_requests": len(models),
        "raw_request_ids_unique": len({r["request_id"] for r in models}),
        "context_events": len(contexts),
        "native_tool_events": len(tools),
        "projection_candidates": len(best),
        "errors": errors,
    }
    save(out / "summary.json", summary)
    return summary


def project_request(body, index, directory, maximum=24576):
    from repropatch.artifacts import EvidenceRef
    from repropatch.context import complete_rounds, encoded, fold_tool_output, visible

    before = complete_rounds(body["input"])
    projected = copy.deepcopy(body)
    text = body["input"][index]["output"]
    references = []

    def archive(raw):
        ref = EvidenceRef.save(directory, "full-output.bin", raw)
        references.append(ref)
        return ref.path

    projected["input"][index]["output"] = fold_tool_output(text, maximum, archive)
    after = complete_rounds(projected["input"])
    without_output = copy.deepcopy(projected)
    without_output["input"][index]["output"] = text
    result = {
        "original_output_bytes": len(text.encode()),
        "projected_output_bytes": len(projected["input"][index]["output"].encode()),
        "original_request_bytes": len(encoded(body)),
        "projected_request_bytes": len(encoded(projected)),
        "original_visible_request_bytes": len(encoded(visible(body))),
        "projected_visible_request_bytes": len(encoded(visible(projected))),
        "boundaries_equal": before == after,
        "non_output_fields_preserved": without_output == body,
        "attachment_roundtrip": all(
            r.read(directory, limit=32 * 1024 * 1024) == text.encode() for r in references
        ),
        "attachment_count": len(references),
        "references": [asdict(r) for r in references],
        "projected_provider_input_tokens": None,
        "new_paid_requests": 0,
    }
    return projected, result


def projection(args, out):
    rows = []
    for path in sorted((args.output / "history/projection-inputs").glob("*.json")):
        sample = load(path)
        directory = out / path.stem
        directory.mkdir()
        row = {k: v for k, v in sample.items() if k != "body"}
        try:
            projected, result = project_request(sample["body"], sample["item_index"], directory)
            save(directory / "original-request.json", sample["body"])
            save(directory / "projected-request.json", projected)
            row.update(result, status="measured")
        except Exception as exc:
            row.update(status="error", error=repr(exc), traceback=traceback.format_exc())
        rows.append(row)
        save(directory / "result.json", row)
    good = [r for r in rows if r["status"] == "measured"]
    summary = {
        "registered_n": 6,
        "selected_n": len(rows),
        "measured_n": len(good),
        "attachment_roundtrip_n": sum(r["attachment_roundtrip"] for r in good),
        "protocol_preserved_n": sum(
            r["boundaries_equal"] and r["non_output_fields_preserved"] for r in good
        ),
        "original_output_bytes": sum(r["original_output_bytes"] for r in good),
        "projected_output_bytes": sum(r["projected_output_bytes"] for r in good),
        "new_paid_requests": 0,
        "projected_provider_input_tokens": None,
        "rows": rows,
    }
    table(out / "samples.csv", rows)
    save(out / "summary.json", summary)
    return summary


def reconcile(args, out):
    rows, requests = [], []
    originals = [
        json.loads(line)
        for line in (args.output / "history/attempts.jsonl").read_text().splitlines()
    ]
    archives = archive_index(args)
    for original in originals:
        reference = archives[original["attempt_id"]]
        path = archive_path(args.audit_index, reference)
        assert file_sha(path) == reference["sha256"]
        with tarfile.open(path) as tar:
            raw = tar_bytes(tar, f"ledgers/{original['arm']}.sqlite3")
            connection = sqlite3.connect(":memory:")
            connection.deserialize(raw)
            connection.row_factory = sqlite3.Row
            issued = [dict(r) for r in connection.execute("SELECT * FROM requests ORDER BY id")]
            presend = [
                dict(r)
                for r in connection.execute(
                    "SELECT id,sequence,purpose,issued,telemetry FROM pre_send ORDER BY sequence"
                )
            ]
            connection.close()
        parsed = []
        for r in issued:
            usage = json.loads(r["usage"]) if r["usage"] else None
            r.update(usage=usage, attempt_id=original["attempt_id"], arm=original["arm"])
            requests.append(r)
            parsed.append(usage)
        totals = {
            key: coverage([(u or {}).get(key) for u in parsed])
            for key in ("input_tokens", "output_tokens")
        }
        row = {
            "attempt_id": original["attempt_id"],
            "arm": original["arm"],
            "execution_source_commit": original["execution_source_commit"],
            "archive": str(path),
            "archive_sha256": reference["sha256"],
            "ledger_member": f"ledgers/{original['arm']}.sqlite3",
            "ledger_sha256": digest(raw),
            "issued_requests": len(issued),
            "presend_rows": len(presend),
            "unissued_presend": [p for p in presend if not p["issued"]],
            "purpose_counts": dict(Counter(r["purpose"] for r in issued)),
            "totals": totals,
            "usage_matches": len(issued) == original["requests"]
            and all(
                totals[k]["sum"] == original[k] and totals[k]["n"] == len(issued) for k in totals
            ),
        }
        rows.append(row)
        append(out / "attempts.jsonl", row)
    for row in requests:
        append(out / "requests.jsonl", row)
    table(out / "attempts.csv", rows)
    summary = {
        "attempts": len(rows),
        "usage_matches_n": sum(r["usage_matches"] for r in rows),
        "issued_requests": sum(r["issued_requests"] for r in rows),
        "unissued_presend": sum(len(r["unissued_presend"]) for r in rows),
        "purpose_counts": dict(Counter(r["purpose"] for r in requests)),
        "input_tokens": sum(r["totals"]["input_tokens"]["sum"] for r in rows),
        "output_tokens": sum(r["totals"]["output_tokens"]["sum"] for r in rows),
        "unknown_usage_requests": sum(r["usage"] is None for r in requests),
    }
    save(out / "summary.json", summary)
    return summary


def raw_projection(args, out):
    from repropatch.task import canonical_json

    originals = [
        json.loads(line)
        for line in (args.output / "history/attempts.jsonl").read_text().splitlines()
    ]
    best = {}
    archives = archive_index(args)
    for original in originals:
        if original["arm"] not in ("full", "no-checks", "shell-only"):
            continue
        reference = archives[original["attempt_id"]]
        path = archive_path(args.audit_index, reference)
        assert file_sha(path) == reference["sha256"]
        with tarfile.open(path) as tar:
            for member in tar.getmembers():
                if (
                    not member.isfile()
                    or not member.name.startswith(original["arm"] + "/runs/")
                    or "/agent/tool-results/" not in member.name
                    or member.size <= 24576
                ):
                    continue
                raw = tar_bytes(tar, member.name)
                text = canonical_json(json.loads(raw)).decode()
                size, sha = len(text.encode()), digest(text.encode())
                if size <= 24576:
                    continue
                key = (-size, original["attempt_id"], member.name)
                if sha in best and best[sha]["rank"] <= key:
                    continue
                best[sha] = {
                    "rank": key,
                    "attempt_id": original["attempt_id"],
                    "arm": original["arm"],
                    "archive": str(path),
                    "archive_sha256": reference["sha256"],
                    "execution_source_commit": original["execution_source_commit"],
                    "member": member.name,
                    "member_sha256": digest(raw),
                    "text": text,
                }
                if len(best) > 6:
                    del best[max(best, key=lambda x: best[x]["rank"])]
    rows = []
    for index, sample in enumerate(sorted(best.values(), key=lambda s: s["rank"]), 1):
        directory = out / f"{index:02d}"
        directory.mkdir()
        row = {k: v for k, v in sample.items() if k != "text"}
        try:
            with tarfile.open(sample["archive"]) as tar:
                root = sample["member"].split("/agent/tool-results/")[0]
                events = [
                    json.loads(line) for line in tar_bytes(tar, root + "/events.jsonl").splitlines()
                ]
                event = next(
                    e
                    for e in events
                    if e["type"] == "tool_finished"
                    and root + "/" + e["payload"]["result_ref"]["path"] == sample["member"]
                )
                call_id = event["payload"]["provider_call_id"]
                found = None
                for member in sorted(tar.getnames()):
                    if not member.startswith(sample["arm"] + "/http-native/") or not REQUEST.search(
                        member
                    ):
                        continue
                    body = json.loads(tar_bytes(tar, member))
                    for i, item in enumerate(body.get("input") or []):
                        if (
                            isinstance(item, dict)
                            and item.get("type") == "function_call_output"
                            and item.get("call_id") == call_id
                        ):
                            found = member, body, i
                            break
                    if found:
                        break
                if found is None:
                    raise ValueError("NO_ARCHIVED_NEXT_PROVIDER_INPUT_FOR_TOOL_RESULT")
                member, body, i = found
                save(directory / "historical-provider-request.json", body)
                unfolded = copy.deepcopy(body)
                unfolded["input"][i]["output"] = sample["text"]
                projected, result = project_request(unfolded, i, directory)
                save(directory / "unfolded-request.json", unfolded)
                save(directory / "projected-request.json", projected)
                response = json.loads(
                    tar_bytes(tar, member.removesuffix("-request.json") + "-response.json")
                )
                row.update(
                    result,
                    status="measured",
                    request_member=member,
                    tool_finished_seq=event["seq"],
                    call_id=call_id,
                    historical_provider_usage=response.get("usage"),
                    unfolded_provider_input_tokens=None,
                )
        except Exception as exc:
            row.update(status="error", error=repr(exc), traceback=traceback.format_exc())
        save(directory / "result.json", row)
        rows.append(row)
    good = [r for r in rows if r["status"] == "measured"]
    summary = {
        "registered_n": 6,
        "selected_n": len(rows),
        "measured_n": len(good),
        "attachment_roundtrip_n": sum(r["attachment_roundtrip"] for r in good),
        "protocol_preserved_n": sum(
            r["boundaries_equal"] and r["non_output_fields_preserved"] for r in good
        ),
        "original_output_bytes": sum(r["original_output_bytes"] for r in good),
        "projected_output_bytes": sum(r["projected_output_bytes"] for r in good),
        "new_paid_requests": 0,
        "projected_provider_input_tokens": None,
        "rows": rows,
    }
    table(out / "samples.csv", rows)
    save(out / "summary.json", summary)
    return summary


def command_record(command, destination):
    started = datetime.now(UTC).isoformat()
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        record = {
            "command": command,
            "started_at": started,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as exc:
        record = {"command": command, "started_at": started, "error": repr(exc)}
    save(destination, record)
    return record


def admission_observer(original_emit, admission):
    def observe(log, event_type, payload, **kwargs):
        result = original_emit(log, event_type, payload, **kwargs)
        if event_type == "model_started" and not admission:
            admission["perf_counter_ns"] = time.perf_counter_ns()
        return result

    return observe


def runtime(args, out):
    from repropatch.artifacts import EvidenceRef
    from repropatch.context import complete_rounds
    from repropatch.demo import prepare_demo
    from repropatch.events import EventLog, read_events
    from repropatch.harness import Harness
    from repropatch.models import load_sdk_script
    from repropatch.recovery import read_checkpoint, resume_run
    from repropatch.task import Task

    command_record(["docker", "version"], out / "docker-version.json")
    command_record(["docker", "image", "inspect", args.image], out / "image.json")
    command_record(["uname", "-a"], out / "host.json")
    command_record(["docker", "info", "--format", "{{json .}}"], out / "docker-info.json")
    resumes, validations = [], []
    args.private.mkdir(parents=True, exist_ok=True)
    prepared = None
    for repeat in range(1, 4):
        row = {
            "repeat": repeat,
            "model": "agents.testing.ScriptedModel",
            "new_paid_requests": 0,
            "synthetic_usage": True,
        }
        save(out / f"resume-{repeat}-registered.json", row)
        try:
            prepared = prepare_demo(
                args.private / f"resume-{repeat}", image=args.image, scenario="recovery"
            )
            model, script = load_sdk_script(Path(prepared["scripts"]["recovery"]), with_source=True)
            task = Task.load(Path(prepared["tasks"]["recovery"]))
            paused = Harness(task, model, script_source=script, pause_after_step=3).run()
            save(out / f"resume-{repeat}-paused.json", paused)
            directory = Path(paused["artifact_directory"])
            before = read_events(directory, paused["run_id"])
            manifest, reference = read_checkpoint(directory, before)
            save(out / f"resume-{repeat}-checkpoint.json", manifest)
            row.update(
                run_id=paused["run_id"],
                artifact_directory=str(directory),
                before=before.run,
                checkpoint=reference,
                prepared=prepared,
            )
            admission = {}
            original_emit = EventLog.emit

            # Observe the committed admission event; keep production behavior and exceptions.
            EventLog.emit = admission_observer(original_emit, admission)
            try:
                started = time.perf_counter_ns()
                resumed = resume_run(directory)
            finally:
                EventLog.emit = original_emit
            save(out / f"resume-{repeat}-resumed.json", resumed)
            after = read_events(directory, paused["run_id"])
            resumed_events = after.events[len(before.events) :]
            model_event = next(e for e in resumed_events if e["type"] == "model_started")
            native_ref = EvidenceRef(**model_event["payload"]["native_input"])
            resumed_input = json.loads(native_ref.read(directory, limit=8 * 1024 * 1024))
            committed_input = json.loads(
                EvidenceRef(**manifest["native_next_input"]).read(directory, limit=8 * 1024 * 1024)
            )
            boundaries = complete_rounds(resumed_input["input"])

            def count(es, name):
                return sum(e["type"] == name for e in es)

            def edits(es):
                return sum(
                    e["type"] == "tool_started" and e["payload"].get("name") == "edit_file"
                    for e in es
                )

            row.update(
                status="measured",
                resume_to_admission_seconds=(admission["perf_counter_ns"] - started) / 1e9,
                admission=admission,
                after=after.run,
                checks={
                    "same_run": resumed["run_id"] == paused["run_id"],
                    "event_prefix": after.events[: len(before.events)] == before.events,
                    "source_tree": manifest["source_tree_sha256"]
                    == (resumed.get("candidate") or {}).get("source_tree_sha256"),
                    "budget_counters": before.run["steps_used"] == 3
                    and before.run["tool_calls_admitted"] == 3
                    and after.run["steps_used"] == 5
                    and after.run["tool_calls_admitted"] == 4,
                    "deadline": before.run["deadline_at"] == after.run["deadline_at"],
                    "baseline_once": count(before.events, "baseline_finished")
                    == count(after.events, "baseline_finished")
                    == 1,
                    "edit_once": edits(before.events) == edits(after.events) == 1,
                    "complete_input_boundary": before.run["segment_open"] == 0
                    and manifest["boundary"] == "model_input_ready"
                    and bool(boundaries),
                    "committed_input_preserved": resumed_input == committed_input,
                    "independent_acceptance": resumed.get("outcome") == "ACCEPTED",
                    "cold_independent": (resumed.get("independent") or {}).get("evaluation_role")
                    == "independent"
                    and (resumed.get("independent") or {}).get("compiler_cache") is None,
                },
            )
        except Exception as exc:
            row.update(status="error", error=repr(exc), traceback=traceback.format_exc())
        resumes.append(row)
        save(out / f"resume-{repeat}-result.json", row)
        print(f"resume {repeat}: {row['status']}", flush=True)

    import difflib

    source = args.source / "src/repropatch/demo_assets/cpp-bugs"
    old = (source / "src/stats.cpp").read_text()
    fixed = old.replace("int best = 0;", "int best = samples.front();")
    regression = fixed.replace("return std::nullopt;", "return 0;")
    assert fixed != old and regression != fixed
    test_old = (source / "tests/stats_test.cpp").read_text()
    test_new = test_old.replace("result != -3", "result != -4")

    def diff(name, before, after):
        return "".join(
            difflib.unified_diff(
                before.splitlines(True),
                after.splitlines(True),
                fromfile=f"a/{name}",
                tofile=f"b/{name}",
            )
        )

    candidates = {
        "normal": diff("src/stats.cpp", old, fixed),
        "test_tamper": diff("src/stats.cpp", old, fixed)
        + diff("tests/stats_test.cpp", test_old, test_new),
        "regression": diff("src/stats.cpp", old, regression),
    }
    if args.recovery_only:
        candidates = {}
    for scenario, patch in candidates.items():
        path = out / f"{scenario}.patch"
        with path.open("xb") as stream:
            stream.write(patch.encode())
        row = {
            "scenario": scenario,
            "candidate_sha256": digest(patch.encode()),
            "candidate_bytes": len(patch.encode()),
            "new_paid_requests": 0,
        }
        save(out / f"verify-{scenario}-registered.json", row)
        try:
            if prepared is None:
                prepared = prepare_demo(
                    args.private / "validation-fixture", image=args.image, scenario="recovery"
                )
            task = Task.load(Path(prepared["tasks"]["recovery"]))
            report = Harness(task, patch_file=path, producer="runtime-evidence-20261106").run()
            save(out / f"verify-{scenario}-report.json", report)
            row.update(
                status="measured",
                run_id=report["run_id"],
                accepted=report["outcome"] == "ACCEPTED",
                outcome=report["outcome"],
                reason=report["reason_code"],
                artifact_directory=report["artifact_directory"],
                independent=report.get("independent"),
                candidate=report.get("candidate"),
                image_id=prepared["image_id"],
                base_commit=prepared["base_commit"],
            )
        except Exception as exc:
            row.update(status="error", error=repr(exc), traceback=traceback.format_exc())
        validations.append(row)
        save(out / f"verify-{scenario}-result.json", row)
        print(f"verify {scenario}: {row['status']}", flush=True)
    good = [r for r in resumes if r["status"] == "measured"]
    summary = {
        "resume_registered_n": 3,
        "resume_measured_n": len(good),
        "resume_all_checks_n": sum(all(r["checks"].values()) for r in good),
        "resume_seconds": coverage([r.get("resume_to_admission_seconds") for r in resumes]),
        "validation_registered_n": len(candidates),
        "new_paid_requests": 0,
        "resumes": resumes,
        "validations": validations,
    }
    save(out / "summary.json", summary)
    return summary


def summarize(args, out):
    from repropatch.reports import inspect_run

    history_result = load(args.output / "history/summary.json")
    ledger = load(args.output / "reconcile/summary.json")
    raw = load(args.output / "raw_projection/summary.json")
    first = load(args.output / "runtime/summary.json")
    second = load(args.output / "runtime2/summary.json")
    validation = []
    for row in first["validations"]:
        independent = row.get("independent") or {}
        tests = independent.get("tests") or []
        item = {
            k: row.get(k)
            for k in (
                "scenario",
                "run_id",
                "status",
                "accepted",
                "reason",
                "candidate_sha256",
                "candidate_bytes",
                "candidate",
                "image_id",
                "base_commit",
                "artifact_directory",
            )
        }
        item["independent_executed"] = independent.get("evaluation_role") == "independent"
        item["cold"] = item["independent_executed"] and independent.get("compiler_cache") is None
        item["f2p"] = {t["name"]: t["observed_status"] for t in tests if t["group"] == "F2P"}
        item["p2p"] = {t["name"]: t["observed_status"] for t in tests if t["group"] == "P2P"}
        item["source_matches_candidate"] = bool(row.get("candidate")) and (
            independent.get("source_tree_sha256") == row["candidate"].get("source_tree_sha256")
        )
        validation.append(item)
    inspections = []
    for path in sorted(args.output.glob("runs*/resume-*/runs/recovery/*/events.sqlite3")):
        inspection = inspect_run(path.parent)
        inspections.append(
            {
                "path": str(path.parent.relative_to(args.output)),
                **{
                    key: inspection.get(key)
                    for key in (
                        "run_id",
                        "state",
                        "outcome",
                        "reason_code",
                        "evidence_complete",
                        "artifacts_complete",
                    )
                },
            }
        )
    cloud_path = args.source / "benchmarks/actions-scale/cloud-results.json"
    cloud = load(cloud_path)
    samples = cloud["target_build_profile"]["samples"]
    build = {
        "source_file": str(cloud_path),
        "source_sha256": file_sha(cloud_path),
        "source_commit": cloud["source_commit"],
        "toolchain": cloud["toolchain"],
        "instance_id": cloud["target_build_profile"]["instance_id"],
        "run_id": cloud["target_build_profile"]["run_id"],
        "groups": {
            v: coverage([s["seconds"] for s in samples if s["variant"] == v])
            for v in sorted({s["variant"] for s in samples})
        },
        "samples": samples,
    }
    summary = {
        "source_commit": COMMIT,
        "new_paid_requests": 0,
        "history": history_result,
        "ledger": ledger,
        "raw_projection": raw,
        "provider_input_projection": load(args.output / "projection/summary.json"),
        "runtime_initial": first,
        "runtime_additional": second,
        "recovery_registered_total": first["resume_registered_n"] + second["resume_registered_n"],
        "recovery_valid_timing_total": (first["resume_measured_n"] + second["resume_measured_n"]),
        "validation": validation,
        "local_artifact_inspections": inspections,
        "build_reuse": build,
    }
    table(out / "validation.csv", validation)
    table(out / "artifact-inspections.csv", inspections)
    save(out / "summary.json", summary)
    return {
        "recovery_registered_total": summary["recovery_registered_total"],
        "recovery_valid_timing_total": summary["recovery_valid_timing_total"],
        "local_inspections_n": len(inspections),
        "local_complete_n": sum(
            r["artifacts_complete"] and r["evidence_complete"] for r in inspections
        ),
    }


def write_archive(path, members):
    manifest = []
    with Path(path).open("xb") as target:
        with gzip.GzipFile(filename="", fileobj=target, mode="wb", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as tar:
                for name, content, mode in members:
                    info = tarfile.TarInfo(name)
                    info.size, info.mode, info.mtime = len(content), mode, 0
                    tar.addfile(info, io.BytesIO(content))
                    manifest.append(
                        {"path": name, "sha256": digest(content), "bytes": len(content)}
                    )
    return manifest


def input_member(name, arm):
    return (
        name in {"provenance.json", f"{arm}/result.json", f"ledgers/{arm}.sqlite3"}
        or (
            name.startswith(f"{arm}/http-native/")
            and (REQUEST.search(name) or re.search(r"/[0-9a-f]{32}-response\.json$", name))
        )
        or (
            name.startswith(f"{arm}/runs/")
            and (name.endswith("/events.jsonl") or "/agent/tool-results/" in name)
        )
    )


def pack(args, out):
    rows = [
        json.loads(line)
        for line in (args.output / "history/attempts.jsonl").read_text().splitlines()
    ]
    index, members = [], {}
    (out / "archives").mkdir()
    for number, row in enumerate(rows, 1):
        source = Path(row["archive"])
        assert file_sha(source) == row["archive_sha256"]
        name = f"archives/{number:03d}-{row['arm']}.tar.gz"
        with tarfile.open(source) as archive:
            retained = [
                (entry.name, tar_bytes(archive, entry.name), entry.mode)
                for entry in sorted(archive.getmembers(), key=lambda m: m.name)
                if entry.isfile() and input_member(entry.name, row["arm"])
            ]
        members[name] = write_archive(out / name, retained)
        index.append(
            {
                "attempt_id": row["attempt_id"],
                "archive": name,
                "sha256": file_sha(out / name),
                "original_archive_sha256": row["archive_sha256"],
                "execution_source_commit": row["execution_source_commit"],
                "member_count": len(members[name]),
            }
        )
    save(
        out / "audit-index.json",
        {
            "schema": "repropatch.portable-audit-index.v1",
            "source_commit": COMMIT,
            "path_base": "directory containing this index",
            "selected_n": 95,
            "scope": "original members unchanged; repack and upstream archive SHA256 retained",
            "fmt_paid_local_archives": index,
        },
    )
    save(out / "archive-members.json", members)
    names = (
        set(source_identity(args.source)["files"])
        | set(SOURCE_INPUTS)
        | {"pyproject.toml", "README.md", "docker/Dockerfile"}
    )
    for name in sorted(names):
        target = out / "source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.source / name, target)
    for name in (
        "protocol.json",
        "raw-output-protocol.json",
        "runtime-observer-protocol.json",
        "source-object-check.json",
    ):
        shutil.copyfile(args.output / name, out / name)
    shutil.copytree(args.output / "raw_projection", out / "projection-samples")
    state_members = []
    for root in ("runs", "runs2"):
        for path in sorted((args.output / root).rglob("*")):
            if path.is_file() and not path.is_symlink():
                state_members.append(
                    (
                        str(path.relative_to(args.output)),
                        path.read_bytes(),
                        path.stat().st_mode & 0o777,
                    )
                )
    state_manifest = write_archive(out / "runtime-state.tar.gz", state_members)
    save(out / "runtime-state-members.json", state_manifest)
    manifest = {
        "schema": "repropatch.portable-inputs.v1",
        "source_commit": COMMIT,
        "source": source_identity(out / "source"),
        "files": [
            {"path": str(p.relative_to(out)), "sha256": file_sha(p), "bytes": p.stat().st_size}
            for p in sorted(out.rglob("*"))
            if p.is_file()
        ],
    }
    save(out / "input-manifest.json", manifest)
    summary = {
        "archive_count": len(index),
        "historical_sqlite_count": len(index),
        "runtime_sqlite_count": sum(r["path"].endswith("/events.sqlite3") for r in state_manifest),
        "archive_bytes": sum((out / r["archive"]).stat().st_size for r in index),
        "runtime_archive_bytes": (out / "runtime-state.tar.gz").stat().st_size,
        "source_files": len(names),
        "paid_requests": 0,
    }
    save(out / "summary.json", summary)
    return summary


def safe_member_path(root, name):
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("UNSAFE_ARCHIVE_MEMBER")
    result = (root / path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("UNSAFE_ARCHIVE_MEMBER")
    return result


def audit(args, out):
    """Audit the relocatable package without Docker, a provider, or private archives."""
    from repropatch.reports import inspect_run

    package = args.package.resolve()
    manifest = load(package / "input-manifest.json")
    for entry in manifest["files"]:
        assert file_sha(safe_member_path(package, entry["path"])) == entry["sha256"]
    assert source_identity(args.source) == manifest["source"]
    source_check = load(package / "source-object-check.json")
    assert source_check["all_match"] and source_check["commit"] == COMMIT
    originals = selected_rows(load(args.source / SOURCE_INPUTS[0]))
    by_id = {r["attempt_id"]: r for r in originals}
    archives = archive_index(args)
    assert set(archives) == set(by_id)
    member_manifest = load(package / "archive-members.json")
    checks, request_ids = [], set()
    for aid, reference in archives.items():
        path = archive_path(args.audit_index, reference)
        assert file_sha(path) == reference["sha256"]
        arm = by_id[aid]["arm"]
        with tarfile.open(path) as tar:
            for entry in member_manifest[reference["archive"]]:
                assert digest(tar_bytes(tar, entry["path"])) == entry["sha256"]
            worker_sha = digest(tar_bytes(tar, f"{arm}/result.json"))
            assert worker_sha == by_id[aid]["score"]["worker_result_sha256"]
            connection = sqlite3.connect(":memory:")
            connection.deserialize(tar_bytes(tar, f"ledgers/{arm}.sqlite3"))
            assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            requests = connection.execute("SELECT id,usage,purpose FROM requests").fetchall()
            unissued = connection.execute(
                "SELECT count(*) FROM pre_send WHERE issued=0"
            ).fetchone()[0]
            connection.close()
        usage = [json.loads(r[1]) for r in requests]
        expected = by_id[aid]["usage"]
        assert len(requests) == expected["requests"]
        assert all(r[0] not in request_ids for r in requests)
        request_ids.update(r[0] for r in requests)
        totals = {key: sum(u[key] for u in usage) for key in ("input_tokens", "output_tokens")}
        assert all(totals[key] == expected[key] for key in totals)
        checks.append(
            {
                "attempt_id": aid,
                "requests": len(requests),
                "unissued": unissued,
                "worker_hash_matches": True,
                "sqlite_integrity": "ok",
                **totals,
            }
        )
    state_root = out / "state"
    with tarfile.open(package / "runtime-state.tar.gz") as tar:
        for entry in load(package / "runtime-state-members.json"):
            content = tar_bytes(tar, entry["path"])
            assert digest(content) == entry["sha256"]
            path = safe_member_path(state_root, entry["path"])
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with path.open("xb") as target:
                target.write(content)
    inspections = []
    for path in sorted(state_root.glob("runs*/resume-*/runs/recovery/*/events.sqlite3")):
        connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        connection.close()
        inspection = inspect_run(path.parent)
        inspections.append(
            {
                key: inspection[key]
                for key in (
                    "run_id",
                    "outcome",
                    "reason_code",
                    "evidence_complete",
                    "artifacts_complete",
                )
            }
        )
    assert len(inspections) == 9
    assert all(r["evidence_complete"] and r["artifacts_complete"] for r in inspections)
    projections = []
    for sample in sorted((package / "projection-samples").glob("[0-9][0-9]")):
        body = load(sample / "unfolded-request.json")
        expected = load(sample / "result.json")
        index = next(
            i
            for i, item in enumerate(body["input"])
            if item.get("call_id") == expected["call_id"]
            and item.get("type") == "function_call_output"
        )
        directory = out / "projection" / sample.name
        directory.mkdir(parents=True)
        _, result = project_request(body, index, directory)
        for key in (
            "original_output_bytes",
            "projected_output_bytes",
            "attachment_roundtrip",
            "boundaries_equal",
            "non_output_fields_preserved",
        ):
            assert result[key] == expected[key]
        projections.append(result)
    assert len(projections) == 6
    summary = {
        "input_hash_checks": len(manifest["files"]),
        "historical_attempts": len(checks),
        "requests": sum(r["requests"] for r in checks),
        "unissued_presend": sum(r["unissued"] for r in checks),
        "input_tokens": sum(r["input_tokens"] for r in checks),
        "output_tokens": sum(r["output_tokens"] for r in checks),
        "runtime_sqlite_integrity_n": len(inspections),
        "runtime_complete_n": len(inspections),
        "projection_roundtrip_n": len(projections),
        "new_paid_requests": 0,
        "original_output_bytes": sum(r["original_output_bytes"] for r in projections),
        "projected_output_bytes": sum(r["projected_output_bytes"] for r in projections),
        "attempts": checks,
        "runtime_inspections": inspections,
        "projections": projections,
    }
    save(out / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase",
        choices=[
            "freeze",
            "history",
            "projection",
            "reconcile",
            "raw_projection",
            "runtime",
            "summarize",
            "pack",
            "audit",
        ],
    )
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package", type=Path, default=PACKAGE)
    parser.add_argument("--audit-index", type=Path)
    parser.add_argument("--private", type=Path, default=Path("/tmp/repropatch-runtime-evidence"))
    parser.add_argument("--image", default="repropatch-runtime-evidence:20261106")
    parser.add_argument("--label", help="New append-only series directory, default: phase")
    parser.add_argument("--recovery-only", action="store_true")
    args = parser.parse_args()
    args.source = args.source or args.package / "source"
    args.audit_index = args.audit_index or args.package / "audit-index.json"
    args.source, args.output = args.source.resolve(), args.output.resolve()
    if args.phase == "audit":
        args.output.mkdir(parents=True, exist_ok=False)
        activate(args.source)
        result = audit(args, args.output)
        print(json.dumps({k: v for k, v in result.items() if not isinstance(v, (dict, list))}))
        return
    protocol = load(args.output / "protocol.json")
    assert protocol["source_commit"] == COMMIT
    if args.phase == "freeze":
        freeze(args)
        return
    frozen = load(args.output / "frozen-inputs.json")
    assert file_sha(args.output / "protocol.json") == frozen["protocol_sha256"]
    assert source_identity(args.source) == frozen["source"]
    activate(args.source)
    label = args.label or args.phase
    if not re.fullmatch(r"[A-Za-z0-9_-]+", label):
        parser.error("--label must be one directory name")
    out = args.output / label
    out.mkdir(parents=True, exist_ok=False)
    meta = {
        "started_at": datetime.now(UTC).isoformat(),
        "source_commit": COMMIT,
        "source_path": str(args.source),
        "protocol_sha256": frozen["protocol_sha256"],
        "driver_sha256": file_sha(__file__),
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {p: importlib.metadata.version(p) for p in ("openai-agents", "openai")},
    }
    if args.phase in ("reconcile", "raw_projection"):
        meta["supplemental_protocol_sha256"] = file_sha(args.output / "raw-output-protocol.json")
    if args.phase == "runtime" and (args.output / "runtime-observer-protocol.json").exists():
        meta["supplemental_protocol_sha256"] = file_sha(
            args.output / "runtime-observer-protocol.json"
        )
    with (out / "driver.py").open("xb") as stream:
        stream.write(Path(__file__).read_bytes())
    save(out / "execution.json", meta)
    try:
        result = globals()[args.phase](args, out)
        save(
            out / "finished.json",
            {
                "finished_at": datetime.now(UTC).isoformat(),
                "summary_sha256": file_sha(out / "summary.json"),
            },
        )
        print(json.dumps({k: v for k, v in result.items() if not isinstance(v, (dict, list))}))
    except Exception as exc:
        save(out / "exception.json", {"error": repr(exc), "traceback": traceback.format_exc()})
        raise


if __name__ == "__main__":
    main()
