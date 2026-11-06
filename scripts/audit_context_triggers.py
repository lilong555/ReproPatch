"""Read-only, CPU-only replay of archived tool-context projections.

Run with PYTHONPATH=src:scripts. No model, shell tool, container, or archive
extraction is invoked. Measurements are UTF-8 tool-context bytes only.
"""

import argparse
import gzip
import hashlib
import json
import logging
import os
import re
import stat
import tarfile
import tempfile
from collections import Counter
from copy import deepcopy
from pathlib import Path

from repropatch.context import ContextPolicy, ContextState, fold_tool_output
from repropatch.context_optimization import STRATEGIES, ContextOptimizer, initialize
from repropatch.errors import ReproPatchError
from repropatch.task import canonical_json
from repropatch.workspace import SourceManifest

MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_EXPANDED_BYTES = 512 * 1024 * 1024
MAX_MEMBER_BYTES = 32 * 1024 * 1024
MAX_CACHED_BYTES = 256 * 1024 * 1024
MAX_READ_BYTES = 32 * 1024 * 1024
MAX_FILES = 20_000
MAX_JSON_NODES = 500_000
MAX_JSON_DEPTH = 64
READ_TOOLS = {"read_file", "search_code", "list_directory", "run_command"}
ROOT_PATTERN = re.compile(r"worker/runs/([^/]+)/execution-config\.json")
SHA_PATTERN = re.compile(r"[a-f0-9]{64}")
MEASUREMENT = "offline_tool_context_bytes"
LOGGER = logging.getLogger(__name__)


class AuditError(ValueError):
    pass


class ConfigurationMismatch(AuditError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(name):
    if (
        not isinstance(name, str)
        or not name
        or len(name.encode()) > 4096
        or "\\" in name
        or ":" in name
        or any(ord(c) < 32 for c in name)
        or any(part in {"", ".", ".."} for part in name.split("/"))
    ):
        raise AuditError("unsafe_path")
    return name


def reference_fields(ref):
    if (
        not isinstance(ref, dict)
        or type(ref.get("size_bytes")) is not int
        or not 0 <= ref["size_bytes"] <= MAX_READ_BYTES
        or not isinstance(ref.get("sha256"), str)
        or not SHA_PATTERN.fullmatch(ref["sha256"])
    ):
        raise AuditError("invalid_reference")
    return safe_path(ref.get("path")), ref["size_bytes"], ref["sha256"]


def parse_json(raw):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise AuditError("duplicate_json_key")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw,
            object_pairs_hook=unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(AuditError("invalid_json")),
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise AuditError("invalid_json") from exc
    stack, nodes = [(value, 0)], 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if depth > MAX_JSON_DEPTH or nodes > MAX_JSON_NODES:
            raise AuditError("json_limit")
        children = (
            item.values() if isinstance(item, dict) else item if isinstance(item, list) else ()
        )
        stack.extend((child, depth + 1) for child in children)
    return value


class _BoundedReader:
    def __init__(self, source):
        self.source, self.used = source, 0

    def read(self, size):
        if size < 0 or size > MAX_READ_BYTES or self.used + size > MAX_EXPANDED_BYTES:
            raise AuditError("expanded_archive_limit")
        raw = self.source.read(size)
        self.used += len(raw)
        return raw


class Archive:
    """Validate members while streaming; retain only the run and audit metadata."""

    def __init__(self, path):
        self.path = Path(path)
        self.files, self.identities, self.verified_refs = {}, {}, set()
        descriptor = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ARCHIVE_BYTES:
                raise AuditError("archive_size_or_type")
            checksum = hashlib.sha256()
            for block in iter(lambda: source.read(1024 * 1024), b""):
                checksum.update(block)
            self.sha256 = checksum.hexdigest()
            source.seek(0)
            with gzip.GzipFile(fileobj=source, mode="rb") as decompressed:
                reader = _BoundedReader(decompressed)
                with tarfile.open(fileobj=reader, mode="r|") as archive:
                    cached, seen, regular = 0, set(), set()
                    for member in archive:
                        name = safe_path(member.name.rstrip("/") if member.isdir() else member.name)
                        if name in seen:
                            raise AuditError("duplicate_member")
                        seen.add(name)
                        if len(seen) > MAX_FILES:
                            raise AuditError("member_count_limit")
                        if not (member.isfile() or member.isdir()) or member.sparse is not None:
                            raise AuditError("unsupported_member_type")
                        if not 0 <= member.size <= MAX_MEMBER_BYTES:
                            raise AuditError("member_size_limit")
                        if member.isdir():
                            if member.size:
                                raise AuditError("invalid_directory")
                            continue
                        regular.add(name)
                        retain = name.startswith("worker/runs/") or name in {
                            "archive-manifest.json",
                            "manifest.json",
                            "input-plan.json",
                            "worker/result.json",
                            "execution-started.json",
                        }
                        stream = archive.extractfile(member)
                        chunks, consumed, file_hash = [], 0, hashlib.sha256()
                        while block := stream.read(64 * 1024):
                            consumed += len(block)
                            file_hash.update(block)
                            if retain:
                                cached += len(block)
                                if cached > MAX_CACHED_BYTES:
                                    raise AuditError("cache_size_limit")
                                chunks.append(block)
                        if consumed != member.size:
                            raise AuditError("truncated_member")
                        self.identities[name] = (consumed, file_hash.hexdigest())
                        if retain:
                            self.files[name] = b"".join(chunks)
                    for name in seen:
                        parts = name.split("/")
                        if any("/".join(parts[:i]) in regular for i in range(1, len(parts))):
                            raise AuditError("file_directory_collision")
                # Consume the gzip trailer to check CRC and bound trailing expansion.
                while reader.read(64 * 1024):
                    pass
            after = os.fstat(source.fileno())
            if any(
                getattr(after, key) != getattr(info, key)
                for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
            ):
                raise AuditError("archive_changed_during_read")
        self.inventory_verified = False
        if "archive-manifest.json" in self.files:
            inventory = self.json("archive-manifest.json")
            if not isinstance(inventory, dict) or not isinstance(inventory.get("files"), list):
                raise AuditError("invalid_archive_manifest")
            names = set()
            for ref in inventory["files"]:
                name, _, _ = reference_fields(ref)
                if name in names:
                    raise AuditError("duplicate_manifest_entry")
                names.add(name)
                self.verify(ref)
            if names != set(self.identities) - {"archive-manifest.json"}:
                raise AuditError("archive_inventory_mismatch")
            self.inventory_verified = True

    def read(self, name):
        safe_path(name)
        if name not in self.files:
            raise AuditError("missing_file")
        raw = self.files[name]
        if len(raw) > MAX_READ_BYTES:
            raise AuditError("read_size_limit")
        return raw

    def json(self, name):
        return parse_json(self.read(name))

    def verify(self, ref, root=""):
        path, size, sha = reference_fields(ref)
        name = root + path
        safe_path(name)
        actual = self.identities.get(name)
        if actual is None:
            raise AuditError("missing_reference")
        if actual[0] != size:
            raise AuditError("reference_size_mismatch")
        if actual[1] != sha:
            raise AuditError("reference_sha_mismatch")
        self.verified_refs.add((name, size, sha))
        return name

    def read_ref(self, ref, root):
        return self.read(self.verify(ref, root))

    def verify_nested(self, value, root):
        stack = [value]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                # Source manifests describe repository files, not archived EvidenceRefs.
                if (
                    "path" in item
                    and ("sha256" in item or "size_bytes" in item)
                    and "git_mode" not in item
                ):
                    self.verify(item, root)
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)


def audit_sources():
    root = Path(__file__).resolve().parents[1]
    paths = [Path(__file__).resolve(), *sorted((root / "src/repropatch").glob("*.py"))]
    return {str(path.relative_to(root)): digest(path.read_bytes()) for path in paths}


def load_events(archive, root, run_id):
    events, previous = [], 0
    for line in archive.read(root + "events.jsonl").splitlines():
        event = parse_json(line)
        if (
            not isinstance(event, dict)
            or event.get("run_id") != run_id
            or type(event.get("seq")) is not int
            or event["seq"] <= previous
            or not isinstance(event.get("payload"), dict)
        ):
            raise AuditError("invalid_event_order_or_identity")
        previous = event["seq"]
        events.append(event)
    return events


def frozen_configuration(archive, root, events):
    frozen = [event for event in events if event["type"] == "inputs_frozen"]
    if not frozen:
        raise AuditError("missing_frozen_configuration")
    first_boundary = next(
        (
            event["seq"]
            for event in events
            if event["type"]
            in {
                "checkpoint_committed",
                "model_started",
                "model_finished",
                "tool_finished",
            }
        ),
        None,
    )
    if first_boundary is not None and frozen[0]["seq"] >= first_boundary:
        raise ConfigurationMismatch("configuration_frozen_after_execution")
    size, sha = archive.identities[root + "execution-config.json"]
    expected = ("execution-config.json", size, sha)
    for event in frozen:
        ref = event["payload"].get("configuration")
        archive.verify(ref, root)
        if reference_fields(ref) != expected:
            raise ConfigurationMismatch("frozen_configuration_mismatch")
    reference = frozen[0]["payload"]["configuration"]
    return parse_json(archive.read_ref(reference, root)), deepcopy(reference)


def checkpoints(archive, root, events, configuration_ref):
    result = {}
    for event in events:
        if event["type"] != "checkpoint_committed":
            continue
        ref = event["payload"].get("manifest_ref")
        try:
            manifest = parse_json(archive.read_ref(ref, root))
            fingerprints = (
                manifest.get("input_fingerprints") if isinstance(manifest, dict) else None
            )
            if not isinstance(fingerprints, dict):
                raise ConfigurationMismatch("checkpoint_configuration_invalid")
            try:
                configuration_identity = reference_fields(fingerprints.get("configuration"))
            except AuditError as exc:
                raise ConfigurationMismatch("checkpoint_configuration_invalid") from exc
            if configuration_identity != reference_fields(configuration_ref):
                raise ConfigurationMismatch("checkpoint_configuration_mismatch")
            archive.verify_nested(manifest, root)
            step = manifest["step_id"]
            if type(step) is not int or step < 0 or step != event["payload"].get("step_id"):
                raise AuditError("checkpoint_step_mismatch")
            if manifest.get("boundary") != "model_input_ready":
                raise AuditError("unsupported_checkpoint_boundary")
            source = SourceManifest.from_dict(
                parse_json(archive.read_ref(manifest["source_manifest"], root))
            )
            if source.sha256 != manifest.get("source_tree_sha256"):
                raise AuditError("checkpoint_source_mismatch")
            result[event["seq"]] = {"step": step, "source": source.sha256, "ref": deepcopy(ref)}
        except ConfigurationMismatch:
            raise
        except (AuditError, KeyError, TypeError, ValueError, ReproPatchError) as exc:
            result[event["seq"]] = {"error": str(exc), "ref": deepcopy(ref)}
    return result


def empty_metrics():
    return deepcopy(initialize({})["metrics"])


def aggregate_metrics(target, source):
    for strategy in STRATEGIES:
        for key in (
            "attempts",
            "candidates",
            "triggers",
            "input_bytes",
            "output_bytes",
            "saved_bytes",
            "added_bytes",
        ):
            target[strategy][key] += source[strategy].get(key, 0)
        target[strategy]["skip_reasons"] = dict(
            Counter(target[strategy]["skip_reasons"])
            + Counter(source[strategy].get("skip_reasons", {}))
        )


def audit_run(archive, root):
    run_id = root.split("/")[-2]
    events = load_events(archive, root, run_id)
    config, configuration_ref = frozen_configuration(archive, root, events)
    if not isinstance(config, dict) or not isinstance(config.get("context_policy"), dict):
        raise AuditError("missing_context_policy")
    policy = ContextPolicy.from_dict(config["context_policy"])
    context = ContextState(policy)
    optimizer = ContextOptimizer(context, read_evidence=lambda ref: archive.read_ref(ref, root))
    checkpoint_map = checkpoints(archive, root, events, configuration_ref)
    rows, calls, batches, seen_tools = [], {}, {}, set()
    current_checkpoint = None
    model_errors, validation_errors = {}, []
    originals = {key: config.get(key) for key in ("implementation_sha256", "harness_version")}
    for event in events:
        kind, payload, step = event["type"], event["payload"], event.get("step_id")
        if kind == "inputs_frozen":
            archive.verify(payload.get("configuration"), root)
            originals.update(
                {key: payload.get(key) for key in ("base_commit", "task_sha256", "image_id")}
            )
        elif kind == "checkpoint_committed":
            current_checkpoint = checkpoint_map[event["seq"]]
            if "error" in current_checkpoint:
                validation_errors.append(
                    {"seq": event["seq"], "reason": current_checkpoint["error"]}
                )
                optimizer.source_changed(None)
        elif kind == "context_compacted":
            context.optimization_state["dedup_index"] = {}
        elif kind == "model_finished" and payload.get("request_purpose", "repair") == "repair":
            try:
                output = parse_json(archive.read_ref(payload.get("native"), root))
                items = output["output"]
                if not isinstance(items, list):
                    raise AuditError("invalid_native_output")
                selected = [
                    item
                    for item in items
                    if isinstance(item, dict) and item.get("type") == "function_call"
                ]
                ids = [item.get("call_id") for item in selected]
                if any(not isinstance(identity, str) or not identity for identity in ids) or len(
                    set(ids)
                ) != len(ids):
                    raise AuditError("duplicate_or_invalid_provider_call")
                calls[step] = {item["call_id"]: item for item in selected}
            except (AuditError, KeyError, TypeError) as exc:
                model_errors[step] = str(exc)
        elif kind == "tool_batch_admitted":
            batches[step] = payload.get("calls", [])
        elif kind == "tool_finished":
            tool_id, name = event.get("tool_call_id"), payload.get("name")
            row = {
                "seq": event["seq"],
                "step_id": step,
                "tool_id": tool_id,
                "tool": name,
                "measurement": MEASUREMENT,
                "status": "replayed",
                "source_tree_sha256": None,
                "source_checkpoint": None,
                "source_status": "missing_source",
                "raw_bytes": None,
                "raw_file_bytes": None,
                "native_bytes": None,
                "projected_bytes": None,
                "saved_bytes": 0,
                "decisions": [],
            }
            rows.append(row)
            try:
                if not isinstance(tool_id, str) or tool_id in seen_tools:
                    raise AuditError("duplicate_or_invalid_tool_id")
                seen_tools.add(tool_id)
                if step in model_errors:
                    raise AuditError(model_errors[step])
                call = calls.get(step, {}).get(payload.get("provider_call_id"))
                if not call or call.get("name") != name:
                    raise AuditError("missing_or_mismatched_native_call")
                arguments = parse_json(call["arguments"])
                if not isinstance(arguments, dict):
                    raise AuditError("invalid_tool_arguments")
                admitted = batches.get(step)
                if not isinstance(admitted, list) or not any(
                    item.get("tool_call_id") == tool_id
                    and item.get("name") == name
                    and item.get("provider_call_id") == payload.get("provider_call_id")
                    for item in admitted
                    if isinstance(item, dict)
                ):
                    raise AuditError("missing_or_mismatched_admission")
                reference = payload.get("result_ref")
                raw = archive.read_ref(reference, root)
                value = parse_json(raw)
                if not isinstance(value, dict):
                    raise AuditError("invalid_tool_receipt")
                archive.verify_nested(value, root)
                text = canonical_json(value).decode()
                native = (
                    fold_tool_output(
                        text, policy.tool_output_max_bytes, lambda _, ref=reference: ref["path"]
                    )
                    if policy.compaction_enabled
                    else text
                )
                row.update(
                    raw_bytes=len(text.encode()),
                    raw_file_bytes=len(raw),
                    native_bytes=len(native.encode()),
                )
                batch = list(calls.get(step, {}).values())
                mixed = len(batch) > 1 and any(item.get("name") not in READ_TOOLS for item in batch)
                source_checkpoint = current_checkpoint
                if name not in READ_TOOLS:
                    # The next boundary supplies the post-write workspace identity.
                    following = [
                        cp
                        for seq, cp in checkpoint_map.items()
                        if seq > event["seq"] and cp.get("step") == step
                    ]
                    source_checkpoint = following[0] if following else None
                valid_source = (
                    source_checkpoint
                    and "error" not in source_checkpoint
                    and (
                        source_checkpoint["step"] == step - 1
                        if name in READ_TOOLS
                        else source_checkpoint["step"] == step
                    )
                )
                if mixed:
                    row.update(status="unsupported", source_status="mixed_read_write_batch")
                elif valid_source:
                    row.update(
                        source_tree_sha256=source_checkpoint["source"],
                        source_checkpoint=source_checkpoint["ref"],
                        source_status="checkpoint",
                    )
                else:
                    row["status"] = "missing_source"
                before_metrics = deepcopy(context.optimization_state["metrics"])
                projection, _ = optimizer.project(
                    name,
                    deepcopy(arguments),
                    deepcopy(value),
                    deepcopy(reference),
                    tool_id=tool_id,
                    source=row["source_tree_sha256"],
                    native=native,
                )
                row["projected_bytes"] = len(projection.encode())
                row["saved_bytes"] = row["native_bytes"] - row["projected_bytes"]
                row["decisions"] = deepcopy(optimizer.last_decisions)
                decided = {decision["strategy"] for decision in row["decisions"]}
                for strategy in STRATEGIES:
                    if strategy not in decided:
                        row["decisions"].append(
                            {
                                "strategy": strategy,
                                "outcome": "not_audited"
                                if getattr(policy, strategy)
                                else "disabled",
                                "reason": "request_level_strategy"
                                if getattr(policy, strategy)
                                else "policy_disabled",
                            }
                        )
                for decision in row["decisions"]:
                    strategy = decision["strategy"]
                    decision.setdefault("reason", "savings_gate_passed")
                    decision.update(
                        tool_id=tool_id,
                        tool=name,
                        raw_bytes=row["raw_bytes"],
                        native_bytes=row["native_bytes"],
                        projected_bytes=row["projected_bytes"],
                        candidate=bool(
                            context.optimization_state["metrics"][strategy]["candidates"]
                            - before_metrics[strategy]["candidates"]
                        ),
                    )
            except (AuditError, KeyError, TypeError, ValueError) as exc:
                row.update(status="evidence_error", reason=str(exc))
                row["decisions"] = [
                    {
                        "strategy": strategy,
                        "outcome": "audit_skipped",
                        "reason": str(exc),
                        "tool_id": tool_id,
                        "tool": name,
                        "raw_bytes": row["raw_bytes"],
                        "native_bytes": row["native_bytes"],
                        "projected_bytes": None,
                    }
                    for strategy in STRATEGIES
                ]
                optimizer.source_changed(None)
    metrics = deepcopy(context.optimization_state["metrics"])
    totals = {
        key: sum(row[key] or 0 for row in rows)
        for key in ("raw_bytes", "native_bytes", "projected_bytes", "saved_bytes")
    }
    # Both sides of the comparison include exactly the successfully replayed receipts.
    compared = [row for row in rows if row["projected_bytes"] is not None]
    totals.update(
        native_bytes=sum(row["native_bytes"] for row in compared),
        raw_bytes=sum(row["raw_bytes"] for row in compared),
    )
    return {
        "run_id": run_id,
        "run_evidence_sha256": digest(
            canonical_json(
                [
                    {"path": name[len(root) :], "size_bytes": size, "sha256": sha}
                    for name, (size, sha) in sorted(archive.identities.items())
                    if name.startswith(root)
                ]
            )
        ),
        "original_identity": originals,
        "configuration_ref": configuration_ref,
        "context_policy": deepcopy(config["context_policy"]),
        "tool_count": len(rows),
        "compared_tool_count": len(compared),
        "metrics": metrics,
        "bytes": totals,
        "rows": rows,
        "checkpoint_errors": validation_errors,
        "audit_skip_reasons": dict(
            Counter(
                row.get("reason", row["source_status"])
                for row in rows
                if row["status"] != "replayed"
            )
        ),
        "state_aware_compaction": {
            "scope": "request_level_not_replayed",
            "compact_trigger_tokens": policy.compact_trigger_tokens,
        },
    }


def audit_archive(path):
    archive = Archive(path)
    roots = sorted(
        name[: -len("execution-config.json")]
        for name in archive.files
        if ROOT_PATTERN.fullmatch(name)
    )
    if not roots:
        raise AuditError("missing_execution_config")
    identity = {}
    for name, keys in (
        (
            "worker/result.json",
            ("attempt_id", "task_id", "prepared_commit", "adapter_source_sha256"),
        ),
        (
            "manifest.json",
            ("manifest_sha256", "protocol_sha256", "source_sha256", "source_commit", "git_commit"),
        ),
        ("execution-started.json", ("run_id", "github_run_id", "head_sha", "source_commit")),
    ):
        if name in archive.files:
            value = archive.json(name)
            if isinstance(value, dict):
                identity.update({key: value[key] for key in keys if key in value})
    runs = [audit_run(archive, root) for root in roots]
    return {
        "archive": str(Path(path).resolve()),
        "archive_sha256": archive.sha256,
        "archive_inventory_verified": archive.inventory_verified,
        "verified_reference_count": len(archive.verified_refs),
        "original_identity": identity,
        "runs": runs,
    }


def audit_archives(paths):
    sources = audit_sources()
    results, seen_runs = [], {}
    for path in paths:
        LOGGER.info("Auditing %s", path)
        archive = audit_archive(path)
        unique, duplicates = [], []
        for run in archive["runs"]:
            run_id, evidence = run["run_id"], run["run_evidence_sha256"]
            previous = seen_runs.get(run_id)
            if previous is not None:
                if previous["run_evidence_sha256"] != evidence:
                    raise AuditError(f"conflicting_run_evidence: {run_id}")
                duplicates.append(
                    {
                        "run_id": run_id,
                        "run_evidence_sha256": evidence,
                        "duplicate_of": deepcopy(previous),
                    }
                )
            else:
                unique.append(run)
                seen_runs[run_id] = {
                    "run_evidence_sha256": evidence,
                    "archive": archive["archive"],
                    "archive_sha256": archive["archive_sha256"],
                }
        archive["runs"], archive["duplicate_runs"] = unique, duplicates
        results.append(archive)
    if audit_sources() != sources:
        raise AuditError("audit_source_changed_during_replay")
    metrics, totals = empty_metrics(), Counter()
    for archive in results:
        for run in archive["runs"]:
            aggregate_metrics(metrics, run["metrics"])
            totals.update(run["bytes"])
    return {
        "schema": "repropatch.context-trigger-audit.v1",
        "measurement": MEASUREMENT,
        "scope": "fixed_archived_tool_results_with_original_policy_and_current_optimizer",
        "model_requests": 0,
        "state_compaction_scope": "request_level_not_replayed",
        "audit_source_sha256": sources,
        "archives": results,
        "unique_run_count": len(seen_runs),
        "duplicate_run_count": sum(len(archive["duplicate_runs"]) for archive in results),
        "metrics": metrics,
        "bytes": dict(totals),
    }


def summary(result):
    runs = [run for archive in result["archives"] for run in archive["runs"]]
    lines = [
        "# Offline Tool Context Audit",
        "",
        f"Measurement: `{MEASUREMENT}`. Model requests: 0.",
        "Fixed archived tool results; original context policies; current optimizer.",
        "Bytes measure returned tool text, with native fold_tool_output as the baseline.",
        "State compaction is request-level and outside this tool-result replay.",
        "Task outcomes and provider token consumption require end-to-end execution.",
        "",
        f"Archives: {len(result['archives'])}; tools: {sum(run['tool_count'] for run in runs)}; "
        f"compared: {sum(run['compared_tool_count'] for run in runs)}.",
        f"Unique runs: {result['unique_run_count']}; duplicate runs excluded: "
        f"{result['duplicate_run_count']}.",
        f"Native bytes: {result['bytes'].get('native_bytes', 0)}; "
        f"projected bytes: {result['bytes'].get('projected_bytes', 0)}; "
        f"saved bytes: {result['bytes'].get('saved_bytes', 0)}.",
        "",
        "| Strategy | Attempts | Candidates | Triggers | Saved Bytes | Skip Reasons |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for name, metric in result["metrics"].items():
        skips = (
            ", ".join(f"{key}={value}" for key, value in sorted(metric["skip_reasons"].items()))
            or "-"
        )
        lines.append(
            f"| {name} | {metric['attempts']} | {metric['candidates']} | "
            f"{metric['triggers']} | {metric['saved_bytes']} | {skips} |"
        )
    lines.extend(["", "## Archives", ""])
    for archive in result["archives"]:
        lines.append(
            f"- SHA256 `{archive['archive_sha256']}`; "
            f"verified refs: {archive['verified_reference_count']}."
        )
        for run in archive["runs"]:
            lines.append(
                f"  Run `{run['run_id']}`; trigger threshold: "
                f"{run['state_aware_compaction']['compact_trigger_tokens']}; "
                f"audit skips: {json.dumps(run['audit_skip_reasons'], sort_keys=True)}."
            )
        for duplicate in archive["duplicate_runs"]:
            lines.append(f"  Duplicate run `{duplicate['run_id']}` excluded from totals.")
    return "\n".join(lines) + "\n"


def write_reports(output, reports, inputs):
    inputs = [path.resolve() for path in inputs]
    input_inodes = {(path.stat().st_dev, path.stat().st_ino) for path in inputs}

    def check_target(target):
        if target in inputs:
            raise AuditError("unsafe_output_path")
        try:
            info = target.lstat()
        except FileNotFoundError:
            return
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or (info.st_dev, info.st_ino) in input_inodes
        ):
            raise AuditError("unsafe_output_path")

    targets = [(output / name, raw) for name, raw in reports]
    for target, _ in targets:
        check_target(target)
    pending = []
    try:
        for target, raw in targets:
            descriptor, name = tempfile.mkstemp(prefix=".context-audit-", suffix=".tmp", dir=output)
            temporary = Path(name)
            pending.append((temporary, target))
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        for temporary, target in pending:
            check_target(target)
            os.replace(temporary, target)
    finally:
        for temporary, _ in pending:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, action="append")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    result = audit_archives(args.archive)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    write_reports(
        output,
        (
            ("results.json", json.dumps(result, indent=2, sort_keys=True) + "\n"),
            ("summary.md", summary(result)),
        ),
        args.archive,
    )
    LOGGER.info("Wrote %s and %s", output / "results.json", output / "summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
