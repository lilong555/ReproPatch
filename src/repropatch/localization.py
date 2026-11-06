"""Bounded literal search and ranking from runtime-registered visible feedback.

Only ``observe`` accepts feedback; ``search`` accepts no evidence paths. File
summaries and hit-line pages contain positions, with source windows provided by
the existing read_file tool. Cursor MACs bind pagination to the source, scope,
query, policy and (for feedback ranking) the registered evidence snapshot.
"""

import base64
import hashlib
import hmac
import json
import re
import secrets
import stat
import time
from array import array
from bisect import bisect_left
from collections import OrderedDict
from copy import deepcopy
from dataclasses import asdict, dataclass

from .context_diagnostics import COMPILER, SGR
from .errors import PolicyError, SourceChanged
from .task import canonical_json, relative_file

OUTPUT_BYTES = 64 * 1024
MAX_CACHE_BYTES = 64 * 1024 * 1024
MAX_CACHE_CHUNKS = 8
RANKING_RESERVE_BYTES = 1024
MAX_VISIBLE_BYTES = 2 * 1024 * 1024
MAX_PARSE_LINES = 32768
MAX_LINE_BYTES = 16384
MAX_RECEIPTS = 32
MAX_EVIDENCE = 64
MAX_STATE_BYTES = 8 * 1024 * 1024
HIDDEN_ROLES = frozenset({"oracle", "cold", "cold_verification", "independent", "candidate_export"})
FEEDBACK_SCHEMA = "repropatch.localization-feedback.v1"
FEEDBACK_LOG_NAMES = ("baseline-configure.log", "baseline-build.log", "baseline-ctest.log")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
GTEST = re.compile(r"^(?P<file>.+?):(?P<line>\d{1,10}):\s*Failure(?:\s.*)?$")
STACK = re.compile(r"(?:^|\s)(?P<file>[^\s:]+):(?P<line>\d{1,10})(?::\d{1,10})?(?:\s|$)")
RUN_TEST = re.compile(r"^\[\s*RUN\s*\]\s+(\S+)")
FAIL_TEST = re.compile(r"^\[\s*FAILED\s*\]\s+(\S+)")
TEXT_FIELDS = ("stdout", "stderr", "output", "diagnostic", "unparsed_output")


def _sha(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _error(reason):
    raise PolicyError("LOCALIZATION_" + reason)


@dataclass(frozen=True)
class LocalizationLimits:
    """Deterministic scan limits are separate from serialized page limits."""

    scan_bytes: int = 16 * 1024 * 1024
    scan_files: int = 128
    page_files: int = 12
    hit_lines: int = 8
    output_bytes: int = OUTPUT_BYTES

    def __post_init__(self):
        for name, maximum in (
            ("scan_bytes", 16 * 1024 * 1024),
            ("scan_files", 1024),
            ("page_files", 32),
            ("hit_lines", 32),
            ("output_bytes", OUTPUT_BYTES),
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= maximum:
                _error("INVALID_LIMIT_" + name.upper())
        if self.output_bytes < 16 * 1024:
            _error("INVALID_LIMIT_OUTPUT_BYTES")


class Localization:
    def __init__(self, toolbox, mode="bounded", state=None, *, limits=None, source_roots=()):
        if mode not in {"bounded", "feedback"}:
            _error("INVALID_MODE")
        self.toolbox = toolbox
        self.mode = mode
        self.limits = limits or LocalizationLimits()
        roots = ["/src", str(toolbox.workspace.path), *source_roots]
        if any(not isinstance(root, str) or not root.startswith("/") for root in roots):
            _error("INVALID_SOURCE_ROOT")
        self.source_roots = tuple(
            sorted(set(root.rstrip("/") for root in roots), key=len, reverse=True)
        )
        if "" in self.source_roots:
            _error("INVALID_SOURCE_ROOT")
        self._policy = _sha(
            {
                "limits": asdict(self.limits),
                "roots": sorted(source_roots),
                "cache_version": 1,
                "cache_bytes": MAX_CACHE_BYTES,
                "cache_chunks": MAX_CACHE_CHUNKS,
                "ranking_reserve_bytes": RANKING_RESERVE_BYTES,
            }
        )
        self._key = secrets.token_hex(32)
        self._source_tree_sha256 = toolbox.workspace.expected_manifest.sha256
        self._source_epoch = 0
        self._receipts = []
        self._cache = OrderedDict()
        self._cache_bytes = 0
        self._metrics = {
            "searches": 0,
            "scan_files": 0,
            "scan_bytes": 0,
            "scan_seconds": 0.0,
            "ranking_seconds": 0.0,
            "output_bytes": 0,
            "receipts_evicted": 0,
            "cache_builds": 0,
            "cache_hits": 0,
            "cache_evictions": 0,
            "source_read_bytes": 0,
            "validation_read_bytes": 0,
            "metadata_checks": 0,
        }
        if state is not None:
            self._restore(state)

    def _restore(self, state):
        try:
            raw = canonical_json(state)
            if len(raw) > MAX_STATE_BYTES:
                _error("STATE_LIMIT")
            body = deepcopy(state)
            digest = body.pop("state_sha256")
            if (
                _sha(body) != digest
                or body["schema_version"] != 1
                or body["policy_sha256"] != self._policy
                or not SHA256.fullmatch(body["cursor_key"])
                or not isinstance(body["receipts"], list)
                or len(body["receipts"]) > MAX_RECEIPTS
            ):
                _error("STATE_INVALID")
            for receipt in body["receipts"]:
                content = dict(receipt)
                checksum = content.pop("record_sha256")
                if _sha(content) != checksum:
                    _error("EVIDENCE_HASH_MISMATCH")
                if len(receipt["evidence"]) > MAX_EVIDENCE:
                    _error("STATE_INVALID")
                for evidence in receipt["evidence"]:
                    content = dict(evidence)
                    evidence_id = content.pop("evidence_id")
                    checksum = content.pop("evidence_sha256")
                    if _sha(content) != checksum or evidence_id != _sha(
                        [receipt["receipt_id"], receipt["identity_sha256"], checksum]
                    ):
                        _error("EVIDENCE_HASH_MISMATCH")
            self._key = body["cursor_key"]
            self._source_tree_sha256 = body["source_tree_sha256"]
            self._source_epoch = body["source_epoch"]
            if (
                not SHA256.fullmatch(self._source_tree_sha256)
                or type(self._source_epoch) is not int
                or self._source_epoch < 0
            ):
                _error("STATE_INVALID")
            self._receipts = body["receipts"]
            self._metrics = body["metrics"]
        except (TypeError, ValueError, KeyError, UnicodeError, RecursionError):
            _error("STATE_INVALID")

    def to_dict(self):
        self._track_source()
        body = {
            "schema_version": 1,
            "policy_sha256": self._policy,
            "cursor_key": self._key,
            "source_tree_sha256": self._source_tree_sha256,
            "source_epoch": self._source_epoch,
            "receipts": deepcopy(self._receipts),
            "metrics": dict(self._metrics),
        }
        return {**body, "state_sha256": _sha(body)}

    def _track_source(self):
        source = self.toolbox.workspace.expected_manifest.sha256
        if source != self._source_tree_sha256:
            self._source_epoch += 1
            self._source_tree_sha256 = source
            self._cache.clear()
            self._cache_bytes = 0
        return source

    def track_source(self):
        """Invalidate on every prepared tool boundary, before deferred delivery."""
        return self._track_source()

    def _identity(self, query, path, source):
        return _sha(
            {
                "source": source,
                "source_epoch": self._source_epoch,
                "query": query,
                "path": path,
                "readable": sorted(self.toolbox.readable),
                "policy": self._policy,
                "ranking": self._ranking_identity(),
            }
        )

    def _ranking_identity(self):
        return (
            _sha([r["record_sha256"] for r in self._receipts])
            if self.mode == "feedback"
            else "bounded"
        )

    def _cursor(self, binding, **position):
        raw = canonical_json({"v": 1, "binding": binding, **position})
        mac = hmac.new(bytes.fromhex(self._key), raw, hashlib.sha256).hexdigest()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=") + "." + mac

    def _decode_cursor(self, token, binding):
        try:
            if not isinstance(token, str) or len(token) > 4096:
                _error("CURSOR_INVALID")
            encoded, mac = token.split(".")
            raw = base64.b64decode(
                encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True
            )
            expected = hmac.new(bytes.fromhex(self._key), raw, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(mac, expected):
                _error("CURSOR_INVALID")
            value = json.loads(raw)
            if value.get("v") != 1 or value.get("binding") != binding:
                _error("CURSOR_STALE_OR_MISMATCHED")
            return value
        except (ValueError, TypeError, UnicodeError):
            _error("CURSOR_INVALID")

    def _path(self, location):
        if not isinstance(location, str) or len(location) > 4096:
            _error("EVIDENCE_PATH_INVALID")
        if "\\" in location or any(c in location for c in ("\0", "\n", "\r")):
            _error("EVIDENCE_PATH_INVALID")
        if ".." in location.split("/"):
            _error("EVIDENCE_PATH_TRAVERSAL")
        path = location
        if path.startswith("/"):
            root = next((root for root in self.source_roots if path.startswith(root + "/")), None)
            if root is None:
                _error("EVIDENCE_PATH_UNMAPPED")
            path = path[len(root) + 1 :]
        if path.startswith("./"):
            path = path[2:]
        if path not in self.toolbox._scope(path):
            _error("EVIDENCE_PATH_NOT_READABLE")
        return path

    def _fragments(self, data, prefix=""):
        """Walk the public command/test schema, skipping archive refs and metadata."""
        stack = [(data, prefix, {}, 0)]
        visited = 0
        while stack:
            value, pointer, metadata, depth = stack.pop()
            visited += 1
            if visited > 4096 or depth > 8:
                yield None, pointer, {}, False
                return
            if isinstance(value, str):
                yield value, pointer, metadata, False
                continue
            if isinstance(value, list):
                if len(value) > 4096:
                    yield None, pointer, {}, False
                    return
                stack.extend(
                    (item, f"{pointer}/{i}", metadata, depth + 1)
                    for i, item in reversed(list(enumerate(value)))
                )
                continue
            if not isinstance(value, dict):
                continue
            if (
                value.get("visibility") == "hidden"
                or value.get("hidden") is True
                or value.get("evaluation_role") in HIDDEN_ROLES
            ):
                continue
            metadata = {
                **metadata,
                **{
                    key: value[key]
                    for key in (
                        "command_id",
                        "evaluation_id",
                        "image_id",
                        "exit_code",
                        "status",
                        "name",
                    )
                    if isinstance(value.get(key), (str, int, bool))
                    or value.get(key) is None
                    and key in value
                },
            }
            if (
                pointer.rsplit("/", 2)[-2:-1] == ["diagnostics"]
                and "file" in value
                and "line" in value
            ):
                yield value, pointer, metadata, True
                continue
            for key in reversed(
                (
                    *TEXT_FIELDS,
                    "diagnostics",
                    "failed_commands",
                    "tests",
                    "configure",
                    "build",
                    "discovery",
                )
            ):
                if key in value:
                    stack.append((value[key], pointer + "/" + key, metadata, depth + 1))

    def _baseline_fragments(self, data, prefix):
        if (
            set(data)
            != {
                "schema",
                "instance_id",
                "prepared_commit",
                "source_tree_sha256",
                "logs",
                "feedback_sha256",
            }
            or not isinstance(data["logs"], list)
            or len(data["logs"]) != 3
        ):
            _error("FEEDBACK_SCHEMA_INVALID")
        if (
            not isinstance(data["instance_id"], str)
            or not data["instance_id"]
            or not isinstance(data["prepared_commit"], str)
            or re.fullmatch(r"(?:[a-f0-9]{40}|[a-f0-9]{64})", data["prepared_commit"]) is None
        ):
            _error("FEEDBACK_IDENTITY_INVALID")
        payload = {key: value for key, value in data.items() if key != "feedback_sha256"}
        if _sha(payload) != data["feedback_sha256"]:
            _error("FEEDBACK_HASH_MISMATCH")
        fragments = []
        for index, (entry, name) in enumerate(zip(data["logs"], FEEDBACK_LOG_NAMES, strict=True)):
            if (
                not isinstance(entry, dict)
                or set(entry) != {"name", "sha256", "text"}
                or entry["name"] != name
                or not isinstance(entry["text"], str)
                or hashlib.sha256(entry["text"].encode("utf-8")).hexdigest() != entry["sha256"]
            ):
                _error("FEEDBACK_LOG_INVALID")
            fragments.append(
                (
                    entry["text"],
                    f"{prefix}/logs/{index}/text",
                    {
                        "log_name": name,
                        "log_sha256": entry["sha256"],
                        "feedback_sha256": data["feedback_sha256"],
                        "instance_id": data["instance_id"],
                        "prepared_commit": data["prepared_commit"],
                    },
                    False,
                )
            )
        return fragments

    def observe(
        self, name, arguments, visible_value, *, receipt_id, source_tree_sha256, source_epoch=None
    ):
        """Register the JSON actually delivered by the runtime, never an archive."""
        self._track_source()
        if name not in {"baseline", "run_command", "run_shell"}:
            return {"registered": False, "reason": "unsupported_tool"}
        evidence_epoch = self._source_epoch if source_epoch is None else source_epoch
        if type(evidence_epoch) is not int or not 0 <= evidence_epoch <= self._source_epoch:
            _error("EVIDENCE_EPOCH_INVALID")
        self.toolbox.bounded(receipt_id, 256)
        if (
            not receipt_id
            or not isinstance(source_tree_sha256, str)
            or not SHA256.fullmatch(source_tree_sha256)
        ):
            _error("EVIDENCE_IDENTITY_INVALID")
        try:
            if isinstance(visible_value, str):
                if len(visible_value.encode()) > MAX_VISIBLE_BYTES:
                    _error("VISIBLE_BYTES_LIMIT")
                visible_value = json.loads(visible_value)
            raw = canonical_json(visible_value)
            args_raw = canonical_json(arguments)
        except (TypeError, ValueError, UnicodeError, RecursionError):
            _error("VISIBLE_JSON_INVALID")
        if len(raw) > MAX_VISIBLE_BYTES or len(args_raw) > 8192:
            _error("VISIBLE_BYTES_LIMIT")
        if not isinstance(visible_value, dict):
            _error("VISIBLE_JSON_INVALID")
        if "ok" in visible_value and visible_value["ok"] is not True:
            return {"registered": False, "reason": "tool_unsuccessful"}
        data = visible_value.get("data", visible_value)
        if not isinstance(data, dict):
            _error("VISIBLE_JSON_INVALID")
        if any(
            value.get("visibility") == "hidden"
            or value.get("hidden") is True
            or value.get("evaluation_role") in HIDDEN_ROLES
            for value in (visible_value, data)
        ):
            _error("EVIDENCE_NOT_VISIBLE")
        manifest = self.toolbox.workspace.expected_manifest
        if (
            source_tree_sha256 != manifest.sha256
            or data.get("source_tree_sha256", source_tree_sha256) != source_tree_sha256
        ):
            _error("EVIDENCE_SOURCE_MISMATCH")
        identity = _sha(
            {
                "tool": name,
                "arguments": arguments,
                "visible_value": visible_value,
                "source_tree_sha256": source_tree_sha256,
                "source_epoch": evidence_epoch,
            }
        )
        existing = next((r for r in self._receipts if r["receipt_id"] == receipt_id), None)
        if existing is not None:
            if existing["identity_sha256"] != identity:
                _error("RECEIPT_CONFLICT")
            return {
                "registered": True,
                "reason": "already_registered",
                "evidence_count": len(existing["evidence"]),
            }
        record = {
            "receipt_id": receipt_id,
            "tool": name,
            "arguments_sha256": hashlib.sha256(args_raw).hexdigest(),
            "visible_sha256": hashlib.sha256(raw).hexdigest(),
            "identity_sha256": identity,
            "source_tree_sha256": source_tree_sha256,
            "source_epoch": evidence_epoch,
            "evidence": [],
            "rejections": {},
            "failed_tests": [],
        }
        files, seen = {}, set()
        total_lines = 0
        limited = False
        prefix = "/data" if data is not visible_value else ""
        fragments = (
            self._baseline_fragments(data, prefix)
            if name == "baseline" and data.get("schema") == FEEDBACK_SCHEMA
            else self._fragments(data, prefix)
        )
        for fragment, pointer, metadata, structured in fragments:
            if fragment is None:
                limited = True
                break
            lines = [fragment] if structured else fragment.splitlines()
            active_test = metadata.get("name")
            for line_index, line in enumerate(lines, 1):
                total_lines += 1
                if total_lines > MAX_PARSE_LINES or len(record["evidence"]) >= MAX_EVIDENCE:
                    limited = True
                    break
                if len(canonical_json(line)) > MAX_LINE_BYTES:
                    record["rejections"]["line_bytes_limit"] = (
                        record["rejections"].get("line_bytes_limit", 0) + 1
                    )
                    continue
                if structured:
                    location, number = line.get("file"), line.get("line")
                    kind = "compiler"
                else:
                    clean = SGR.sub("", line)
                    if test := RUN_TEST.match(clean):
                        active_test = test[1]
                    if failed := FAIL_TEST.match(clean):
                        if len(record["failed_tests"]) < MAX_EVIDENCE:
                            record["failed_tests"].append(failed[1][:256])
                    match = COMPILER.fullmatch(clean)
                    kind = "compiler"
                    if match is None:
                        match, kind = GTEST.fullmatch(clean), "gtest"
                    if match is None and re.match(r"^\s*#\d+\s", clean):
                        match, kind = STACK.search(clean), "stack"
                    if match is None:
                        continue
                    location, number = match["file"], match["line"]
                    if len(number) > 10:
                        continue
                    number = int(number)
                try:
                    if type(number) is not int or not 0 < number < 2**31:
                        _error("EVIDENCE_LINE_INVALID")
                    path = self._path(location)
                    if path not in files:
                        _, text = self.toolbox._text(path)
                        entry = manifest.by_path[path]
                        if hashlib.sha256(text.encode()).hexdigest() != entry.sha256:
                            raise SourceChanged("SOURCE_CHANGED: localization source hash mismatch")
                        files[path] = (entry.sha256, len(text.splitlines()))
                    file_sha, line_count = files[path]
                    if number > line_count:
                        _error("EVIDENCE_LINE_OUT_OF_RANGE")
                except PolicyError as exc:
                    reason = str(exc).split(":", 1)[0]
                    record["rejections"][reason] = record["rejections"].get(reason, 0) + 1
                    continue
                key = (path, number, kind, _sha(line))
                if key in seen:
                    continue
                seen.add(key)
                item = {
                    "kind": kind,
                    "path": path,
                    "line": number,
                    "file_sha256": file_sha,
                    "fragment_sha256": _sha(line),
                    "fragment_pointer": pointer,
                    "fragment_line": line_index,
                    "metadata": {
                        k: v[:256] if isinstance(v, str) else v for k, v in metadata.items()
                    },
                    "test_name": active_test[:256] if isinstance(active_test, str) else None,
                }
                item["evidence_sha256"] = _sha(item)
                item["evidence_id"] = _sha([receipt_id, identity, item["evidence_sha256"]])
                record["evidence"].append(item)
            if limited:
                break
        record["parse_limited"] = limited
        record["record_sha256"] = _sha(record)
        if self.toolbox.workspace.expected_manifest.sha256 != source_tree_sha256:
            raise SourceChanged("SOURCE_CHANGED: localization source changed during observation")
        self._receipts.append(record)
        while (
            len(self._receipts) > MAX_RECEIPTS
            or len(canonical_json(self._receipts)) > MAX_STATE_BYTES - 8192
        ):
            self._receipts.pop(0)
            self._metrics["receipts_evicted"] += 1
        return {
            "registered": True,
            "reason": "registered",
            "evidence_count": len(record["evidence"]),
            "parse_limited": limited,
            "rejections": dict(record["rejections"]),
        }

    def register_baseline(self, visible_value, *, receipt_id="baseline", source_tree_sha256):
        return self.observe(
            "baseline",
            {},
            visible_value,
            receipt_id=receipt_id,
            source_tree_sha256=source_tree_sha256,
        )

    def _active_evidence(self, source, manifest):
        active, stale = {}, 0
        for receipt in self._receipts:
            for item in receipt["evidence"]:
                entry = manifest.get(item["path"])
                if (
                    receipt["source_tree_sha256"] != source
                    or receipt["source_epoch"] != self._source_epoch
                    or entry is None
                    or entry.sha256 != item["file_sha256"]
                ):
                    stale += 1
                    continue
                if item["path"] not in self.toolbox.readable:
                    continue
                active.setdefault(item["path"], []).append(
                    {
                        **item,
                        "receipt_id": receipt["receipt_id"],
                        "tool": receipt["tool"],
                        "visible_sha256": receipt["visible_sha256"],
                        "source_tree_sha256": source,
                        "source_epoch": self._source_epoch,
                    }
                )
        return active, stale

    @staticmethod
    def _node_metadata(path):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise SourceChanged("SOURCE_CHANGED: Symlink access is forbidden")
        common = (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)
        if stat.S_ISDIR(info.st_mode):
            return ("directory", *common)
        if not stat.S_ISREG(info.st_mode):
            raise SourceChanged("SOURCE_CHANGED: localization source is not a regular file")
        return ("file", *common, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)

    def _guard(self, path, guards, cost):
        if path not in guards:
            cost["metadata_checks"] += 1
            guards[path] = self._node_metadata(path)

    def _file_guards(self, name, guards, cost):
        # The immutable manifest is fully audited by the runtime before tools.
        # Cache hits verify paths/inodes/timestamps without rereading source.
        path = self.toolbox.workspace.path
        self._guard(path, guards, cost)
        for part in relative_file(name).split("/"):
            if guards[path][0] != "directory":
                raise SourceChanged("SOURCE_CHANGED: localization source parent changed")
            path /= part
            self._guard(path, guards, cost)
        if guards[path][0] != "file":
            raise SourceChanged("SOURCE_CHANGED: localization source file changed")

    def _validate_cache(self, guards, cost):
        try:
            for path, recorded in guards.items():
                cost["metadata_checks"] += 1
                if self._node_metadata(path) != recorded:
                    raise SourceChanged("SOURCE_CHANGED: localization cache metadata changed")
        except (OSError, SourceChanged) as exc:
            self._cache.clear()
            self._cache_bytes = 0
            self._source_epoch += 1
            if isinstance(exc, SourceChanged):
                raise
            raise SourceChanged("SOURCE_CHANGED: localization cache validation failed") from exc

    def _file(self, name, query, source, entries, index, cost):
        entry = entries[name]
        try:
            _, text = self.toolbox._text(name)
        except PolicyError as exc:
            if str(exc).startswith("NOT_UTF8"):
                cost["bytes"] += entry.size_bytes
                return None
            raise
        cost["bytes"] += entry.size_bytes
        if hashlib.sha256(text.encode()).hexdigest() != entry.sha256:
            raise SourceChanged("SOURCE_CHANGED: localization source hash mismatch")
        hits = array("I", (i for i, line in enumerate(text.splitlines(), 1) if query in line))
        return {
            "candidate_id": _sha([source, query, name, entry.sha256]),
            "path": name,
            "file_sha256": entry.sha256,
            "match_count": len(hits),
            "_hits": hits,
            "_file_index": index,
        }

    def _chunk(self, query, path, scope, source, entries, start, cost):
        key = (_sha([source, self._source_epoch, query, path, scope, self._policy]), start)
        if key in self._cache:
            chunk = self._cache[key]
            self._validate_cache(chunk["guards"], cost)
            self._cache.move_to_end(key)
            self._metrics["cache_hits"] += 1
            return chunk, True
        guards, rows, skipped, next_start, scheduled_bytes = {}, [], 0, start, 0
        workspace = self.toolbox.workspace
        # Real Worktree ownership uses these control files. Metadata checks also
        # protect them on a cache hit while keeping validation source reads zero.
        if hasattr(workspace, "manager") and hasattr(workspace, "common"):
            for control in (
                workspace.path,
                workspace.path / ".git",
                workspace.manager,
                workspace.manager / "gitdir",
                workspace.common,
            ):
                self._guard(control, guards, cost)
        try:
            while next_start < len(scope) and next_start - start < self.limits.scan_files:
                name = scope[next_start]
                size = entries[name].size_bytes
                if size > self.limits.scan_bytes:
                    _error("SCAN_FILE_EXCEEDS_BUDGET")
                if next_start > start and scheduled_bytes + size > self.limits.scan_bytes:
                    break
                scheduled_bytes += size
                self._file_guards(name, guards, cost)
                row = self._file(name, query, source, entries, next_start, cost)
                next_start += 1
                cost["files"] += 1
                if row is None:
                    skipped += 1
                elif row["match_count"]:
                    rows.append(row)
            self._validate_cache(guards, cost)
        except OSError as exc:
            raise SourceChanged("SOURCE_CHANGED: localization source metadata unavailable") from exc
        size = (
            sum(row["_hits"].__sizeof__() + len(row["path"].encode()) * 4 + 1024 for row in rows)
            + sum(len(str(p).encode()) * 4 + 512 for p in guards)
            + 4096
        )
        if size > MAX_CACHE_BYTES:
            _error("CACHE_CHUNK_LIMIT")
        chunk = {
            "rows": rows,
            "by_index": {r["_file_index"]: r for r in rows},
            "next_start": next_start,
            "start": start,
            "guards": guards,
            "complete": next_start == len(scope),
            "skipped": skipped,
            "pool_sha256": _sha([r["candidate_id"] for r in rows]),
            "size_bytes": size,
            "views": None,
        }
        while self._cache and (
            len(self._cache) >= MAX_CACHE_CHUNKS or self._cache_bytes + size > MAX_CACHE_BYTES
        ):
            _, evicted = self._cache.popitem(last=False)
            self._cache_bytes -= evicted["size_bytes"]
            self._metrics["cache_evictions"] += 1
        self._cache[key] = chunk
        self._cache_bytes += size
        self._metrics["cache_builds"] += 1
        return chunk, False

    @staticmethod
    def _contains(hits, line):
        index = bisect_left(hits, line)
        return index < len(hits) and hits[index] == line

    @staticmethod
    def _compact_evidence(evidence):
        result = {key: evidence[key] for key in ("line", "kind", "evidence_id")}
        identity = evidence["receipt_id"]
        if len(canonical_json(identity)) <= 96:
            result["receipt_id"] = identity
        else:
            result["receipt_sha256"] = hashlib.sha256(identity.encode()).hexdigest()
        return result

    def _views(self, chunk, source, entries):
        identity = self._ranking_identity()
        if chunk["views"] is not None and chunk["views"]["identity"] == identity:
            return chunk["views"]
        evidence, stale = self._active_evidence(source, entries)
        rows = list(chunk["rows"])
        ranks = {}
        applicable = False
        for row in rows:
            relevant = sorted(
                evidence.get(row["path"], ()),
                key=lambda e: (
                    not self._contains(row["_hits"], e["line"]),
                    e["line"],
                    e["evidence_id"],
                ),
            )
            direct = bool(relevant) and self._contains(row["_hits"], relevant[0]["line"])
            applicable |= bool(relevant)
            ranks[row["candidate_id"]] = {
                "reason": "direct_location"
                if direct
                else "same_file"
                if relevant
                else "text_order",
                "evidence_count": len(relevant),
                "evidence": [self._compact_evidence(e) for e in relevant[:2]],
            }
        if self.mode == "feedback":
            priority = {"direct_location": 0, "same_file": 1, "text_order": 2}
            rows.sort(key=lambda r: (priority[ranks[r["candidate_id"]]["reason"]], r["path"]))
        fallback = (
            "bounded_mode"
            if self.mode == "bounded"
            else None
            if applicable
            else "evidence_outside_candidate_pool"
            if evidence
            else "stale_evidence"
            if stale
            else "feedback_parse_limited"
            if any(r["parse_limited"] for r in self._receipts)
            else "no_location_evidence"
            if self._receipts
            else "no_registered_feedback"
        )
        views = {
            "identity": identity,
            "rows": rows,
            "ranks": ranks,
            "stale": stale,
            "fallback": fallback,
        }
        chunk["views"] = views
        return views

    def _candidate(self, row, binding, start, offset=0):
        lines = list(row["_hits"][offset : offset + self.limits.hit_lines])
        next_offset = offset + len(lines)
        return {
            **{key: row[key] for key in ("candidate_id", "path", "file_sha256", "match_count")},
            "hit_lines": lines,
            "hit_lines_next_cursor": self._cursor(
                binding,
                kind="hits",
                start=start,
                file_index=row["_file_index"],
                hit_offset=next_offset,
            )
            if next_offset < row["match_count"]
            else None,
        }

    def _page_capacity(self, chunk, query, path, binding):
        if "page_capacity" in chunk:
            return chunk["page_capacity"]
        # Both arms reserve the same maximum header and compact ranking space.
        # A pool-wide maximum row size makes page cardinality order-independent.
        header_bytes = len(canonical_json({"query": query, "scope": path})) + 4096
        largest = 1
        for row in chunk["rows"]:
            item = self._candidate(row, binding, chunk["start"])
            item["hit_lines"] = [2**32 - 1] * self.limits.hit_lines
            item["hit_lines_next_cursor"] = self._cursor(
                binding,
                kind="hits",
                start=2**32 - 1,
                file_index=2**32 - 1,
                hit_offset=2**32 - 1,
            )
            largest = max(largest, len(canonical_json(item)) + RANKING_RESERVE_BYTES + 1)
        capacity = min(self.limits.page_files, (self.limits.output_bytes - header_bytes) // largest)
        if capacity < 1:
            _error("OUTPUT_BUDGET_TOO_SMALL")
        chunk["page_capacity"] = capacity
        return capacity

    def search(self, query, path=".", cursor=None):
        self.toolbox.bounded(query, 1024)
        if not query:
            _error("EMPTY_QUERY")
        scope = self.toolbox._scope(path)
        manifest = self.toolbox.workspace.expected_manifest
        source, entries = self._track_source(), manifest.by_path
        binding = self._identity(query, path, source)
        position = (
            self._decode_cursor(cursor, binding)
            if cursor is not None
            else {
                "kind": "files",
                "start": 0,
                "offset": 0,
                "before": 0,
                "skipped": 0,
            }
        )
        cost = {"files": 0, "bytes": 0, "metadata_checks": 0}
        started = time.perf_counter()
        chunk, cache_hit = self._chunk(query, path, scope, source, entries, position["start"], cost)
        scan_seconds = time.perf_counter() - started
        ranking_started = time.perf_counter()
        views = self._views(chunk, source, entries)
        capacity = self._page_capacity(chunk, query, path, binding)
        ranking_seconds = time.perf_counter() - ranking_started
        is_hits = position["kind"] == "hits"
        if is_hits:
            row = chunk["by_index"].get(position["file_index"])
            if row is None or not 0 <= position["hit_offset"] < row["match_count"]:
                _error("CURSOR_POSITION_INVALID")
            selected = [row]
            offset, before = 0, 0
        else:
            offset, before = position["offset"], position["before"]
            selected = views["rows"][offset : offset + capacity]
        result = {
            "schema_version": 1,
            "mode": self.mode,
            "query": query,
            "scope": path,
            "source_tree_sha256": source,
            "source_epoch": self._source_epoch,
            "candidate_pool_sha256": chunk["pool_sha256"],
            "page_kind": position["kind"],
            "common_page_files": capacity,
            "candidates": [],
            "matched_files": 1 if is_hits else before + len(chunk["rows"]),
            "scan_complete": True if is_hits else chunk["complete"],
            "count_is_lower_bound": False
            if is_hits
            else not chunk["complete"] or bool(chunk["skipped"] + position.get("skipped", 0)),
            "truncated": False,
            "next_cursor": None,
            "continuation": None,
            "coverage_status": "not_collected",
            "fallback_reason": views["fallback"],
            "stale_evidence_count": views["stale"],
            "scan": {
                "files": cost["files"],
                "bytes": cost["bytes"],
                "skipped_files": chunk["skipped"],
                "seconds": scan_seconds,
                "source_read_bytes": cost["bytes"],
                "validation_read_bytes": 0,
                "metadata_checks": cost["metadata_checks"],
            },
            "cache": {
                "hit": cache_hit,
                "builds": int(not cache_hit),
                "retained_bytes": self._cache_bytes,
            },
            "ranking_seconds": ranking_seconds,
        }
        for row in selected:
            item = self._candidate(
                row, binding, chunk["start"], position["hit_offset"] if is_hits else 0
            )
            if self.mode == "feedback":
                item["ranking"] = deepcopy(views["ranks"][row["candidate_id"]])
            result["candidates"].append(item)
        after = offset + len(selected)
        if is_hits:
            result["next_cursor"] = result["candidates"][0]["hit_lines_next_cursor"]
            result["continuation"] = "hit_lines" if result["next_cursor"] else None
        elif after < len(views["rows"]):
            result["next_cursor"] = self._cursor(
                binding,
                kind="files",
                start=chunk["start"],
                offset=after,
                before=before,
                skipped=position.get("skipped", 0),
            )
            result["continuation"] = "files"
        elif not chunk["complete"]:
            result["next_cursor"] = self._cursor(
                binding,
                kind="files",
                start=chunk["next_start"],
                offset=0,
                before=before + len(chunk["rows"]),
                skipped=chunk["skipped"] + position.get("skipped", 0),
            )
            result["continuation"] = "scan"
        result["truncated"] = result["next_cursor"] is not None or any(
            c["hit_lines_next_cursor"] for c in result["candidates"]
        )
        size = len(canonical_json(result))
        if size > self.limits.output_bytes:
            _error("OUTPUT_RESERVE_EXCEEDED")
        if self.toolbox.workspace.expected_manifest.sha256 != source:
            raise SourceChanged("SOURCE_CHANGED: localization source changed during scan")
        self._metrics["searches"] += 1
        self._metrics["scan_files"] += cost["files"]
        self._metrics["scan_bytes"] += cost["bytes"]
        self._metrics["source_read_bytes"] += cost["bytes"]
        self._metrics["metadata_checks"] += cost["metadata_checks"]
        self._metrics["scan_seconds"] += scan_seconds
        self._metrics["ranking_seconds"] += ranking_seconds
        self._metrics["output_bytes"] += size
        return result
