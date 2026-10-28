"""模型超时的 Task 派生身份与原生资格证据。"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from formal_benchmark import prepare_execution_contract
from prepare_multiswe_task import git
from verify_qualification_evidence import verify_tree

from repropatch.task import Task


@pytest.mark.parametrize(
    "overrides",
    [None, {"max_steps": 24, "max_tool_calls": 48, "wall_seconds": 7200}],
)
def test_execution_timeout_retains_native_qualification_identity(task, tmp_path, overrides):
    source = tmp_path / "qualified"
    source.mkdir()
    raw = task.to_dict()
    raw["budget"]["model_timeout_seconds"] = 90
    original = Task.from_dict(raw, tmp_path)
    (source / "task.yaml").write_bytes(original.source_bytes)
    parent = {"status": "QUALIFIED", "task_file_sha256": "native-contract"}
    (source / "result.json").write_text(json.dumps(parent))
    (source / "manifest.json").write_text('{"fixture":true}')
    shutil.copytree(task.repository, source / "repository")
    original_bytes = {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
    result = prepare_execution_contract(source, tmp_path / "execution", 180, overrides)
    current = Task.load(result / "task.yaml")
    expected = original.to_dict()
    expected["budget"].update(overrides or {})
    expected["budget"]["model_timeout_seconds"] = 180
    assert current.to_dict() == expected
    assert all((source / name).read_bytes() == content for name, content in original_bytes.items())
    qualification = json.loads((result / "result.json").read_text())
    assert qualification["execution_budget_override"] == {
        **(overrides or {}),
        "model_timeout_seconds": 180,
    }
    assert (
        qualification["native_qualification_parent_sha256"]
        == hashlib.sha256(original_bytes["result.json"]).hexdigest()
    )
    assert qualification["task_file_sha256"] == hashlib.sha256(current.source_bytes).hexdigest()
    assert (result / "native-qualification-task.yaml").read_bytes() == original.source_bytes
    assert git(result / "repository", "rev-parse", "HEAD").decode().strip() == task.revision
    assert not verify_tree(result, json.loads((result / "manifest.json").read_text()))


def test_text_execution_contract_preserves_binary_test_resources(task, tmp_path):
    from cpp_native_adapter import text_readable_paths

    from repropatch.task import ImageIdentity, resolve_task

    binary = {
        "tests/plot.png": b"\x89PNG\r\n",
        "tests/input.bin": b"input\x00data",
        "tests/invalid.txt": b"\xff",
    }
    corpus = task.repository / "dependencies/.cache/simdjson-data/sample.json"
    corpus.parent.mkdir(parents=True)
    corpus.write_text('{"test": true}\n')
    for name, content in binary.items():
        (task.repository / name).write_bytes(content)
    git(task.repository, "add", ".")
    git(task.repository, "commit", "-qm", "固定二进制测试资源")
    raw = task.to_dict()
    raw["files"]["readable"].append("dependencies/")
    raw["tests"]["protected_paths"].append("dependencies/")
    raw["repository"]["commit"] = git(task.repository, "rev-parse", "HEAD").decode().strip()
    original = Task.from_dict(raw, tmp_path)
    directory = tmp_path / "qualified"
    directory.mkdir()
    (directory / "task.yaml").write_bytes(original.source_bytes)
    (directory / "result.json").write_text(json.dumps({"status": "QUALIFIED"}))
    (directory / "manifest.json").write_text("{}")
    readable = text_readable_paths(original.repository, original.readable_paths, original.revision)
    target = prepare_execution_contract(
        directory,
        tmp_path / "execution",
        original.budget.model_timeout_seconds,
        readable_paths=readable,
    )
    current = Task.load(target / "task.yaml")
    resolved = resolve_task(current, image_identity=ImageIdentity(current.environment.image))
    assert set(binary) <= resolved.protected_files
    assert set(binary).isdisjoint(resolved.readable_files)
    assert "dependencies/.cache/simdjson-data/sample.json" in resolved.protected_files
    assert "dependencies/.cache/simdjson-data/sample.json" not in resolved.readable_files
    assert resolved.editable_files == {"src/stats.cpp"}
    assert "tests/stats_test.cpp" in resolved.readable_files
    assert "src/" in current.readable_paths
    assert current.tests == original.tests and current.budget == original.budget
    assert (directory / "task.yaml").read_bytes() == original.source_bytes
    assert all((task.repository / name).read_bytes() == data for name, data in binary.items())
    evidence = json.loads((target / "result.json").read_text())
    assert evidence["execution_readable_policy"] == "utf8-text-v1"
    assert evidence["task_file_sha256"] == hashlib.sha256(current.source_bytes).hexdigest()
    assert not verify_tree(target, json.loads((target / "manifest.json").read_text()))


def test_native_environment_exports_exact_commit_bytes(task, tmp_path):
    from dataclasses import replace

    from prepare_mini_environment import export_commit_source

    from repropatch.workspace import git_blob, git_tree

    source = task.repository
    (source / ".gitattributes").write_text("*.bat eol=crlf\nhidden.txt export-ignore\n")
    (source / "run.bat").write_bytes(b"echo fixture\n")
    (source / "hidden.txt").write_text("committed\n")
    (source / "executable.sh").write_text("#!/bin/sh\nexit 0\n")
    (source / "executable.sh").chmod(0o755)
    git(source, "add", ".")
    git(source, "commit", "-qm", "固定导出属性")
    frozen = replace(task, revision=git(source, "rev-parse", "HEAD").decode().strip())
    (source / "run.bat").write_text("uncommitted\n")
    target = tmp_path / "export"
    export_commit_source(frozen, target)
    for entry in git_tree(source, frozen.revision):
        path = target / entry.path
        assert path.read_bytes() == git_blob(source, entry.oid)
        assert path.stat().st_mode & 0o777 == (0o755 if entry.git_mode == "100755" else 0o644)
    assert (target / "run.bat").read_bytes() == b"echo fixture\n"
    assert (target / "hidden.txt").read_text() == "committed\n"
