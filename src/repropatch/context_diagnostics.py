"""Bounded, evidence-backed compiler and GTest context projections.

Unknown output is retained verbatim. Recognized compiler context is interned with
per-diagnostic references; only exact normal progress lines are omitted. The
caller decides whether the candidate saves enough context to replace its native
tool view. Evidence readers must enforce their own file and allocation bounds.
"""

import hashlib
import re
from collections import Counter
from copy import deepcopy

from .task import canonical_json

MAX_PARSE_BYTES = 2 * 1024 * 1024
MAX_DIAGNOSTICS = 64
MAX_COMMANDS = 64
MAX_LINES = 32_768
MAX_LINE_BYTES = 16_384
MAX_CONTEXT_BLOCKS = 4096
TEXT_FIELDS = ("stdout", "stderr", "output", "diagnostic")
COMPILER = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+)(?::(?P<column>\d+))?:\s*"
    r"(?P<severity>fatal error|error|warning|note):\s*(?P<message>.+)$"
)
MSVC = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+)(?:,(?P<column>\d+))?\):\s*"
    r"(?P<severity>fatal error|error|warning|note)\s*"
    r"(?P<message>(?:[A-Z]+\d+:)?\s*.+)$"
)
FAILED_TEST = re.compile(r"^\s*\d+\s*-\s*(?P<ctest>.+?)\s+\((?:Failed|SEGFAULT|Timeout)\)\s*$")
GTEST_FAILED = re.compile(r"^\s*\[\s*FAILED\s*\]\s+")
GTEST_DURATION = re.compile(r"\(\d+ ms\)")
SGR = re.compile(r"\x1b\[[0-9;:]*m")
GTEST_START = re.compile(r"^\[==========\] Running \d+ tests? from \d+ test (?:suites?|cases?)\.$")
GTEST_PROGRESS = re.compile(
    r"^(?:\[----------\] (?:Global test environment (?:set-up\.|tear-down\.?)"
    r"|\d+ tests? from \S+(?: \(\d+ ms total\))?)"
    r"|\[==========\] \d+ tests? from \d+ test (?:suites?|cases?) ran\. \(\d+ ms total\)"
    r"|\[  PASSED  \] \d+ tests?\.)$"
)
BUILD_PROGRESS = re.compile(
    r"^\[(?:\d+/\d+|\s*\d+%)\] (?:Building (?:C|CXX|ASM) object \S+"
    r"|Linking (?:C|CXX) (?:(?:static|shared) library|executable) \S+"
    r"|Built target [A-Za-z0-9_.+-]+)$"
)
COMPILER_CONTEXT = re.compile(
    r"^(?:\S.*?:\s+In (?:instantiation|substitution|function|member function|constructor|"
    r"destructor|lambda function) .+"
    r"|\S.*?:\d+(?::\d+)?:\s+(?:recursively )?required from(?: .+)?"
    r"|In file included from .+)$"
)
INCLUDE_CONTINUATION = re.compile(r"^\s+from \S.*:\d+(?::\d+)?[,:]$")
SOURCE_EXCERPT = re.compile(r"^\s*(?:\d+\s*\|.*|\|[ ~^\t]*)$")
CONTEXT_LOCATION = re.compile(
    r"^(?P<location>\S.*?:\d+(?::\d+)?)(?P<text>:\s+(?:recursively )?required from[^\r\n]*[\r\n]*)$"
)


class _Fallback(Exception):
    pass


def _utf8(text):
    if not isinstance(text, str):
        raise _Fallback("invalid_text")
    if len(text) > MAX_PARSE_BYTES:
        raise _Fallback("parse_bytes_limit")
    try:
        raw = text.encode("utf-8")
    except UnicodeError:
        raise _Fallback("invalid_utf8") from None
    if len(raw) > MAX_PARSE_BYTES:
        raise _Fallback("parse_bytes_limit")
    return raw


def _read_log(ref, reader, details):
    if ref is None:
        raise _Fallback("evidence_missing")
    if (
        not isinstance(ref, dict)
        or not isinstance(ref.get("path"), str)
        or not ref["path"]
        or len(ref["path"]) > 4096
        or type(ref.get("size_bytes")) is not int
        or ref["size_bytes"] < 0
        or not isinstance(ref.get("sha256"), str)
        or not re.fullmatch(r"[a-f0-9]{64}", ref["sha256"])
    ):
        raise _Fallback("evidence_ref_invalid")
    if ref["size_bytes"] > MAX_PARSE_BYTES:
        raise _Fallback("evidence_bytes_limit")
    if details["read_bytes"] + ref["size_bytes"] > MAX_PARSE_BYTES:
        raise _Fallback("evidence_total_bytes_limit")
    if reader is None:
        raise _Fallback("evidence_reader_unavailable")
    try:
        raw = reader(deepcopy(ref))
    except Exception as exc:
        details["reader_error_type"] = type(exc).__name__
        raise _Fallback("evidence_read_failed") from None
    if not isinstance(raw, bytes):
        raise _Fallback("evidence_not_bytes")
    if len(raw) > MAX_PARSE_BYTES:
        raise _Fallback("evidence_bytes_limit")
    if len(raw) != ref["size_bytes"]:
        raise _Fallback("evidence_size_mismatch")
    if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise _Fallback("evidence_hash_mismatch")
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise _Fallback("evidence_invalid_utf8") from None
    details["read_bytes"] += len(raw)
    details["read_streams"] += 1
    return text


def _diagnostic(match):
    item = match.groupdict()
    if any(len(str(value).encode()) > 4096 for value in item.values()):
        raise _Fallback("diagnostic_field_limit")
    if len(item["line"]) > 10 or (item["column"] and len(item["column"]) > 10):
        raise _Fallback("diagnostic_location_invalid")
    item["line"] = int(item["line"])
    item["column"] = int(item["column"]) if item["column"] else None
    if not 0 < item["line"] < 2**31 or (
        item["column"] is not None and not 0 <= item["column"] < 2**31
    ):
        raise _Fallback("diagnostic_location_invalid")
    return item


def _gtest_name(name):
    # Validate the token and separator independently to keep near misses linear.
    return name if "." in name[1:-1] and not any(c.isspace() for c in name) else None


def _gtest_event(line, prefix, *, timed=False):
    if not line.startswith(prefix):
        return None
    payload = line[len(prefix) :]
    if timed:
        name, separator, duration = payload.partition(" ")
        return _gtest_name(name) if separator and GTEST_DURATION.fullmatch(duration) else None
    return _gtest_name(payload)


def _gtest_failure(line):
    prefix = GTEST_FAILED.match(line)
    if prefix is None:
        return None
    parts = line[prefix.end() :].split(maxsplit=1)
    if not parts or (len(parts) > 1 and not GTEST_DURATION.fullmatch(parts[1].rstrip())):
        return None
    return _gtest_name(parts[0])


def _parse_text(text, details, full_log_ref=None):
    raw = _utf8(text)
    details["parsed_bytes"] += len(raw)
    if details["parsed_bytes"] > MAX_PARSE_BYTES:
        raise _Fallback("parse_total_bytes_limit")
    lines = text.splitlines(keepends=True)
    details["parsed_lines"] += len(lines)
    if details["parsed_lines"] > MAX_LINES:
        raise _Fallback("parse_lines_limit")
    if any(len(line.encode()) > MAX_LINE_BYTES for line in lines):
        raise _Fallback("parse_line_bytes_limit")
    clean = [SGR.sub("", line.rstrip("\r\n")) for line in lines]
    diagnostics, diagnostic_index, failures, remainder = [], {}, {}, []
    contexts, context_index, blocks = [], {}, {}
    pending = []
    omitted = {"gtest_progress": 0, "build_progress": 0}
    active_test, gtest_started = None, False
    compiler_seen = False

    def intern(line):
        if line not in context_index:
            if len(contexts) >= MAX_CONTEXT_BLOCKS:
                raise _Fallback("context_blocks_limit")
            context_index[line] = len(contexts)
            contexts.append(line)
        return context_index[line]

    def flush_pending():
        remainder.extend(pending)
        pending.clear()

    i = 0
    while i < len(lines):
        line = clean[i]
        failed = _gtest_failure(line)
        if active_test is not None:
            # Expected/Actual payloads may themselves resemble progress messages.
            if failed == active_test:
                active_test = None
            else:
                ok = _gtest_event(line, "[       OK ] ", timed=True)
                if ok == active_test:
                    active_test = None
                remainder.append(lines[i])
                i += 1
                continue
        # Compiler messages can contain arbitrary, unindented continuation lines.
        # Without a stream boundary, subsequent progress belongs to unknown output.
        progress_allowed = not compiler_seen and not pending
        run = _gtest_event(line, "[ RUN      ] ")
        if run:
            flush_pending()
            ok = (
                _gtest_event(clean[i + 1], "[       OK ] ", timed=True)
                if i + 1 < len(lines)
                else None
            )
            if progress_allowed and gtest_started and run == ok:
                omitted["gtest_progress"] += 2
                i += 2
                continue
            active_test = run
        if progress_allowed and GTEST_START.fullmatch(line):
            flush_pending()
            gtest_started = True
            omitted["gtest_progress"] += 1
        elif progress_allowed and gtest_started and GTEST_PROGRESS.fullmatch(line):
            flush_pending()
            omitted["gtest_progress"] += 1
        elif progress_allowed and BUILD_PROGRESS.fullmatch(line):
            omitted["build_progress"] += 1
        elif match := COMPILER.fullmatch(line) or MSVC.fullmatch(line):
            compiler_seen = True
            item = _diagnostic(match)
            key = canonical_json(item)
            if key not in diagnostic_index:
                diagnostic_index[key] = len(diagnostics)
                diagnostics.append({**item, "occurrences": 0})
            index = diagnostic_index[key]
            diagnostics[index]["occurrences"] += 1
            before = tuple(intern(part) for part in pending)
            pending.clear()
            excerpt = []
            while i + 1 < len(lines) and SOURCE_EXCERPT.fullmatch(clean[i + 1]):
                i += 1
                excerpt.append(lines[i])
            after = (intern("".join(excerpt)),) if excerpt else ()
            if before or after:
                block_key = (index, before, after)
                blocks[block_key] = blocks.get(block_key, 0) + 1
        elif failed or (ctest := FAILED_TEST.fullmatch(line)):
            flush_pending()
            name = failed or ctest["ctest"]
            if len(name.encode()) > 4096:
                raise _Fallback("diagnostic_field_limit")
            failures[name] = failures.get(name, 0) + 1
        elif COMPILER_CONTEXT.fullmatch(line) or (pending and INCLUDE_CONTINUATION.fullmatch(line)):
            pending.append(lines[i])
        else:
            flush_pending()
            remainder.append(lines[i])
        if len(diagnostics) + len(failures) > MAX_DIAGNOSTICS:
            raise _Fallback("diagnostics_limit")
        if len(blocks) > MAX_CONTEXT_BLOCKS:
            raise _Fallback("context_blocks_limit")
        i += 1
    flush_pending()
    if not diagnostics and not failures and not any(omitted.values()):
        return None
    parsed = {
        "diagnostics": diagnostics,
        "failed_tests": [{"name": name, "occurrences": n} for name, n in failures.items()],
        "unparsed_output": "".join(remainder),
        "omitted_lines": omitted,
    }
    if contexts:
        # Repeated template messages at different source locations share text;
        # each location and its association with a diagnostic remains explicit.
        matches = [CONTEXT_LOCATION.fullmatch(context) for context in contexts]
        counts = Counter(match["text"] for match in matches if match)
        shared, shared_index = [], {}
        for index, match in enumerate(matches):
            if match and counts[match["text"]] > 1 and len(match["text"]) >= 128:
                if match["text"] not in shared_index:
                    shared_index[match["text"]] = len(shared)
                    shared.append(match["text"])
                contexts[index] = {
                    "location": match["location"],
                    "text_ref": shared_index[match["text"]],
                }
        if shared:
            parsed["context_texts"] = shared
        parsed["context_blocks"] = contexts
        parsed["diagnostic_blocks"] = [
            {
                "diagnostic": index,
                **({"before": list(before)} if before else {}),
                **({"after": list(after)} if after else {}),
                **({"occurrences": n} if n > 1 else {}),
            }
            for (index, before, after), n in blocks.items()
        ]
    if full_log_ref is not None:
        parsed["full_log_ref"] = deepcopy(full_log_ref)
    details["diagnostics"] += len(diagnostics)
    details["failed_tests"] += len(failures)
    for category, count in omitted.items():
        details["omitted_lines"][category] += count
    return parsed


def project_diagnostics(name, value, reference, *, read_evidence=None):
    """Return ``(candidate, reason, details)`` without changing the raw receipt.

    ``candidate=None`` requests native fallback. ``projected`` means parsing
    succeeded, with the caller still responsible for the savings/output gate.
    A truncated preview requires both checked stream archives. Genuine output
    truncation, uncertain command completion, corrupt evidence and resource
    limits fail the entire projection, preserving unique diagnostics at the tail.
    ``read_evidence(ref_dict)`` returns bytes and performs runtime path checks.
    Context block entries are verbatim strings or ``{location, text_ref}``;
    concatenate the location with ``context_texts[text_ref]`` to recover the
    full fragment. Diagnostic blocks reference these entries before/after each
    diagnostic. Their omitted occurrence count defaults to one.
    """
    details = {
        "parsed_bytes": 0,
        "parsed_lines": 0,
        "read_bytes": 0,
        "read_streams": 0,
        "diagnostics": 0,
        "failed_tests": 0,
        "omitted_lines": {"gtest_progress": 0, "build_progress": 0},
    }
    try:
        if name not in {"run_command", "run_shell"}:
            raise _Fallback("unsupported_tool")
        if not isinstance(value, dict) or value.get("ok") is not True:
            raise _Fallback("tool_unsuccessful")
        data = value.get("data")
        if not isinstance(data, dict):
            raise _Fallback("invalid_receipt")
        if name == "run_command" and data.get("view_version") != 2:
            raise _Fallback("unsupported_view")
        if name == "run_shell" and type(data.get("exit_code")) is not int:
            raise _Fallback("invalid_exit_code")
        commands = data.get("failed_commands", [])
        if not isinstance(commands, list) or any(not isinstance(c, dict) for c in commands):
            raise _Fallback("invalid_commands")
        if len(commands) > MAX_COMMANDS:
            raise _Fallback("commands_limit")
        for command in [data, *commands]:
            for flag in ("truncated", "output_truncated", "timed_out"):
                if flag in command and type(command[flag]) is not bool:
                    raise _Fallback("invalid_completion_flags")
            if command.get("output_truncated"):
                raise _Fallback("output_truncated")
            if command.get("timed_out") or command.get("status") == "timed_out":
                raise _Fallback("command_timeout")
            if command.get("status", "exited") != "exited":
                raise _Fallback("command_incomplete")
            if command.get("error") or command.get("error_code"):
                raise _Fallback("command_error")
        candidate = deepcopy(value)
        projected = False
        for index, command in enumerate(
            [candidate["data"], *candidate["data"].get("failed_commands", [])]
        ):
            details["command_index"] = index
            if command.get("truncated"):
                for field in ("stdout", "stderr"):
                    details["field"] = field
                    command[field] = _read_log(command.get(field + "_log"), read_evidence, details)
                    byte_count = command.get(field + "_bytes")
                    if byte_count is not None and (
                        type(byte_count) is not int or byte_count != len(command[field].encode())
                    ):
                        raise _Fallback("stream_size_mismatch")
                if "output" in command:
                    command["output"] = command["stdout"] + command["stderr"]
            for field in TEXT_FIELDS:
                if field not in command:
                    continue
                details["field"] = field
                parsed = _parse_text(command[field], details, command.get(field + "_log"))
                if parsed is not None:
                    command[field] = parsed
                    projected |= bool(parsed["diagnostics"] or parsed["failed_tests"])
        if not projected:
            raise _Fallback("no_diagnostics")
        candidate["context_projection"] = {
            "kind": "structured_diagnostics",
            "raw_result_ref": deepcopy(reference),
        }
        details.pop("command_index", None)
        details.pop("field", None)
        return candidate, "projected", details
    except _Fallback as exc:
        return None, str(exc), details
