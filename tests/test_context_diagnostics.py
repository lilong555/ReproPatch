"""CPU-only diagnostic projection contracts with compiler and GTest output."""

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from copy import deepcopy

import pytest

import repropatch.context_diagnostics as diagnostics
from repropatch.context import ContextPolicy, ContextState, fold_tool_output
from repropatch.context_diagnostics import project_diagnostics
from repropatch.context_optimization import ContextOptimizer
from repropatch.task import canonical_json


def evidence(raw=b"", path="logs/command/stdout.bin"):
    return {"path": path, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


REFERENCE = evidence(b"raw tool result", "agent/tool-results/tool.json")
ERROR = "src/format.cc:17:4: error: expected value\n"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Diagnostic projections must remain offline")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def receipt(text=ERROR, **command_options):
    return {
        "ok": True,
        "progress": {"model_steps_remaining": 8},
        "data": {
            "view_version": 2,
            "passed": False,
            "evaluation_role": "agent_check",
            "source_tree_sha256": "a" * 64,
            "tests": [{"name": "format-test", "observed_status": "failed"}],
            "failed_commands": [
                {
                    "status": "exited",
                    "exit_code": 8,
                    "stdout": text,
                    "stderr": "",
                    **command_options,
                }
            ],
        },
    }


def project(value, **kwargs):
    before = deepcopy(value)
    result = project_diagnostics("run_command", value, REFERENCE, **kwargs)
    assert value == before
    return result


def parsed_stdout(candidate):
    return candidate["data"]["failed_commands"][0]["stdout"]


def archived(raw, *, stderr=b""):
    value = receipt(
        "truncated preview",
        truncated=True,
        stdout_log=evidence(raw),
        stderr_log=evidence(stderr, "logs/command/stderr.bin"),
        stdout_bytes=len(raw),
        stderr_bytes=len(stderr),
    )
    store = {"logs/command/stdout.bin": raw, "logs/command/stderr.bin": stderr}
    return value, lambda ref: store[ref["path"]]


def context_texts(parsed):
    return [
        block
        if isinstance(block, str)
        else block["location"] + parsed["context_texts"][block["text_ref"]]
        for block in parsed.get("context_blocks", [])
    ]


def gtest_log(normal_tests=104):
    progress = "".join(
        f"[ RUN      ] format_test.normal_{i}\n[       OK ] format_test.normal_{i} (0 ms)\n"
        for i in range(normal_tests)
    )
    return (
        "Test project /build\n"
        "1/1 Test #7: format-test ......................***Failed   20.12 sec\n"
        "[1/2] Building CXX object test/CMakeFiles/format-test.dir/format-test.cc.o\n"
        "[2/2] Linking CXX executable bin/format-test\n"
        f"[==========] Running {normal_tests + 1} tests from 1 test suite.\n"
        "[----------] Global test environment set-up.\n"
        f"[----------] {normal_tests + 1} tests from format_test\n"
        + progress
        + "[ RUN      ] format_test.format_nan\n"
        "/src/test/format-test.cc:312: Failure\n"
        "Expected equality of these values:\n"
        '  " nan"\n'
        '  fmt::format("{: }", nan)\n'
        '    Which is: "nan"\n'
        "[  FAILED  ] format_test.format_nan (1 ms)\n"
        "[----------] Global test environment tear-down\n"
        f"[==========] {normal_tests + 1} tests from 1 test suite ran. (8 ms total)\n"
        f"[  PASSED  ] {normal_tests} tests.\n"
        "[  FAILED  ] 1 test, listed below:\n"
        "[  FAILED  ] format_test.format_nan\n"
        "CMake Error at /src/test/repropatch-build-test.cmake:8 (message):\n"
        "  REPROPATCH_RUNTIME_REGRESSION: 1\n"
        "The following tests FAILED:\n"
        "  7 - format-test (Failed)\n"
    )


def template_log():
    result = "[1/65] Building CXX object test/CMakeFiles/printf-test.dir/printf-test.cc.o\n"
    for kind in ("int", "unsigned int", "long", "unsigned long", "long long", "unsigned long long"):
        for location in (2200, 2217, 2232):
            result += (
                f"/src/include/fmt/format.h: In instantiation of 'write_padded<{kind}>'\n"
                f"/src/include/fmt/format.h:{location}:19:   required from "
                "'bool loc_writer<Char>::operator()(T) "
                "[with typename std::enable_if<is_integral<T>::value && "
                "!std::is_same<T, bool>::value, "
                f"int>::type <anonymous> = 0; T = {kind}; Char = wchar_t]'\n"
                "/src/include/fmt/core.h:1689:15:   required from 'visit_format_arg(visitor)'\n"
                "/src/include/fmt/xchar.h:34:21:   required from here\n"
                f"/src/include/fmt/format.h:1784:9: error: no matching call to writer<{kind}>\n"
                " 1784 |   it = f(it);\n"
                "      |        ~^~~~\n"
                f"/src/include/fmt/format.h:{location}:44: note: candidate writer<{kind}>\n"
                f" {location} |       write_padded(out, specs, size, size, [&](iterator it) {{\n"
                "      |                                            ^\n"
            )
    return result + "src/last.cpp:90: error: unique final error\nld: unknown linker failure\n"


def test_gtest_progress_removed_with_expected_actual_and_unique_failures_retained():
    value = receipt(gtest_log())
    candidate, reason, details = project(value)
    parsed = parsed_stdout(candidate)
    assert reason == "projected"
    assert len(canonical_json(candidate)) < len(canonical_json(value)) * 0.3
    assert parsed["diagnostics"] == []
    assert parsed["failed_tests"] == [
        {"name": "format_test.format_nan", "occurrences": 2},
        {"name": "format-test", "occurrences": 1},
    ]
    for text in (
        "format_test.format_nan",
        "/src/test/format-test.cc:312: Failure",
        "Expected equality of these values:",
        '  " nan"',
        '    Which is: "nan"',
        "REPROPATCH_RUNTIME_REGRESSION: 1",
        "***Failed",
    ):
        assert text in parsed["unparsed_output"]
    assert details["omitted_lines"] == {"gtest_progress": 214, "build_progress": 2}
    assert candidate["data"]["tests"] == value["data"]["tests"]
    assert candidate["data"]["failed_commands"][0]["exit_code"] == 8
    assert candidate["context_projection"] == {
        "kind": "structured_diagnostics",
        "raw_result_ref": REFERENCE,
    }


def test_template_context_shared_without_losing_locations_or_unique_tail():
    text = template_log()
    candidate, reason, _ = project(receipt(text))
    parsed = parsed_stdout(candidate)
    assert reason == "projected"
    errors = [item for item in parsed["diagnostics"] if item["severity"] == "error"]
    assert len(errors) == 7
    assert errors[-1]["message"] == "unique final error"
    assert sum(item["occurrences"] for item in errors) == 19
    assert parsed["unparsed_output"] == "ld: unknown linker failure\n"
    contexts = context_texts(parsed)
    assert any(isinstance(block, dict) for block in parsed["context_blocks"])
    assert len(canonical_json(candidate)) < len(canonical_json(receipt(text))) * 0.85
    for block in parsed["diagnostic_blocks"]:
        diagnostic = parsed["diagnostics"][block["diagnostic"]]
        before = "".join(contexts[i] for i in block.get("before", []))
        after = "".join(contexts[i] for i in block.get("after", []))
        if diagnostic["severity"] == "error":
            assert "In instantiation" in before
            assert "required from here" in before
            assert "1784 |   it = f(it);" in after
        else:
            assert str(diagnostic["line"]) in after
    assert all(context in text for context in contexts)


def test_duplicate_lines_keep_old_diagnostic_fields_and_occurrence_contract():
    candidate, _, _ = project(receipt(ERROR * 300 + "ld: unknown error\n"))
    parsed = parsed_stdout(candidate)
    assert parsed["diagnostics"] == [
        {
            "file": "src/format.cc",
            "line": 17,
            "column": 4,
            "severity": "error",
            "message": "expected value",
            "occurrences": 300,
        }
    ]
    assert parsed["unparsed_output"] == "ld: unknown error\n"


def test_msvc_shell_and_ctest_failures():
    value = {
        "ok": True,
        "data": {
            "status": "exited",
            "exit_code": 8,
            "stderr": "C:\\src\\stats.cpp(42,7): error C2001: expected value\n"
            "  1 - negative_values (SEGFAULT)\n  2 - timeout_test (Timeout)\n",
        },
    }
    before = deepcopy(value)
    candidate, reason, _ = project_diagnostics("run_shell", value, REFERENCE)
    assert reason == "projected" and value == before
    parsed = candidate["data"]["stderr"]
    assert parsed["diagnostics"][0]["column"] == 7
    assert parsed["diagnostics"][0]["message"] == "C2001: expected value"
    assert {test["name"] for test in parsed["failed_tests"]} == {"negative_values", "timeout_test"}


def test_ansi_color_recognized_and_unknown_control_sequences_retained():
    text = "\x1b[01;31m" + ERROR.rstrip() + "\x1b[0m\n"
    unknown = "\x1b]8;;https://example.com\x07linker: unknown\x1b]8;;\x07\n"
    candidate, _, _ = project(receipt(text + unknown))
    parsed = parsed_stdout(candidate)
    assert parsed["diagnostics"][0]["file"] == "src/format.cc"
    assert parsed["unparsed_output"] == unknown


@pytest.mark.parametrize(
    "payload",
    [
        "[1/2] Building CXX object fake.o\n",
        "[ RUN      ] Fake.Test\n[       OK ] Fake.Test (0 ms)\n",
        "[  PASSED  ] 40 tests.\n",
        "[----------] Global test environment tear-down\n",
        ERROR,
    ],
)
def test_progress_shaped_expected_actual_payload_is_retained(payload):
    text = (
        "[==========] Running 1 test from 1 test suite.\n"
        "[ RUN      ] Real.Failure\nExpected: literal output\nActual:\n"
        + payload
        + "[  FAILED  ] Real.Failure (1 ms)\n"
    )
    candidate, _, details = project(receipt(text))
    assert payload in parsed_stdout(candidate)["unparsed_output"]
    assert details["omitted_lines"]["gtest_progress"] == 1
    assert details["omitted_lines"]["build_progress"] == 0


def test_compiler_warning_before_gtest_preserves_diagnostic_shaped_test_body():
    warning = "compile.cc:1:2: warning: repeated build warning\n"
    payload = "payload.cc:42:3: error: literal expected compiler text\n"
    body = "Expected: literal compiler output\n" + payload + "Actual: empty\n"
    text = (
        warning * 200
        + "[==========] Running 1 test from 1 test suite.\n"
        + "[ RUN      ] Formatter.ErrorText\n"
        + body
        + "[  FAILED  ] Formatter.ErrorText (0 ms)\n"
    )
    candidate, reason, details = project(receipt(text))
    parsed = parsed_stdout(candidate)
    assert reason == "projected"
    assert body in parsed["unparsed_output"]
    assert parsed["diagnostics"] == [
        {
            "file": "compile.cc",
            "line": 1,
            "column": 2,
            "severity": "warning",
            "message": "repeated build warning",
            "occurrences": 200,
        }
    ]
    assert parsed["failed_tests"] == [{"name": "Formatter.ErrorText", "occurrences": 1}]
    assert details["omitted_lines"] == {"gtest_progress": 0, "build_progress": 0}
    assert len(canonical_json(candidate)) < len(canonical_json(receipt(text))) * 0.2


def test_unknown_output_inside_passing_test_and_following_failure_kept():
    text = (
        "[==========] Running 2 tests from 1 test suite.\n"
        "[ RUN      ] Real.Pass\nwarning: custom output\n[       OK ] Real.Pass (0 ms)\n"
        "[ RUN      ] Real.Fail\nExpected: 1\nActual: 2\n[  FAILED  ] Real.Fail (0 ms)\n"
    )
    candidate, _, _ = project(receipt(text))
    parsed = parsed_stdout(candidate)
    assert "warning: custom output" in parsed["unparsed_output"]
    assert "Expected: 1\nActual: 2" in parsed["unparsed_output"]


@pytest.mark.parametrize(
    "text",
    [
        "unknown failure\n",
        "[1/2] Building CXX object harmless.o\n",
        "[==========] Running 1 test from 1 test suite.\n"
        "[ RUN      ] X.Y\n[       OK ] X.Y (0 ms)\n",
        "",
    ],
)
def test_no_diagnostic_uses_native_fallback(text):
    assert project(receipt(text))[:2] == (None, "no_diagnostics")


def test_ambiguous_progress_and_unknown_template_context_are_preserved():
    unknown = (
        "[1/2] Building CXX object broken.o error: failed\n"
        "[----------] 2 tests from Suite unexpected failure\n"
        "[       OK ] X.Y (0 ms) extra error\n"
        "new-compiler: unrecognized location\n"
    )
    candidate, _, _ = project(receipt(ERROR + unknown))
    assert parsed_stdout(candidate)["unparsed_output"] == unknown


@pytest.mark.parametrize("diagnostic_first", [False, True])
@pytest.mark.parametrize(
    ("prefix", "suffix"),
    [("[ RUN      ] ", " "), ("[       OK ] ", " (0 ms) extra"), ("[  FAILED  ] ", " extra")],
)
def test_gtest_near_misses_have_bounded_runtime(prefix, suffix, diagnostic_first):
    near_misses = (prefix + "a." * 8000 + suffix + "\n") * 120
    error = "x.cc:1: error: real diagnostic\n"
    text = error + near_misses if diagnostic_first else near_misses + error
    assert len(text.encode()) < diagnostics.MAX_PARSE_BYTES
    assert max(map(len, text.splitlines(keepends=True))) < diagnostics.MAX_LINE_BYTES
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
import time
from repropatch.context_diagnostics import project_diagnostics

text = sys.stdin.read()
value = {"ok": True, "data": {"exit_code": 1, "stdout": text}}
start = time.perf_counter()
candidate, reason, details = project_diagnostics("run_shell", value, {})
elapsed = time.perf_counter() - start
assert reason == "projected", (reason, details)
parsed = candidate["data"]["stdout"]
assert parsed["unparsed_output"] == text.replace("x.cc:1: error: real diagnostic\\n", "")
assert parsed["diagnostics"][0]["message"] == "real diagnostic"
print(elapsed)
""",
        ],
        input=text,
        text=True,
        capture_output=True,
        timeout=15,
        check=True,
    )
    assert float(result.stdout) < 5.0


@pytest.mark.parametrize("name", ["Suite.Case", "Param/Suite.Case/0", "a..", ".a.b", "..."])
def test_gtest_token_parser_preserves_names_and_failure_spacing(name):
    text = (
        "[==========] Running 2 tests from 1 test suite.\n"
        f"[ RUN      ] {name}\n[       OK ] {name} (12 ms)\n"
        f"[ RUN      ] Real.Failure\nExpected: {name}\n"
        "  [FAILED]\tReal.Failure\t(12 ms)  \n"
        f"\t[ FAILED ] {name}  \n"
    )
    candidate, reason, details = project(receipt(text))
    assert reason == "projected"
    assert parsed_stdout(candidate)["failed_tests"] == [
        {"name": "Real.Failure", "occurrences": 1},
        {"name": name, "occurrences": 1},
    ]
    assert details["omitted_lines"]["gtest_progress"] == 3


@pytest.mark.parametrize(
    "payload",
    [
        "[1/2] Building CXX object secret_target.o\n",
        "[==========] Running 1 test from 1 test suite.\n"
        "[ RUN      ] Fake.Pass\n[       OK ] Fake.Pass (0 ms)\n"
        "[  PASSED  ] 1 test.\n",
    ],
)
def test_progress_after_compiler_diagnostic_stays_visible(payload):
    candidate, reason, details = project(receipt(ERROR + payload + "actual differs\n"))
    assert reason == "projected"
    assert parsed_stdout(candidate)["unparsed_output"] == payload + "actual differs\n"
    assert details["omitted_lines"] == {"gtest_progress": 0, "build_progress": 0}


def test_progress_after_compiler_context_stays_visible():
    body = "assert.cc: In function 'void example()':\n[1/2] Building CXX object secret_target.o\n"
    candidate, reason, details = project(receipt(body + ERROR))
    assert reason == "projected"
    assert parsed_stdout(candidate)["unparsed_output"] == body
    assert details["omitted_lines"]["build_progress"] == 0


def test_real_gcc_multiline_assertion_survives_archive_read_and_savings_gate():
    compiler = shutil.which("gcc")
    if compiler is None:
        pytest.skip("GCC is required for the real compiler regression")
    result = subprocess.run(
        [compiler, "-x", "c++", "-fsyntax-only", "-fdiagnostics-color=never", "-"],
        input='#line 1 "assert.cc"\n'
        'static_assert(false,"expected build output:\\n'
        '[1/2] Building CXX object secret_target.o\\nactual differs");\n',
        text=True,
        capture_output=True,
        env={**os.environ, "LC_ALL": "C"},
        timeout=15,
    )
    assert result.returncode == 1, result.stderr
    continuation = "[1/2] Building CXX object secret_target.o\nactual differs\n"
    assert continuation in result.stderr
    raw = (result.stderr * 300).encode()
    value, read = archived(raw)
    value["data"]["failed_commands"][0]["stdout"] = result.stderr * 200
    original = deepcopy(value)
    reference = evidence(canonical_json(value), REFERENCE["path"])
    policy = ContextPolicy(diagnostic_extraction=True)
    state = ContextState(policy)
    calls = []

    def reader(ref):
        calls.append(deepcopy(ref))
        return read(ref)

    optimizer = ContextOptimizer(state, read_evidence=reader)
    native = fold_tool_output(
        canonical_json(value).decode(), policy.tool_output_max_bytes, lambda raw: reference["path"]
    )
    visible, events = optimizer.project(
        "run_command",
        {"name": "reproduce"},
        value,
        reference,
        tool_id="multiline-assert",
        source=value["data"]["source_tree_sha256"],
        native=native,
    )
    assert events, optimizer.last_decisions
    assert len(visible.encode()) <= policy.tool_output_max_bytes
    assert len(native.encode()) - len(visible.encode()) >= max(128, len(native.encode()) // 10)
    parsed = parsed_stdout(json.loads(visible))
    assert parsed["unparsed_output"] == continuation * 300
    assert parsed["diagnostics"][0]["occurrences"] == 300
    assert parsed["diagnostics"][0]["message"].endswith("expected build output:")
    assert parsed["omitted_lines"]["build_progress"] == 0
    assert parsed["full_log_ref"] == evidence(raw)
    assert calls == [evidence(raw), evidence(b"", "logs/command/stderr.bin")]
    assert value == original


def test_truncated_preview_reads_complete_checked_streams_and_tail():
    raw = (gtest_log() + "src/tail.cc:71: error: unique tail\n").encode()
    value, read = archived(raw, stderr=b"ld: unrecognized linker failure\n")
    called = []

    def reader(ref):
        called.append(deepcopy(ref))
        return read(ref)

    candidate, reason, details = project(value, read_evidence=reader)
    assert reason == "projected" and details["read_streams"] == 2
    parsed = parsed_stdout(candidate)
    assert parsed["diagnostics"][-1]["message"] == "unique tail"
    assert parsed["full_log_ref"] == value["data"]["failed_commands"][0]["stdout_log"]
    assert candidate["data"]["failed_commands"][0]["stderr"] == "ld: unrecognized linker failure\n"
    assert candidate["data"]["failed_commands"][0]["truncated"] is True
    assert len(called) == 2


def test_reader_reference_mutation_cannot_change_input():
    value, read = archived(ERROR.encode())

    def reader(ref):
        raw = read(ref)
        ref["path"] = "mutated"
        return raw

    assert project(value, read_evidence=reader)[1] == "projected"


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda c: c.pop("stdout_log"), "evidence_missing"),
        (lambda c: c.pop("stderr_log"), "evidence_missing"),
        (lambda c: c["stdout_log"].update(sha256="a" * 64), "evidence_hash_mismatch"),
        (lambda c: c["stdout_log"].update(size_bytes=1), "evidence_size_mismatch"),
        (lambda c: c["stdout_log"].update(size_bytes=-1), "evidence_ref_invalid"),
        (lambda c: c["stdout_log"].update(size_bytes=True), "evidence_ref_invalid"),
        (lambda c: c["stdout_log"].update(sha256="invalid"), "evidence_ref_invalid"),
        (lambda c: c["stdout_log"].update(path=""), "evidence_ref_invalid"),
        (
            lambda c: c["stdout_log"].update(size_bytes=diagnostics.MAX_PARSE_BYTES + 1),
            "evidence_bytes_limit",
        ),
        (lambda c: c.update(stdout_bytes=1), "stream_size_mismatch"),
    ],
)
def test_bad_archive_metadata_falls_back_without_partial_projection(mutation, reason):
    value, read = archived(ERROR.encode())
    mutation(value["data"]["failed_commands"][0])
    assert project(value, read_evidence=read)[:2] == (None, reason)


def test_absent_reader_and_invalid_utf8_archive():
    value, _ = archived(ERROR.encode())
    assert project(value)[:2] == (None, "evidence_reader_unavailable")
    value, read = archived(ERROR.encode() + b"\xff")
    assert project(value, read_evidence=read)[:2] == (None, "evidence_invalid_utf8")


def test_reader_failure_is_sanitized():
    value, _ = archived(ERROR.encode())

    def reader(ref):
        raise OSError("secret-placeholder-should-not-be-logged")

    candidate, reason, details = project(value, read_evidence=reader)
    assert candidate is None and reason == "evidence_read_failed"
    assert details["reader_error_type"] == "OSError"
    assert "secret-placeholder" not in repr(details)


@pytest.mark.parametrize("raw", ["not bytes", bytearray(b"x"), None])
def test_reader_return_type_checked(raw):
    value, _ = archived(ERROR.encode())
    assert project(value, read_evidence=lambda ref: raw)[:2] == (None, "evidence_not_bytes")


def test_reader_return_size_bound_checked(monkeypatch):
    value, _ = archived(ERROR.encode())
    monkeypatch.setattr(diagnostics, "MAX_PARSE_BYTES", 100)
    assert project(value, read_evidence=lambda ref: b"x" * 101)[:2] == (
        None,
        "evidence_bytes_limit",
    )


def test_total_archive_budget_prevents_second_read(monkeypatch):
    value, read = archived(ERROR.encode(), stderr=b"x" * 80)
    calls = []

    def reader(ref):
        calls.append(ref["path"])
        return read(ref)

    monkeypatch.setattr(diagnostics, "MAX_PARSE_BYTES", 100)
    assert project(value, read_evidence=reader)[:2] == (None, "evidence_total_bytes_limit")
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("options", "reason"),
    [
        ({"output_truncated": True}, "output_truncated"),
        ({"timed_out": True}, "command_timeout"),
        ({"status": "timed_out"}, "command_timeout"),
        ({"status": "running"}, "command_incomplete"),
        ({"status": "cancelled"}, "command_incomplete"),
        ({"error": "output reader failed"}, "command_error"),
        ({"error_code": "PROCESS_ERROR"}, "command_error"),
        ({"truncated": "false"}, "invalid_completion_flags"),
    ],
)
def test_incomplete_commands_fallback_before_archive_read(options, reason):
    value, _ = archived(ERROR.encode())
    value["data"]["failed_commands"][0].update(options)

    def reader(ref):
        pytest.fail("Incomplete commands must be rejected before evidence reads")

    assert project(value, read_evidence=reader)[:2] == (None, reason)


def test_bad_second_stream_or_command_falls_back_entire_receipt():
    value, read = archived(ERROR.encode(), stderr=b"\xff")
    assert project(value, read_evidence=read)[:2] == (None, "evidence_invalid_utf8")
    value = receipt(ERROR)
    value["data"]["failed_commands"].append({"stdout": ERROR, "status": "timed_out"})
    assert project(value)[:2] == (None, "command_timeout")


def test_build_progress_in_stdout_with_compiler_diagnostics_in_stderr():
    text = "".join(f"[{i}/100] Building CXX object source_{i}.o\n" for i in range(100))
    candidate, reason, details = project(receipt(text, stderr=ERROR))
    assert reason == "projected"
    assert parsed_stdout(candidate)["diagnostics"] == []
    assert parsed_stdout(candidate)["unparsed_output"] == ""
    assert details["omitted_lines"]["build_progress"] == 100
    assert candidate["data"]["failed_commands"][0]["stderr"]["diagnostics"][0]["line"] == 17


def test_full_archive_output_alias_and_missing_preview_fields_are_supported():
    value, read = archived(ERROR.encode())
    command = value["data"]["failed_commands"][0]
    command.pop("stdout")
    command.pop("stderr")
    command["output"] = "preview alias"
    candidate, reason, _ = project(value, read_evidence=read)
    assert reason == "projected"
    assert parsed_stdout(candidate)["diagnostics"][0]["message"] == "expected value"
    assert candidate["data"]["failed_commands"][0]["output"]["diagnostics"][0]["line"] == 17


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("x" * (diagnostics.MAX_PARSE_BYTES + 1), "parse_bytes_limit"),
        (ERROR + "x" * (diagnostics.MAX_LINE_BYTES + 1), "parse_line_bytes_limit"),
        ("\n" * (diagnostics.MAX_LINES + 1), "parse_lines_limit"),
        ("".join(f"x.cc:{i + 1}: error: distinct\n" for i in range(65)), "diagnostics_limit"),
        ("x.cc:1: error: " + "x" * 5000, "diagnostic_field_limit"),
        ("x.cc:0: error: bad location", "diagnostic_location_invalid"),
        ("x.cc:999999999999999: error: huge location", "diagnostic_location_invalid"),
        ("x.cc:1:999999999999999: error: huge column", "diagnostic_location_invalid"),
        ("\ud800", "invalid_utf8"),
        (123, "invalid_text"),
    ],
)
def test_parser_limits_use_native_without_dropping_tail(text, reason):
    assert project(receipt(text))[:2] == (None, reason)


def test_total_parse_limit_and_context_table_limit(monkeypatch):
    monkeypatch.setattr(diagnostics, "MAX_PARSE_BYTES", 100)
    value = receipt(ERROR, stderr=ERROR * 2)
    assert project(value)[:2] == (None, "parse_total_bytes_limit")
    monkeypatch.setattr(diagnostics, "MAX_PARSE_BYTES", 2 * 1024 * 1024)
    monkeypatch.setattr(diagnostics, "MAX_CONTEXT_BLOCKS", 1)
    assert project(receipt(template_log()))[:2] == (None, "context_blocks_limit")


def test_legacy_complete_fixture_needs_no_archive_reader():
    value = receipt(ERROR * 10, stdout_log={"path": "legacy", "sha256": "a" * 64, "size_bytes": 10})
    assert project(value)[1] == "projected"


@pytest.mark.parametrize(
    ("name", "value", "reason"),
    [
        ("read_file", {}, "unsupported_tool"),
        ("run_shell", {"ok": False}, "tool_unsuccessful"),
        ("run_shell", {"ok": True, "data": None}, "invalid_receipt"),
        ("run_shell", {"ok": True, "data": {"exit_code": True}}, "invalid_exit_code"),
        ("run_command", {"ok": True, "data": {}}, "unsupported_view"),
        (
            "run_command",
            {"ok": True, "data": {"view_version": 2, "failed_commands": None}},
            "invalid_commands",
        ),
        (
            "run_command",
            {"ok": True, "data": {"view_version": 2, "failed_commands": [None]}},
            "invalid_commands",
        ),
        (
            "run_command",
            {"ok": True, "data": {"view_version": 2, "failed_commands": [{}] * 65}},
            "commands_limit",
        ),
    ],
)
def test_invalid_receipts_have_explicit_reasons(name, value, reason):
    assert project_diagnostics(name, value, REFERENCE)[:2] == (None, reason)
