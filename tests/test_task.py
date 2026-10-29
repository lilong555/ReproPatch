"""核验 Task v2 的输入锁定、动态权限展开及跨进程指纹。"""

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace

import pytest
import yaml
from conftest import ROOT

from repropatch.cli import main
from repropatch.errors import ReproPatchError
from repropatch.task import Budget, ImageIdentity, Task, canonical_json, relative_file, resolve_task
from repropatch.workspace import git


def valid():
    return yaml.safe_load((ROOT / "examples/tasks/negative-maximum.v2.yaml").read_text())


def identity(task):
    return ImageIdentity(task.environment.image)


def test_v2_defaults_immutable_and_normalized(tmp_path):
    raw = valid()
    raw.pop("budget")
    task = Task.from_dict(raw, tmp_path)
    assert task.version == 2 and task.budget == Budget()
    assert task.repository == (tmp_path / "../cpp-bugs").resolve()
    assert task.commands["build"][-1] == "2"
    assert task.environment.memory_mib == 2048
    assert task.environment.tmp_executable is False
    raw["environment"]["tmp_executable"] = True
    assert Task.from_dict(raw, tmp_path).environment.tmp_executable is True
    with pytest.raises(FrozenInstanceError):
        task.budget.max_steps = 1
    with pytest.raises(FrozenInstanceError):
        task.commands.configure = ("sh",)


@pytest.mark.parametrize("value", [1, True, "2", 3])
def test_v1_and_other_versions_have_explicit_migration_error(tmp_path, value):
    with pytest.raises(ReproPatchError, match="TASK_VERSION_UNSUPPORTED.*TASK_FORMAT"):
        Task.from_dict({"version": value}, tmp_path)


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("repository", "commit", "HEAD"),
        ("repository", "commit", "a" * 12),
        ("repository", "commit", "A" * 40),
        ("repository", "url", "https://example.invalid/repo"),
        ("environment", "image", "ubuntu:24.04"),
        ("environment", "platform", "linux/arm64"),
        ("environment", "cpu_limit", float("nan")),
        ("environment", "memory_mib", True),
        ("environment", "build_tmpfs_mib", 2048),
        ("environment", "tmp_executable", "true"),
        ("environment", "tmp_executable", 1),
        ("budget", "max_tool_calls", "80"),
        ("budget", "wall_seconds", 250),
        ("commands", "build", ["sh", "-c", "echo injected"]),
        ("commands", "reproduce", ["ctest", "--test-dir", "/build", "-R", "anything"]),
        ("commands", "verify", valid()["commands"]["verify"] + ["--repeat", "until-pass:2"]),
        ("files", "editable", ["src/"]),
        ("files", "editable", ["src/*.cpp"]),
        ("files", "editable", ["../x.cpp"]),
        ("budget", "unknown", 1),
    ],
)
def test_invalid_contract_is_rejected(tmp_path, section, key, value):
    raw = valid()
    raw[section][key] = value
    with pytest.raises(ReproPatchError):
        Task.from_dict(raw, tmp_path)


@pytest.mark.parametrize("name", ["", "negative_values", "bad\nname"])
def test_fixed_tests_cannot_overlap_or_have_invalid_names(tmp_path, name):
    raw = valid()
    raw["tests"]["pass_to_pass"].append(name)
    with pytest.raises(ReproPatchError):
        Task.from_dict(raw, tmp_path)


@pytest.mark.parametrize(
    "path",
    [
        "/etc/passwd",
        "../x",
        "a/../b",
        ".git/config",
        ".repropatch/report.json",
        "a//b",
        "a\\b",
        ".",
        "a/./b",
        "a/",
        "x\x00.cpp",
        "x\n.cpp",
    ],
)
def test_path_policy(path):
    with pytest.raises(ReproPatchError):
        relative_file(path)


@pytest.mark.parametrize(
    "source,match",
    [
        ("version: 2\nversion: 2\n", "unique.*行 2 列 1"),
        ("version: 2\nbudget: {max_steps: 1, max_steps: 2}", "unique"),
        ("key: &anchor [1]\nother: *anchor", "anchor/alias"),
        ("!!python/object/apply:os.system ['false']", "解析错误"),
        ("a: " + "[" * 13 + "0" + "]" * 13, "深度"),
        ("#" + "x" * (128 * 1024), "128 KiB"),
    ],
)
def test_yaml_boundary_is_bounded_and_safe(tmp_path, source, match):
    path = tmp_path / "task.yaml"
    path.write_text(source)
    with pytest.raises(ReproPatchError, match=match):
        Task.load(path)


def test_static_validation_needs_no_repository_docker_network_or_run(tmp_path, monkeypatch, capsys):
    raw = valid()
    raw["repository"]["path"] = "missing-repository"
    path = tmp_path / "task.yaml"
    path.write_text(yaml.safe_dump(raw))

    def forbidden(*args, **kwargs):
        pytest.fail("静态校验不应启动任何进程")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert main(["validate-task", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["version"] == 2
    assert list(tmp_path.iterdir()) == [path]


def test_resolution_expands_only_commit_files_and_protects_tests(task, repository):
    (repository / "src/untracked.cpp").write_text("ignored")
    (repository / "src/stats.cpp").write_text("uncommitted")
    resolved = resolve_task(task, image_identity=identity(task))
    assert resolved.editable_files == {"src/stats.cpp"}
    assert resolved.protected_files == {"CMakeLists.txt", "tests/stats_test.cpp"}
    assert "src/stats.hpp" in resolved.readable_files
    assert "src/untracked.cpp" not in resolved.readable_files
    assert resolved.base_commit == task.revision
    assert resolved.task_source_sha256 == hashlib.sha256(task.source_bytes).hexdigest()
    assert (
        resolved.task_sha256
        == hashlib.sha256(canonical_json(resolved.execution_contract())).hexdigest()
    )


@pytest.mark.parametrize(
    "mode",
    [
        "missing",
        "protected",
        "unreadable",
        "nested-root",
        "source-root",
        "placeholder",
        "wrong-image",
        "wrong-oid-format",
    ],
)
def test_dynamic_freeze_refuses_unresolvable_inputs(task, mode):
    if mode == "missing":
        task = replace(task, readable_paths=("missing/",))
    elif mode == "protected":
        task = replace(task, editable_paths=("tests/stats_test.cpp",))
    elif mode == "unreadable":
        task = replace(task, readable_paths=("src/stats.hpp",))
    elif mode == "nested-root":
        task = replace(task, output_root=task.workspace_root / "outputs")
    elif mode == "source-root":
        task = replace(task, workspace_root=task.repository / ".workspaces")
    elif mode == "placeholder":
        task = replace(task, environment=replace(task.environment, image="sha256:" + "0" * 64))
    elif mode == "wrong-oid-format":
        task = replace(task, revision="a" * 64)
    image = ImageIdentity("sha256:" + "b" * 64) if mode == "wrong-image" else identity(task)
    with pytest.raises(ReproPatchError):
        resolve_task(task, image_identity=image)


def test_full_tag_object_is_not_a_commit(task, repository):
    git(
        repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@localhost",
        "tag",
        "-a",
        "annotated",
        "-m",
        "tag",
    )
    tag = git(repository, "rev-parse", "annotated").strip()
    with pytest.raises(ReproPatchError, match="COMMIT_TYPE_INVALID"):
        resolve_task(replace(task, revision=tag), image_identity=identity(task))


def test_symlink_in_fixed_tree_is_rejected(task, repository):
    (repository / "link").symlink_to("src/stats.cpp")
    git(repository, "add", "link")
    git(
        repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@localhost",
        "commit",
        "-m",
        "symlink",
    )
    task = replace(task, revision=git(repository, "rev-parse", "HEAD").strip())
    with pytest.raises(ReproPatchError, match="UNSUPPORTED_SOURCE_LAYOUT"):
        resolve_task(task, image_identity=identity(task))


def test_hash_ignores_locations_retain_and_yaml_but_preserves_execution_order(task, tmp_path):
    first = resolve_task(task, image_identity=identity(task))
    moved = replace(
        task,
        workspace_root=tmp_path / "another-workspace",
        output_root=tmp_path / "another-output",
        retain="always",
        source_bytes=b"different source bytes",
    )
    second = resolve_task(moved, image_identity=identity(moved))
    assert first.task_sha256 == second.task_sha256
    assert first.task_source_sha256 != second.task_source_sha256
    changed = replace(
        task, tests=replace(task.tests, pass_to_pass=tuple(reversed(task.tests.pass_to_pass)))
    )
    assert resolve_task(changed, image_identity=identity(changed)).task_sha256 != first.task_sha256
    assert (
        resolve_task(
            replace(task, budget=replace(task.budget, max_steps=11)), image_identity=identity(task)
        ).task_sha256
        != first.task_sha256
    )


def test_hash_is_identical_across_repository_directories_and_hash_seeds(task, tmp_path):
    other = tmp_path / "repo-copy"
    git(task.repository, "clone", "--no-hardlinks", str(task.repository), str(other))
    moved = replace(task, repository=other)
    assert (
        resolve_task(moved, image_identity=identity(moved)).task_sha256
        == resolve_task(task, image_identity=identity(task)).task_sha256
    )
    manifest = tmp_path / "task.yaml"
    manifest.write_text(yaml.safe_dump(task.to_dict()))
    program = (
        "import sys; from pathlib import Path; "
        "from repropatch.task import Task, ImageIdentity, resolve_task; "
        "t=Task.load(Path(sys.argv[1])); "
        "print(resolve_task(t,image_identity=ImageIdentity(t.environment.image)).task_sha256)"
    )
    values = [
        subprocess.check_output(
            [sys.executable, "-c", program, str(manifest)],
            cwd=ROOT,
            env=dict(os.environ, PYTHONHASHSEED=seed),
            text=True,
        ).strip()
        for seed in ("1", "71", "random")
    ]
    assert len(set(values)) == 1


def test_freeze_uses_loaded_bytes_after_source_yaml_is_changed(task, tmp_path):
    path = tmp_path / "task.yaml"
    path.write_text(yaml.safe_dump(task.to_dict()))
    loaded = Task.load(path)
    path.write_text("version: 1")
    resolved = resolve_task(loaded, image_identity=identity(loaded))
    assert resolved.task.version == 2
    assert resolved.task_source_sha256 == hashlib.sha256(loaded.source_bytes).hexdigest()


def test_sha256_repository_commit_is_supported(task, tmp_path):
    repository = tmp_path / "sha256-repo"
    repository.mkdir()
    git(repository, "init", "--object-format=sha256", "-b", "main")
    for name in ("CMakeLists.txt", "src/stats.cpp", "src/stats.hpp", "tests/stats_test.cpp"):
        target = repository / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((task.repository / name).read_bytes())
    git(repository, "add", ".")
    git(
        repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@localhost",
        "commit",
        "-m",
        "fixture",
    )
    commit = git(repository, "rev-parse", "HEAD").strip()
    assert len(commit) == 64
    changed = replace(task, repository=repository, revision=commit)
    assert resolve_task(changed, image_identity=identity(changed)).base_commit == commit


@pytest.mark.parametrize("content", [b"\xff", b"valid\0binary"])
def test_readable_must_be_utf8_text_from_the_commit(task, content):
    target = task.repository / "src/binary.dat"
    target.write_bytes(content)
    git(task.repository, "add", "src/binary.dat")
    git(
        task.repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@localhost",
        "commit",
        "-m",
        "binary",
    )
    changed = replace(task, revision=git(task.repository, "rev-parse", "HEAD").strip())
    with pytest.raises(ReproPatchError, match="UNSUPPORTED_TEXT_FILE"):
        resolve_task(changed, image_identity=identity(changed))


def test_binary_build_resource_is_kept_outside_readable(task):
    from repropatch.workspace import Worktree

    target = task.repository / "data/input.bin"
    target.parent.mkdir()
    target.write_bytes(b"\x00\xff\x01")
    (task.repository / "src/replacement.txt").write_bytes("有效文本\ufffd".encode())
    git(task.repository, "add", ".")
    git(
        task.repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@localhost",
        "commit",
        "-m",
        "resources",
    )
    changed = replace(task, revision=git(task.repository, "rev-parse", "HEAD").strip())
    frozen = resolve_task(changed, image_identity=identity(changed))
    assert "data/input.bin" not in frozen.readable_files
    assert "src/replacement.txt" in frozen.readable_files
    with Worktree(
        changed.repository, changed.workspace_root / "binary-resource", changed.revision
    ) as work:
        destination = changed.output_root / "binary-snapshot"
        work.export(destination)
        assert (destination / "data/input.bin").read_bytes() == b"\x00\xff\x01"


def test_repository_subdirectory_cannot_place_output_in_source(task):
    from repropatch.harness import Harness

    changed = replace(
        task, repository=task.repository / "src", output_root=task.repository / "outputs"
    )
    with pytest.raises(ReproPatchError, match="REPOSITORY_ROOT_REQUIRED"):
        Harness(changed, object())
    assert not (task.repository / "outputs").exists()


def test_invalid_utf8_git_path_is_not_replaced_with_a_different_name(task):
    path = os.fsencode(task.repository) + b"/src/invalid-\xff.cpp"
    with open(path, "wb") as stream:
        stream.write(b"int value;")
    git(task.repository, "add", ".")
    git(
        task.repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@localhost",
        "commit",
        "-m",
        "invalid path",
    )
    changed = replace(task, revision=git(task.repository, "rev-parse", "HEAD").strip())
    with pytest.raises(ReproPatchError, match="UNSUPPORTED_PATH_ENCODING"):
        resolve_task(changed, image_identity=identity(changed))


def test_bare_repository_remains_supported(task, tmp_path):
    path = tmp_path / "bare.git"
    git(task.repository, "clone", "--bare", str(task.repository), str(path))
    changed = replace(task, repository=path)
    assert (
        resolve_task(changed, image_identity=identity(changed)).task_sha256
        == resolve_task(task, image_identity=identity(task)).task_sha256
    )
