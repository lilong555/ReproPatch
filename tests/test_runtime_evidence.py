"""Focused tests for evidence accounting, not task-success measurements."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "runtime_evidence", Path(__file__).parents[1] / "scripts/benchmark_runtime_evidence.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_coverage_keeps_unknown_denominator():
    assert MODULE.coverage([5, None, 7]) == {
        "sum": 12,
        "n": 2,
        "denominator": 3,
        "median": 6,
    }


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("ORACLE_PASSED", "oracle_passed"),
        ("ORACLE_BUILD_FAILED", "oracle_build_failed"),
        ("ORACLE_TESTS_FAILED", "oracle_tests_failed"),
    ],
)
def test_observation_uses_oracle_status(status, expected):
    assert MODULE.observed_stage({"status": status}) == expected


def test_projection_roundtrip_and_original_preserved(tmp_path):
    text = "\u8bca\u65ad" * 10000
    body = {
        "input": [
            {"type": "function_call", "name": "bash", "call_id": "c", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "c", "output": text},
        ]
    }
    projected, row = MODULE.project_request(body, 1, tmp_path)
    assert row["projected_output_bytes"] <= 24576
    assert row["attachment_roundtrip"]
    assert row["boundaries_equal"]
    assert row["non_output_fields_preserved"]
    assert row["projected_provider_input_tokens"] is None
    assert body["input"][1]["output"] == text
    assert projected != body


def test_projection_rejects_orphan_output(tmp_path):
    with pytest.raises(Exception, match="COMPACTION_FAILED"):
        MODULE.project_request(
            {
                "input": [
                    {"type": "function_call_output", "call_id": "missing", "output": "x" * 30000},
                ]
            },
            0,
            tmp_path,
        )


def test_archive_request_selection_excludes_cli_copies():
    assert MODULE.REQUEST.search("codex/http-native/" + "a" * 32 + "-request.json")
    assert not MODULE.REQUEST.search("codex/http-native/" + "a" * 32 + "-cli-request.json")


def test_admission_observer_only_records_successful_first_admission():
    calls, admission = [], {}

    class Log:
        @property
        def state(self):
            raise AssertionError("observer must not inspect state")

    def emit(log, kind, payload, **kwargs):
        calls.append((kind, payload, kwargs))
        if payload.get("fail"):
            raise ValueError("production exception")
        return 42

    observer = MODULE.admission_observer(emit, admission)
    log = Log()
    assert observer(log, "tool_started", {}) == 42
    assert admission == {}
    with pytest.raises(ValueError, match="production exception"):
        observer(log, "model_started", {"fail": True})
    assert admission == {}
    assert observer(log, "model_started", {}, step_id=4) == 42
    first = admission.copy()
    observer(log, "model_started", {}, step_id=5)
    assert admission == first and len(calls) == 4


def test_portable_index_is_relative_to_index_not_cwd(tmp_path, monkeypatch):
    index = tmp_path / "package/audit-index.json"
    monkeypatch.chdir(tmp_path)
    assert MODULE.archive_path(index, {"archive": "archives/a.tar.gz"}) == (
        tmp_path / "package/archives/a.tar.gz"
    )


def test_legacy_absolute_index_remains_readable(tmp_path):
    archive = tmp_path / "a.tar.gz"
    assert MODULE.archive_path(tmp_path / "index.json", {"local_paths": [str(archive)]}) == archive


def test_repacked_members_exclude_transport_duplicates():
    prefix = "codex/http-native/" + "a" * 32
    assert MODULE.input_member(prefix + "-request.json", "codex")
    assert MODULE.input_member(prefix + "-response.json", "codex")
    assert not MODULE.input_member(prefix + "-cli-request.json", "codex")
    assert not MODULE.input_member(prefix + "-response.sse", "codex")
    assert MODULE.input_member("ledgers/codex.sqlite3", "codex")


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a/../../escape"])
def test_package_extraction_rejects_unsafe_member(tmp_path, name):
    with pytest.raises(ValueError, match="UNSAFE_ARCHIVE_MEMBER"):
        MODULE.safe_member_path(tmp_path, name)
