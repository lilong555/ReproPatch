"""授权 C++ 源码的语法结构索引与可追溯修复状态。"""

import hashlib
import json
import posixpath
import time
from importlib.metadata import version
from pathlib import PurePosixPath

from .errors import PolicyError
from .task import canonical_json

SOURCE_SUFFIXES = frozenset(
    {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".ipp", ".tpp"}
)
STATE_VERSION = "cpp-evidence-state-v1"
MAX_QUERY_FILES = 64
MAX_FILE_NODES = 20_000
MAX_RESULTS = 60
STATE_PROMPT_BYTES = 12_000
QUERY_KINDS = frozenset({"definitions", "references", "includes", "state", "evidence"})
COUNTERS = {
    "queries_total": 0,
    "parse_count": 0,
    "cache_hits": 0,
    "indexed_bytes_total": 0,
    "index_seconds_total": 0.0,
    "parse_seconds_total": 0.0,
}


def cumulative_metrics(state):
    """累计计量独立于近期观察列表，跨压缩与恢复保持连续。"""
    return {
        **{name: state.get(name, default) for name, default in COUNTERS.items()},
        "query_kinds": dict(state.get("query_kinds", {})),
    }


def _clip(value, maximum):
    return str(value).encode()[:maximum].decode(errors="ignore")


def state_view(state, *, maximum=STATE_PROMPT_BYTES):
    """面向模型的有界状态视图；完整工具结果由证据引用保留。"""
    value = {
        "version": STATE_VERSION,
        "parser": state.get("parser"),
        "indexed_files": len(state.get("files", {})),
        "metrics": cumulative_metrics(state),
        "changes": list(state.get("changes", {}).values())[-16:],
        "checks": state.get("checks", [])[-4:],
        "recent_observations": state.get("observations", [])[-8:],
        "query_tool": "query_code",
        "details": "state查询修复状态；evidence按已登记tool_id或baseline读取原始可见记录。",
    }
    while len(canonical_json(value)) > maximum:
        for key in ("recent_observations", "checks", "changes"):
            if value[key]:
                value[key].pop(0)
                break
        else:
            break
    return value


class SemanticState:
    """结构查询只经过 Toolbox 的授权读取；序列化状态独立于 AST 缓存。"""

    def __init__(self, toolbox, state=None, *, read_evidence=None):
        self.toolbox = toolbox
        self.read_evidence = read_evidence
        self.state = (
            json.loads(json.dumps(state))
            if state is not None
            else {
                "version": STATE_VERSION,
                "files": {},
                "changes": {},
                "checks": [],
                "observations": [],
                "evidence": {},
                "sequence": 0,
            }
        )
        if self.state.get("version") != STATE_VERSION:
            raise PolicyError("SEMANTIC_STATE_VERSION: 修复状态版本无效")
        for name, default in COUNTERS.items():
            self.state.setdefault(name, default)
        self.state.setdefault("query_kinds", {})
        self.cache = {}
        self.parser = None

    def _parser(self):
        if self.parser is None:
            try:
                import tree_sitter_cpp
                from tree_sitter import Language, Parser
            except ImportError as exc:
                raise PolicyError("STRUCTURE_PARSER_UNAVAILABLE: 缺少 C++ 结构解析器") from exc
            self.parser = Parser(Language(tree_sitter_cpp.language()))
            self.state["parser"] = {
                "name": "tree-sitter-cpp",
                "version": version("tree-sitter-cpp"),
                "runtime_version": version("tree-sitter"),
                "relation_semantics": "syntactic",
            }
        return self.parser

    @staticmethod
    def _text(node, raw, maximum=600):
        return _clip(raw[node.start_byte : node.end_byte].decode(errors="replace"), maximum)

    @staticmethod
    def _walk(node):
        stack = [node]
        while stack:
            item = stack.pop()
            yield item
            stack.extend(reversed(item.named_children))

    def _name(self, node, raw):
        if node is None:
            return ""
        while node.type in {
            "function_declarator",
            "pointer_declarator",
            "reference_declarator",
            "parenthesized_declarator",
            "array_declarator",
        }:
            child = node.child_by_field_name("declarator")
            if child is None:
                child = next(iter(node.named_children), None)
            if child is None:
                break
            node = child
        return self._text(node, raw, 240)

    def _index(self, path):
        started = time.perf_counter()
        try:
            return self._index_contents(path)
        finally:
            self.state["index_seconds_total"] += time.perf_counter() - started

    def _index_contents(self, path):
        _, text = self.toolbox._text(path)
        raw = text.encode()
        digest = hashlib.sha256(raw).hexdigest()
        cached = self.cache.get(path)
        if cached is not None and cached["sha256"] == digest:
            self.state["cache_hits"] += 1
            return cached
        parser = self._parser()
        started = time.perf_counter()
        tree = parser.parse(raw)
        self.state["parse_seconds_total"] += time.perf_counter() - started
        self.state["parse_count"] += 1
        self.state["indexed_bytes_total"] += len(raw)
        records = []
        total = 0
        truncated = False
        for node in self._walk(tree.root_node):
            kind, symbol, scope = None, "", []
            if node.type in {"function_definition", "declaration", "field_declaration"}:
                declarator = node.child_by_field_name("declarator")
                function = (
                    next(
                        (n for n in self._walk(declarator) if n.type == "function_declarator"),
                        None,
                    )
                    if declarator is not None
                    else None
                )
                if function is not None:
                    kind = (
                        "function_definition"
                        if node.type == "function_definition"
                        else "function_declaration"
                    )
                    symbol = self._name(function, raw)
                elif declarator is not None:
                    kind = "variable_declaration"
                    symbol = self._name(
                        declarator.child_by_field_name("declarator") or declarator, raw
                    )
            elif node.type in {
                "class_specifier",
                "struct_specifier",
                "enum_specifier",
                "namespace_definition",
                "alias_declaration",
                "preproc_def",
                "preproc_function_def",
            }:
                name = node.child_by_field_name("name")
                if name is not None:
                    kind, symbol = node.type, self._text(name, raw, 240)
            elif node.type == "call_expression":
                function = node.child_by_field_name("function")
                if function is not None:
                    kind, symbol = "call", self._text(function, raw, 240)
            elif node.type in {"identifier", "type_identifier", "field_identifier"}:
                kind, symbol = "reference", self._text(node, raw, 240)
            elif node.type == "preproc_include":
                target = node.child_by_field_name("path")
                if target is not None:
                    kind, symbol = "include", self._text(target, raw, 512).strip('<>"')
            if kind is None or not symbol:
                continue
            total += 1
            if len(records) >= MAX_FILE_NODES:
                truncated = True
                continue
            parent = node.parent
            owner_function = None
            while parent is not None:
                if parent.type == "function_definition" and owner_function is None:
                    owner_function = self._name(parent.child_by_field_name("declarator"), raw)
                if parent.type in {"namespace_definition", "class_specifier", "struct_specifier"}:
                    name = parent.child_by_field_name("name")
                    if name is not None:
                        scope.append(self._text(name, raw, 240))
                parent = parent.parent
            scope.reverse()
            record = {
                "path": path,
                "line": node.start_point.row + 1,
                "end_line": node.end_point.row + 1,
                "kind": kind,
                "symbol": symbol,
                "scope": "::".join(scope),
                "qualified_symbol": "::".join([*scope, symbol]),
                "text": self._text(node, raw),
                "node_id": f"{path}:{node.start_byte}:{kind}",
                "source_sha256": digest,
            }
            if kind in {"call", "reference", "include"}:
                record["edge"] = {
                    "relation": {
                        "call": "calls_syntactic",
                        "reference": "references_syntactic",
                        "include": "includes",
                    }[kind],
                    "source": "::".join([*scope, owner_function])
                    if owner_function
                    else "::".join(scope) or path,
                    "target": symbol,
                }
            if kind == "include":
                candidates = [
                    posixpath.normpath(posixpath.join(posixpath.dirname(path), symbol)),
                    symbol,
                ]
                record["target_path"] = next(
                    (p for p in candidates if p in self.toolbox.readable), None
                )
            records.append(record)
        indexed = {
            "sha256": digest,
            "source_bytes": len(raw),
            "records": records,
            "parse_has_error": tree.root_node.has_error,
            "index_truncated": truncated,
            "record_count": total,
        }
        self.cache[path] = indexed
        self.state["files"][path] = {
            key: value for key, value in indexed.items() if key != "records"
        }
        return indexed

    def query(self, kind, query="", path=".", offset=0):
        self.state["queries_total"] += 1
        counter = kind if isinstance(kind, str) and kind in QUERY_KINDS else "invalid"
        counts = self.state["query_kinds"]
        counts[counter] = counts.get(counter, 0) + 1
        self.toolbox.bounded(query, 1024)
        self.toolbox.bounded(path, 4096)
        if type(offset) is not int or offset < 0:
            raise PolicyError("INVALID_ARGUMENT: offset 必须为非负文件偏移")
        if kind not in QUERY_KINDS:
            raise PolicyError("INVALID_ARGUMENT: 未知结构查询类型")
        if kind == "evidence":
            return self._query_evidence(query, offset)
        scope = self.toolbox._scope(path)
        if kind == "state":
            return self._query_state(query, frozenset(scope), path)
        files = [p for p in scope if PurePosixPath(p).suffix.lower() in SOURCE_SUFFIXES]
        selected = files[offset : offset + MAX_QUERY_FILES]
        matches, errors = [], []
        more_matches = False
        for name in selected:
            try:
                indexed = self._index(name)
            except PolicyError as exc:
                errors.append({"path": name, "reason": _clip(exc, 300)})
                continue
            if indexed["parse_has_error"] or indexed["index_truncated"]:
                errors.append(
                    {
                        "path": name,
                        "parse_has_error": indexed["parse_has_error"],
                        "index_truncated": indexed["index_truncated"],
                    }
                )
            for record in indexed["records"]:
                selected_kind = (
                    record["kind"] not in {"call", "reference", "include"}
                    if kind == "definitions"
                    else record["kind"] in {"call", "reference"}
                    if kind == "references"
                    else record["kind"] == "include"
                )
                if selected_kind and (
                    not query or query in record["qualified_symbol"] or query in record["text"]
                ):
                    if len(matches) < MAX_RESULTS:
                        matches.append(record)
                    else:
                        more_matches = True
        next_offset = offset + len(selected)
        return {
            "kind": kind,
            "query": query,
            "relation_semantics": "syntactic",
            "matches": matches,
            "matches_truncated": more_matches,
            "indexed_files": selected,
            "total_scope_files": len(files),
            "next_offset": next_offset if next_offset < len(files) else None,
            "parse_notes": errors,
            "parser": self.state.get("parser"),
        }

    def _query_state(self, query, scope, path):
        groups = {
            "changes": list(self.state["changes"].values()),
            "checks": self.state["checks"],
            "observations": self.state["observations"],
        }
        result = {
            "version": STATE_VERSION,
            "sequence": self.state["sequence"],
            "metrics": cumulative_metrics(self.state),
            "groups": {},
        }
        for name, records in groups.items():
            rows = [
                item
                for item in records
                if (path == "." or any(p in scope for p in item.get("paths", [])))
                and (not query or query.lower() in canonical_json(item).decode().lower())
            ]
            result["groups"][name] = rows[-MAX_RESULTS:]
        while len(canonical_json(result)) > 48_000:
            longest = max(result["groups"], key=lambda k: len(result["groups"][k]))
            if not result["groups"][longest]:
                break
            result["groups"][longest].pop(0)
        return result

    def register_evidence(self, identity, reference):
        """只接收运行时生成的引用；查询端通过登记身份读取完整性已校验的原文。"""
        self.state.setdefault("evidence", {})[identity] = dict(reference)

    def _query_evidence(self, identity, offset):
        reference = self.state.get("evidence", {}).get(identity)
        if reference is None:
            reference = next(
                (
                    ref
                    for ref in self.state.get("evidence", {}).values()
                    if ref.get("path") == identity
                ),
                None,
            )
        if reference is None or self.read_evidence is None:
            raise PolicyError("EVIDENCE_NOT_VISIBLE: 仅可读取本次修复已登记的可见证据")
        raw = self.read_evidence(reference)
        part = raw[offset : offset + 16_000]
        return {
            "identity": identity,
            "reference": reference,
            "offset": offset,
            "offset_unit": "bytes",
            "text": part.decode(errors="replace"),
            "next_offset": offset + len(part) if offset + len(part) < len(raw) else None,
        }

    def observe(self, name, arguments, value, reference, *, tool_id):
        """只登记已完成工具的可见输出与身份，编译和测试状态直接来自工具结果。"""
        self.state["sequence"] += 1
        data = value.get("data", {}) if isinstance(value, dict) else {}
        data = data if isinstance(data, dict) else {}
        paths = {
            candidate
            for candidate in [arguments.get("path"), data.get("path")]
            if isinstance(candidate, str) and candidate in self.toolbox.readable
        }
        paths.update(
            item["path"]
            for item in data.get("matches", [])[:MAX_RESULTS]
            if isinstance(item, dict) and item.get("path") in self.toolbox.readable
        )
        event = {
            "sequence": self.state["sequence"],
            "tool_id": tool_id,
            "tool": name,
            "ok": bool(value.get("ok")),
            "paths": sorted(paths),
            "evidence": reference,
        }
        self.register_evidence(tool_id, reference)
        for key in ("query", "name", "start_line", "max_lines"):
            if key in arguments:
                event[key] = _clip(arguments[key], 512)
        self.state["observations"].append(event)
        self.state["observations"] = self.state["observations"][-128:]
        if name == "edit_file" and value.get("ok") and data.get("path") in paths:
            changed = data["path"]
            self.cache.pop(changed, None)
            self.state["files"].pop(changed, None)
            previous = self.state["changes"].get(changed, {})
            self.state["changes"][changed] = {
                **event,
                "path": changed,
                "before_sha256": previous.get("before_sha256", data.get("before_sha256")),
                "after_sha256": data.get("after_sha256"),
            }
        if name in {"run_command", "run_shell"}:
            check = {
                **event,
                "evaluation_id": data.get("evaluation_id"),
                "issue_code": data.get("issue_code"),
                "diagnostic": _clip(data.get("diagnostic", ""), 1200),
                "failed_tests": [
                    {"name": item.get("name"), "observed_status": item.get("observed_status")}
                    for item in data.get("tests", [])
                    if item.get("observed_status") != "passed"
                ][:30],
            }
            self.state["checks"].append(check)
            self.state["checks"] = self.state["checks"][-32:]
        return event

    def to_dict(self):
        return self.state
