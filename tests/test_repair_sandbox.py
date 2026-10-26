"""持久修复容器的挂载契约与完整源码同步。"""

import os

import pytest

from repropatch.errors import PatchRejected, ReproPatchError
from repropatch.harness import Harness
from repropatch.repair_sandbox import PersistentRepairSandbox
from repropatch.resources import RunResources
from repropatch.workspace import MAX_EDIT_FILE, Worktree, apply_candidate, git


def test_shell_mounts_only_make_declared_files_writable(repository, tmp_path):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        source = tmp_path / "source"
        work.export(source)
        sandbox = PersistentRepairSandbox(source, "repropatch-cpp:0.1", editable=("src/stats.cpp",))
        assert sandbox.bind_mounts() == {
            "/src": (str(source), False),
            "/src/src/stats.cpp": (str(source / "src/stats.cpp"), True),
        }
        args = sandbox.create_argv()
        assert args.count("--mount") == 2
        assert "--read-only" in args and "--network=none" in args
        assert "--cap-drop=ALL" in args and "--user=65534:65534" in args
        assert "--security-opt=no-new-privileges:true" in args
        assert any(arg.startswith("--tmpfs=/build:rw,exec,") for arg in args)
        assert not (source / ".git").exists()
        assert sandbox.ownership()["kind"] == "repair"


@pytest.mark.parametrize("name", ["../src/stats.cpp", "/etc/passwd", "src/not-present.cpp"])
def test_shell_mount_rejects_invalid_source_paths(repository, name):
    with pytest.raises((ReproPatchError, OSError)):
        PersistentRepairSandbox(repository, "repropatch-cpp:0.1", editable=(name,))


def test_snapshot_import_preserves_source_and_roundtrip(repository, tmp_path):
    original = (repository / "src/stats.cpp").read_bytes()
    source_bytes = b"\xef\xbb\xbf" + original.replace(b"\n", b"\r\n").rstrip(b"\r\n")
    (repository / "src/stats.cpp").write_bytes(source_bytes)
    git(repository, "add", ".")
    git(
        repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@localhost",
        "commit",
        "-m",
        "bytes",
    )
    original_index = (repository / ".git/index").read_bytes()
    with (
        Worktree(repository, tmp_path / "work", "HEAD") as work,
        Worktree(repository, tmp_path / "verification", "HEAD") as target,
    ):
        source = tmp_path / "source"
        work.export(source)
        expected = source_bytes.replace(b"int best = 0;", b"int best = samples.front();")
        (source / "src/stats.cpp").write_bytes(expected)
        before = (work.path / "src/stats.cpp").stat()
        manifest, changed = work.import_snapshot(source, {"src/stats.cpp"})
        assert changed == ("src/stats.cpp",)
        assert manifest == work.assert_current()
        after = (work.path / "src/stats.cpp").stat()
        assert (after.st_mode, after.st_uid, after.st_gid) == (
            before.st_mode,
            before.st_uid,
            before.st_gid,
        )
        candidate = work.freeze_candidate(tmp_path / "evidence", {"src/stats.cpp"})
        apply_candidate(
            target, candidate, tmp_path / "evidence", work.initial_manifest, {"src/stats.cpp"}
        )
        assert (target.path / "src/stats.cpp").read_bytes() == expected
        assert work.import_snapshot(source, {"src/stats.cpp"})[1] == ()
    assert (repository / "src/stats.cpp").read_bytes() == source_bytes
    assert (repository / ".git/index").read_bytes() == original_index


@pytest.mark.parametrize(
    "violation",
    ["protected", "new", "deleted", "mode", "binary", "utf8", "size", "symlink", "empty-dir"],
)
def test_snapshot_import_checks_entire_tree_before_any_write(repository, tmp_path, violation):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        source = tmp_path / "source"
        work.export(source)
        editable = source / "src/stats.cpp"
        editable.write_bytes(editable.read_bytes().replace(b"int best = 0;", b"int best = -1;"))
        if violation == "protected":
            (source / "tests/stats_test.cpp").write_text("int main() {}")
        elif violation == "new":
            (source / "new.cpp").write_text("int extra;")
        elif violation == "deleted":
            editable.unlink()
        elif violation == "mode":
            editable.chmod(0o755)
        elif violation == "binary":
            editable.write_bytes(b"\x00")
        elif violation == "utf8":
            editable.write_bytes(b"\xff")
        elif violation == "size":
            editable.write_bytes(b"x" * (MAX_EDIT_FILE + 1))
        elif violation == "symlink":
            editable.unlink()
            editable.symlink_to(repository / "src/stats.cpp")
        else:
            (source / "extra").mkdir()
        with pytest.raises(PatchRejected, match="FORBIDDEN_PATCH"):
            work.import_snapshot(source, {"src/stats.cpp"})
        assert work.assert_current() == work.initial_manifest and work.diff_bytes() == b""


def test_snapshot_can_fill_existing_empty_file(repository, tmp_path):
    (repository / "src/empty.cpp").write_bytes(b"")
    git(repository, "add", ".")
    git(
        repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@localhost",
        "commit",
        "-m",
        "empty",
    )
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        source = tmp_path / "source"
        work.export(source)
        (source / "src/empty.cpp").write_bytes(b"int value;\n")
        work.import_snapshot(source, {"src/empty.cpp"})
        assert work.read_file("src/empty.cpp")[0] == b"int value;\n"
        (source / "src/empty.cpp").write_bytes(b"")
        work.import_snapshot(source, {"src/empty.cpp"})
        assert work.assert_current() == work.initial_manifest


def test_only_registered_frozen_repair_container_may_cross_model_boundary(repository, tmp_path):
    resources = RunResources(
        tmp_path / "runs", tmp_path / "workspaces", "a" * 32, repository, "HEAD"
    )
    try:
        resources.containers["repair"] = {
            "kind": "repair",
            "active": True,
            "paused": True,
            "profile_verified": True,
            "cleanup_confirmed": False,
            "cleanup_error": None,
        }
        assert resources.agent_containers_ready("repair")
        assert not resources.agent_containers_ready()
        assert not resources.containers_clean
        for key, value in (
            ("kind", "evaluation"),
            ("active", False),
            ("paused", False),
            ("profile_verified", False),
            ("cleanup_error", "unconfirmed"),
        ):
            previous = resources.containers["repair"][key]
            resources.containers["repair"][key] = value
            assert not resources.agent_containers_ready("repair")
            resources.containers["repair"][key] = previous
    finally:
        resources.close()


def test_shell_mode_requires_model_and_known_configuration(task, tmp_path):
    with pytest.raises(ReproPatchError, match="TOOL_MODE"):
        Harness(task, object(), tool_mode="shell-fast-feedback")
    with pytest.raises(ReproPatchError, match="TOOL_MODE"):
        Harness(task, patch_file=tmp_path / "patch", tool_mode="shell-only")
    with pytest.raises(ReproPatchError):
        PersistentRepairSandbox(
            task.repository, "repropatch-cpp:0.1", editable=("src/stats.cpp\n",)
        )
    assert os.getuid() != 65534
