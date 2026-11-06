"""Optional, receipt-backed context projections; tool execution stays in the runtime."""

import hashlib
import re
from copy import deepcopy

from .task import canonical_json

STRATEGIES = ("diagnostic_extraction", "deduplicate_results", "state_aware_compaction")
MAX_DIAGNOSTICS = 64
MAX_PARSE_BYTES = 2 * 1024 * 1024
COMPILER = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+)(?::(?P<column>\d+))?:\s*"
    r"(?P<severity>fatal error|error|warning|note):\s*(?P<message>.+)$"
)
MSVC = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+)(?:,(?P<column>\d+))?\):\s*"
    r"(?P<severity>fatal error|error|warning|note)\s*"
    r"(?P<message>(?:[A-Z]+\d+:)?\s*.+)$"
)
FAILED_TEST = re.compile(
    r"^(?:\s*\[\s*FAILED\s*\]\s+(?P<gtest>\S+\.\S+)(?:\s+\(.*\))?"
    r"|\s*\d+\s*-\s*(?P<ctest>.+?)\s+\((?:Failed|SEGFAULT|Timeout)\))\s*$"
)
COMMAND_VOLATILE = {
    "command_id",
    "duration_seconds",
    "duration_ms",
    "started_at",
    "finished_at",
    "container_id",
}
TEXT_FIELDS = ("stdout", "stderr", "output", "diagnostic")


def initialize(state):
    state.setdefault("metrics", {})
    for name in STRATEGIES:
        state["metrics"].setdefault(
            name,
            {
                "attempts": 0,
                "triggers": 0,
                "input_bytes": 0,
                "output_bytes": 0,
                "saved_bytes": 0,
                "added_bytes": 0,
            },
        )
    return state


def record_optimization(state, strategy, before, after, **details):
    metric = initialize(state)["metrics"][strategy]
    metric["triggers"] += 1
    metric["input_bytes"] += before
    metric["output_bytes"] += after
    metric["saved_bytes"] += max(0, before - after)
    metric["added_bytes"] += max(0, after - before)
    event = {
        "strategy": strategy,
        "input_bytes": before,
        "output_bytes": after,
        "saved_bytes": max(0, before - after),
        **details,
    }
    state.setdefault("events", []).append(event)
    state["events"] = state["events"][-128:]
    return event


def _parse_text(text):
    if not isinstance(text, str) or len(text.encode()) > MAX_PARSE_BYTES:
        return None
    diagnostics, failures, remainder = {}, {}, []
    for line in text.splitlines(keepends=True):
        clean = line.rstrip("\r\n")
        match = COMPILER.fullmatch(clean) or MSVC.fullmatch(clean)
        if match:
            item = match.groupdict()
            if any(len(str(value).encode()) > 4096 for value in item.values()):
                return None
            item["line"] = int(item["line"])
            item["column"] = int(item["column"]) if item["column"] else None
            if not 0 < item["line"] < 2**31 or (
                item["column"] is not None and not 0 <= item["column"] < 2**31
            ):
                return None
            key = canonical_json(item)
            if key not in diagnostics:
                diagnostics[key] = {**item, "occurrences": 0}
            diagnostics[key]["occurrences"] += 1
        elif match := FAILED_TEST.fullmatch(clean):
            name = match["gtest"] or match["ctest"]
            if len(name.encode()) > 4096:
                return None
            failures[name] = failures.get(name, 0) + 1
        else:
            # Preserve every unparsed line, including linker errors and source excerpts.
            remainder.append(line)
        if len(diagnostics) + len(failures) > MAX_DIAGNOSTICS:
            return None
    if not diagnostics and not failures:
        return None
    return {
        "diagnostics": list(diagnostics.values()),
        "failed_tests": [{"name": k, "occurrences": v} for k, v in failures.items()],
        "unparsed_output": "".join(remainder),
    }


def _commands(data):
    commands = data.get("failed_commands", [])
    return [data] + [
        item for item in (commands if isinstance(commands, list) else []) if isinstance(item, dict)
    ]


def _complete(data):
    commands = data.get("failed_commands", [])
    if not isinstance(commands, list) or any(not isinstance(item, dict) for item in commands):
        return False
    return all(
        not item.get("truncated")
        and not item.get("output_truncated")
        and item.get("status", "exited") == "exited"
        for item in _commands(data)
    )


def diagnostic_projection(name, value, reference):
    data = value.get("data")
    if name not in {"run_command", "run_shell"} or value.get("ok") is not True:
        return None
    if not isinstance(data, dict) or not _complete(data):
        return None
    if name == "run_shell" and type(data.get("exit_code")) is not int:
        return None
    if name == "run_command" and data.get("view_version") != 2:
        return None
    candidate = deepcopy(value)
    recognized = False
    for command in _commands(candidate["data"]):
        for key in TEXT_FIELDS:
            if key not in command:
                continue
            parsed = _parse_text(command[key])
            if parsed is not None:
                command[key] = parsed
                recognized = True
    if not recognized:
        return None
    candidate["context_projection"] = {
        "kind": "structured_diagnostics",
        "raw_result_ref": reference,
    }
    return candidate


def _stable_check(data):
    """Ignore orchestration identities only; returned metadata stays execution-specific."""
    result = deepcopy(data)
    for key in ("evaluation_id", "evidence", "source_manifest"):
        result.pop(key, None)
    if isinstance(result.get("cleanup"), dict):
        result["cleanup"].pop("container_id", None)
    commands = _commands(result)[1:] + [
        result[key]
        for key in ("configure", "build", "discovery")
        if isinstance(result.get(key), dict)
    ]
    for command in commands:
        for key in COMMAND_VOLATILE:
            command.pop(key, None)
        argv = command.get("argv")
        if isinstance(argv, (list, tuple)) and argv and argv[0] == "ctest":
            argv = command["argv"] = list(argv)
            for index in range(1, len(argv)):
                if argv[index - 1] == "--output-junit" and re.fullmatch(
                    r"/build/\.repropatch-results/[a-f0-9]{32}-[a-f0-9]{32}\.xml",
                    str(argv[index]),
                ):
                    argv[index] = "<evaluation-junit>"
        for key in ("stdout_log", "stderr_log"):
            ref = command.get(key)
            if isinstance(ref, dict):
                command[key] = {k: v for k, v in ref.items() if k != "path"}
    return result


def _dedup_eligible(name, arguments, value, source):
    data = value.get("data")
    return (
        name == "run_command"
        and arguments.get("name") in {"reproduce", "verify"}
        and value.get("ok") is True
        and isinstance(data, dict)
        and data.get("view_version") == 2
        and type(data.get("passed")) is bool
        and data.get("evaluation_role") == "agent_check"
        and isinstance(source, str)
        and bool(source)
        and data.get("source_tree_sha256") == source
        and _complete(data)
        and isinstance(data.get("tests"), list)
        and isinstance(data.get("failed_commands"), list)
        and all(
            isinstance(t, dict)
            and t.get("observed_status")
            in {
                "passed",
                "failed",
                "crashed",
                "timed_out",
                "skipped",
                "not_run",
            }
            for t in data["tests"]
        )
    )


class ContextOptimizer:
    def __init__(self, context):
        self.policy = context.policy
        self.state = initialize(context.optimization_state)

    def source_changed(self, source):
        if not self.policy.deduplicate_results:
            return
        if self.state.get("dedup_source") != source:
            if "dedup_source" in self.state:
                self.state["source_invalidations"] = self.state.get("source_invalidations", 0) + 1
            self.state["dedup_source"] = source
            self.state["dedup_index"] = {}

    def project(self, name, arguments, value, reference, *, tool_id, source, native):
        self.source_changed(source)
        text, events = native, []
        data = value.get("data")
        index, key, first = self.state.setdefault("dedup_index", {}), None, None
        if self.policy.deduplicate_results:
            self.state["metrics"]["deduplicate_results"]["attempts"] += 1
            if _dedup_eligible(name, arguments, value, source):
                content_hash = hashlib.sha256(canonical_json(_stable_check(data))).hexdigest()
                key = hashlib.sha256(
                    canonical_json(
                        {
                            "tool": name,
                            "arguments": arguments,
                            "source": source,
                            "phase": arguments["name"],
                            "content_sha256": content_hash,
                        }
                    )
                ).hexdigest()
                first = index.get(key)
                if first is None:
                    if len(index) >= 256:
                        index.pop(next(iter(index)))
                    index[key] = {
                        "tool_id": tool_id,
                        "reference": reference,
                        "content_sha256": content_hash,
                    }
        candidates = []
        if self.policy.diagnostic_extraction:
            self.state["metrics"]["diagnostic_extraction"]["attempts"] += 1
            candidates.append(
                ("diagnostic_extraction", diagnostic_projection(name, value, reference))
            )
        if first is not None:
            candidate = deepcopy(value)
            for command in _commands(candidate["data"]):
                for field in TEXT_FIELDS:
                    command.pop(field, None)
            for test in candidate["data"]["tests"]:
                test.pop("diagnostic", None)
            candidate["context_projection"] = {
                "kind": "exact_duplicate",
                "duplicate_of": first,
                "raw_result_ref": reference,
                "source_tree_sha256": source,
                "phase": arguments["name"],
                "tool_executed": True,
            }
            candidates.insert(0, ("deduplicate_results", candidate))
        for strategy, candidate in candidates:
            if candidate is None:
                continue
            projected = canonical_json(candidate).decode()
            before, after = len(text.encode()), len(projected.encode())
            if after > self.policy.tool_output_max_bytes or before - after < max(128, before // 10):
                continue
            events.append(
                record_optimization(
                    self.state,
                    strategy,
                    before,
                    after,
                    tool_id=tool_id,
                    source_tree_sha256=source,
                    raw_result_ref=reference,
                    measurement="returned_tool_context",
                )
            )
            text = projected
            break
        return text, events


def state_checkpoint(state, *, maximum):
    source, epoch = state.get("source_tree_sha256"), state.get("source_epoch")
    if not source or epoch is None:
        return None
    current, historical = {}, {}
    for check in state.get("checks", []):
        phase = check.get("phase")
        if phase not in {"reproduce", "verify"} and not str(phase).startswith("run_shell:"):
            continue
        if (check.get("source_tree_sha256"), check.get("source_epoch")) == (source, epoch):
            current[phase] = check
        else:
            historical[phase] = {
                "phase": phase,
                "tool_id": check["tool_id"],
                "currency": "historical",
                "source_tree_sha256": check.get("source_tree_sha256"),
                "evidence": check["evidence"],
            }
    selected = [current[phase] for phase in ("reproduce", "verify") if phase in current]
    shell_checks = [check for phase, check in current.items() if phase.startswith("run_shell:")]
    selected += sorted(
        shell_checks,
        key=lambda check: (check.get("passed") is not True, check["sequence"]),
        reverse=True,
    )[:4]
    checks = deepcopy(selected)
    value = {
        "source_tree_sha256": source,
        "source_epoch": epoch,
        "changes": deepcopy(state.get("current_changes", [])),
        "checks": checks,
        "omitted_current_checks": len(current) - len(checks),
        "pending_checks": [
            phase for phase in ("reproduce", "verify") if not current.get(phase, {}).get("passed")
        ],
        "historical_check_refs": list(historical.values())[-4:],
    }
    for check in checks:
        check["currency"] = "current"
    if len(canonical_json(value)) > maximum:
        value["historical_check_refs"] = []
    if len(canonical_json(value)) > maximum:
        for check in checks:
            check.pop("diagnostic", None)
            check.pop("failed_tests", None)
            check["details_in_evidence"] = True
    return value if len(canonical_json(value)) <= maximum else None
