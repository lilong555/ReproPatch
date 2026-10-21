"""不安装 agent extra 时可执行的 SDK 输入与隔离边界。"""

import asyncio
import json
import subprocess
import sys

import pytest

from repropatch.errors import ReproPatchError
from repropatch.models import load_sdk_script, positive_timeout, prepare_sdk, responses_model


def test_core_modules_do_not_import_optional_sdk():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.modules['agents']=None; sys.modules['openai']=None; "
            "import repropatch.models, repropatch.agent_runtime, repropatch.cli; "
            "assert sys.modules['agents'] is None and sys.modules['openai'] is None",
        ],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_paid_consent_precedes_optional_import_and_key_read(monkeypatch):
    class Guard(dict):
        def get(self, name, *args):
            if name == "OPENAI_API_KEY":
                raise AssertionError("授权前不能读取凭据")
            return super().get(name, *args)

    monkeypatch.setattr("repropatch.models.os.environ", Guard())

    async def scenario():
        async with responses_model("contract-model", model_timeout=1):
            pytest.fail("无授权不能构造模型")

    with pytest.raises(ReproPatchError, match="PAID_MODEL_CONSENT_REQUIRED"):
        asyncio.run(scenario())


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, "1"])
def test_timeout_is_positive_and_finite(value):
    with pytest.raises(ReproPatchError, match="timeout"):
        positive_timeout(value)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/v1",
        "https://user:secret@example.invalid/v1",
        "https://example.invalid/v1?key=secret",
        "https://example.invalid/v1#secret",
        "https://example.invalid:bad/v1",
        "https://example.invalid:0/v1",
        "https://example.invalid/\nsecret",
        "https://example.invalid\\evil/v1",
        "relative",
        None,
    ],
)
def test_endpoint_policy_precedes_dependency_or_credentials(url):
    async def scenario():
        async with responses_model(
            "contract-model", model_timeout=1, allow_paid=True, base_url=url
        ):
            pytest.fail("非法端点不可构造客户端")

    with pytest.raises(ReproPatchError):
        asyncio.run(scenario())


@pytest.mark.parametrize("missing", [True, False])
def test_optional_dependency_error_is_explicit(monkeypatch, missing):
    from importlib.metadata import PackageNotFoundError

    def version(name):
        if missing:
            raise PackageNotFoundError(name)
        return "0.0.0"

    monkeypatch.setattr("repropatch.models.version", version)
    with pytest.raises(
        ReproPatchError, match="ENGINE_DEPENDENCY_MISSING" if missing else "SDK_VERSION_MISMATCH"
    ):
        prepare_sdk()


@pytest.mark.parametrize(
    "payload",
    [
        b'{"version":1,"version":1,"steps":[]}',
        b'{"version":NaN,"steps":[]}',
        b'{"version":true,"steps":[]}',
        b'{"version":1,"steps":[],"module":"x"}',
        b'{"version":1,"steps":[]}',
        b"[" * 2000,
        b" " * 256_001,
        json.dumps({"version": 1, "steps": [{"output": []}] * 101}).encode(),
    ],
)
def test_invalid_script_envelope_is_rejected_without_sdk(tmp_path, payload):
    path = tmp_path / "invalid.json"
    path.write_bytes(payload)
    with pytest.raises(ReproPatchError, match="INVALID_SDK_SCRIPT"):
        load_sdk_script(path)


@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo"])
def test_loader_accepts_only_regular_files(tmp_path, kind):
    import os

    path = tmp_path / "input"
    if kind == "symlink":
        path.symlink_to(tmp_path / "missing")
    elif kind == "directory":
        path.mkdir()
    else:
        os.mkfifo(path)
    with pytest.raises(ReproPatchError, match="INVALID_SDK_SCRIPT"):
        load_sdk_script(path)


def test_model_configuration_rejects_secret_endpoint_before_run():
    from repropatch.models import ResponsesConfig

    sentinel = "synthetic-userinfo-secret"
    with pytest.raises(ReproPatchError) as stopped:
        ResponsesConfig(
            "contract-model", f"https://user:{sentinel}@contract.invalid/v1", "OPENAI_API_KEY", True
        )
    assert sentinel not in str(stopped.value)


@pytest.mark.parametrize("value", [1, None])
def test_proxy_option_rejects_non_boolean_without_sdk(value):
    from repropatch.models import ResponsesConfig

    with pytest.raises(ReproPatchError, match="use_env_proxy"):
        ResponsesConfig("contract-model", "https://contract.invalid", "CONTRACT_KEY", True, value)
