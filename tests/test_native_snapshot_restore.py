"""冻结的 CRLF 字节经过 Git bundle 后仍可精确恢复。"""

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
native = importlib.import_module("check_native_cpp_candidate")


def test_bundle_replay_preserves_original_crlf_and_rejects_content_changes(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / ".gitattributes").write_text("* text=auto\n")
    (source / "value.cpp").write_bytes(b"int value() {\r\n  return 1;\r\n}\r\n")
    native.git(source, "init", "--template=", "-q", ".")
    native.git(source, "add", ".")
    native.git(source, "commit", "-qm", "上游源码")
    original = native.git(source, "rev-parse", "HEAD").decode().strip()
    evidence = tmp_path / "evidence"
    native.save(evidence / "control/upstream-source-manifest.json", native.source_manifest(source))
    (source / "contract.json").write_text("{}\n")
    native.git(source, "add", ".")
    native.git(source, "commit", "-qm", "固定合同")
    native.save(evidence / "control/prepared-source-manifest.json", native.source_manifest(source))
    bundle = evidence / "prepared.bundle"
    native.git(source, "bundle", "create", str(bundle), "HEAD")
    qualification = {
        "prepared_bundle_sha256": native.sha(bundle),
        "upstream_snapshot_commit": original,
        "prepared_commit": native.git(source, "rev-parse", "HEAD").decode().strip(),
    }
    destination = tmp_path / "restored"
    native.restore_repository(evidence, qualification, destination)
    assert native.source_manifest(destination) == native.source_manifest(source)
    expected = native.source_manifest(destination)
    (destination / "value.cpp").write_text("int value() { return 2; }\n")
    with pytest.raises(ValueError, match="CONTENT_MISMATCH"):
        native.restore_manifest_bytes(destination, expected)
