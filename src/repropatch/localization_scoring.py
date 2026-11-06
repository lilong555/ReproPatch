"""Independent old-source labels and exact delivered-source exposure scoring."""

import hashlib
import math
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from statistics import mean

from .artifacts import MAX_AUDIT_BYTES, EvidenceRef, read_regular
from .errors import ReproPatchError
from .events import ENVELOPE_KEYS, EVENT_TYPES, _json, read_events
from .task import canonical_json, relative_file
from .workspace import SourceFile, SourceManifest, git, git_result

LABEL_SCHEMA = "repropatch.localization-labels.v1"
EXPOSURE_SCHEMA = "repropatch.localization.exposure.v1"
SCORE_SCHEMA = "repropatch.localization-score.v1"
ELIGIBILITY_SCHEMA = "repropatch.localization-eligibility.v1"
SHA = re.compile(r"[a-f0-9]{64}")
FOLDED_NOTICE = re.compile(
    r"\n\[\u5b8c\u6574\u5de5\u5177\u8f93\u51fa\uff1a([^\n\uff1b]+)"
    r"\uff1b([1-9][0-9]*) bytes\uff1bsha256=([a-f0-9]{64})\]\n"
)
HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?:.*)")
TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_input_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
)


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _sha(value):
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _path(value):
    _require(isinstance(value, str), "INVALID_PATH")
    relative_file(value)
    _require("\\" not in value, "INVALID_PATH")
    return value


def _digest(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _source(root):
    """Use the runtime manifest identity while excluding repository metadata."""
    root = Path(root).absolute()
    _require(root.is_dir() and not root.is_symlink(), "INVALID_SOURCE_ROOT")
    entries, texts = [], {}

    def onerror(error):
        raise error

    for directory, dirs, names in os.walk(root, followlinks=False, onerror=onerror):
        if Path(directory) == root:
            dirs[:] = [name for name in dirs if name != ".git"]
            names = [name for name in names if name != ".git"]
        _require(all(not (Path(directory) / name).is_symlink() for name in dirs), "SOURCE_SYMLINK")
        for name in sorted(names):
            path = Path(directory) / name
            raw, info = read_regular(path)
            relative = _path(path.relative_to(root).as_posix())
            entries.append(
                SourceFile(
                    relative,
                    hashlib.sha256(raw).hexdigest(),
                    len(raw),
                    "100755" if info.st_mode & 0o100 else "100644",
                )
            )
            try:
                text = raw.decode("utf-8")
                texts[relative] = text.splitlines() if "\0" not in text else None
            except UnicodeError:
                texts[relative] = None
    manifest = SourceManifest(tuple(sorted(entries, key=lambda item: item.path)))
    SourceManifest.from_dict(manifest.to_dict())
    return manifest, texts


def _patch_path(raw, prefix):
    # Git quotes paths using C escapes, including octal UTF-8 bytes.
    if raw.startswith('"'):
        _require(raw.endswith('"'), "INVALID_PATCH_PATH")
        body, output, offset = raw[1:-1], bytearray(), 0
        escapes = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, "\\": 92, '"': 34}
        while offset < len(body):
            if body[offset] != "\\":
                output.extend(body[offset].encode("utf-8"))
                offset += 1
                continue
            offset += 1
            _require(offset < len(body), "INVALID_PATCH_ESCAPE")
            if body[offset] in escapes:
                output.append(escapes[body[offset]])
                offset += 1
            else:
                octal = body[offset : offset + 3]
                _require(re.fullmatch(r"[0-3][0-7]{2}", octal), "INVALID_PATCH_ESCAPE")
                output.append(int(octal, 8))
                offset += 3
        raw = output.decode("utf-8")
    if raw == "/dev/null":
        return None
    _require(raw.startswith(prefix), "PATCH_PREFIX_REQUIRED")
    return _path(raw[len(prefix) :])


def _patch_files(patch):
    lines = patch.decode("utf-8").split("\n")
    if lines[-1] == "":
        lines.pop()
    files, current, index = [], None, 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("diff --git "):
            current = None
            index += 1
            continue
        if line.startswith("--- "):
            _require(
                index + 1 < len(lines) and lines[index + 1].startswith("+++ "),
                "MISSING_NEW_PATCH_PATH",
            )
            current = {
                "old_path": _patch_path(line[4:], "a/"),
                "new_path": _patch_path(lines[index + 1][4:], "b/"),
                "hunks": [],
            }
            _require(
                current["old_path"] is not None or current["new_path"] is not None,
                "EMPTY_PATCH_PATHS",
            )
            files.append(current)
            index += 2
            continue
        if line.startswith("@@"):
            match = HUNK.fullmatch(line)
            _require(current is not None and match is not None, "INVALID_PATCH_HUNK")
            old_start, old_count, new_start, new_count = (
                int(value) if value is not None else 1 for value in match.groups()
            )
            old_seen = new_seen = 0
            body = []
            index += 1
            while old_seen < old_count or new_seen < new_count:
                _require(index < len(lines), "TRUNCATED_PATCH_HUNK")
                item = lines[index]
                index += 1
                if item == "\\ No newline at end of file":
                    continue
                _require(item and item[0] in " +-", "INVALID_PATCH_LINE")
                old_seen += item[0] in " -"
                new_seen += item[0] in " +"
                _require(old_seen <= old_count and new_seen <= new_count, "PATCH_COUNT_MISMATCH")
                body.append(item)
            if index < len(lines) and lines[index] == "\\ No newline at end of file":
                index += 1
            current["hunks"].append(
                {
                    "old_start": old_start,
                    "old_count": old_count,
                    "new_start": new_start,
                    "new_count": new_count,
                    "body": body,
                }
            )
            continue
        _require(not line.startswith(("+", "-", " ", "\\")), "UNCONSUMED_PATCH_LINE")
        _require(not line.startswith(("GIT binary patch", "Binary files")), "BINARY_PATCH")
        index += 1
    _require(files and all(item["hunks"] for item in files), "NO_TEXT_HUNKS")
    paths = [item["old_path"] or item["new_path"] for item in files]
    _require(len(paths) == len(set(paths)), "DUPLICATE_PATCH_FILE")
    return files


def structural_eligibility(patch):
    """Classify qualified reference edits without publishing paths or spans."""
    files = _patch_files(patch)
    changed_existing = any(
        file["old_path"] is not None
        and any(line.startswith("-") for hunk in file["hunks"] for line in hunk["body"])
        for file in files
    )
    if changed_existing:
        return True, "changed_existing_old_lines"
    if all(file["old_path"] is None for file in files):
        return False, "new_file_only"
    return False, "pure_insertion"


def read_eligibility_registry(
    path,
    expected_sha256,
    *,
    instance_ids,
    task_contracts,
    qualification_archive_sha256,
    source_protocol_sha256=None,
):
    raw, _ = read_regular(Path(path), limit=MAX_AUDIT_BYTES)
    _require(
        _sha(expected_sha256) and hashlib.sha256(raw).hexdigest() == expected_sha256,
        "ELIGIBILITY_REGISTRY_HASH_MISMATCH",
    )
    registry = _json(raw)
    _require(registry.get("schema") == ELIGIBILITY_SCHEMA, "ELIGIBILITY_REGISTRY_SCHEMA")
    _require(
        registry.get("registry_sha256")
        == _digest({k: v for k, v in registry.items() if k != "registry_sha256"}),
        "ELIGIBILITY_REGISTRY_CONTENT_HASH",
    )
    if source_protocol_sha256 is not None:
        _require(
            registry.get("source_protocol_sha256") == source_protocol_sha256,
            "ELIGIBILITY_SOURCE_PROTOCOL_MISMATCH",
        )
    _require(
        sorted(item["sha256"] for item in registry["qualification_archives"])
        == sorted(qualification_archive_sha256),
        "ELIGIBILITY_ARCHIVE_SET_MISMATCH",
    )
    rows = registry["tasks"]
    _require(
        isinstance(rows, list)
        and len(rows) == len(instance_ids)
        and {r["instance_id"] for r in rows} == set(instance_ids),
        "ELIGIBILITY_TASK_SET_MISMATCH",
    )
    normalized = {}
    for row in rows:
        _require(
            set(row)
            == {
                "task_id",
                "instance_id",
                "eligible",
                "label_type",
                "reference_patch_sha256",
                "prepared_commit",
                "qualification_archive_sha256",
                "qualification_result_sha256",
                "qualification_task_sha256",
            },
            "ELIGIBILITY_METADATA_SCHEMA",
        )
        task_id = row["instance_id"].replace("__", "-").lower()
        _require(
            row["task_id"] == task_id and task_id not in normalized,
            "ELIGIBILITY_TASK_IDENTITY_MISMATCH",
        )
        _validate_registration(row)
        _require(
            row["prepared_commit"] == task_contracts[row["instance_id"]]["prepared_commit"],
            "ELIGIBILITY_PREPARED_COMMIT_MISMATCH",
        )
        _require(
            row["qualification_archive_sha256"] in qualification_archive_sha256,
            "ELIGIBILITY_TASK_ARCHIVE_MISMATCH",
        )
        normalized[task_id] = row
    _require(
        registry["total_tasks"] == len(rows)
        and registry["eligible_tasks"] == sum(row["eligible"] for row in rows),
        "ELIGIBILITY_COUNT_MISMATCH",
    )
    return normalized


def _validate_registration(row):
    _require(
        isinstance(row, dict) and type(row.get("eligible")) is bool,
        "INVALID_REGISTERED_ELIGIBILITY",
    )
    _require(
        row.get("label_type") in {"changed_existing_old_lines", "pure_insertion", "new_file_only"}
        and row["eligible"] == (row["label_type"] == "changed_existing_old_lines"),
        "REGISTERED_ELIGIBILITY_TYPE_MISMATCH",
    )
    _require(
        _sha(row.get("reference_patch_sha256"))
        and isinstance(row.get("prepared_commit"), str)
        and re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", row["prepared_commit"]),
        "INVALID_REGISTERED_SOURCE_IDENTITY",
    )


def _spans(numbers):
    result = []
    for number in sorted(set(numbers)):
        if result and number == result[-1][1] + 1:
            result[-1][1] = number
        else:
            result.append([number, number])
    return result


def _file_label(file, manifest, texts):
    path = file["old_path"]
    entry = manifest.by_path.get(path)
    text = texts.get(path)
    result = {
        "path": path or file["new_path"],
        "old_path": path,
        "new_path": file["new_path"],
        "source_sha256": entry.sha256 if entry else None,
        "eligible": False,
        "reason": None,
        "gold_old_spans": [],
        "insertion_anchors": [],
        "old_lines": {},
        "function_mapping": "not_collected",
    }
    if path is None:
        return {**result, "reason": "new_file"}
    if entry is None or text is None:
        return {**result, "reason": "missing_base_file" if entry is None else "non_utf8_source"}
    changed, anchors, last_end = [], [], 0
    for hunk in file["hunks"]:
        start, count = hunk["old_start"], hunk["old_count"]
        if (
            (count > 0 and not 1 <= start <= len(text))
            or (count == 0 and not 0 <= start <= len(text))
            or start + count - 1 > len(text)
            or (last_end and start < last_end)
        ):
            return {**result, "reason": "unmappable_old_range"}
        old_line = start if count else start + 1
        last_end = start + count
        removed, added, insertion_after = [], 0, None

        def finish_block(removed, added, insertion_after):
            if removed:
                changed.extend(removed)
            elif added:
                neighbor = [
                    n for n in (insertion_after, insertion_after + 1) if 1 <= n <= len(text)
                ]
                anchors.append(
                    {
                        "after_old_line": insertion_after,
                        "anchor_spans": _spans(neighbor),
                        "inserted_lines": added,
                        "eligible": bool(neighbor),
                        "reason": None if neighbor else "empty_base_file",
                    }
                )

        for item in hunk["body"]:
            if item[0] in " -" and (
                not 1 <= old_line <= len(text) or text[old_line - 1] != item[1:]
            ):
                return {**result, "reason": "base_content_mismatch"}
            if item[0] == " ":
                finish_block(removed, added, insertion_after)
                removed, added, insertion_after = [], 0, None
                old_line += 1
            elif item[0] == "-":
                removed.append(old_line)
                old_line += 1
            else:
                if insertion_after is None:
                    insertion_after = old_line - 1
                added += 1
        finish_block(removed, added, insertion_after)
    result["gold_old_spans"] = _spans(changed)
    result["insertion_anchors"] = anchors
    result["eligible"] = bool(changed)
    result["reason"] = None if changed else "pure_insertion"
    wanted = set(changed)
    for anchor in anchors:
        for start, end in anchor["anchor_spans"]:
            wanted.update(range(start, end + 1))
    result["old_lines"] = {str(line): text[line - 1] for line in sorted(wanted)}
    return result


def _replayed_patch(patch, source_root, parsed, manifest):
    """Let Git resolve hunk offsets in an isolated index of exact source blobs."""
    paths = {
        path
        for file in parsed
        for path in (file["old_path"], file["new_path"])
        if path in manifest.by_path
    }
    with tempfile.TemporaryDirectory(prefix="repropatch-labels-") as directory:
        temporary = Path(directory)
        repository = temporary / "index-repository"
        repository.mkdir()
        git(repository, "init", "--bare", "--template=", "-q")
        for number, path in enumerate(sorted(paths)):
            entry = manifest.by_path[path]
            raw, _ = read_regular(Path(source_root) / path)
            _require(hashlib.sha256(raw).hexdigest() == entry.sha256, "LABEL_SOURCE_CHANGED")
            blob_file = temporary / f"blob-{number}"
            blob_file.write_bytes(raw)
            blob = git(repository, "hash-object", "-w", "--no-filters", str(blob_file)).strip()
            git(repository, "update-index", "--add", "--cacheinfo", entry.git_mode, blob, path)
        base_tree = git(repository, "write-tree").strip()
        reference = temporary / "reference.patch"
        reference.write_bytes(patch)
        applied = git_result(
            repository, "apply", "--cached", "--unidiff-zero", "--whitespace=nowarn", str(reference)
        )
        if not applied.ok:
            return None
        normalized = git(
            repository,
            "diff",
            "--cached",
            "--no-ext-diff",
            "--no-textconv",
            "--no-renames",
            "--text",
            "--unified=3",
            base_tree,
            "--",
            strict=True,
        ).encode("utf-8")
        return normalized or None


def generate_labels(patch: bytes, source_root: Path, *, task_id: str) -> dict:
    """Generate private labels. This function has no runtime or model dependency."""
    _require(isinstance(task_id, str) and task_id, "TASK_ID_REQUIRED")
    manifest, texts = _source(source_root)
    parsed = _patch_files(patch)
    files = [_file_label(file, manifest, texts) for file in parsed]
    mapping = {"method": "hunk_headers", "normalized_patch_sha256": None}
    if any(file["reason"] in {"base_content_mismatch", "unmappable_old_range"} for file in files):
        normalized = _replayed_patch(patch, source_root, parsed, manifest)
        if normalized is not None:
            files = [_file_label(file, manifest, texts) for file in _patch_files(normalized)]
            mapping = {
                "method": "git_index_replay",
                "normalized_patch_sha256": hashlib.sha256(normalized).hexdigest(),
            }
    eligible = any(item["eligible"] for item in files)
    result = {
        "schema": LABEL_SCHEMA,
        "task_id": task_id,
        "patch_sha256": hashlib.sha256(patch).hexdigest(),
        "mapping": mapping,
        "source_tree_sha256": manifest.sha256,
        "source_manifest": manifest.to_dict(),
        "eligible": eligible,
        "label_type": _mapped_label_type(files),
        "reason": None if eligible else "no_mappable_changed_old_lines",
        "insertion_eligible": any(
            anchor["eligible"] for file in files for anchor in file["insertion_anchors"]
        ),
        "files": files,
        "scoring_model_requests": 0,
    }
    result["labels_sha256"] = _digest(result)
    return result


def _mapped_label_type(files):
    if any(file["eligible"] for file in files):
        return "changed_existing_old_lines"
    if any(file["insertion_anchors"] for file in files):
        return "pure_insertion"
    if files and all(file["reason"] == "new_file" for file in files):
        return "new_file_only"
    return "unmappable"


def validate_labels(labels):
    _require(
        isinstance(labels, dict) and labels.get("schema") == LABEL_SCHEMA, "INVALID_LABEL_SCHEMA"
    )
    _require(
        _digest({k: v for k, v in labels.items() if k != "labels_sha256"})
        == labels.get("labels_sha256"),
        "LABEL_HASH_MISMATCH",
    )
    manifest = SourceManifest.from_dict(labels["source_manifest"])
    _require(manifest.sha256 == labels["source_tree_sha256"], "LABEL_SOURCE_MISMATCH")
    _require(isinstance(labels["task_id"], str) and labels["task_id"], "INVALID_LABEL_TASK")
    _require(
        _sha(labels["patch_sha256"]) and type(labels["eligible"]) is bool, "INVALID_LABEL_IDENTITY"
    )
    paths = set()
    for file in labels["files"]:
        path = _path(file["path"])
        _require(path not in paths, "DUPLICATE_LABEL_FILE")
        paths.add(path)
        if file["source_sha256"] is not None:
            _require(
                path in manifest.by_path and file["source_sha256"] == manifest.by_path[path].sha256,
                "LABEL_FILE_HASH_MISMATCH",
            )
        ranges = file["gold_old_spans"] + [
            span for a in file["insertion_anchors"] for span in a["anchor_spans"]
        ]
        for start, end in ranges:
            _require(_integer(start, 1) and _integer(end, start), "INVALID_LABEL_SPAN")
            _require(end - start < 1_000_000, "LABEL_SPAN_TOO_LARGE")
            _require(
                all(isinstance(file["old_lines"].get(str(n)), str) for n in range(start, end + 1)),
                "MISSING_LABEL_TEXT",
            )
        _require(file["eligible"] == bool(file["gold_old_spans"]), "LABEL_ELIGIBILITY_MISMATCH")
    _require(
        labels["eligible"] == any(file["eligible"] for file in labels["files"]),
        "LABEL_ELIGIBILITY_MISMATCH",
    )
    return labels


def _read_trace(directory):
    if (directory / "events.sqlite3").exists():
        snapshot = read_events(directory, directory.name)
        _require(snapshot.version in (1, 2), "LEGACY_TRACE_UNSUPPORTED")
        return list(snapshot.events), "sqlite", snapshot.run
    raw, _ = read_regular(directory / "events.jsonl", limit=MAX_AUDIT_BYTES)
    events = [_json(line) for line in raw.splitlines() if line]
    return events, "jsonl", None


def _validate_trace(events):
    run_id, previous_time = None, None
    for seq, event in enumerate(events, 1):
        _require(isinstance(event, dict) and set(event) == ENVELOPE_KEYS, "INVALID_EVENT_ENVELOPE")
        _require(
            type(event["schema_version"]) is int
            and event["schema_version"] == 1
            and type(event["seq"]) is int
            and event["seq"] == seq,
            "INVALID_EVENT_SEQUENCE",
        )
        _require(
            isinstance(event["run_id"], str) and re.fullmatch(r"[a-f0-9]{32}", event["run_id"]),
            "INVALID_RUN_ID",
        )
        run_id = run_id or event["run_id"]
        _require(event["run_id"] == run_id, "MIXED_RUN_TRACE")
        _require(
            event["type"] in EVENT_TYPES | {"localization_exposure"}
            and isinstance(event["payload"], dict),
            "INVALID_EVENT_TYPE",
        )
        timestamp = datetime.fromisoformat(event["timestamp"])
        _require(
            timestamp.utcoffset() is not None and timestamp.utcoffset().total_seconds() == 0,
            "INVALID_EVENT_TIMESTAMP",
        )
        _require(previous_time is None or timestamp >= previous_time, "REVERSED_EVENT_TIME")
        previous_time = timestamp
        step, tool = event["step_id"], event["tool_call_id"]
        _require(step is None or _integer(step, 1), "INVALID_EVENT_STEP")
        if tool is not None:
            _require(
                step is not None
                and isinstance(tool, str)
                and re.fullmatch(rf"s{step:06d}\.t0[1-8]", tool),
                "INVALID_EVENT_TOOL",
            )
        operation = event["operation_id"]
        _require(
            operation is None
            or (isinstance(operation, str) and re.fullmatch(r"[a-f0-9]{32}", operation)),
            "INVALID_OPERATION_ID",
        )
    return run_id


def _usage(raw):
    _require(raw is None or isinstance(raw, dict), "INVALID_USAGE")
    raw = raw or {}
    for key in TOKEN_KEYS:
        _require(raw.get(key) is None or _integer(raw[key]), "INVALID_TOKEN_COUNT")
    synthetic = raw.get("synthetic")
    _require(synthetic is None or type(synthetic) is bool, "INVALID_SYNTHETIC_FLAG")
    return {
        **{key: None if synthetic else raw.get(key) for key in TOKEN_KEYS},
        "synthetic": synthetic,
        "raw": raw or None,
    }


def _exposure(event, directory):
    p = event["payload"]
    required = {
        "schema",
        "phase",
        "tool_name",
        "tool_call_id",
        "model_step",
        "tool_calls_used",
        "localization_tools_used",
        "tool_ordinal",
        "elapsed_seconds",
        "cumulative_usage",
        "source_tree_sha256",
        "source_files",
        "delivered_ref",
        "carrier_phase",
        "produced_model_step",
        "delivery_status",
    }
    _require(required <= p.keys() and p["schema"] == EXPOSURE_SCHEMA, "INVALID_EXPOSURE_SCHEMA")
    _require(p["phase"] in {"localization", "repair"}, "INVALID_EXPOSURE_PHASE")
    _require(isinstance(p["tool_name"], str) and p["tool_name"], "INVALID_TOOL_NAME")
    for key in ("model_step", "tool_calls_used", "localization_tools_used", "tool_ordinal"):
        _require(_integer(p[key]), "INVALID_EXPOSURE_COUNTER")
    _require(
        p["localization_tools_used"] <= p["tool_calls_used"]
        and p["tool_ordinal"] <= p["tool_calls_used"],
        "INVALID_EXPOSURE_BUDGET",
    )
    _require(
        type(p["elapsed_seconds"]) in (int, float)
        and math.isfinite(p["elapsed_seconds"])
        and p["elapsed_seconds"] >= 0,
        "INVALID_ELAPSED_SECONDS",
    )
    confirmed = p.get("delivery_status") == "confirmed"
    _require(confirmed, "UNCONFIRMED_EXPOSURE")
    if p["tool_name"] == "baseline":
        _require(
            p["tool_call_id"] in {None, "baseline"} and event["tool_call_id"] is None,
            "EXPOSURE_TOOL_ID_MISMATCH",
        )
    else:
        produced = p["produced_model_step"]
        _require(_integer(produced, 1) and produced < p["model_step"], "INVALID_PRODUCING_STEP")
        _require(
            isinstance(p["tool_call_id"], str)
            and re.fullmatch(rf"s{produced:06d}\.t0[1-8]", p["tool_call_id"]),
            "EXPOSURE_TOOL_ID_MISMATCH",
        )
        _require(event["tool_call_id"] in {None, p["tool_call_id"]}, "EXPOSURE_TOOL_ID_MISMATCH")
    _require(p["model_step"] >= (event["step_id"] or 0), "EXPOSURE_STEP_MISMATCH")
    _require(
        p["carrier_phase"] in {"localization", "repair"} and p["model_step"] >= 1,
        "INVALID_CARRIER_PHASE",
    )
    _require(p["tool_name"] == "baseline" or p["tool_call_id"] is not None, "MISSING_TOOL_ID")
    _require(
        _sha(p["source_tree_sha256"]) and isinstance(p["source_files"], dict),
        "INVALID_SOURCE_IDENTITY",
    )
    for path, sha in p["source_files"].items():
        _path(path)
        _require(_sha(sha), "INVALID_SOURCE_FILE_HASH")
    _require(
        isinstance(p["delivered_ref"], dict)
        and set(p["delivered_ref"]) == {"path", "sha256", "size_bytes"},
        "INVALID_DELIVERED_REF",
    )
    raw = EvidenceRef(**p["delivered_ref"]).read(directory, limit=MAX_AUDIT_BYTES)
    text = raw.decode("utf-8")
    receipt_format = p.get("receipt_format", "json")
    _require(receipt_format in {"json", "folded_text", "unparsed_text"}, "INVALID_RECEIPT_FORMAT")
    try:
        body = _json(text)
    except ValueError:
        _require(receipt_format == "folded_text", "UNPARSED_DELIVERED_TEXT")
        notices = list(FOLDED_NOTICE.finditer(text))
        _require(len(notices) == 1, "INVALID_FOLDED_NOTICE")
        reference, original_bytes, original_hash = notices[0].groups()
        _path(reference)
        _require(int(original_bytes) > len(raw), "INVALID_FOLDED_ORIGINAL_SIZE")
        body = {
            "folded_receipt": {
                "path": reference,
                "sha256": original_hash,
                "size_bytes": int(original_bytes),
            }
        }
    else:
        _require(receipt_format == "json", "RECEIPT_FORMAT_MISMATCH")
        _require(isinstance(body, dict), "INVALID_DELIVERED_BODY")
    return p, body, _usage(p["cumulative_usage"])


def _body_lines(name, body):
    """Only explicit source text yields lines; compacted/error receipts yield none."""
    if body.get("ok") is False or "data" not in body:
        return [], []
    data = body["data"]
    _require(isinstance(data, dict), "INVALID_DELIVERED_DATA")
    lines, candidates = [], []
    if name == "read_file" and "text" in data:
        path, text, start, end = data["path"], data["text"], data["start_line"], data["end_line"]
        _path(path)
        _require(
            isinstance(text, str) and "\0" not in text and _integer(start, 1) and _integer(end),
            "INVALID_SOURCE_WINDOW",
        )
        parts = text.splitlines()
        _require(end == start + len(parts) - 1, "SOURCE_WINDOW_COUNT_MISMATCH")
        lines = [
            (
                path,
                start + offset,
                part,
                offset == len(parts) - 1 and not text.endswith(("\n", "\r")),
            )
            for offset, part in enumerate(parts)
        ]
    elif name == "search_code" and "matches" in data:
        _require(isinstance(data["matches"], list), "INVALID_SOURCE_MATCHES")
        for match in data["matches"]:
            _require(isinstance(match, dict), "INVALID_SOURCE_MATCH")
            path, number, text = match["path"], match["line"], match["text"]
            _path(path)
            _require(
                _integer(number, 1)
                and isinstance(text, str)
                and "\0" not in text
                and len(text.splitlines()) <= 1,
                "INVALID_SOURCE_MATCH",
            )
            lines.append((path, number, text, True))
    elif name == "search_files" and "candidates" in data:
        _require(isinstance(data["candidates"], list), "INVALID_CANDIDATES")
        for candidate in data["candidates"]:
            _require(isinstance(candidate, dict), "INVALID_CANDIDATE")
            candidates.append(_path(candidate["path"]))
    return lines, candidates


def _metric(eligible, first, tool_budget, covered, spans):
    hit = first is not None if eligible else None
    within = first is not None and first["budget_tools"] <= tool_budget if eligible else None
    return {
        "eligible": eligible,
        "hit_event": hit,
        "first_hit": first,
        "hit_within_budget": within,
        "censored": not hit if eligible else None,
        "capped_first_hit_tools": min(first["budget_tools"], tool_budget)
        if first
        else (tool_budget if eligible else None),
        "covered_spans": len(covered),
        "total_spans": spans,
        "span_coverage": len(covered) / spans if spans else None,
        "all_spans_hit": len(covered) == spans if spans else None,
    }


def score_run(
    run_dir: Path, labels: dict, *, tool_budget=8, phase="localization", cold_score=None
) -> dict:
    validate_labels(labels)
    _require(
        _integer(tool_budget, 1) and phase in {"localization", "repair", "all"},
        "INVALID_SCORE_BUDGET",
    )
    directory = Path(run_dir)
    result = {
        "schema": SCORE_SCHEMA,
        "status": "scored",
        "task_id": labels["task_id"],
        "labels_sha256": labels["labels_sha256"],
        "reference_patch_sha256": labels["patch_sha256"],
        "label_type": _mapped_label_type(labels["files"]),
        "source_tree_sha256": labels["source_tree_sha256"],
        "run_id": None,
        "phase": phase,
        "tool_budget": tool_budget,
        "eligible": labels["eligible"],
        "label_reason": labels["reason"],
        "trace_source": None,
        "evidence_status": "complete",
        "errors": [],
        "exposures": [],
        "candidate_top5": [],
        "post_edit_exposures": [],
        "stop_reason": None,
        "outcome": None,
        "observed_until": None,
        "phase_finished": None,
        "provider_usage": _usage(None),
        "cold_verification": cold_score,
        "scoring_model_requests": 0,
    }
    changed = [
        (file["path"], start, end)
        for file in labels["files"]
        for start, end in file["gold_old_spans"]
    ]
    anchors = [
        (file["path"], start, end)
        for file in labels["files"]
        for a in file["insertion_anchors"]
        for start, end in a["anchor_spans"]
    ]
    gold_files = {path for path, _, _ in changed}
    by_path = {file["path"]: file for file in labels["files"]}
    first = anchor_first = candidate_first = None
    covered, anchor_covered, candidate_order = set(), set(), []
    last_counters, seen_ids, events, successful_models = None, set(), [], {}
    try:
        events, result["trace_source"], state = _read_trace(directory)
        result["run_id"] = _validate_trace(events)
        _require(events, "EMPTY_TRACE")
        if state:
            result.update(
                outcome=state.get("outcome"),
                stop_reason=state.get("agent_stop_reason") or state.get("reason_code"),
            )
        for event in events:
            p = event["payload"]
            if event["type"] == "model_finished":
                result["provider_usage"] = _usage(p.get("cumulative_usage"))
                successful_models[event["step_id"]] = result["provider_usage"]
            elif event["type"] == "localization_phase_finished":
                result["phase_finished"] = {
                    "seq": event["seq"],
                    "timestamp": event["timestamp"],
                    **p,
                }
            elif event["type"] == "agent_stopped":
                result["stop_reason"] = p.get("reason") or p.get("reason_code")
            elif event["type"] == "state_changed" and p.get("to") == "FINISHED":
                result.update(
                    outcome=p.get("outcome"),
                    stop_reason=result["stop_reason"] or p.get("reason_code"),
                )
            if event["type"] != "localization_exposure":
                continue
            try:
                p, body, usage = _exposure(event, directory)
                if p.get("delivery_status") == "confirmed":
                    _require(
                        successful_models.get(p["model_step"]) == usage,
                        "UNCONFIRMED_CARRIER_RESPONSE",
                    )
                counters = tuple(
                    p[k]
                    for k in (
                        "model_step",
                        "tool_calls_used",
                        "localization_tools_used",
                        "tool_ordinal",
                        "elapsed_seconds",
                    )
                )
                _require(
                    last_counters is None
                    or all(a >= b for a, b in zip(counters, last_counters, strict=True)),
                    "REVERSED_EXPOSURE_COUNTER",
                )
                identity = p["tool_call_id"] or "baseline"
                _require(identity not in seen_ids, "DUPLICATE_EXPOSURE")
                seen_ids.add(identity)
                last_counters = counters
                lines, candidates = _body_lines(p["tool_name"], body)
                _require(
                    all(
                        path in p["source_files"]
                        for path in {*candidates, *(line[0] for line in lines)}
                    ),
                    "UNAUTHORIZED_EXPOSURE_PATH",
                )
                point = {
                    "seq": event["seq"],
                    "timestamp": event["timestamp"],
                    "phase": p["phase"],
                    "carrier_phase": p.get("carrier_phase"),
                    "receipt_format": p.get("receipt_format", "json"),
                    "tool_name": p["tool_name"],
                    "tool_call_id": p["tool_call_id"],
                    **{
                        k: p[k]
                        for k in (
                            "model_step",
                            "tool_calls_used",
                            "localization_tools_used",
                            "tool_ordinal",
                            "elapsed_seconds",
                        )
                    },
                    "budget_tools": p["tool_calls_used"],
                    "provider_usage": usage,
                    "delivered_ref": p["delivered_ref"],
                }
                result["provider_usage"] = usage
                in_phase = phase == "all" or p["phase"] == phase
                current_source = p["source_tree_sha256"] == labels["source_tree_sha256"]
                if current_source:
                    expected = {f["path"]: f["sha256"] for f in labels["source_manifest"]["files"]}
                    _require(
                        all(expected.get(path) == sha for path, sha in p["source_files"].items()),
                        "SOURCE_FILE_IDENTITY_MISMATCH",
                    )
                if not current_source:
                    result["post_edit_exposures"].append(
                        {**point, "reason": "source_tree_changed", "source_lines": len(lines)}
                    )
                if not in_phase:
                    continue
                result["observed_until"] = point
                row = {
                    **point,
                    "base_source": current_source,
                    "source_lines": len(lines),
                    "candidate_paths": candidates,
                    "changed_span_ids": [],
                    "anchor_span_ids": [],
                }
                if current_source:
                    for path, number, text, partial in lines:
                        if not text:
                            continue
                        file = by_path.get(path)
                        expected_line = file["old_lines"].get(str(number)) if file else None
                        if expected_line is not None:
                            _require(
                                text == expected_line
                                or (partial and text and expected_line.startswith(text)),
                                "DELIVERED_SOURCE_TEXT_MISMATCH",
                            )
                            for index, (gold_path, start, end) in enumerate(changed):
                                if path == gold_path and start <= number <= end:
                                    row["changed_span_ids"].append(index)
                            for index, (gold_path, start, end) in enumerate(anchors):
                                if path == gold_path and start <= number <= end:
                                    row["anchor_span_ids"].append(index)
                    for path in candidates:
                        if path not in candidate_order:
                            candidate_order.append(path)
                        if (
                            path in gold_files
                            and candidate_order.index(path) < 5
                            and candidate_first is None
                        ):
                            candidate_first = point
                    if row["changed_span_ids"] and first is None:
                        first = point
                    if row["anchor_span_ids"] and anchor_first is None:
                        anchor_first = point
                    covered.update(row["changed_span_ids"])
                    anchor_covered.update(row["anchor_span_ids"])
                result["exposures"].append(row)
            except (OSError, ValueError, TypeError, KeyError, ReproPatchError) as exc:
                result["errors"].append({"seq": event["seq"], "code": str(exc).split(":", 1)[0]})
    except (OSError, ValueError, TypeError, KeyError, ReproPatchError) as exc:
        result["errors"].append({"seq": None, "code": str(exc).split(":", 1)[0]})
    if not result["exposures"]:
        result["errors"].append({"seq": None, "code": "NO_VALID_EXPOSURES"})
    if result["errors"]:
        result["evidence_status"] = "incomplete"
    result.update(_metric(labels["eligible"], first, tool_budget, covered, len(changed)))
    result["insertion_anchor"] = _metric(
        labels["insertion_eligible"], anchor_first, tool_budget, anchor_covered, len(anchors)
    )
    result["candidate_top5"] = candidate_order[:5]
    result["candidate_top5_hit"] = candidate_first is not None if gold_files else None
    result["candidate_top5_first_hit"] = candidate_first
    result["trace_last_seq"] = events[-1]["seq"] if events else None
    result["stop_reason"] = result["stop_reason"] or (
        "missing_trace" if not events else "not_recorded"
    )
    return result


def summarize_scores(
    scores,
    *,
    task_ids,
    arms=("A", "B", "C"),
    repeat_ids=(1, 2),
    labels_by_task=None,
    tool_budget=8,
    eligibility_by_task=None,
    outcomes_by_run=None,
):
    """Average repeats within each task before paired task-level differences."""
    _require(len(task_ids) == len(set(task_ids)) and task_ids, "INVALID_TASK_DENOMINATOR")
    _require(_integer(tool_budget, 1), "INVALID_SUMMARY_TOOL_BUDGET")
    registrations = eligibility_by_task or {}
    outcomes = outcomes_by_run or {}
    _require(
        all(
            task in task_ids and arm in arms and repeat in repeat_ids
            for task, arm, repeat in outcomes
        ),
        "UNREGISTERED_ACCOUNTING_OUTCOME",
    )
    if eligibility_by_task is not None:
        _require(set(task_ids) <= registrations.keys(), "MISSING_REGISTERED_ELIGIBILITY")
        for task_id in task_ids:
            registration = registrations[task_id]
            _validate_registration(registration)
            _require(registration["task_id"] == task_id, "REGISTERED_TASK_IDENTITY_MISMATCH")
    indexed = {}
    for score in scores:
        _require(score.get("schema") == SCORE_SCHEMA, "INVALID_SCORE_SCHEMA")
        key = score["task_id"], score["arm"], score["repeat_id"]
        _require(
            key[0] in task_ids and key[1] in arms and key[2] in repeat_ids, "UNREGISTERED_SCORE"
        )
        _require(key not in indexed, "DUPLICATE_ATTEMPT_SCORE")
        _require(score.get("tool_budget") == tool_budget, "SCORE_TOOL_BUDGET_MISMATCH")
        registration = registrations.get(key[0])
        if registration:
            _require(
                type(score.get("eligible")) is bool
                and score["eligible"] == registration["eligible"],
                "REGISTERED_ELIGIBILITY_CONTRACT_MISMATCH",
            )
            _require(
                score.get("label_type") == registration["label_type"]
                and score.get("reference_patch_sha256") == registration["reference_patch_sha256"],
                "REGISTERED_LABEL_CONTRACT_MISMATCH",
            )
        if score["eligible"]:
            _require(
                type(score.get("hit_within_budget")) is bool
                and type(score.get("candidate_top5_hit")) is bool
                and _integer(score.get("capped_first_hit_tools"))
                and score["capped_first_hit_tools"] <= tool_budget,
                "ELIGIBLE_SCORE_METRICS_MISSING",
            )
        indexed[key] = score
    metrics = ("hit_within_budget", "capped_first_hit_tools", "candidate_top5_hit")
    tasks = []
    for task in task_ids:
        available = [score for (t, _, _), score in indexed.items() if t == task]
        label_ids = {
            (score["labels_sha256"], score["eligible"], score["tool_budget"], score["phase"])
            for score in available
        }
        _require(len(label_ids) <= 1, "TASK_SCORE_CONTRACT_MISMATCH")
        frozen_labels = (labels_by_task or {}).get(task)
        registered = registrations.get(task)
        if frozen_labels is not None:
            validate_labels(frozen_labels)
            _require(frozen_labels["task_id"] == task, "FROZEN_LABEL_TASK_MISMATCH")
            _require(
                all(s["labels_sha256"] == frozen_labels["labels_sha256"] for s in available),
                "FROZEN_LABEL_IDENTITY_MISMATCH",
            )
            if registered:
                _require(
                    frozen_labels["eligible"] == registered["eligible"]
                    and _mapped_label_type(frozen_labels["files"]) == registered["label_type"]
                    and frozen_labels["patch_sha256"] == registered["reference_patch_sha256"],
                    "REGISTERED_FROZEN_LABEL_CONTRACT_MISMATCH",
                )
        eligible = (
            registered["eligible"]
            if registered
            else (
                frozen_labels["eligible"]
                if frozen_labels
                else (available[0]["eligible"] if available else None)
            )
        )
        budget = available[0]["tool_budget"] if available else tool_budget
        actual_label = frozen_labels is not None or bool(available)
        kind = (
            registered["label_type"]
            if registered
            else (
                _mapped_label_type(frozen_labels["files"])
                if frozen_labels
                else (available[0].get("label_type") if available else None)
            )
        )
        row = {
            "task_id": task,
            "eligible": eligible,
            "registered_eligible": registered["eligible"] if registered else None,
            "label_type": kind,
            "actual_label_available": actual_label,
            "observed_score_runs": len(available),
            "arms": {},
        }
        for arm in arms:
            repeats = [indexed.get((task, arm, repeat)) for repeat in repeat_ids]
            accounting = [
                outcomes.get((task, arm, repeat)) or score or {}
                for repeat, score in zip(repeat_ids, repeats, strict=True)
            ]
            values = {}
            for metric in metrics:
                observations = [
                    (
                        score.get(metric)
                        if score
                        else (budget if metric == "capped_first_hit_tools" else False)
                    )
                    for score in repeats
                ]
                values[metric] = (
                    mean(float(value) for value in observations)
                    if eligible and all(v is not None for v in observations)
                    else None
                )
            values["provider_input_tokens"] = _complete_mean(
                [_usage(s.get("provider_usage"))["input_tokens"] for s in accounting]
            )
            values["provider_output_tokens"] = _complete_mean(
                [_usage(s.get("provider_usage"))["output_tokens"] for s in accounting]
            )
            values["cold_accepted"] = _complete_mean(
                [(s.get("cold_verification") or {}).get("accepted") for s in accounting]
            )
            row["arms"][arm] = {
                **values,
                "observed_repeats": sum(s is not None for s in repeats),
                "expected_repeats": len(repeat_ids),
                "insertion_anchor_hit_within_budget": _complete_mean(
                    [
                        (s.get("insertion_anchor") or {}).get("hit_within_budget") if s else None
                        for s in repeats
                    ]
                )
                if kind == "pure_insertion"
                else None,
            }
        tasks.append(row)
    pairs = []
    for left, right in zip(arms, arms[1:], strict=False):
        for metric in (
            *metrics,
            "provider_input_tokens",
            "provider_output_tokens",
            "cold_accepted",
        ):
            diffs = [
                {
                    "task_id": row["task_id"],
                    "difference": row["arms"][right][metric] - row["arms"][left][metric],
                }
                for row in tasks
                if row["arms"][left][metric] is not None and row["arms"][right][metric] is not None
            ]
            pairs.append(
                {
                    "contrast": f"{right}-{left}",
                    "metric": metric,
                    "task_denominator": len(diffs),
                    "mean_difference": mean(d["difference"] for d in diffs) if diffs else None,
                    "negative": sum(d["difference"] < 0 for d in diffs),
                    "equal": sum(d["difference"] == 0 for d in diffs),
                    "positive": sum(d["difference"] > 0 for d in diffs),
                    "tasks": diffs,
                }
            )
    return {
        "schema": "repropatch.localization-summary.v1",
        "total_tasks": len(task_ids),
        "eligible_tasks": sum(row["eligible"] is True for row in tasks),
        "registered_eligible_tasks": sum(row["registered_eligible"] is True for row in tasks),
        "missing_registration_tasks": sum(row["registered_eligible"] is None for row in tasks),
        "missing_label_tasks": sum(not row["actual_label_available"] for row in tasks),
        "missing_score_tasks": sum(row["observed_score_runs"] == 0 for row in tasks),
        "actual_label_tasks": sum(row["actual_label_available"] for row in tasks),
        "label_coverage": sum(row["eligible"] is True for row in tasks) / len(tasks),
        "expected_runs": len(task_ids) * len(arms) * len(repeat_ids),
        "observed_runs": len(scores),
        "missing_score_runs": len(task_ids) * len(arms) * len(repeat_ids) - len(scores),
        "complete_actual_scores": sum(
            s.get("evidence_status") == "complete" and s.get("status") == "scored" for s in scores
        ),
        "all_actual_scores_complete": len(scores) == len(task_ids) * len(arms) * len(repeat_ids)
        and all(
            s.get("evidence_status") == "complete" and s.get("status") == "scored" for s in scores
        ),
        "tasks": tasks,
        "full_overview": tasks,
        "insertion_only_tasks": [row for row in tasks if row["label_type"] == "pure_insertion"],
        "paired": pairs,
        "arms": {
            arm: {
                metric: {
                    "mean": mean(values)
                    if (
                        values := [
                            row["arms"][arm][metric]
                            for row in tasks
                            if row["arms"][arm][metric] is not None
                        ]
                    )
                    else None,
                    "task_denominator": len(values),
                }
                for metric in (
                    *metrics,
                    "provider_input_tokens",
                    "provider_output_tokens",
                    "cold_accepted",
                )
            }
            for arm in arms
        },
    }


def _complete_mean(values):
    return mean(values) if values and all(v is not None for v in values) else None
