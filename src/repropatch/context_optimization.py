"""Optional, receipt-backed context projections; tool execution stays in the runtime."""

import hashlib
import re
from copy import deepcopy

from .context_diagnostics import TEXT_FIELDS, project_diagnostics
from .context_state_projection import state_checkpoint as state_checkpoint
from .task import canonical_json

STRATEGIES = ("diagnostic_extraction", "deduplicate_results", "state_aware_compaction")
COMMAND_VOLATILE = {
    "command_id",
    "duration_seconds",
    "duration_ms",
    "started_at",
    "finished_at",
    "container_id",
}


def initialize(state):
    state.setdefault("metrics", {})
    for name in STRATEGIES:
        metric = state["metrics"].setdefault(name, {})
        for key in (
            "attempts",
            "candidates",
            "triggers",
            "input_bytes",
            "output_bytes",
            "saved_bytes",
            "added_bytes",
        ):
            metric.setdefault(key, 0)
        metric.setdefault("skip_reasons", {})
    return state


def record_skip(state, strategy, reason, **details):
    reasons = initialize(state)["metrics"][strategy]["skip_reasons"]
    reasons[reason] = reasons.get(reason, 0) + 1
    event = {"strategy": strategy, "outcome": "skipped", "reason": reason, **details}
    state.setdefault("decisions", []).append(event)
    state["decisions"] = state["decisions"][-128:]
    return event


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


def diagnostic_projection(name, value, reference, *, read_evidence=None):
    return project_diagnostics(name, value, reference, read_evidence=read_evidence)[0]


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


def _dedup_reason(name, arguments, value, source):
    data = value.get("data")
    if name not in {"run_command", "read_file", "search_code", "list_directory"}:
        return "tool_not_supported"
    if value.get("ok") is not True:
        return "tool_error"
    if not isinstance(source, str) or not source:
        return "missing_source_identity"
    if not isinstance(data, dict):
        return "invalid_receipt"
    if name == "read_file":
        valid = (
            isinstance(arguments.get("path"), str)
            and data.get("path") == arguments["path"]
            and isinstance(data.get("text"), str)
            and type(data.get("truncated")) is bool
            and all(type(data.get(key)) is int for key in ("start_line", "end_line", "total_lines"))
        )
        return None if valid else "invalid_receipt"
    if name == "search_code":
        valid = (
            isinstance(arguments.get("query"), str)
            and bool(arguments["query"])
            and type(data.get("truncated")) is bool
            and isinstance(data.get("matches"), list)
            and all(
                isinstance(item, dict)
                and isinstance(item.get("path"), str)
                and type(item.get("line")) is int
                and isinstance(item.get("text"), str)
                for item in data["matches"]
            )
        )
        return None if valid else "invalid_receipt"
    if name == "list_directory":
        valid = (
            type(data.get("truncated")) is bool
            and isinstance(data.get("entries"), list)
            and all(
                isinstance(item, dict)
                and isinstance(item.get("name"), str)
                and item.get("type") in {"directory", "file"}
                for item in data["entries"]
            )
        )
        return None if valid else "invalid_receipt"
    if arguments.get("name") not in {"reproduce", "verify"}:
        return "unsupported_phase"
    if data.get("source_tree_sha256") != source:
        return "source_mismatch"
    if not _complete(data):
        return "incomplete_output"
    valid = (
        data.get("view_version") == 2
        and type(data.get("passed")) is bool
        and data.get("evaluation_role") == "agent_check"
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
    return None if valid else "invalid_receipt"


def _dedup_eligible(name, arguments, value, source):
    return _dedup_reason(name, arguments, value, source) is None


class ContextOptimizer:
    def __init__(self, context, *, read_evidence=None):
        self.policy = context.policy
        self.state = initialize(context.optimization_state)
        self.read_evidence = read_evidence
        self.last_decisions = []

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
        self.last_decisions = []
        details = {"tool_id": tool_id, "tool": name, "source_tree_sha256": source}

        def skip(strategy, reason, **extra):
            self.last_decisions.append(
                record_skip(self.state, strategy, reason, **{**details, **extra})
            )

        def accept(strategy, candidate):
            self.state["metrics"][strategy]["candidates"] += 1
            projected = canonical_json(candidate).decode()
            before, after = len(native.encode()), len(projected.encode())
            if after > self.policy.tool_output_max_bytes:
                skip(strategy, "output_limit", input_bytes=before, candidate_bytes=after)
                return None
            if before - after < max(128, before // 10):
                skip(strategy, "insufficient_savings", input_bytes=before, candidate_bytes=after)
                return None
            event = record_optimization(
                self.state,
                strategy,
                before,
                after,
                tool_id=tool_id,
                source_tree_sha256=source,
                raw_result_ref=reference,
                measurement="returned_tool_context",
            )
            self.last_decisions.append({**event, "outcome": "projected"})
            return projected, [event]

        data = value.get("data")
        index, key, first = self.state.setdefault("dedup_index", {}), None, None
        if self.policy.deduplicate_results:
            self.state["metrics"]["deduplicate_results"]["attempts"] += 1
            reason = _dedup_reason(name, arguments, value, source)
            # A folded first read never disclosed the entire returned slice to the model.
            if (
                reason is None
                and name != "run_command"
                and native != canonical_json(value).decode()
            ):
                reason = "first_result_not_fully_visible"
            if reason is not None:
                skip("deduplicate_results", reason)
            else:
                stable = _stable_check(data) if name == "run_command" else data
                content_hash = hashlib.sha256(canonical_json(stable)).hexdigest()
                phase = arguments["name"] if name == "run_command" else name
                key = hashlib.sha256(
                    canonical_json(
                        {
                            "tool": name,
                            "arguments": arguments,
                            "source": source,
                            "phase": phase,
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
                    skip("deduplicate_results", "first_observation")
        if first is not None:
            candidate = deepcopy(value)
            if name == "run_command":
                for command in _commands(candidate["data"]):
                    for field in TEXT_FIELDS:
                        command.pop(field, None)
                for test in candidate["data"]["tests"]:
                    test.pop("diagnostic", None)
            else:
                field = {
                    "read_file": "text",
                    "search_code": "matches",
                    "list_directory": "entries",
                }[name]
                content = candidate["data"].pop(field)
                candidate["data"]["returned_items"] = (
                    len(content.splitlines()) if name == "read_file" else len(content)
                )
            candidate["context_projection"] = {
                "kind": "exact_duplicate",
                "duplicate_of": first,
                "raw_result_ref": reference,
                "source_tree_sha256": source,
                "phase": arguments["name"] if name == "run_command" else name,
                "tool_executed": True,
            }
            accepted = accept("deduplicate_results", candidate)
            if accepted is not None:
                if self.policy.diagnostic_extraction:
                    self.state["metrics"]["diagnostic_extraction"]["attempts"] += 1
                    skip("diagnostic_extraction", "superseded_by_dedup")
                return accepted
        if self.policy.diagnostic_extraction:
            self.state["metrics"]["diagnostic_extraction"]["attempts"] += 1
            candidate, reason, projection_details = project_diagnostics(
                name,
                value,
                reference,
                read_evidence=self.read_evidence,
            )
            if candidate is None:
                skip("diagnostic_extraction", reason, **projection_details)
            else:
                accepted = accept("diagnostic_extraction", candidate)
                if accepted is not None:
                    return accepted
        return native, []
