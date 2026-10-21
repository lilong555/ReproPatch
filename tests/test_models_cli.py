import json

import pytest
from conftest import ROOT

from repropatch.cli import main


def test_cli_validate_and_version(capsys):
    assert main(["validate-task", str(ROOT / "examples/tasks/negative-maximum.v2.yaml")]) == 0
    assert json.loads(capsys.readouterr().out)["valid"]
    with pytest.raises(SystemExit) as stop:
        main(["--version"])
    assert stop.value.code == 0


def test_cli_requires_script(capsys):
    assert main(["run", str(ROOT / "examples/tasks/negative-maximum.v2.yaml")]) == 2
    assert "--mock-script" in capsys.readouterr().err


def test_doctor_missing_docker_is_not_success(monkeypatch, capsys):
    monkeypatch.setattr(
        "repropatch.cli.shutil.which", lambda name: None if name == "docker" else "/usr/bin/git"
    )
    assert main(["doctor"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["daemon"] is False and result["docker"] is None


@pytest.mark.sdk
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
        str(ROOT / "examples/tasks/negative-maximum.v2.yaml"),
        "--engine",
        "fake",
        "--mock-script",
        str(ROOT / "examples/models/fix-negative-maximum.json"),
    ]
    assert main(args) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_paid_cli_requires_model_name(capsys):
    assert (
        main(
            [
                "run",
                str(ROOT / "examples/tasks/negative-maximum.v2.yaml"),
                "--engine",
                "sdk",
            ]
        )
        == 2
    )
    assert "--model-name" in capsys.readouterr().err


@pytest.mark.parametrize("engine,option", [("agents-sdk", "--model"), ("sdk", "--model-name")])
def test_real_engine_aliases_require_explicit_consent(engine, option, capsys, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("付费授权前不能创建 Run")

    monkeypatch.setattr("repropatch.cli.Harness", forbidden)
    assert (
        main(
            [
                "run",
                str(ROOT / "examples/tasks/negative-maximum.v2.yaml"),
                "--engine",
                engine,
                option,
                "contract-model",
            ]
        )
        == 2
    )
    assert "PAID_MODEL_CONSENT_REQUIRED" in capsys.readouterr().err


def test_verify_patch_parser_does_not_accept_model_permissions(capsys):
    for option in ("--engine", "--model", "--key-env", "--allow-paid-model", "--pause-after-step"):
        with pytest.raises(SystemExit) as stopped:
            main(
                [
                    "verify-patch",
                    str(ROOT / "examples/tasks/negative-maximum.v2.yaml"),
                    "--patch",
                    "candidate.patch",
                    option,
                    "value",
                ]
            )
        assert stopped.value.code == 2
    capsys.readouterr()


@pytest.mark.parametrize("engine", ["fake", "agents-sdk"])
def test_cli_proxy_is_explicit_real_model_configuration(engine, monkeypatch, capsys):
    captured = []

    class StoppedHarness:
        def __init__(self, task, config, output_root):
            captured.append(config)

        def run(self):
            from repropatch.errors import ReproPatchError

            raise ReproPatchError("CONTRACT_STOP")

    monkeypatch.setattr("repropatch.cli.Harness", StoppedHarness)
    args = [
        "run",
        str(ROOT / "examples/tasks/negative-maximum.v2.yaml"),
        "--engine",
        engine,
        "--use-env-proxy",
    ]
    if engine == "fake":
        args += ["--mock-script", str(ROOT / "examples/models/fix-negative-maximum.json")]
        assert main(args) == 2
        assert not captured
    else:
        args += ["--model", "contract-model", "--allow-paid-model"]
        assert main(args) == 3
        assert captured[0].use_env_proxy is True
    capsys.readouterr()
