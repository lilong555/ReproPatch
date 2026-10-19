import os

import pytest

from repropatch.errors import PolicyError
from repropatch.tools import Toolbox
from repropatch.workspace import Worktree, copy_patch, git


def test_worktree_isolation_export_and_cleanup(repository, tmp_path):
    original = (repository / "src/stats.cpp").read_text()
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        (work.path / "src/stats.cpp").write_text(
            original.replace("int best = 0;", "int best = -1;")
        )
        first = work.export(tmp_path / "export1")
        second = work.export(tmp_path / "export2")
        assert first == second
        assert not (tmp_path / "export1/.git").exists()
        assert (repository / "src/stats.cpp").read_text() == original
        assert work.changes() == ["src/stats.cpp"]
    assert not (tmp_path / "work").exists()
    assert len(git(repository, "worktree", "list", "--porcelain").split("worktree ")) == 2


def test_tools_and_edit_policy(repository, tmp_path):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        tools = Toolbox(work, ("src/stats.cpp",), lambda name: [])
        assert "int best = 0;" in tools.invoke("read_file", {"path": "src/stats.cpp"})["content"]
        assert tools.invoke("search_code", {"query": "maximum_sample"})["matches"]
        for name, args in [
            ("read_file", {"path": "../repo/src/stats.cpp"}),
            ("read_file", {"path": ".git"}),
            ("read_file", {"path": "src/stats.cpp", "extra": "x"}),
            ("run_command", {"name": "sh -c rm -rf /"}),
            ("edit_file", {"path": "tests/stats_test.cpp", "old": "return 1;", "new": "return 0;"}),
            ("edit_file", {"path": "src/stats.cpp", "old": "missing", "new": "x"}),
            ("shell", {"command": "pwd"}),
        ]:
            with pytest.raises(PolicyError):
                tools.invoke(name, args)
        assert tools.invoke(
            "edit_file",
            {"path": "src/stats.cpp", "old": "int best = 0;", "new": "int best = samples.front();"},
        )["changed"]


def test_symlink_export_rejected(repository, tmp_path):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        file = work.path / "src/stats.cpp"
        file.unlink()
        file.symlink_to("/etc/passwd")
        with pytest.raises(PolicyError, match="Symlink"):
            work.export(tmp_path / "export")


def test_hardlink_export_rejected(repository, tmp_path):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        os.link(work.path / "src/stats.cpp", tmp_path / "hardlink")
        with pytest.raises(PolicyError, match="hard links"):
            work.export(tmp_path / "export")


def test_protected_patch_rejected(repository, tmp_path):
    with (
        Worktree(repository, tmp_path / "a", "HEAD") as a,
        Worktree(repository, tmp_path / "b", "HEAD") as b,
    ):
        (a.path / "CMakeLists.txt").write_text("# weakened build")
        with pytest.raises(PolicyError, match="protected"):
            copy_patch(a, b, ("src/stats.cpp",))


def test_untracked_and_binary_rejected(repository, tmp_path):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        (work.path / "new.cpp").write_text("data")
        with pytest.raises(PolicyError, match="tracked"):
            work.safe_path("new.cpp")
        (work.path / "src/stats.cpp").write_bytes(b"\xff\x00")
        with pytest.raises(PolicyError, match="UTF-8"):
            Toolbox(work, (), None).read_file("src/stats.cpp")
