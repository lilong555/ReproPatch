"""工程演示与只读诊断的命令行契约。"""

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from repropatch.cli import main, parser
from repropatch.errors import ReproPatchError


def install_module(monkeypatch, name, **attributes):
    module = ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)


def test_demo_defaults_are_explicit_and_require_no_model_options():
    args = parser().parse_args(["demo"])
    assert args.output == Path(".repropatch/demo")
    assert args.image == "repropatch-cpp:0.1"
    assert args.scenario == "all"
    assert not hasattr(args, "allow_paid_model")


@pytest.mark.parametrize("status,expected", [("passed", 0), ("failed", 3)])
def test_demo_json_dispatch(monkeypatch, capsys, tmp_path, status, expected):
    calls = []

    def run_demo(output, image, scenario):
        calls.append((output, image, scenario))
        return {"status": status, "model_kind": "scripted", "paid_model_requests": 0}

    install_module(
        monkeypatch,
        "repropatch.demo",
        run_demo=run_demo,
        demo_markdown=lambda result: "演示",
    )
    output = tmp_path / "demo"
    assert (
        main(
            [
                "demo",
                "--output",
                str(output),
                "--image",
                "local-image",
                "--scenario",
                "recovery",
                "--json",
            ]
        )
        == expected
    )
    assert calls == [(output, "local-image", "recovery")]
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == status and result["paid_model_requests"] == 0


def test_demo_text_and_preparation_error(monkeypatch, capsys):
    install_module(
        monkeypatch,
        "repropatch.demo",
        run_demo=lambda *args: {"status": "passed"},
        demo_markdown=lambda result: "修复与恢复演示",
    )
    assert main(["demo"]) == 0
    assert capsys.readouterr().out.strip() == "修复与恢复演示"

    def refused(*args):
        raise ReproPatchError("DEMO_OUTPUT_EXISTS: 演示目录已存在")

    install_module(
        monkeypatch,
        "repropatch.demo",
        run_demo=refused,
        demo_markdown=lambda result: "",
    )
    assert main(["demo"]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "DEMO_OUTPUT_EXISTS" in captured.err


@pytest.mark.parametrize("option", ["--allow-paid-model", "--model", "--api-base", "--key-env"])
def test_demo_rejects_paid_model_configuration(option, capsys):
    with pytest.raises(SystemExit) as stopped:
        main(["demo", option])
    assert stopped.value.code == 2
    capsys.readouterr()


@pytest.mark.parametrize("complete,expected", [(True, 0), (False, 3)])
def test_diagnose_exit_code_tracks_evidence_not_repair_outcome(
    monkeypatch, capsys, tmp_path, complete, expected
):
    run_id = "a" * 32
    directory = tmp_path / run_id
    directory.mkdir()
    calls = []

    def diagnose_run(path):
        calls.append(path)
        return {"run_id": run_id, "outcome": "ERROR", "evidence_complete": complete}

    install_module(
        monkeypatch,
        "repropatch.diagnostics",
        diagnose_run=diagnose_run,
        diagnostics_markdown=lambda result: "运行诊断",
    )
    assert main(["diagnose", run_id, "--root", str(tmp_path), "--json"]) == expected
    assert calls == [directory]
    assert json.loads(capsys.readouterr().out)["outcome"] == "ERROR"


def test_diagnose_invalid_id_is_rejected_before_reading(monkeypatch, capsys):
    def forbidden(path):
        pytest.fail("非法 Run ID 已进入读取路径")

    install_module(
        monkeypatch,
        "repropatch.diagnostics",
        diagnose_run=forbidden,
        diagnostics_markdown=lambda result: "",
    )
    assert main(["diagnose", "../another-run"]) == 2
    assert capsys.readouterr().err


def test_doctor_reports_actionable_missing_tools(monkeypatch, capsys):
    monkeypatch.setattr("repropatch.cli.shutil.which", lambda name: None)
    assert main(["doctor", "--json"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["ready"] is False
    assert len(result["next_actions"]) == 2
    assert "Git" in result["next_actions"][0]
    assert "docker info" in result["next_actions"][1]
