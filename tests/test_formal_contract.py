"""模型超时的 Task 派生身份与原生资格证据。"""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from formal_benchmark import prepare_execution_contract
from verify_qualification_evidence import verify_tree

from repropatch.task import Task


def test_execution_timeout_retains_native_qualification_identity(task, tmp_path):
    source = tmp_path / "qualified"
    source.mkdir()
    raw = task.to_dict()
    raw["budget"]["model_timeout_seconds"] = 90
    original = Task.from_dict(raw, tmp_path)
    (source / "task.yaml").write_bytes(original.source_bytes)
    parent = {"status": "QUALIFIED", "task_file_sha256": "native-contract"}
    (source / "result.json").write_text(json.dumps(parent))
    (source / "manifest.json").write_text('{"fixture":true}')
    original_bytes = {p.name: p.read_bytes() for p in source.iterdir()}
    result = prepare_execution_contract(source, tmp_path / "execution", 180)
    current = Task.load(result / "task.yaml")
    expected = original.to_dict()
    expected["budget"]["model_timeout_seconds"] = 180
    assert current.to_dict() == expected
    assert all((source / name).read_bytes() == content for name, content in original_bytes.items())
    qualification = json.loads((result / "result.json").read_text())
    assert (
        qualification["native_qualification_parent_sha256"]
        == hashlib.sha256(original_bytes["result.json"]).hexdigest()
    )
    assert qualification["task_file_sha256"] == hashlib.sha256(current.source_bytes).hexdigest()
    assert (result / "native-qualification-task.yaml").read_bytes() == original.source_bytes
    assert not verify_tree(result, json.loads((result / "manifest.json").read_text()))
