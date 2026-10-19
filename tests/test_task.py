import math

import pytest
import yaml
from conftest import ROOT

from repropatch.errors import ReproPatchError
from repropatch.task import Task, relative_file


def valid():
    return yaml.safe_load((ROOT / "examples/tasks/negative-maximum.yaml").read_text())


def test_task_resolves_repository_relative_to_manifest():
    task = Task.load(ROOT / "examples/tasks/negative-maximum.yaml")
    assert task.repository == ROOT / "examples/cpp-bugs"
    assert task.commands["build"][-1] == "2"


@pytest.mark.parametrize(
    "key,value",
    [
        ("version", 2),
        ("version", True),
        ("id", "../../x"),
        ("repository", None),
        ("commands", {"configure": "cmake -S ."}),
        ("max_steps", True),
        ("max_steps", 101),
        ("timeout_seconds", math.nan),
        ("timeout_seconds", 0),
        ("failure_exit_code", 0),
        ("editable_paths", ["CMakeLists.txt"]),
        ("editable_paths", ["../x.cpp"]),
        ("revision", "--exec=evil"),
        ("prompt", ""),
        ("typo", "unknown"),
    ],
)
def test_invalid_task_rejected(tmp_path, key, value):
    raw = valid()
    raw[key] = value
    with pytest.raises(ReproPatchError):
        Task.from_dict(raw, tmp_path)


@pytest.mark.parametrize(
    "path",
    [
        "/etc/passwd",
        "../x",
        "a/../b",
        ".git/config",
        "a//b",
        "a\\b",
        ".",
        "a/./b",
        "a/",
        "x\x00.cpp",
    ],
)
def test_path_policy(path):
    with pytest.raises(ReproPatchError):
        relative_file(path)


def test_yaml_duplicate_keys_rejected(tmp_path):
    path = tmp_path / "duplicate.yaml"
    path.write_text("version: 1\nversion: 1\n")
    with pytest.raises(ReproPatchError, match="unique"):
        Task.load(path)


def test_unsafe_yaml_constructor_rejected(tmp_path):
    path = tmp_path / "unsafe.yaml"
    path.write_text("!!python/object/apply:os.system ['touch /tmp/should-not-exist']")
    with pytest.raises(ReproPatchError):
        Task.load(path)


def test_shell_command_not_allowed(tmp_path):
    raw = valid()
    raw["commands"]["build"] = ["sh", "-c", "echo injected"]
    with pytest.raises(ReproPatchError):
        Task.from_dict(raw, tmp_path)


def test_non_string_editable_path_is_a_clean_policy_error(tmp_path):
    raw = valid()
    raw["editable_paths"] = [{"path": "src/stats.cpp"}]
    with pytest.raises(ReproPatchError):
        Task.from_dict(raw, tmp_path)
