"""core-only wheel 门禁的安装身份、终态、只读性与失败证据契约。"""

import copy
import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import SimulatedSandbox

from repropatch.harness import Harness


@pytest.fixture
def gate():
    path = Path(__file__).resolve().parents[1] / "scripts/check_core_distribution.py"
    spec = importlib.util.spec_from_file_location("core_distribution_gate_contract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def wheel_identity(tmp_path):
    site = tmp_path / "venv/lib/python3.12/site-packages"
    package = site / "repropatch"
    package.mkdir(parents=True)
    content = b'__version__ = "0.4.0"\n'
    (package / "__init__.py").write_bytes(content)
    wheel = tmp_path / "repropatch-0.4.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("repropatch/__init__.py", content)
        archive.writestr(
            "repropatch-0.4.0.dist-info/METADATA", "Name: repropatch\nVersion: 0.4.0\n"
        )
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    return wheel, {
        "version": "0.4.0",
        "module_version": "0.4.0",
        "isolated": True,
        "prefix": str(tmp_path / "venv"),
        "base_prefix": "/base-python",
        "module_origin": str(package / "__init__.py"),
        "distribution_origin": str(package / "__init__.py"),
        "site_packages": [str(site)],
        "origin": {"url": wheel.as_uri(), "archive_info": {"hashes": {"sha256": digest}}},
        "optional_modules": {"agents": False, "openai": False},
        "distributions": [
            {"name": "repropatch", "version": "0.4.0"},
            {"name": "PyYAML", "version": "6.0.3"},
        ],
        "implementation_sha256": "a" * 64,
    }


def test_exact_noneditable_core_wheel_identity(gate, wheel_identity):
    wheel, identity = wheel_identity
    result = gate.validate_installation(identity, wheel)
    assert result["wheel_sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert set(result["wheel_files"]) == {"repropatch/__init__.py"}


@pytest.mark.parametrize(
    "change",
    [
        "version",
        "module-version",
        "editable",
        "source",
        "hash",
        "agents",
        "openai",
        "sdk-distribution",
        "global-python",
        "unisolated",
        "package-bytes",
        "metadata",
    ],
)
def test_installation_identity_refuses_incompatible_environment(gate, wheel_identity, change):
    wheel, identity = wheel_identity
    if change == "version":
        identity["version"] = "0.3.0"
    elif change == "module-version":
        identity["module_version"] = "0.3.0"
    elif change == "editable":
        identity["origin"]["dir_info"] = {"editable": True}
    elif change == "source":
        identity["origin"]["url"] = wheel.parent.as_uri()
    elif change == "hash":
        identity["origin"]["archive_info"]["hashes"]["sha256"] = "0" * 64
    elif change in {"agents", "openai"}:
        identity["optional_modules"][change] = True
    elif change == "sdk-distribution":
        identity["distributions"].append({"name": "openai_agents", "version": "0.24.0"})
    elif change == "global-python":
        identity["prefix"] = identity["base_prefix"]
    elif change == "unisolated":
        identity["isolated"] = False
    elif change == "package-bytes":
        Path(identity["module_origin"]).write_bytes(b"changed")
    else:
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("repropatch/__init__.py", Path(identity["module_origin"]).read_bytes())
            archive.writestr(
                "repropatch-0.3.0.dist-info/METADATA", "Name: repropatch\nVersion: 0.3.0\n"
            )
        identity["origin"]["archive_info"]["hashes"]["sha256"] = hashlib.sha256(
            wheel.read_bytes()
        ).hexdigest()
    with pytest.raises(ValueError):
        gate.validate_installation(identity, wheel)


@pytest.mark.parametrize(
    "actual,expected,passed", [(0, 0, True), (1, 1, True), (0, 1, False), (3, 0, False)]
)
def test_command_exit_contract_and_original_logs(
    gate, tmp_path, monkeypatch, actual, expected, passed
):
    logs = tmp_path / "commands"
    logs.mkdir()
    summary = {"commands": []}

    def run(argv, **options):
        options["stdout"].write(b'{"outcome":"REJECTED"}\n')
        options["stderr"].write(b"diagnostic\n")
        return SimpleNamespace(returncode=actual)

    monkeypatch.setattr(gate.subprocess, "run", run)
    argv = [sys.executable, "-I", "-m", "repropatch", "verify-patch"]
    if passed:
        assert (
            json.loads(gate.execute(summary, logs, tmp_path, "verify", argv, expected=expected))[
                "outcome"
            ]
            == "REJECTED"
        )
    else:
        with pytest.raises(ValueError, match="退出码"):
            gate.execute(summary, logs, tmp_path, "verify", argv, expected=expected)
    record = summary["commands"][0]
    assert record["returncode"] == actual and record["expected_returncode"] == expected
    assert record["argv"] == argv and record["cwd"] == str(tmp_path)
    assert record["stderr"]["sha256"] == hashlib.sha256(b"diagnostic\n").hexdigest()


@pytest.fixture
def simulated_report(task, external_patch):
    class CandidateSandbox(SimulatedSandbox):
        def execute_test(self, name):
            if (
                name == "negative_values"
                and "int best = -1;" in (self.source / "src/stats.cpp").read_text()
            ):
                return 8, "failed", "expected -3, got -1"
            return super().execute_test(name)

    def create(scenario="correct"):
        patch = external_patch(
            "int best = samples.front();" if scenario == "correct" else "int best = -1;"
        )
        report = Harness(task, patch_file=patch, sandbox_factory=CandidateSandbox).run()
        fixture = {
            "commit": report["base_commit"],
            "task_sha256": report["task_sha256"],
            "image_id": "sha256:" + "b" * 64,
        }
        installation = {"implementation_sha256": report["provenance"]["implementation_sha256"]}
        value = copy.deepcopy(report)
        value.update(isolated=True, harness_version="0.4.0")
        value["provenance"].update(software_version="0.4.0", image_id=fixture["image_id"])
        for index, role in enumerate(("baseline", "independent"), 1):
            stage = value[role]
            stage.update(
                isolated=True, image_id=fixture["image_id"], container_name=f"repropatch-{index}"
            )
            stage["cleanup"]["container_id"] = str(index) * 64
        value["evaluations"] = [value["baseline"], value["independent"]]
        return report, value, fixture, installation

    return create


@pytest.mark.parametrize("scenario", ["correct", "wrong"])
def test_baseline_and_independent_use_existing_verification_contract(
    gate, simulated_report, task, scenario
):
    original, value, fixture, installation = simulated_report(scenario)
    assert "successful" not in value["independent"]
    audit = gate.validate_report(
        value, scenario, task, fixture, installation, Path(original["artifact_directory"])
    )
    assert len(audit["containers"]) == 2 and audit["model_requests"] == 0
    assert value["outcome"] == gate.EXPECTED[scenario][1]


@pytest.mark.parametrize(
    "change",
    [
        "isolation",
        "cache",
        "cleanup",
        "container",
        "requests",
        "implementation",
        "reason",
        "missing-test",
        "incomplete-build",
    ],
)
def test_release_report_checks_relevant_identity_and_cold_cleanup(
    gate, simulated_report, task, change
):
    original, value, fixture, installation = simulated_report()
    if change == "isolation":
        value["baseline"]["isolated"] = False
    elif change == "cache":
        value["independent"]["compiler_cache"] = {"kind": "ccache"}
    elif change == "cleanup":
        value["independent"]["cleanup"]["confirmed"] = False
    elif change == "container":
        value["independent"]["cleanup"]["container_id"] = value["baseline"]["cleanup"][
            "container_id"
        ]
    elif change == "requests":
        value["agent"]["http_attempts"] = 1
    elif change == "implementation":
        installation["implementation_sha256"] = "0" * 64
    elif change == "missing-test":
        value["independent"]["tests"].pop()
    elif change == "incomplete-build":
        value["independent"]["build"] = None
    else:
        value["reason_code"] = "F2P_FAILED"
    with pytest.raises(ValueError):
        gate.validate_report(
            value, "correct", task, fixture, installation, Path(original["artifact_directory"])
        )


@pytest.mark.parametrize("mutate", [False, True])
def test_readonly_queries_preserve_every_run_file(
    gate, simulated_report, task, monkeypatch, mutate
):
    original, _, fixture, installation = simulated_report()
    directory = Path(original["artifact_directory"])
    row = {name: original[name] for name in ("run_id", "state", "outcome", "reason_code")}
    row["artifact_dir"] = str(directory)
    monkeypatch.setattr(gate, "validate_report", lambda *args: {"model_requests": 0})

    def invoke(name, argv):
        if name.endswith("container-cleanup"):
            return ""
        if mutate:
            (directory / "unexpected.txt").write_bytes(b"query side effect")
        return json.dumps(
            {"run_id": row["run_id"], "outcome": row["outcome"], "evidence_complete": True}
        )

    if mutate:
        with pytest.raises(ValueError, match="只读查询"):
            gate.audit_run(row, "correct", directory.parent, task, fixture, installation, invoke)
    else:
        result = gate.audit_run(
            row, "correct", directory.parent, task, fixture, installation, invoke
        )
        assert result["readonly_queries_preserved_all_files"] and result["containers_removed"]


@pytest.mark.parametrize(
    "kind", ["existing", "linked-parent", "dangling", "run", "traversal", "source"]
)
def test_output_preflight_precedes_every_write_and_subprocess(gate, tmp_path, monkeypatch, kind):
    keep = tmp_path / "keep.bin"
    keep.write_bytes(b"keep")
    if kind == "existing":
        output = tmp_path
    elif kind == "linked-parent":
        link = tmp_path / "linked"
        link.symlink_to(tmp_path, target_is_directory=True)
        output = link / "new"
    elif kind == "dangling":
        output = tmp_path / "dangling"
        output.symlink_to(tmp_path / "missing", target_is_directory=True)
    elif kind == "run":
        (tmp_path / "events.sqlite3").write_bytes(b"database")
        output = tmp_path / "new"
    elif kind == "traversal":
        output = tmp_path / "new/../other"
    else:
        output = Path(gate.__file__).resolve().parents[1] / "scripts/core-gate-forbidden-output"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "core-gate",
            "--wheel",
            str(tmp_path / "missing.whl"),
            "--image",
            "example",
            "--output",
            str(output),
        ],
    )

    def forbidden(*args, **kwargs):
        pytest.fail("输出路径预检须先于进程执行")

    monkeypatch.setattr(gate.subprocess, "run", forbidden)
    with pytest.raises(SystemExit) as stopped:
        gate.main()
    assert stopped.value.code == 2 and keep.read_bytes() == b"keep"
    if kind != "existing":
        assert not output.exists()


def test_missing_docker_fails_with_complete_raw_evidence(
    gate, wheel_identity, tmp_path, monkeypatch
):
    wheel, identity = wheel_identity
    output = tmp_path / "gate-evidence"
    monkeypatch.setattr(
        sys,
        "argv",
        ["core-gate", "--wheel", str(wheel), "--image", "example", "--output", str(output)],
    )

    def run(argv, **options):
        if "-c" in argv:
            options["stdout"].write(json.dumps(identity).encode())
            return SimpleNamespace(returncode=0)
        assert argv[:4] == [sys.executable, "-I", "-m", "repropatch"]
        assert not Path(options["cwd"]).is_relative_to(Path(gate.__file__).resolve().parents[1])
        options["stdout"].write(
            json.dumps({"ready": False, "docker": None, "daemon": False}).encode()
        )
        options["stderr"].write(b"docker unavailable\n")
        return SimpleNamespace(returncode=2)

    monkeypatch.setattr(gate.subprocess, "run", run)
    assert gate.main() == 1
    summary = json.loads((output / "summary.json").read_bytes())
    assert summary["status"] == "failed" and "DOCKER_UNAVAILABLE" in summary["error"]
    assert summary["commands"][-1]["returncode"] == 2 and summary["temporary_cwd_removed"]
    assert summary["scenarios"] == [] and summary["model_requests"] == 0
    assert output.stat().st_mode & 0o777 == 0o700
    for line in (output / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
