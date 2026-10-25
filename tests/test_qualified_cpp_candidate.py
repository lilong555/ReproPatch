"""Protect the independent Oracle's candidate boundary and failure evidence."""

import difflib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_qualified_cpp_candidate as oracle  # noqa: E402
from qualify_cpp_batch import CONFIGURE  # noqa: E402


def diff(path, before, after, *, header=True):
    return (f"diff --git a/{path} b/{path}\n" if header else "") + "".join(
        difflib.unified_diff([before], [after], fromfile=f"a/{path}", tofile=f"b/{path}")
    )


def test_git_parser_rejects_hidden_plain_unified_test_patch(tmp_path):
    (tmp_path / "include").mkdir()
    (tmp_path / "test").mkdir()
    (tmp_path / "include/value.h").write_text("int value = 0;\n")
    (tmp_path / "test/format-test.cc").write_text("int expected = 0;\n")
    oracle.git(tmp_path, "init", "--template=", "-q", ".")
    patch = tmp_path / "candidate.patch"
    allowed = diff("include/value.h", "int value = 0;\n", "int value = 1;\n")
    patch.write_text(allowed)
    assert oracle.candidate_paths(tmp_path, patch) == ["include/value.h"]
    patch.write_text(
        allowed
        + diff(
            "test/format-test.cc",
            "int expected = 0;\n",
            "int expected = 1;\n",
            header=False,
        )
    )
    # Git accepts this mixed format; scope validation must inspect both sections.
    oracle.git(tmp_path, "apply", "--check", str(patch))
    with pytest.raises(oracle.CandidateRejected, match="CANDIDATE_SCOPE_REJECTED"):
        oracle.candidate_paths(tmp_path, patch)


@pytest.fixture
def attempt(tmp_path, monkeypatch):
    source = tmp_path / "upstream"
    (source / "include").mkdir(parents=True)
    (source / "test").mkdir()
    (source / "include/value.h").write_text("int value = 0;\n")
    (source / "test/format-test.cc").write_text("int expected = 0;\n")
    oracle.git(source, "init", "--template=", "-q", ".")
    oracle.git(source, "add", ".")
    oracle.git(source, "commit", "-qm", "fixture")
    base = oracle.git(source, "rev-parse", "HEAD").decode().strip()
    directory = tmp_path / "qualified"
    control = directory / "control"
    control.mkdir(parents=True)
    record = {
        "instance_id": "fmtlib__fmt-999999",
        "org": "fmtlib",
        "repo": "fmt",
        "base": {"sha": base},
        "fix_patch": diff("include/value.h", "int value = 0;\n", "int value = 1;\n"),
        "test_patch": diff("test/format-test.cc", "int expected = 0;\n", "int expected = 1;\n"),
        "fix_patch_result": {"passed_tests": ["format-test", "control-test"]},
    }
    (control / "test.patch").write_text(record["test_patch"])
    (control / "reference.patch").write_text(record["fix_patch"])
    (directory / "task.yaml").write_text("fixture: true\n")
    oracle.archive(source, base, directory / "repository")
    oracle.git(directory / "repository", "init", "--template=", "-q", ".")
    oracle.git(directory / "repository", "add", ".")
    oracle.git(directory / "repository", "commit", "-qm", "prepared")
    qualification = {
        **oracle.FORMAT,
        "status": "QUALIFIED",
        "backend": "docker",
        "optimization": "O0",
        "instance_id": record["instance_id"],
        "upstream_commit": base,
        "required_tests": ["control-test", "format-test"],
        "f2p": ["format-test"],
        "p2p": ["control-test"],
        "test_patch_sha256": oracle.sha(control / "test.patch"),
        "reference_patch_sha256": oracle.sha(control / "reference.patch"),
        "image_id": "sha256:" + "a" * 64,
        "task_file_sha256": oracle.sha(directory / "task.yaml"),
        "prepared_commit": oracle.git(directory / "repository", "rev-parse", "HEAD")
        .decode()
        .strip(),
        "configure": [*CONFIGURE, "-DCMAKE_CXX_FLAGS_RELEASE=-O0 -DNDEBUG"],
    }
    oracle.save(directory / "result.json", qualification)
    monkeypatch.setattr(oracle, "records", lambda _: [record])
    args = SimpleNamespace(
        output=tmp_path / "attempt",
        qualification=directory / "result.json",
        candidate=control / "reference.patch",
        dataset=tmp_path,
        repository=source,
        timeout=60,
        build_jobs=1,
    )
    oracle.CANCELLED.clear()
    yield args, qualification
    oracle.CANCELLED.clear()


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"backend": "host", "status": "HOST_QUALIFIED"}, "UNSUPPORTED_QUALIFICATION_BACKEND"),
        ({"image_id": "ubuntu:latest"}, "IMMUTABLE_DOCKER_IMAGE_REQUIRED"),
    ],
)
def test_qualification_cannot_bypass_docker_boundary(attempt, change, reason):
    args, qualification = attempt
    qualification.update(change)
    oracle.save(args.qualification, qualification)
    result = oracle.check(args)
    assert result["accepted"] is False and result["status"] == "INFRASTRUCTURE_FAILED"
    assert result["diagnostic"] == reason
    assert (args.output / "oracle-verdict.json").is_file()


def test_missing_candidate_has_its_own_archived_status(attempt):
    args, _ = attempt
    args.candidate = args.candidate.parent / "missing.patch"
    result = oracle.check(args)
    assert result["status"] == "MISSING_CANDIDATE" and not result["accepted"]
    assert json.loads((args.output / "oracle-verdict.json").read_text())["status"] == (
        "MISSING_CANDIDATE"
    )
    assert (args.output / "manifest.json").is_file()


def fake_executor(monkeypatch, tmp_path, outcome):
    class Executor:
        def __init__(self, *_):
            self.configure = [*CONFIGURE, "-DCMAKE_CXX_FLAGS_RELEASE=-O0 -DNDEBUG"]
            self.commands = []
            self.build_root = tmp_path / "fake-build"
            self.build_root.mkdir()

        def suite(self, *_):
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr(oracle, "Executor", Executor)


@pytest.mark.parametrize(
    "error,status",
    [
        (TimeoutError("TASK_DEADLINE"), "TIMED_OUT"),
        (TimeoutError("TASK_CANCELLED"), "CANCELLED"),
        (TimeoutError("OUTPUT_LIMIT"), "OUTPUT_LIMIT_EXCEEDED"),
    ],
)
def test_deadline_cancel_and_output_limit_keep_distinct_evidence(
    attempt, monkeypatch, tmp_path, error, status
):
    args, _ = attempt
    fake_executor(monkeypatch, tmp_path, error)
    result = oracle.check(args)
    assert result["status"] == status and not result["accepted"]
    assert result["cleanup"]["status"] == "SUCCEEDED"
    assert json.loads((args.output / "oracle-verdict.json").read_text())["status"] == status
    assert (args.output / "manifest.json").is_file()


def test_cleanup_failure_cannot_report_success_or_lose_verdict(attempt, monkeypatch, tmp_path):
    args, _ = attempt
    fake_executor(
        monkeypatch,
        tmp_path,
        {"status": "PASSED", "tests": {"format-test": "passed", "control-test": "passed"}},
    )
    remove = oracle.shutil.rmtree

    def fail_build_cleanup(path, *args, **kwargs):
        if path == tmp_path / "fake-build":
            raise PermissionError("controlled cleanup failure")
        return remove(path, *args, **kwargs)

    monkeypatch.setattr(oracle.shutil, "rmtree", fail_build_cleanup)
    result = oracle.check(args)
    assert result["status"] == "CLEANUP_FAILED" and not result["accepted"]
    assert result["oracle_passed_before_cleanup"] is True
    assert result["cleanup"]["status"] == "FAILED"
    assert json.loads((args.output / "oracle-verdict.json").read_text())["status"] == (
        "CLEANUP_FAILED"
    )


def test_manifest_failure_is_explicit_in_verdict(attempt, monkeypatch, tmp_path):
    args, _ = attempt
    fake_executor(
        monkeypatch,
        tmp_path,
        {"status": "PASSED", "tests": {"format-test": "passed", "control-test": "passed"}},
    )
    save = oracle.save

    def fail_manifest(path, value):
        if path.name == "manifest.json":
            raise OSError("controlled archive failure")
        save(path, value)

    monkeypatch.setattr(oracle, "save", fail_manifest)
    result = oracle.check(args)
    assert result["status"] == "ARCHIVE_FAILED" and not result["accepted"]
    assert json.loads((args.output / "oracle-verdict.json").read_text())["status"] == (
        "ARCHIVE_FAILED"
    )
