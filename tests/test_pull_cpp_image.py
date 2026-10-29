"""资格环境网络恢复不重试测试，也不更换冻结镜像。"""

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
pull = importlib.import_module("pull_cpp_image")
IMAGE = "ghcr.io/lilong555/repropatch-cross-cpp@sha256:" + "a" * 64


def test_network_retry_keeps_immutable_image_and_succeeds(tmp_path, monkeypatch):
    calls, sleeps = [], []

    def run(argv, **kwargs):
        calls.append(argv)
        assert kwargs["timeout"] == 300
        return SimpleNamespace(
            returncode=1 if len(calls) < 3 else 0,
            stdout="",
            stderr="context deadline exceeded" if len(calls) < 3 else "",
        )

    monkeypatch.setattr(pull.subprocess, "run", run)
    monkeypatch.setattr(pull.time, "sleep", sleeps.append)
    output = tmp_path / "image-pull.json"
    assert pull.pull_image(IMAGE, output, instance="nlohmann__json-3008") == 0
    assert calls == [["docker", "pull", IMAGE]] * 3
    assert sleeps == [2, 4]
    report = json.loads(output.read_text())
    assert report["status"] == "IMAGE_PULLED"
    assert report["model_requests"] == 0
    assert report["qualification_executed"] is False


def test_network_retries_are_bounded_and_redact_signed_urls(tmp_path, monkeypatch):
    monkeypatch.setattr(
        pull.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr='Get "https://ghcr.io/blob?sig=private": context deadline exceeded',
        ),
    )
    monkeypatch.setattr(pull.time, "sleep", lambda _: None)
    output = tmp_path / "image-pull.json"
    assert pull.pull_image(IMAGE, output) == 1
    report = json.loads(output.read_text())
    assert report["status"] == "IMAGE_PULL_FAILED"
    assert len(report["attempts"]) == 3
    assert "private" not in output.read_text()


def test_image_permission_failure_is_not_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(
        pull.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="denied: unauthorized"),
    )
    output = tmp_path / "image-pull.json"
    assert pull.pull_image(IMAGE, output) == 1
    assert len(json.loads(output.read_text())["attempts"]) == 1


def test_mutable_image_tag_is_rejected_before_network(tmp_path):
    with pytest.raises(ValueError, match="IMMUTABLE_CPP_IMAGE_REQUIRED"):
        pull.pull_image("ghcr.io/lilong555/repropatch-cross-cpp:latest", tmp_path / "result.json")
