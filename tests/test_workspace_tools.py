import os

import pytest

from repropatch.errors import PolicyError, SourceChanged
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
        assert "int best = 0;" in tools.read_file("src/stats.cpp")["text"]
        assert tools.search_code("maximum_sample")["matches"]
        found = tools.search_code("maximum_sample", path="src/stats.cpp", context_lines=2)
        hit = found["matches"][0]
        assert hit["editable"] and hit["context"]["start_line"] <= hit["line"]
        lines = tools.read_file("src/stats.cpp")["text"].splitlines()
        window = hit["context"]
        assert window["text"] == "\n".join(lines[window["start_line"] - 1 : window["end_line"]])
        assert "context" not in tools.search_code("maximum_sample", context_lines=0)["matches"][0]
        for callback in (
            lambda: tools.read_file("../repo/src/stats.cpp"),
            lambda: tools.read_file(".git"),
            lambda: tools.run_command("sh -c rm -rf /"),
            lambda: tools.edit_file("tests/stats_test.cpp", "return 1;", "return 0;"),
            lambda: tools.edit_file("src/stats.cpp", "missing", "x"),
            lambda: tools.search_code("maximum_sample", context_lines=True),
            lambda: tools.search_code("maximum_sample", context_lines=21),
        ):
            with pytest.raises(PolicyError):
                callback()
        result = tools.edit_file("src/stats.cpp", "int best = 0;", "int best = samples.front();")
        assert result["before_sha256"] != result["after_sha256"]


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
        with pytest.raises(SourceChanged, match="SOURCE_CHANGED"):
            Toolbox(work, (), None).read_file("src/stats.cpp")


def test_structured_tools_obey_resolved_readable_set(repository, tmp_path):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        tools = Toolbox(work, ("src/stats.cpp",), lambda name: [], readable={"src/stats.cpp"})
        with pytest.raises(PolicyError, match="readable"):
            tools.read_file("tests/stats_test.cpp")
        assert all(
            match["path"] == "src/stats.cpp"
            for match in tools.search_code("maximum_sample")["matches"]
        )


def test_line_ranges_and_directory_scope_are_bounded(repository, tmp_path):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        tools = Toolbox(
            work, ("src/stats.cpp",), lambda name: [], readable={"src/stats.cpp", "src/stats.hpp"}
        )
        preview = tools.read_file("src/stats.cpp", start_line=2, max_lines=2)
        assert preview["start_line"] == 2 and preview["end_line"] == 3 and preview["truncated"]
        assert len(preview["text"].splitlines()) == 2
        assert tools.list_directory()["entries"] == [{"name": "src", "type": "directory"}]
        with pytest.raises(PolicyError):
            tools.read_file("src/stats.cpp", True, 2)
        with pytest.raises(PolicyError):
            tools.search_code("x" * 1025)
        with pytest.raises(PolicyError):
            tools.list_directory("../")


def test_git_tools_use_phase_deadline_without_leaking_to_cleanup(repository, monkeypatch):
    import time

    from repropatch.errors import OperationDeadline
    from repropatch.process import RawResult
    from repropatch.workspace import git_deadline, git_result

    timeouts = []

    def execute(argv, **kwargs):
        timeouts.append(kwargs["timeout"])
        return RawResult(tuple(argv), 0, b"", b"", 0)

    monkeypatch.setattr("repropatch.workspace.run_process_bytes", execute)
    with git_deadline(time.monotonic() + 0.25):
        git_result(repository, "status")
    git_result(repository, "status")
    assert 0 < timeouts[0] <= 0.25 and timeouts[1] == 60
    with git_deadline(time.monotonic() - 1), pytest.raises(OperationDeadline):
        git_result(repository, "status")
    assert len(timeouts) == 2
