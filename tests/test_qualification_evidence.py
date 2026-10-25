"""Publication must fail closed for truncated evidence and retain cancellations."""

import importlib.util
import json
from pathlib import Path

import pytest


def test_summary_requires_verified_bytes_and_never_overwrites_originals(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts/verify_qualification_evidence.py"
    spec = importlib.util.spec_from_file_location("evidence_audit", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    batch = tmp_path / "batch"
    rows = []
    for name in ("recoverable", "incomplete", "status-mismatch"):
        directory = batch / name
        directory.mkdir(parents=True)
        row = {
            "instance_id": name,
            "status": "HOST_QUALIFIED",
            "backend": "native",
            "commands": [{"exit_code": 0}],
        }
        rows.append(row)
        for relative in module.required_task_artifacts(row):
            path = directory / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture evidence\n")
        (directory / "result.json").write_text(json.dumps(row) + "\n")
        (directory / "commands.json").write_text(json.dumps(row["commands"], indent=2) + "\n")
        (directory / "native.log").write_text("full original output\n")
        manifest = {
            str(p.relative_to(directory)): {"size": p.stat().st_size, "sha256": module.digest(p)}
            for p in directory.rglob("*")
            if p.is_file()
        }
        (directory / "manifest.json").write_text(json.dumps(manifest))
    rows[-1]["status"] = "QUALIFIED"
    rows.append({"instance_id": "cancelled-before-start", "status": "CANCELLED"})
    original_summary = batch / "batch-summary.json"
    original_summary.write_text(json.dumps({"results": rows}))
    source_manifest = {}
    for relative in (
        "scripts/qualify_cpp_batch.py",
        "scripts/prepare_multiswe_task.py",
        "scripts/screen_multiswe.py",
        "src/repropatch/task.py",
    ):
        path = batch / "execution-source" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((script.parents[1] / relative).read_bytes())
        source_manifest[relative] = {"size": path.stat().st_size, "sha256": module.digest(path)}
    (batch / "source-manifest.json").write_text(json.dumps(source_manifest))
    summary_hash = module.digest(original_summary)
    damaged_commands = batch / "recoverable/commands.json"
    damaged_commands.write_text("[]\n")
    damaged_log = batch / "incomplete/native.log"
    damaged_log.write_text("partial")
    summary_output = tmp_path / "audited/batch-summary.json"
    module.audit([batch], tmp_path / "audit", True, summary_output)
    audited = json.loads(summary_output.read_text())
    by_id = {r["instance_id"]: r for r in audited["results"]}
    assert by_id["recoverable"]["evidence_status"] == "RECOVERED_EXACT"
    assert by_id["incomplete"]["status"] == "EVIDENCE_INCOMPLETE"
    assert by_id["incomplete"]["execution_status"] == "HOST_QUALIFIED"
    assert by_id["status-mismatch"]["status"] == "EVIDENCE_INCOMPLETE"
    assert by_id["status-mismatch"]["evidence_status"] == "INCOMPLETE"
    assert by_id["cancelled-before-start"]["status"] == "CANCELLED"
    assert by_id["cancelled-before-start"]["evidence_status"] == "MISSING"
    assert len(audited["host_qualified_tasks"]) == 1
    assert damaged_commands.read_text() == "[]\n"
    assert damaged_log.read_text() == "partial"
    assert module.digest(original_summary) == summary_hash

    empty = batch / "empty/manifest.json"
    empty.parent.mkdir()
    empty.write_text("{}")
    assert module.verify_tree(empty.parent, {}, {"result.json"}) == [
        {"file": "manifest.json", "reason": "EMPTY_OR_INVALID_MANIFEST"}
    ]
    assert module.verify_tree(
        batch, {"batch-summary.json": {"size": 0, "sha256": "bad"}}, {"missing"}
    )
    original_summary.unlink()
    with pytest.raises(FileNotFoundError):
        module.audit([batch], tmp_path / "missing-audit", summary_output=tmp_path / "missing.json")
