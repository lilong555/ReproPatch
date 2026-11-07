"""Read-only load and compression-opportunity audit of frozen context runs.

No recorded commands or model requests are executed. Archive members are verified
by the existing bounded archive reader. Provider usage, runtime estimates and
tokenizer proxies have separate fields throughout the output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import re
import sqlite3
import statistics
import tarfile
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

from audit_context_triggers import Archive, AuditError, load_events, parse_json

from repropatch.context import opaque_bytes, visible
from repropatch.task import canonical_json

LOGGER = logging.getLogger(__name__)
THRESHOLDS = (4096, 8192, 16000, 24000, 32000, 48000)
STRATEGIES = ("diagnostic_extraction", "deduplicate_results", "state_aware_compaction")
MAX_REQUESTS = 512
MAX_EXTRA_BYTES = 64 * 1024 * 1024
PASS = re.compile(r"^\[\s*OK\s*\]\s+([^\s]+)(?:\s|$)")
RUN = re.compile(r"^\[\s*RUN\s*\]\s+([^\s]+)(?:\s|$)")
BUILD = re.compile(r"^\[\s*\d+(?:/\d+|%)\]\s+(?:Building|Linking|Built|Generating)\b")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utf8_proxy(text: str) -> int:
    return math.ceil(len(text.encode()) / 3)


@lru_cache(maxsize=1)
def encoding():
    import tiktoken

    return tiktoken.get_encoding("o200k_base")


@lru_cache(maxsize=4096)
def token_proxy(text: str) -> int:
    return len(encoding().encode(text, disallowed_special=()))


def proxy_item(item) -> int:
    return token_proxy(canonical_json(visible(item)).decode())


def distribution(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return {
            "n": 0,
            "min": None,
            "median": None,
            "p75": None,
            "p90": None,
            "max": None,
            "mean": None,
        }

    def quantile(q):
        position = (len(values) - 1) * q
        lo, hi = math.floor(position), math.ceil(position)
        return values[lo] + (values[hi] - values[lo]) * (position - lo)

    return {
        "n": len(values),
        "min": values[0],
        "median": statistics.median(values),
        "p75": quantile(0.75),
        "p90": quantile(0.9),
        "max": values[-1],
        "mean": statistics.mean(values),
    }


def extra_members(archive, names):
    """Read selected, already inventoried members without extracting paths."""
    found, total = {}, 0
    with tarfile.open(archive.path, "r|gz") as stream:
        for member in stream:
            if member.name not in names:
                continue
            if not member.isfile() or not 0 <= member.size <= MAX_EXTRA_BYTES:
                raise AuditError("extra_member_size_or_type")
            total += member.size
            if total > MAX_EXTRA_BYTES:
                raise AuditError("extra_members_total_limit")
            raw = stream.extractfile(member).read(member.size + 1)
            if archive.identities.get(member.name) != (len(raw), sha(raw)):
                raise AuditError("extra_member_identity")
            found[member.name] = raw
    if set(found) != set(names):
        raise AuditError("missing_extra_members")
    return found


def ledger_rows(raw, attempt_id):
    with tempfile.TemporaryDirectory(prefix="repropatch-context-load-") as folder:
        path = Path(folder) / "usage.sqlite3"
        path.write_bytes(raw)
        with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
            db.execute("PRAGMA trusted_schema=OFF")
            db.row_factory = sqlite3.Row
            issued = [
                dict(row)
                for row in db.execute(
                    "SELECT rowid AS database_row,* FROM requests ORDER BY rowid LIMIT ?",
                    (MAX_REQUESTS + 1,),
                )
            ]
            prepared = [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM pre_send ORDER BY sequence LIMIT ?", (MAX_REQUESTS + 1,)
                )
            ]
    if max(len(issued), len(prepared)) > MAX_REQUESTS:
        raise AuditError("request_count_limit")
    if any(row["attempt"] != attempt_id for row in issued + prepared):
        raise AuditError("ledger_attempt_mismatch")
    return issued, prepared


def text_fields(value, path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            child = path + "/" + key
            if isinstance(item, str) and key in {"text", "stdout", "stderr", "diagnostic"}:
                yield child, item
            elif isinstance(item, (dict, list)):
                yield from text_fields(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from text_fields(item, path + "/" + str(index))


def literal_candidates(value, tool):
    """Observable surface candidates; these labels do not assert semantic safety."""
    repeats, passed, build, examples = 0, 0, 0, []
    seen = set()
    for path, text in text_fields(value):
        lines = text.splitlines(keepends=True)
        ok = {m.group(1) for line in lines if (m := PASS.match(line.strip()))}
        for line in lines:
            stripped = line.strip()
            size = len(line.encode())
            if size >= 32 and stripped in seen:
                repeats += size
                if len(examples) < 3:
                    examples.append(
                        {"kind": "literal_repeat", "field": path, "text": stripped[:240]}
                    )
            if size >= 32:
                seen.add(stripped)
            if tool in {"run_command", "run_shell", "fixed_baseline"}:
                run = RUN.match(stripped)
                if PASS.match(stripped) or (run and run.group(1) in ok):
                    passed += size
                    if len(examples) < 3:
                        examples.append(
                            {"kind": "passing_test_progress", "field": path, "text": stripped[:240]}
                        )
                if BUILD.match(stripped):
                    build += size
                    if len(examples) < 3:
                        examples.append(
                            {"kind": "build_progress", "field": path, "text": stripped[:240]}
                        )
    return {
        "literal_repeat_bytes": repeats,
        "passing_test_progress_bytes": passed,
        "build_progress_bytes": build,
        "examples": examples,
    }


def repair_pressure_points(requests, compactions):
    # The admission estimator measures the actual issued request. The plan's
    # pre-compaction value is recorded separately and can precede a shorter input.
    points = [
        {
            "sequence": r["sequence"],
            "step_id": r["step_id"],
            "value": r["runtime_estimated_input_tokens"],
            "kind": "pre_send",
        }
        for r in requests
        if r["purpose"] == "repair"
    ]
    points += [
        {
            "sequence": c["sequence"],
            "step_id": c.get("step_id"),
            "value": c["pre_compact_tokens"],
            "kind": "pre_compaction_plan",
        }
        for c in compactions
    ]
    return points


def threshold_profile(requests, compactions, threshold):
    reached = sorted(
        (
            p
            for p in repair_pressure_points(requests, compactions)
            if p["value"] is not None and p["value"] >= threshold
        ),
        key=lambda p: p["sequence"],
    )
    first = reached[0] if reached else None
    return {
        "threshold": threshold,
        "reached": bool(first),
        "first": first,
        "recorded_points_at_or_above": len(reached),
        "later_repair_requests": sum(
            r["purpose"] == "repair" and r["sequence"] > first["sequence"] for r in requests
        )
        if first
        else 0,
    }


def add_cross_observation_candidates(observations):
    previous_data, previous_exact, previous_lines = {}, {}, defaultdict(dict)
    file_lines = {obs["tool_id"]: obs.get("_file_lines", {}) for obs in observations}
    for obs in observations:
        obs["same_source_exact_data_previous"] = None
        obs["same_source_arguments_data_previous"] = None
        obs["same_file_version_overlap_bytes"] = 0
        obs["new_file_version_successor"] = None
        obs["later_check_successor"] = None
        obs["later_same_file_version_reads"] = []
        obs["later_matching_edits"] = []
        obs["later_same_file_version_overlap_bytes"] = 0
        if obs["tool"] in {"read_file", "search_code", "list_directory"}:
            key = (obs["source_tree_sha256"], obs["tool"], obs["data_sha256"])
            if obs["source_tree_sha256"]:
                obs["same_source_exact_data_previous"] = previous_data.get(key)
                previous_data[key] = obs["tool_id"]
                exact_key = (*key, sha(canonical_json(obs.get("arguments", {}))))
                obs["same_source_arguments_data_previous"] = previous_exact.get(exact_key)
                previous_exact[exact_key] = obs["tool_id"]
        if obs["tool"] == "read_file" and obs.get("file_sha256"):
            key = (obs["file_path"], obs["file_sha256"])
            for line_no, line in file_lines[obs["tool_id"]].items():
                if previous_lines[key].get(line_no) == line:
                    obs["same_file_version_overlap_bytes"] += len(line.encode())
                previous_lines[key][line_no] = line
        obs.pop("_file_lines", None)
    for index, obs in enumerate(observations):
        matched_future_lines = set()
        for newer in observations[index + 1 :]:
            if obs["tool"] == "read_file" and obs.get("file_sha256"):
                old_lines = file_lines[obs["tool_id"]]
                if (
                    newer["tool"] == "read_file"
                    and obs.get("file_path") == newer.get("file_path")
                    and obs["file_sha256"] == newer.get("file_sha256")
                ):
                    common = {
                        line_no
                        for line_no, line in file_lines[newer["tool_id"]].items()
                        if old_lines.get(line_no) == line
                    }
                    if common:
                        matched_future_lines.update(common)
                        obs["later_same_file_version_reads"].append(
                            {
                                "tool_id": newer["tool_id"],
                                "step_id": newer["step_id"],
                                "matched_line_count": len(common),
                                "matched_bytes": sum(len(old_lines[n].encode()) for n in common),
                            }
                        )
                if (
                    newer["tool"] == "edit_file"
                    and newer.get("tool_ok")
                    and obs.get("file_path") == newer.get("edited_file_path")
                    and obs["file_sha256"] == newer.get("edit_before_sha256")
                    and (old := newer.get("arguments", {}).get("old"))
                    and old in "".join(old_lines[n] for n in sorted(old_lines))
                ):
                    obs["later_matching_edits"].append(
                        {
                            "tool_id": newer["tool_id"],
                            "step_id": newer["step_id"],
                            "old_anchor_bytes": len(old.encode()),
                            "before_sha256": newer["edit_before_sha256"],
                            "after_sha256": newer["edit_after_sha256"],
                        }
                    )
            if (
                obs["tool"] == "read_file"
                and newer["tool"] == "read_file"
                and obs.get("file_path") == newer.get("file_path")
                and obs.get("file_sha256")
                and newer.get("file_sha256")
                and obs["file_sha256"] != newer["file_sha256"]
                and obs["new_file_version_successor"] is None
            ):
                start = max(obs.get("start_line", 0), newer.get("start_line", 0))
                end = min(obs.get("end_line", -1), newer.get("end_line", -1))
                if end >= start:
                    obs["new_file_version_successor"] = {
                        "tool_id": newer["tool_id"],
                        "step_id": newer["step_id"],
                        "overlap_lines": end - start + 1,
                        "fully_covers_old_range": newer["start_line"] <= obs["start_line"]
                        and newer["end_line"] >= obs["end_line"],
                        "new_file_sha256": newer["file_sha256"],
                    }
                    # Keep the first cross-version range relation, while
                    # continuing to inspect verified reads and patch anchors.
            if (
                obs["tool"] == "run_command"
                and newer["tool"] == "run_command"
                and obs["arguments"] == newer["arguments"]
            ):
                obs["later_check_successor"] = {
                    "tool_id": newer["tool_id"],
                    "step_id": newer["step_id"],
                    "same_source": obs["source_tree_sha256"] == newer["source_tree_sha256"],
                    "check_mode": obs.get("check_mode"),
                    "old_tool_ok": obs["tool_ok"],
                    "new_tool_ok": newer["tool_ok"],
                    "old_test_passed": obs.get("test_passed"),
                    "new_test_passed": newer.get("test_passed"),
                    "old_evaluation_role": obs.get("evaluation_role"),
                    "new_evaluation_role": newer.get("evaluation_role"),
                }
                break
        if obs["tool"] == "read_file":
            obs["later_same_file_version_overlap_bytes"] = sum(
                len(file_lines[obs["tool_id"]][n].encode()) for n in matched_future_lines
            )


def observation_row(event, call, value, raw, source, source_files, root, attempt):
    payload = event["payload"]
    data = value.get("data") or {}
    data = data if isinstance(data, dict) else {"value": data}
    text = canonical_json(value).decode()
    arguments = parse_json(call["arguments"])
    row = {
        "attempt_id": attempt["attempt_id"],
        "job_key": attempt["job_key"],
        "instance_id": attempt["instance_id"],
        "arm": attempt["arm"],
        "repeat": attempt["repeat"],
        "tool_id": event["tool_call_id"],
        "provider_call_id": payload["provider_call_id"],
        "step_id": event["step_id"],
        "event_seq": event["seq"],
        "tool": payload["name"],
        "arguments": arguments,
        "tool_ok": payload.get("ok"),
        "test_passed": data.get("passed") if type(data.get("passed")) is bool else None,
        "check_mode": arguments.get("name") if payload["name"] == "run_command" else None,
        "evaluation_role": data.get("evaluation_role"),
        "source_tree_sha256": source,
        "raw_ref": {
            "path": root + payload["result_ref"]["path"],
            "sha256": sha(raw),
            "size_bytes": len(raw),
        },
        "raw_canonical_bytes": len(text.encode()),
        "raw_proxy_tokens_o200k": token_proxy(text),
        "raw_proxy_tokens_utf8_div3": utf8_proxy(text),
        "data_sha256": sha(canonical_json(data)),
        "literal_raw_candidates": literal_candidates(value, payload["name"]),
        "appearances": [],
    }
    if payload["name"] == "read_file":
        path = data.get("path")
        start, end = data.get("start_line"), data.get("end_line")
        row.update(
            file_path=path, file_sha256=source_files.get(path), start_line=start, end_line=end
        )
        row["_file_lines"] = (
            {
                start + index: line
                for index, line in enumerate(data.get("text", "").splitlines(keepends=True))
            }
            if type(start) is int
            else {}
        )
    elif payload["name"] == "edit_file":
        row.update(
            edited_file_path=data.get("path"),
            edit_before_sha256=data.get("before_sha256"),
            edit_after_sha256=data.get("after_sha256"),
        )
    return row


def enrich_observations(observations, requests, output_lookup):
    by_tool = {obs.get("tool_id"): obs for obs in observations}
    for obs in observations:
        appearances = obs["appearances"]
        first = appearances[0] if appearances else None
        obs["first_visible_bytes"] = first["bytes"] if first else None
        obs["first_visible_proxy_tokens_o200k"] = first["proxy_tokens_o200k"] if first else None
        obs["first_visible_proxy_tokens_utf8_div3"] = (
            first["proxy_tokens_utf8_div3"] if first else None
        )
        obs["observed_in_repair_requests"] = sum(a["purpose"] == "repair" for a in appearances)
        obs["actual_repair_exposure_proxy_tokens_o200k"] = sum(
            a["proxy_tokens_o200k"] for a in appearances if a["purpose"] == "repair"
        )
        first_output = output_lookup.get(obs["provider_call_id"])
        try:
            value = parse_json(first_output) if first_output is not None else None
        except AuditError:
            value = None
        obs["first_visible_json_complete"] = isinstance(value, dict)
        obs["literal_visible_candidates"] = (
            literal_candidates(value, obs["tool"]) if isinstance(value, dict) else None
        )
        obs["raw_to_first_visible_bytes_saved"] = (
            obs["raw_canonical_bytes"] - first["bytes"] if first else None
        )
        candidates = [
            a
            for a in appearances
            if a["purpose"] == "repair" and a["step_id"] >= obs["step_id"] + 3
        ]
        stub = canonical_json(
            {
                "tool": obs["tool"],
                "tool_ok": obs["tool_ok"],
                "test_passed": obs["test_passed"],
                "result_ref": obs["raw_ref"]["path"].split("/agent/")[-1],
                "source_tree_sha256": obs["source_tree_sha256"],
            }
        ).decode()
        stub_tokens = token_proxy(stub)
        for proxy, field in (
            ("o200k", "proxy_tokens_o200k"),
            ("utf8_div3", "proxy_tokens_utf8_div3"),
        ):
            long = bool(first and first[field] > 500)
            obs["delayed_500_candidate_" + proxy] = bool(long and candidates)
        eligible = candidates if obs["delayed_500_candidate_o200k"] else []
        for relations in ("later_same_file_version_reads", "later_matching_edits"):
            for relation in obs.get(relations, []):
                newer = by_tool[relation["tool_id"]]
                newer_requests = {
                    a["sequence"] for a in newer["appearances"] if a["purpose"] == "repair"
                }
                relation["qualifying_repair_coappearances"] = sum(
                    a["sequence"] in newer_requests for a in eligible
                )
        obs["delayed_first_repair_sequence"] = eligible[0]["sequence"] if eligible else None
        obs["delayed_actual_repair_appearances"] = len(eligible)
        obs["delayed_repair_exposure_proxy_tokens_o200k"] = sum(
            a["proxy_tokens_o200k"] for a in eligible
        )
        obs["delayed_reference_stub_proxy_tokens_o200k"] = stub_tokens
        obs["delayed_mask_envelope_savings_proxy_tokens_o200k"] = sum(
            max(0, a["proxy_tokens_o200k"] - stub_tokens) for a in eligible
        )
        obs["later_repair_requests_after_two_completed_steps"] = sum(
            r["purpose"] == "repair"
            and r["step_id"] is not None
            and r["step_id"] >= obs["step_id"] + 3
            for r in requests
        )


def audit_one(task):
    attempt, artifact, raw_dir = task
    started = time.monotonic()
    identity = {k: attempt[k] for k in ("job_key", "attempt_id", "instance_id", "arm", "repeat")}
    folder = Path(raw_dir) / artifact["name"]
    path = folder / "context-attempt.tar.gz"
    if not path.is_file():
        return {
            "trial": {**identity, "status": "missing_archive", "accepted": attempt["accepted"]},
            "requests": [],
            "observations": [],
        }
    try:
        archive = Archive(path)
        receipt = parse_json((folder / "download.json").read_bytes())
        tar_ref = next(item for item in receipt["members"] if item["path"] == path.name)
        if tar_ref["sha256"] != archive.sha256 or receipt["sha256"] != artifact[
            "digest"
        ].removeprefix("sha256:"):
            raise AuditError("download_identity_mismatch")
        worker = archive.json("worker/result.json")
        if worker["attempt_id"] != attempt["attempt_id"]:
            raise AuditError("worker_attempt_mismatch")
        root = "worker/runs/" + worker["native_run_id"] + "/"
        events = load_events(archive, root, worker["native_run_id"])
        config = archive.json(root + "execution-config.json")
        calls, native_steps, observations, compactions = {}, {}, [], []
        source, source_files = None, {}
        for event in events:
            payload = event["payload"]
            if event["type"] == "checkpoint_committed":
                checkpoint = parse_json(archive.read_ref(payload["manifest_ref"], root))
                source = checkpoint["source_tree_sha256"]
                source_files = {
                    f["path"]: f["sha256"]
                    for f in parse_json(archive.read_ref(checkpoint["source_manifest"], root))[
                        "files"
                    ]
                }
            elif (
                event["type"] == "model_started"
                and payload.get("request_purpose", "repair") == "repair"
            ):
                native = parse_json(archive.read_ref(payload["native_input"], root))
                native_steps[
                    sha(
                        canonical_json(
                            {"input": native["input"], "instructions": native.get("instructions")}
                        )
                    )
                ] = event["step_id"]
            elif (
                event["type"] == "model_finished"
                and payload.get("request_purpose", "repair") == "repair"
            ):
                output = parse_json(archive.read_ref(payload["native"], root))
                for item in output["output"]:
                    if item.get("type") == "function_call":
                        calls[item["call_id"]] = item
            elif event["type"] == "tool_finished":
                call_id = payload["provider_call_id"]
                call = calls.get(call_id)
                if not call or call["name"] != payload["name"]:
                    raise AuditError("native_tool_identity_mismatch")
                raw = archive.read_ref(payload["result_ref"], root)
                observations.append(
                    observation_row(
                        event, call, parse_json(raw), raw, source, source_files, root, attempt
                    )
                )
            elif event["type"] == "context_compacted":
                compactions.append(
                    {**payload, "event_seq": event["seq"], "step_id": event["step_id"]}
                )
        extra = extra_members(archive, {"usage.sqlite3"})
        issued, prepared = ledger_rows(extra["usage.sqlite3"], attempt["attempt_id"])
        issued_by_id = {row["id"]: row for row in issued}
        observation_by_call = {row["provider_call_id"]: row for row in observations}
        requests, output_lookup = [], {}
        unknown_tool_outputs = []
        baseline_proxy, fixed_user_proxy, initial_candidates = None, None, None
        for pre in prepared:
            if not pre["issued"]:
                continue
            entry = issued_by_id[pre["id"]]
            raw_body = pre["payload"]
            raw_body = raw_body.encode() if isinstance(raw_body, str) else raw_body
            if sha(raw_body) != entry["request_sha256"] or archive.identities.get(
                "worker/http-native/" + entry["id"] + "-request.json"
            ) != (len(raw_body), sha(raw_body)):
                raise AuditError("http_request_identity_mismatch")
            body = parse_json(raw_body)
            telemetry = parse_json(pre["telemetry"])
            usage = parse_json(entry["usage"]) if entry["usage"] else {}
            key = sha(
                canonical_json({"input": body["input"], "instructions": body.get("instructions")})
            )
            step = native_steps.get(key)
            if pre["purpose"] == "repair" and step is None:
                raise AuditError("http_native_input_mismatch")
            request = {
                **identity,
                "sequence": pre["sequence"],
                "request_id": entry["id"],
                "purpose": pre["purpose"],
                "step_id": step,
                "status_code": entry["status_code"],
                "provider_input_tokens": usage.get("input_tokens"),
                "provider_output_tokens": usage.get("output_tokens"),
                "provider_cached_input_tokens": usage.get("input_tokens_details", {}).get(
                    "cached_tokens"
                ),
                "runtime_estimated_input_tokens": telemetry.get("estimated_input_tokens"),
                "runtime_estimation_basis": telemetry.get("estimation_basis"),
                "transport_bytes": len(raw_body),
                "opaque_transport_bytes": opaque_bytes(body),
                "visible_items_proxy_tokens_o200k_sum": sum(
                    proxy_item(item) for item in body["input"]
                ),
                "header_proxy_tokens_o200k": proxy_item(
                    {k: v for k, v in body.items() if k != "input"}
                ),
                "tool_outputs_bytes": 0,
                "tool_outputs_proxy_tokens_o200k": 0,
                "tool_output_count": 0,
                "request_ref": "worker/http-native/" + entry["id"] + "-request.json",
                "request_sha256": sha(raw_body),
            }
            if pre["purpose"] == "repair" and baseline_proxy is None:
                fixed = next(
                    (
                        item.get("content")
                        for item in body["input"]
                        if item.get("role") == "user" and isinstance(item.get("content"), str)
                    ),
                    "",
                )
                fixed_user_proxy = token_proxy(fixed)
                try:
                    parsed_fixed = parse_json(fixed)
                    baseline = parsed_fixed.get("baseline", {})
                    baseline_proxy = token_proxy(canonical_json(baseline).decode())
                    initial_candidates = literal_candidates(baseline, "fixed_baseline")
                except (AuditError, AttributeError):
                    baseline_proxy = 0
            for item in body["input"]:
                if item.get("type") != "function_call_output":
                    continue
                text = item.get("output")
                if not isinstance(text, str):
                    raise AuditError("tool_output_not_text")
                call_id = item.get("call_id")
                observation = observation_by_call.get(call_id)
                if observation is None:
                    unknown_tool_outputs.append(
                        {"request_sequence": pre["sequence"], "call_id": call_id}
                    )
                    continue
                appearance = {
                    "sequence": pre["sequence"],
                    "purpose": pre["purpose"],
                    "step_id": step,
                    "sha256": sha(text.encode()),
                    "bytes": len(text.encode()),
                    "proxy_tokens_o200k": token_proxy(text),
                    "proxy_tokens_utf8_div3": utf8_proxy(text),
                }
                observation["appearances"].append(appearance)
                output_lookup.setdefault(call_id, text)
                request["tool_output_count"] += 1
                request["tool_outputs_bytes"] += appearance["bytes"]
                request["tool_outputs_proxy_tokens_o200k"] += appearance["proxy_tokens_o200k"]
            requests.append(request)
        if unknown_tool_outputs:
            raise AuditError("unmatched_tool_output")
        expected_input = attempt["usage"]["input_tokens"]
        input_total = sum(r["provider_input_tokens"] or 0 for r in requests)
        if len(requests) != attempt["usage"]["requests"] or input_total != expected_input:
            raise AuditError("provider_ledger_total_mismatch")
        add_cross_observation_candidates(observations)
        enrich_observations(observations, requests, output_lookup)
        for compact in compactions:
            compact["later_repair_requests"] = sum(
                r["purpose"] == "repair" and r["sequence"] > compact["sequence"] for r in requests
            )
        trial = {
            **identity,
            "status": "audited",
            "accepted": attempt["accepted"],
            "classification": attempt["classification"],
            "stop_reason": attempt["stop_reason"],
            "budget_exhausted": attempt["stop_reason"] == "REQUEST_BUDGET_EXHAUSTED",
            "model_requests": len(requests),
            "repair_requests": sum(r["purpose"] == "repair" for r in requests),
            "compact_requests": sum(r["purpose"] == "compact" for r in requests),
            "tool_calls": len(observations),
            "provider_input_tokens": input_total,
            "provider_output_tokens": sum(r["provider_output_tokens"] or 0 for r in requests),
            "provider_usage_missing": sum(r["provider_input_tokens"] is None for r in requests),
            "provider_peak_input_tokens": max(
                (r["provider_input_tokens"] or 0 for r in requests), default=0
            ),
            "runtime_peak_estimated_input_tokens": max(
                [r["runtime_estimated_input_tokens"] or 0 for r in requests]
                + [c["pre_compact_tokens"] for c in compactions]
            ),
            "runtime_peak_repair_plan_estimated_input_tokens": max(
                (p["value"] or 0 for p in repair_pressure_points(requests, compactions)),
                default=0,
            ),
            "first_fixed_user_proxy_tokens_o200k": fixed_user_proxy,
            "initial_baseline_feedback_proxy_tokens_o200k": baseline_proxy,
            "initial_baseline_literal_candidates": initial_candidates,
            "original_context_policy": config["context_policy"],
            "mechanisms": {k: attempt["mechanisms"][k] for k in STRATEGIES},
            "thresholds": {str(n): threshold_profile(requests, compactions, n) for n in THRESHOLDS},
            "compactions": compactions,
            "delayed_500_candidate_observations_o200k": sum(
                o["delayed_500_candidate_o200k"] for o in observations
            ),
            "delayed_500_candidate_observations_utf8_div3": sum(
                o["delayed_500_candidate_utf8_div3"] for o in observations
            ),
            "delayed_mask_envelope_savings_proxy_tokens_o200k": sum(
                o["delayed_mask_envelope_savings_proxy_tokens_o200k"] for o in observations
            ),
            "archive_sha256": archive.sha256,
            "artifact_id": artifact["id"],
            "artifact_url": artifact["url"],
            "archive_inventory_verified": archive.inventory_verified,
            "archive_members_verified": len(archive.identities),
            "audit_elapsed_seconds": round(time.monotonic() - started, 3),
        }
        return {"trial": trial, "requests": requests, "observations": observations}
    except Exception as exc:
        LOGGER.exception("%s audit failed", identity["job_key"])
        return {
            "trial": {
                **identity,
                "status": "audit_error",
                "error": type(exc).__name__ + ": " + str(exc),
                "accepted": attempt["accepted"],
            },
            "requests": [],
            "observations": [],
        }


def aggregate(trials, requests, observations):
    good = [t for t in trials if t["status"] == "audited"]
    trial_ids = {t["attempt_id"] for t in good}
    requests = [r for r in requests if r["attempt_id"] in trial_ids]
    observations = [o for o in observations if o["attempt_id"] in trial_ids]
    summary = {
        "expected_trials": len(trials),
        "audited_trials": len(good),
        "audit_status": dict(Counter(t["status"] for t in trials)),
        "tasks": len({t["instance_id"] for t in trials}),
        "cold_accepted": sum(t["accepted"] is True for t in trials),
        "budget_exhausted": sum(t["budget_exhausted"] for t in good),
        "model_requests": sum(t["model_requests"] for t in good),
        "repair_requests": sum(t["repair_requests"] for t in good),
        "compact_requests": sum(t["compact_requests"] for t in good),
        "tool_observations": len(observations),
        "unconsumed_tool_observations": sum(not o["appearances"] for o in observations),
        "provider_input_tokens": sum(t["provider_input_tokens"] for t in good),
        "provider_output_tokens": sum(t["provider_output_tokens"] for t in good),
        "provider_cached_input_tokens": sum(
            r["provider_cached_input_tokens"] or 0 for r in requests
        ),
        "provider_usage_missing": sum(t["provider_usage_missing"] for t in good),
    }
    summary["trial_distributions"] = {
        key: distribution(t[key] for t in good)
        for key in (
            "model_requests",
            "repair_requests",
            "tool_calls",
            "provider_input_tokens",
            "provider_peak_input_tokens",
            "runtime_peak_estimated_input_tokens",
            "runtime_peak_repair_plan_estimated_input_tokens",
            "first_fixed_user_proxy_tokens_o200k",
            "initial_baseline_feedback_proxy_tokens_o200k",
        )
    }
    obs_keys = (
        "raw_canonical_bytes",
        "raw_proxy_tokens_o200k",
        "first_visible_bytes",
        "first_visible_proxy_tokens_o200k",
        "observed_in_repair_requests",
        "delayed_actual_repair_appearances",
        "later_repair_requests_after_two_completed_steps",
    )
    summary["observation_distributions"] = {
        key: distribution(o[key] for o in observations) for key in obs_keys
    }
    summary["visible_size_buckets_o200k"] = dict(
        Counter(
            "unconsumed"
            if (n := o["first_visible_proxy_tokens_o200k"]) is None
            else "0-500"
            if n <= 500
            else "501-1024"
            if n <= 1024
            else "1025-4096"
            if n <= 4096
            else "4097+"
            for o in observations
        )
    )
    summary["tool_types"] = {
        tool: {
            "count": len(rows),
            "first_visible_tokens_o200k": distribution(
                o["first_visible_proxy_tokens_o200k"] for o in rows
            ),
            "raw_bytes": sum(o["raw_canonical_bytes"] for o in rows),
            "first_visible_bytes": sum(o["first_visible_bytes"] or 0 for o in rows),
            "delayed_500_candidates": sum(o["delayed_500_candidate_o200k"] for o in rows),
            "delayed_exposure_tokens_o200k": sum(
                o["delayed_repair_exposure_proxy_tokens_o200k"] for o in rows
            ),
        }
        for tool in sorted({o["tool"] for o in observations})
        if (rows := [o for o in observations if o["tool"] == tool])
    }
    summary["threshold_coverage"] = {
        str(n): {
            "reached_trials": sum(t["thresholds"][str(n)]["reached"] for t in good),
            "later_repair_requests": distribution(
                t["thresholds"][str(n)]["later_repair_requests"]
                for t in good
                if t["thresholds"][str(n)]["reached"]
            ),
            "first_sequence": distribution(
                t["thresholds"][str(n)]["first"]["sequence"]
                for t in good
                if t["thresholds"][str(n)]["reached"]
            ),
        }
        for n in THRESHOLDS
    }
    summary["delayed_500"] = {
        "o200k_candidate_observations": sum(o["delayed_500_candidate_o200k"] for o in observations),
        "utf8_div3_candidate_observations": sum(
            o["delayed_500_candidate_utf8_div3"] for o in observations
        ),
        "o200k_trials_with_opportunity": sum(
            t["delayed_500_candidate_observations_o200k"] > 0 for t in good
        ),
        "utf8_div3_trials_with_opportunity": sum(
            t["delayed_500_candidate_observations_utf8_div3"] > 0 for t in good
        ),
        "repair_exposure_proxy_tokens_o200k": sum(
            o["delayed_repair_exposure_proxy_tokens_o200k"] for o in observations
        ),
        "mask_envelope_savings_proxy_tokens_o200k": sum(
            o["delayed_mask_envelope_savings_proxy_tokens_o200k"] for o in observations
        ),
        "exposed_repair_requests_per_candidate": distribution(
            o["delayed_actual_repair_appearances"]
            for o in observations
            if o["delayed_500_candidate_o200k"]
        ),
    }
    summary["surface_candidates"] = {
        "same_source_exact_data": sum(
            o["same_source_exact_data_previous"] is not None for o in observations
        ),
        "same_source_arguments_exact_data": sum(
            o["same_source_arguments_data_previous"] is not None for o in observations
        ),
        "same_file_version_overlap_observations": sum(
            o["same_file_version_overlap_bytes"] > 0 for o in observations
        ),
        "same_file_version_overlap_bytes": sum(
            o["same_file_version_overlap_bytes"] for o in observations
        ),
        "new_file_version_overlap_observations": sum(
            o["new_file_version_successor"] is not None for o in observations
        ),
        "later_same_command_checks": sum(
            o["later_check_successor"] is not None for o in observations
        ),
    }
    read_candidates = [
        o for o in observations if o["tool"] == "read_file" and o["delayed_500_candidate_o200k"]
    ]
    verified_reads = {
        (o["attempt_id"], o["tool_id"])
        for o in read_candidates
        if any(r["qualifying_repair_coappearances"] for r in o["later_same_file_version_reads"])
    }
    verified_edits = {
        (o["attempt_id"], o["tool_id"])
        for o in read_candidates
        if any(r["qualifying_repair_coappearances"] for r in o["later_matching_edits"])
    }
    summary["read_candidate_evidence"] = {
        "delayed_500_read_candidates": len(read_candidates),
        "later_identical_version_line_overlap": len(verified_reads),
        "later_version_matched_patch_anchor": len(verified_edits),
        "both": len(verified_reads & verified_edits),
        "verified_relation_union": len(verified_reads | verified_edits),
        "without_verified_future_relation": len(read_candidates)
        - len(verified_reads | verified_edits),
        "cross_version_numeric_range_relation": sum(
            o["new_file_version_successor"] is not None for o in read_candidates
        ),
        "same_version_future_overlap_bytes": sum(
            o["later_same_file_version_overlap_bytes"] for o in read_candidates
        ),
    }
    for view in ("raw", "visible"):
        for kind in ("literal_repeat_bytes", "passing_test_progress_bytes", "build_progress_bytes"):
            summary["surface_candidates"][view + "_" + kind] = sum(
                (o["literal_" + view + "_candidates"] or {}).get(kind, 0) for o in observations
            )
    summary["visible_request_component_proxies"] = {
        "tool_output_tokens_o200k_sum": sum(
            r["tool_outputs_proxy_tokens_o200k"] for r in requests if r["purpose"] == "repair"
        ),
        "visible_items_tokens_o200k_sum": sum(
            r["visible_items_proxy_tokens_o200k_sum"] for r in requests if r["purpose"] == "repair"
        ),
        "header_tokens_o200k_sum": sum(
            r["header_proxy_tokens_o200k"] for r in requests if r["purpose"] == "repair"
        ),
    }
    summary["mechanisms"] = {
        key: {
            "trigger_count": sum(t["mechanisms"][key]["trigger_count"] for t in good),
            "recorded_candidates": sum(
                t["mechanisms"][key].get("metrics", {}).get("candidates", 0) for t in good
            ),
            "candidate_telemetry_present_trials": sum(
                "candidates" in t["mechanisms"][key].get("metrics", {}) for t in good
            ),
            "recorded_saved_bytes": sum(
                t["mechanisms"][key].get("metrics", {}).get("saved_bytes", 0) for t in good
            ),
        }
        for key in STRATEGIES
    }
    summary["compactions"] = [
        {"job_key": t["job_key"], "attempt_id": t["attempt_id"], **c}
        for t in good
        for c in t["compactions"]
    ]
    return summary


def write_outputs(output, results, input_refs, smoke):
    output.mkdir(parents=True, exist_ok=True)
    trials = [result["trial"] for result in results]
    requests = [row for result in results for row in result["requests"]]
    observations = [row for result in results for row in result["observations"]]
    summary = {
        "schema": "repropatch.context-opportunities.v1",
        "scope": "smoke" if smoke else "full",
        "input_refs": input_refs,
        "measurements": {
            "provider_usage": (
                "Actual per-request provider usage, includes cached input; "
                "auxiliary calls included."
            ),
            "runtime_estimate": (
                "Recorded pre_send estimate plus pre-compaction plan events; "
                "UTF-8/3 anchored by observed provider usage."
            ),
            "tokenizer_proxy": (
                "tiktoken 0.12.0 o200k_base, tool-output strings and additive "
                "visible components; opaque encrypted content omitted."
            ),
            "mask_envelope": (
                "Fixed-action-sequence projection of age-qualified observations to "
                "a reference stub; an opportunity envelope with no semantic-safety "
                "or online savings claim."
            ),
            "delay": (
                "Tool step k becomes eligible after two later completed steps; "
                "first possible repair input is k+3."
            ),
            "surface_candidates": (
                "Literal/overlap/version relations; category byte counts can overlap "
                "and are not summed into a savings claim."
            ),
        },
        "all": aggregate(trials, requests, observations),
        "arms": {
            arm: aggregate([t for t in trials if t["arm"] == arm], requests, observations)
            for arm in sorted({t["arm"] for t in trials})
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    for name, rows in (
        ("trials.jsonl", trials),
        ("requests.jsonl", requests),
        ("observations.jsonl", observations),
    ):
        with (output / name).open("w") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    # Review samples are determined by type/size and a stable identity hash.
    buckets = defaultdict(list)
    for obs in observations:
        size = obs["first_visible_proxy_tokens_o200k"] or 0
        bucket = "short" if size <= 500 else "medium" if size <= 4000 else "long"
        buckets[(obs["tool"], bucket)].append(obs)
    selected = [
        obs
        for bucket in sorted(buckets)
        for obs in sorted(
            buckets[bucket], key=lambda o: sha((o["attempt_id"] + "/" + o["tool_id"]).encode())
        )[:2]
    ]
    for key in (
        "same_source_exact_data_previous",
        "same_source_arguments_data_previous",
        "new_file_version_successor",
        "later_check_successor",
    ):
        choices = [o for o in observations if o[key]]
        selected += sorted(
            choices, key=lambda o: sha((o["attempt_id"] + "/" + o["tool_id"]).encode())
        )[:2]
    unique = {(o["attempt_id"], o["tool_id"]): o for o in selected}
    (output / "review-samples.json").write_text(
        json.dumps(list(unique.values()), ensure_ascii=False, indent=2) + "\n"
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import tiktoken

    if tiktoken.__version__ != "0.12.0":
        parser.error("This frozen audit uses tiktoken==0.12.0")
    encoding()
    result_bytes, artifact_bytes = args.results.read_bytes(), args.artifacts.read_bytes()
    attempts = parse_json(result_bytes)["attempts"]
    artifacts = parse_json(artifact_bytes)["raw_artifacts"]
    by_job = {
        a["name"].rsplit("-", 2)[-2] + "-" + a["name"].rsplit("-", 1)[-1]: a for a in artifacts
    }
    attempts = sorted(attempts, key=lambda a: a["job_key"])
    if args.limit is not None:
        if args.limit <= 0:
            parser.error("limit must be positive")
        attempts = attempts[: args.limit]
    if len({a["attempt_id"] for a in attempts}) != len(attempts):
        parser.error("duplicate attempt identity")
    tasks = [(a, by_job[a["job_key"]], str(args.raw_dir)) for a in attempts]
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(audit_one, tasks):
            results.append(result)
            LOGGER.info(
                "%s %s (%d/%d)",
                result["trial"]["job_key"],
                result["trial"]["status"],
                len(results),
                len(tasks),
            )
    refs = {
        "results_sha256": sha(result_bytes),
        "artifacts_sha256": sha(artifact_bytes),
        "audit_source_sha256": sha(Path(__file__).read_bytes()),
        "runtime_source_commit": "2597016d80ea47c8bbc06c93598093c307a24ee7",
        "analysis_base_commit": "1841f6e97ced42d9c914ac494b0e5ab8a0c388f5",
        "artifact_run": 42219312911,
    }
    summary = write_outputs(args.output_dir, results, refs, args.limit is not None)
    LOGGER.info(
        "%s",
        json.dumps(
            {
                k: summary["all"][k]
                for k in (
                    "expected_trials",
                    "audited_trials",
                    "model_requests",
                    "provider_input_tokens",
                )
            },
            ensure_ascii=False,
        ),
    )
    return int(summary["all"]["audited_trials"] != summary["all"]["expected_trials"])


if __name__ == "__main__":
    raise SystemExit(main())
