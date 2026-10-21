"""使用真实 Git 验证源码清单、字节往返和受控编辑。"""

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import SimulatedSandbox

from repropatch.errors import InfrastructureError, PatchRejected, PolicyError, SourceChanged
from repropatch.harness import Harness
from repropatch.task import canonical_json, resolve_task
from repropatch.tools import Toolbox
from repropatch.workspace import (
    MAX_EDIT_FILE,
    MAX_SOURCE_FILE,
    EvidenceRef,
    Worktree,
    apply_candidate,
    git,
    source_manifest,
)


def commit(repo):
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-m", "fixture")
    return git(repo, "rev-parse", "HEAD").strip()


def index_bytes(repo):
    return (repo / ".git/index").read_bytes()


def test_manifest_and_snapshot_cover_exact_bytes_modes_and_unicode(repository, tmp_path):
    (repository / "src/名字.cpp").write_bytes(b"// unicode\n")
    (repository / "input.bin").write_bytes(b"\x00\xff\r\n")
    (repository / "empty.txt").write_bytes(b"")
    (repository / "src/stats.cpp").chmod(0o755)
    revision = commit(repository)
    with Worktree(repository, tmp_path / "work", revision) as work:
        expected = {"schema_version": 1, "files": []}
        for name in sorted(work.files()):
            path = work.path / name
            content = path.read_bytes()
            expected["files"].append(
                {
                    "path": name,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "size_bytes": len(content),
                    "git_mode": "100755" if path.stat().st_mode & 0o100 else "100644",
                }
            )
        raw = json.dumps(
            expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        assert work.initial_manifest.to_dict() == expected
        assert work.initial_manifest.sha256 == hashlib.sha256(raw).hexdigest()
        snapshot = tmp_path / "snapshot"
        assert work.export(snapshot) == work.initial_manifest.sha256
        assert source_manifest(snapshot) == work.initial_manifest
        assert (snapshot / "input.bin").read_bytes() == b"\x00\xff\r\n"
        assert not (snapshot / ".git").exists()
        assert (snapshot / "src/stats.cpp").stat().st_mode & 0o777 == 0o755
        assert (snapshot / "input.bin").stat().st_mode & 0o777 == 0o644
        assert all(
            Path(directory).stat().st_mode & 0o777 == 0o755 for directory, _, _ in os.walk(snapshot)
        )


@pytest.mark.parametrize("variant", ["lf", "crlf", "bom", "no-eof", "bom-crlf-no-eof"])
def test_patch_roundtrips_without_changing_text_representation(repository, tmp_path, variant):
    path = repository / "src/stats.cpp"
    original = path.read_bytes()
    if "crlf" in variant:
        original = original.replace(b"\n", b"\r\n")
    if "bom" in variant:
        original = b"\xef\xbb\xbf" + original
    if "no-eof" in variant:
        original = original.rstrip(b"\r\n")
    path.write_bytes(original)
    path.chmod(0o755)
    revision = commit(repository)
    original_index = index_bytes(repository)
    with (
        Worktree(repository, tmp_path / "a", revision) as a,
        Worktree(repository, tmp_path / "b", revision) as b,
    ):
        tools = Toolbox(a, ("src/stats.cpp",), lambda name: [])
        info = (a.path / "src/stats.cpp").stat()
        tools.edit_file("src/stats.cpp", "int best = 0;", "int best = samples.front();")
        expected = original.replace(b"int best = 0;", b"int best = samples.front();")
        assert (a.path / "src/stats.cpp").read_bytes() == expected
        after = (a.path / "src/stats.cpp").stat()
        assert (after.st_mode, after.st_uid, after.st_gid) == (
            info.st_mode,
            info.st_uid,
            info.st_gid,
        )
        root = tmp_path / "evidence"
        candidate = a.freeze_candidate(
            root, {"src/stats.cpp"}, {"tests/stats_test.cpp", "CMakeLists.txt"}
        )
        manifest = apply_candidate(b, candidate, root, a.initial_manifest, {"src/stats.cpp"})
        assert b.manifest() == a.manifest() == manifest
        assert (b.path / "src/stats.cpp").read_bytes() == expected
        assert b.diff_bytes() == (root / "patch.diff").read_bytes() == a.diff_bytes()
        assert candidate.changed_files == ("src/stats.cpp",)
        assert candidate.manifest.sha256 != candidate.source_tree_sha256
        assert (root / "patch.diff").stat().st_mode & 0o777 == 0o600
    assert path.read_bytes() == original and index_bytes(repository) == original_index


def test_git_attributes_cannot_silently_normalize_candidate_bytes(repository, tmp_path):
    (repository / ".gitattributes").write_text("src/stats.cpp text eol=lf\n")
    revision = commit(repository)
    with (
        Worktree(repository, tmp_path / "a", revision) as a,
        Worktree(repository, tmp_path / "b", revision) as b,
    ):
        original = (a.path / "src/stats.cpp").read_bytes().decode()
        desired = original.replace("int best = 0;", "int best = samples.front();").replace(
            "\n", "\r\n"
        )
        a.edit_text("src/stats.cpp", original, desired)
        candidate = a.freeze_candidate(tmp_path / "evidence", {"src/stats.cpp"})
        with pytest.raises(PatchRejected, match="PATCH_ROUNDTRIP_MISMATCH"):
            apply_candidate(
                b, candidate, tmp_path / "evidence", a.initial_manifest, {"src/stats.cpp"}
            )
        assert (a.path / "src/stats.cpp").read_bytes() == desired.encode()


@pytest.mark.parametrize(
    "kind", ["new", "ignored", "deleted", "mode", "protected", "symlink", "fifo", "empty-dir"]
)
def test_unsupported_candidate_changes_are_rejected(repository, tmp_path, kind):
    if kind == "ignored":
        (repository / ".gitignore").write_text("extra.cpp\n")
        commit(repository)
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        path = work.path / "src/stats.cpp"
        if kind in {"new", "ignored"}:
            (work.path / "extra.cpp").write_text("extra")
        elif kind == "deleted":
            path.unlink()
        elif kind == "mode":
            path.chmod(0o755)
        elif kind == "protected":
            (work.path / "tests/stats_test.cpp").write_text("weakened")
        elif kind == "symlink":
            path.unlink()
            path.symlink_to(repository / "src/stats.cpp")
        elif kind == "fifo":
            os.mkfifo(work.path / "extra.fifo")
        elif kind == "empty-dir":
            (work.path / "extra-directory").mkdir()
            path.write_bytes(path.read_bytes().replace(b"int best = 0;", b"int best = -1;"))
        with pytest.raises(PatchRejected, match="FORBIDDEN_PATCH"):
            work.freeze_candidate(tmp_path / "evidence", {"src/stats.cpp"})


@pytest.mark.parametrize("artifact", ["patch", "manifest"])
def test_corrupt_evidence_is_error_before_applying_patch(repository, tmp_path, artifact):
    with (
        Worktree(repository, tmp_path / "a", "HEAD") as a,
        Worktree(repository, tmp_path / "b", "HEAD") as b,
    ):
        a.edit_text("src/stats.cpp", "int best = 0;", "int best = samples.front();")
        root = tmp_path / "evidence"
        candidate = a.freeze_candidate(root, {"src/stats.cpp"})
        (root / getattr(candidate, artifact).path).write_bytes(b"corrupt")
        with pytest.raises(InfrastructureError, match="ARTIFACT_CORRUPT"):
            apply_candidate(b, candidate, root, a.initial_manifest, {"src/stats.cpp"})
        assert b.manifest() == b.initial_manifest


def test_evidence_reference_rejects_symlink_and_escape(tmp_path):
    root = tmp_path / "actual"
    root.mkdir()
    reference = EvidenceRef.save(root, "data.bin", b"safe")
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(InfrastructureError, match="ARTIFACT_CORRUPT"):
        reference.read(alias, limit=1024)
    with pytest.raises(InfrastructureError, match="ARTIFACT_CORRUPT"):
        replace(reference, path="../actual/data.bin").read(root, limit=1024)


@pytest.mark.parametrize(
    "key",
    [
        "include.path",
        "filter.evil.process",
        "core.fsmonitor",
        "core.hooksPath",
        "diff.external",
        "diff.evil.textconv",
        "extensions.worktreeConfig",
        "remote.origin.promisor",
    ],
)
def test_unsafe_git_config_never_executes_external_programs(repository, tmp_path, key):
    marker = tmp_path / "must-not-run"
    script = tmp_path / "external.sh"
    script.write_text(f"#!/bin/sh\ntouch '{marker}'\n")
    script.chmod(0o755)
    value = (
        "true" if key in {"extensions.worktreeConfig", "remote.origin.promisor"} else str(script)
    )
    if key == "include.path":
        script.write_text(f"[core]\nfsmonitor = {script}\n")
    git(repository, "config", "--local", key, value)
    original_index = index_bytes(repository)
    original_config = (repository / ".git/config").read_bytes()
    with pytest.raises(PolicyError, match="UNSAFE_GIT_CONFIG"):
        with Worktree(repository, tmp_path / "work", "HEAD"):
            pytest.fail("不应创建工作树")
    assert not marker.exists() and not (tmp_path / "work").exists()
    assert index_bytes(repository) == original_index
    assert (repository / ".git/config").read_bytes() == original_config


def test_attribute_audit_reads_fixed_commit_and_keeps_original_index(repository, tmp_path):
    (repository / ".gitattributes").write_text("[attr]custom filter=missing\nsrc/*.cpp custom\n")
    revision = commit(repository)
    (repository / ".gitattributes").write_text("# uncommitted hiding attempt\n")
    original_index = index_bytes(repository)
    with pytest.raises(PolicyError, match="UNSUPPORTED_GIT_FILTER"):
        with Worktree(repository, tmp_path / "work", revision):
            pytest.fail("不应检出依赖 filter 的源码")
    assert index_bytes(repository) == original_index
    assert (repository / ".gitattributes").read_text() == "# uncommitted hiding attempt\n"


@pytest.mark.sdk
def test_external_change_during_tool_is_infrastructure_failure(task, tmp_path):
    from agents.testing import ModelStep, ScriptedModel, function_call

    def tamper(call):
        work = next(task.workspace_root.glob("*/repair"))
        (work / "tests/stats_test.cpp").write_text("unexpected external change")
        return ModelStep(
            output=[
                function_call(
                    "edit_file",
                    {
                        "path": "src/stats.cpp",
                        "old": "int best = 0;",
                        "new": "int best = samples.front();",
                    },
                    call_id="tamper",
                )
            ]
        )

    report = Harness(
        task,
        ScriptedModel([ModelStep(responder=tamper)]),
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
    ).run()
    assert report["status"] == "error" and "SOURCE_CHANGED" in report["error"]
    assert (
        not report["verified"] and report["candidate"] is None and len(report["evaluations"]) == 1
    )


@pytest.mark.sdk
@pytest.mark.parametrize("mutation", ["contents", "empty-directory"])
def test_modified_snapshot_is_not_successful_evidence(task, model, tmp_path, mutation):
    class ModifiedSnapshot(SimulatedSandbox):
        def __enter__(self):
            if mutation == "contents":
                (self.source / "src/stats.cpp").write_text("modified snapshot")
            else:
                (self.source / "untracked-directory").mkdir()
            return self

    report = Harness(task, model, tmp_path / "runs", sandbox_factory=ModifiedSnapshot).run()
    assert report["status"] == "error" and "SOURCE_CHANGED" in report["error"]
    assert not report["verified"] and report["model_steps"] == 0


def test_preview_and_edit_use_separate_byte_limits(repository, tmp_path):
    raw = b"// " + b"x" * 100_000 + b"\nint unique = 0;\n"
    (repository / "src/stats.cpp").write_bytes(raw)
    revision = commit(repository)
    with Worktree(repository, tmp_path / "work", revision) as work:
        tools = Toolbox(work, ("src/stats.cpp",), lambda name: [])
        preview = tools.read_file("src/stats.cpp")
        assert preview["truncated"] and len(canonical_json(preview)) <= 64 * 1024
        assert tools.edit_file("src/stats.cpp", "int unique = 0;", "int unique = 1;")[
            "after_sha256"
        ]
        assert (work.path / "src/stats.cpp").read_bytes() == raw.replace(
            b"unique = 0", b"unique = 1"
        )
        with pytest.raises(PolicyError, match="EDIT_FILE_TOO_LARGE"):
            tools.edit_file("src/stats.cpp", "int unique = 1;", "x" * MAX_EDIT_FILE)
        work.assert_current()


def test_tree_byte_limit_is_checked_before_checkout(task):
    large = task.repository / "data0.bin"
    large.write_bytes(b"x" * MAX_SOURCE_FILE)
    for number in range(1, 17):
        os.link(large, task.repository / f"data{number}.bin")
    changed = replace(task, revision=commit(task.repository))
    with pytest.raises(PolicyError, match="SOURCE_TREE_TOO_LARGE"):
        resolve_task(changed)
    assert not changed.workspace_root.exists()


def test_cleanup_refuses_replaced_root_and_preserves_other_tree(repository, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    sentinel = other / "keep"
    sentinel.write_text("untouched")
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        saved = tmp_path / "saved"
        work.path.rename(saved)
        work.path.symlink_to(other, target_is_directory=True)
        try:
            with pytest.raises(SourceChanged):
                work.close()
            assert sentinel.read_text() == "untouched"
        finally:
            work.path.unlink()
            saved.rename(work.path)


def test_patch_size_limit_rejects_instead_of_freezing_a_truncated_diff(repository, tmp_path):
    raw = b"//" + b"x" * (MAX_EDIT_FILE - 3) + b"\n"
    (repository / "bulk").mkdir()
    for number in range(8):
        (repository / f"bulk/file{number}.cpp").write_bytes(raw)
    revision = commit(repository)
    names = {f"bulk/file{number}.cpp" for number in range(8)}
    with Worktree(repository, tmp_path / "work", revision) as work:
        for name in sorted(names):
            work.edit_text(name, raw.decode(), raw.replace(b"x", b"y").decode())
        with pytest.raises(PatchRejected, match="PATCH_TOO_LARGE"):
            work.freeze_candidate(tmp_path / "evidence", names)
        assert not (tmp_path / "evidence/patch.diff").exists()


def test_atomic_edit_does_not_follow_directory_swap_to_another_tree(
    repository, tmp_path, monkeypatch
):
    import repropatch.workspace

    other = tmp_path / "other"
    other.mkdir()
    sentinel = other / "stats.cpp"
    sentinel.write_bytes(b"foreign contents")
    saved = tmp_path / "saved-source"
    actual_replace = os.replace
    with Worktree(repository, tmp_path / "work", "HEAD") as work:

        def swap_parent(source, target, **kwargs):
            if "dst_dir_fd" in kwargs:
                content = (work.path / "src" / source).read_bytes()
                (other / source).write_bytes(content)
                (work.path / "src").rename(saved)
                (work.path / "src").symlink_to(other, target_is_directory=True)
            return actual_replace(source, target, **kwargs)

        monkeypatch.setattr(repropatch.workspace.os, "replace", swap_parent)
        try:
            with pytest.raises(SourceChanged):
                work.edit_text("src/stats.cpp", "int best = 0;", "int best = samples.front();")
            assert sentinel.read_bytes() == b"foreign contents"
        finally:
            if (work.path / "src").is_symlink():
                (work.path / "src").unlink()
                saved.rename(work.path / "src")


def test_snapshot_copy_does_not_follow_swapped_directory(repository, tmp_path, monkeypatch):
    import repropatch.workspace

    other = tmp_path / "other"
    other.mkdir()
    sentinel = other / "stats.cpp"
    sentinel.write_bytes(b"foreign contents")
    snapshot = tmp_path / "snapshot"
    saved = tmp_path / "saved-snapshot"
    actual_open = os.open
    swapped = False
    with Worktree(repository, tmp_path / "work", "HEAD") as work:

        def swap_directory(path, flags, *args, **kwargs):
            nonlocal swapped
            if path == "stats.cpp" and flags & os.O_CREAT and not swapped:
                (snapshot / "src").rename(saved)
                (snapshot / "src").symlink_to(other, target_is_directory=True)
                swapped = True
            return actual_open(path, flags, *args, **kwargs)

        monkeypatch.setattr(repropatch.workspace.os, "open", swap_directory)
        try:
            with pytest.raises(SourceChanged):
                work.export(snapshot)
            assert swapped and sentinel.read_bytes() == b"foreign contents"
        finally:
            if (snapshot / "src").is_symlink():
                (snapshot / "src").unlink()
                saved.rename(snapshot / "src")
