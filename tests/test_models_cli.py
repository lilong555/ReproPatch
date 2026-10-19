import json
import urllib.error
from io import BytesIO

import pytest
from conftest import ROOT

from repropatch.cli import main
from repropatch.errors import ReproPatchError
from repropatch.models import MockModel, OpenAICompatibleModel, ToolCall, Turn


def test_cli_validate_and_version(capsys):
    assert main(["validate-task", str(ROOT / "examples/tasks/negative-maximum.yaml")]) == 0
    assert json.loads(capsys.readouterr().out)["valid"]
    with pytest.raises(SystemExit) as stop:
        main(["--version"])
    assert stop.value.code == 0


def test_cli_requires_script(capsys):
    assert main(["run", str(ROOT / "examples/tasks/negative-maximum.yaml")]) == 2
    assert "--script" in capsys.readouterr().err


def test_doctor_missing_docker_is_not_success(monkeypatch, capsys):
    monkeypatch.setattr(
        "repropatch.cli.shutil.which", lambda name: None if name == "docker" else "/usr/bin/git"
    )
    assert main(["doctor"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["daemon"] is False and result["docker"] is None


def test_cli_run_reports_infrastructure_failure(tmp_path, monkeypatch, capsys):
    import repropatch.cli

    class FakeHarness:
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            return {
                "run_id": "unit",
                "status": "error",
                "isolated": None,
                "duration_seconds": 0.0,
                "artifact_directory": str(tmp_path),
            }

    monkeypatch.setattr(repropatch.cli, "Harness", FakeHarness)
    args = [
        "run",
        str(ROOT / "examples/tasks/negative-maximum.yaml"),
        "--script",
        str(ROOT / "examples/models/fix-negative-maximum.json"),
    ]
    assert main(args) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_paid_cli_requires_model_name(capsys):
    assert (
        main(
            [
                "run",
                str(ROOT / "examples/tasks/negative-maximum.yaml"),
                "--model",
                "openai-compatible",
            ]
        )
        == 2
    )
    assert "--model-name" in capsys.readouterr().err


def test_paid_adapter_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with pytest.raises(ReproPatchError, match="consent"):
        OpenAICompatibleModel("test")
    with pytest.raises(ReproPatchError, match="HTTPS"):
        OpenAICompatibleModel("test", base_url="http://localhost", allow_paid=True)
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(ReproPatchError, match="unset"):
        OpenAICompatibleModel("test", allow_paid=True)


def test_adapter_tool_call_and_usage(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-only")
    payload = {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "1",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path":"src/stats.cpp"}',
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 42, "completion_tokens": 12},
    }
    observed = {}

    class FakeOpener:
        def open(self, request, timeout):
            observed["request"] = request
            return BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: FakeOpener())
    model = OpenAICompatibleModel("test", allow_paid=True)
    turn = model.complete([], [])
    assert turn.calls[0].arguments == {"path": "src/stats.cpp"}
    assert model.usage == [payload["usage"]]
    assert observed["request"].get_header("Authorization") == "Bearer unit-test-only"
    assert "unit-test-only" not in observed["request"].data.decode()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"choices": []},
        {"choices": [{"finish_reason": "length"}]},
        {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "tool_calls": [
                            {"id": "1", "function": {"name": "x", "arguments": "invalid-json"}}
                        ]
                    },
                }
            ]
        },
    ],
)
def test_adapter_rejects_malformed_responses(monkeypatch, payload):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-only")

    class FakeOpener:
        def open(self, request, timeout):
            return BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: FakeOpener())
    with pytest.raises(ReproPatchError):
        OpenAICompatibleModel("test", allow_paid=True).complete([], [])


def test_adapter_errors_do_not_echo_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-secret")

    class FakeOpener:
        def open(self, request, timeout):
            raise urllib.error.URLError("sensitive server detail unit-test-secret")

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: FakeOpener())
    with pytest.raises(ReproPatchError) as error:
        OpenAICompatibleModel("test", allow_paid=True).complete([], [])
    assert "unit-test-secret" not in str(error.value)


def test_mock_script_and_turn_format(tmp_path):
    script = tmp_path / "bad.json"
    script.write_text("{}")
    with pytest.raises(ReproPatchError):
        MockModel.load(script)
    turn = Turn("", [ToolCall("1", "read_file", {"path": "x"})])
    assert json.loads(turn.message()["tool_calls"][0]["function"]["arguments"]) == {"path": "x"}
