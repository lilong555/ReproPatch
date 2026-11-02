"""冻结 GoogleTest 身份、真实测试失败与冷评分器执行身份的离线验证。"""

import hashlib
import importlib
import json
import shutil
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
runner = importlib.import_module("native_cpp_runner")
qualification = importlib.import_module("qualify_cross_repo")

FROZEN_PARSER = (
    "def parser(log):\n"
    "    import re\n"
    '    states = {"OK": "pass", "FAILED": "fail", "SKIPPED": "skip"}\n'
    "    return {name: states[state] for state, name in re.findall(\n"
    "        r'\\[\\s+(OK|FAILED|SKIPPED)\\s+\\]\\s+(\\S+)\\s+\\(\\d+', log)}\n"
)

CASE = "Glsl/CompileVulkan1_1ToSpirvTest.FromFile/spv_int8_frag"


@pytest.mark.parametrize(
    ("marker", "state"), [("OK", "pass"), ("FAILED", "fail"), ("SKIPPED", "skip")]
)
@pytest.mark.parametrize("parameter", ['GetParam() = "spv.int8.frag"', "TypeParam = unsigned char"])
def test_parameterized_terminal_preserves_frozen_case_identity(marker, state, parameter):
    log = f"2: [  {marker}  ] {CASE}, where {parameter} (8 ms)\n"
    assert runner.parser_results(FROZEN_PARSER, log) == {}
    assert runner.glslang_results(FROZEN_PARSER, log) == {CASE: state}


def test_parameterized_summary_and_diagnostic_lines_supply_no_terminal():
    log = (
        f"2: [ RUN      ] {CASE}\n"
        f'2: [  FAILED  ] {CASE}, where GetParam() = "spv.int8.frag"\n'
        f'2: diagnostic: [  FAILED  ] {CASE}, where GetParam() = "spv.int8.frag" (8 ms)\n'
        "2: [  FAILED  ] 1 test, listed below:\n"
    )
    assert runner.glslang_results(FROZEN_PARSER, log) == {}


def test_parameterized_failure_wins_over_later_success():
    log = (
        f'2: [  FAILED  ] {CASE}, where GetParam() = "spv.int8.frag" (8 ms)\n'
        f"2: [       OK ] {CASE} (1 ms)\n"
    )
    assert runner.glslang_results(FROZEN_PARSER, log) == {CASE: "fail"}


@pytest.mark.integration
@pytest.mark.parametrize("outcome", ["passed", "p2p_failed", "missing", "additional_failure"])
def test_cold_oracle_preserves_contract_and_reports_group_states(tmp_path, outcome):
    if any(shutil.which(tool) is None for tool in ("cmake", "ctest", "python3")):
        pytest.skip("需要 CMake、CTest 与 Python 3")
    source = tmp_path / "source"
    protected = source / "repropatch-native"
    protected.mkdir(parents=True)
    frozen_runner = protected / "runner.py"
    frozen_runner.write_text('raise RuntimeError("冻结任务 runner 保持原字节")\n')
    contract_file = protected / "contract.json"
    contract = {
        "mode": "glslang",
        "parser": FROZEN_PARSER,
        "required_native_tests": ["SpvPatternTest.Uint8", "SpvPatternTest.Uint16", CASE],
        "groups": {
            "native-f2p-001": ["SpvPatternTest.Uint8"],
            "native-f2p-002": ["SpvPatternTest.Uint16"],
            "native-p2p": [CASE],
        },
    }
    contract_file.write_text(json.dumps(contract))
    script = source / "gtests.py"
    output = "[       OK ] SpvPatternTest.Uint8 (0 ms)\n[       OK ] SpvPatternTest.Uint16 (0 ms)\n"
    if outcome != "missing":
        marker = "FAILED" if outcome == "p2p_failed" else "OK"
        output += f'[  {marker}  ] {CASE}, where GetParam() = "spv.int8.frag" (8 ms)\n'
    script.write_text(
        f"import sys\nprint({output!r}, end='')\nsys.exit({int(outcome == 'p2p_failed')})\n"
    )
    shell_command = "false" if outcome == "additional_failure" else "true"
    (source / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.22)\nproject(fixture NONE)\nenable_testing()\n"
        f'add_test(NAME glslang-gtests COMMAND "{sys.executable}" "{script}")\n'
        f"add_test(NAME glslang-testsuite COMMAND ${{CMAKE_COMMAND}} -E {shell_command})\n"
    )
    before = {path: path.read_bytes() for path in (frozen_runner, contract_file)}
    executor = qualification.NativeExecutor(
        "native",
        None,
        tmp_path,
        time.monotonic() + 30,
        {"memory_mib": 1024, "configure": ["cmake", "-S", "/src", "-B", "/build"]},
    )
    try:
        result = executor.native_oracle(source, "oracle", contract)
        assert {path: path.read_bytes() for path in before} == before
        identity = json.loads((tmp_path / "oracle-cold-runner.json").read_text())
        assert (executor.build_root / "oracle/repropatch-cold-oracle-runner.py").stat().st_mode & (
            0o777
        ) == 0o444
        assert identity["runner_sha256"] == qualification.sha(
            qualification.ROOT / "scripts/native_cpp_runner.py"
        )
        assert identity["frozen_runner_sha256"] == hashlib.sha256(before[frozen_runner]).hexdigest()
        assert identity["contract_sha256"] == hashlib.sha256(before[contract_file]).hexdigest()
        command = next(row["argv"] for row in executor.commands if row["stage"] == "ctest")
        assert command[:3] == ["python3", "-I", "/build/repropatch-cold-oracle-runner.py"]
        assert "--oracle" in command and "--group" not in command
        native = json.loads((tmp_path / "oracle-native-results.json").read_text())
        if outcome == "missing":
            assert result["status"] == "TEST_RESULT_IDENTITY_MISMATCH"
            assert native["missing"] == [CASE]
            return
        assert result["status"] == ("PASSED" if outcome == "passed" else "TESTS_FAILED")
        assert result["tests"] == {
            "native-f2p-001": "passed",
            "native-f2p-002": "passed",
            "native-p2p": "failed" if outcome == "p2p_failed" else "passed",
        }
        assert native["missing"] == []
        assert set(result["native_tests"]) == set(contract["required_native_tests"])
        expected_extra = (
            ["ctest::glslang-gtests"]
            if outcome == "p2p_failed"
            else ["ctest::glslang-testsuite"]
            if outcome == "additional_failure"
            else []
        )
        assert result["additional_failures"] == expected_extra
    finally:
        shutil.rmtree(executor.build_root)


def test_additional_failure_preserves_executor_error_classification(tmp_path, monkeypatch):
    executor = qualification.NativeExecutor(
        "native", None, tmp_path, time.monotonic() + 30, {"memory_mib": 1024, "configure": []}
    )

    def run(command, source, build, phase, stage):
        if stage == "ctest":
            build.mkdir(parents=True, exist_ok=True)
            (build / "native-results.json").write_text(
                json.dumps(
                    {
                        "tests": {"control": "passed"},
                        "missing": [],
                        "additional_failures": ["ctest::other"],
                    }
                )
            )
        return {"exit_code": 17 if stage == "ctest" else 0}

    monkeypatch.setattr(executor, "run", run)
    try:
        result = executor.native_oracle(
            tmp_path, "oracle", {"mode": "ctest", "groups": {"native-p2p": ["control"]}}
        )
        assert result["status"] == "TEST_EXECUTION_FAILED"
    finally:
        shutil.rmtree(executor.build_root)


@pytest.mark.parametrize("failure", ["mutation", "path_conflict"])
def test_cold_oracle_detects_scoring_runner_integrity_failure(tmp_path, monkeypatch, failure):
    protected = tmp_path / "repropatch-native"
    protected.mkdir()
    (protected / "runner.py").write_text("frozen runner\n")
    contract = {"mode": "glslang"}
    (protected / "contract.json").write_text(json.dumps(contract))
    executor = qualification.NativeExecutor(
        "native", None, tmp_path, time.monotonic() + 30, {"memory_mib": 1024, "configure": []}
    )

    def run(command, source, build, phase, stage):
        build.mkdir(parents=True, exist_ok=True)
        path = build / "repropatch-cold-oracle-runner.py"
        if stage == "build" and failure == "path_conflict":
            path.symlink_to(protected / "runner.py")
        if stage == "ctest" and failure == "mutation":
            path.chmod(0o600)
            path.write_text("changed runner\n")
        return {"exit_code": 0}

    monkeypatch.setattr(executor, "run", run)
    previous = executor.deadline
    try:
        error = (
            "NATIVE_ORACLE_RUNNER_IDENTITY_MISMATCH"
            if failure == "mutation"
            else "NATIVE_ORACLE_RUNNER_PATH_CONFLICT"
        )
        with pytest.raises(ValueError, match=error):
            executor.native_oracle(tmp_path, "oracle", contract)
        assert executor.deadline == previous
    finally:
        shutil.rmtree(executor.build_root)
