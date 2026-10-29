"""原生 CTest 的未构建目标与只读源目录保留完整测试合同。"""

import hashlib
import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
runner = importlib.import_module("native_cpp_runner")
adapter = importlib.import_module("cpp_native_adapter")


@pytest.mark.integration
def test_missing_ctest_binary_command_builds_only_its_deferred_target(tmp_path):
    if any(shutil.which(tool) is None for tool in ("cmake", "ctest", "cc")):
        pytest.skip("需要 CMake、CTest 与 C 编译器")
    source, build = tmp_path / "source", tmp_path / "build"
    source.mkdir()
    (source / "net.test.c").write_text("int main(void) { return 0; }\n")
    (source / "other.test.c").write_text("int main(void) { return 0; }\n")
    (source / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.22)\nproject(fixture C)\nenable_testing()\n"
        "add_executable(caf-net-test net.test.c)\n"
        "add_executable(other-test other.test.c)\n"
        "add_test(NAME caf.net.actor_shell COMMAND caf-net-test)\n"
        'add_test(NAME "case with spaces" COMMAND caf-net-test)\n'
        "add_test(NAME unrelated COMMAND other-test)\n"
        "include(${CMAKE_BINARY_DIR}/repropatch-deferred.cmake OPTIONAL)\n"
    )
    query = build / ".cmake/api/v1/query/codemodel-v2"
    query.parent.mkdir(parents=True)
    query.touch()
    configure = ["cmake", "-S", str(source), "-B", str(build)]
    subprocess.run(configure, check=True, capture_output=True)
    inventory = json.loads(
        subprocess.check_output(["ctest", "--test-dir", str(build), "--show-only=json-v1"])
    )
    # 真正的 CTest 在可执行文件尚不存在时，JSON 中缺失 command 字段。
    assert all("command" not in test for test in inventory["tests"])
    contract = {
        "mode": "ctest",
        "official_test_paths": ["net.test.c", "other.test.c"],
        "groups": {"caf.net.actor_shell": ["caf.net.actor_shell"]},
    }
    runner.prepare_native(contract, source, build)
    assert runner.group_targets(contract, build, ["caf.net.actor_shell"]) == ["caf-net-test"]
    assert runner.group_targets(contract, build, ["case with spaces"]) == ["caf-net-test"]
    assert runner.group_targets(contract, build, ["unrelated"]) == ["other-test"]
    subprocess.run(configure, check=True, capture_output=True)
    subprocess.run(["cmake", "--build", str(build)], check=True, capture_output=True)
    assert not (build / "caf-net-test").exists()
    assert runner.run_group(contract, source, build, "caf.net.actor_shell") == 0
    assert (build / "caf-net-test").is_file()
    assert not (build / "other-test").exists()


def test_ambiguous_generated_ctest_command_requires_review(tmp_path):
    (tmp_path / "CTestTestfile.cmake").write_text(
        'add_test([=[same]=] "/build/debug/test")\nadd_test([=[same]=] "/build/release/test")\n'
    )
    with pytest.raises(ValueError, match="NATIVE_CTEST_COMMAND_AMBIGUOUS"):
        runner.generated_ctest_commands(tmp_path, {"same"})


def test_caf_keeps_required_ping_pong_example_enabled():
    configuration = adapter.recipe({"org": "actor-framework", "repo": "actor-framework"})
    assert "-DCAF_ENABLE_EXAMPLES=ON" in configuration["configure"]
    assert "-DCAF_ENABLE_EXAMPLES=OFF" not in configuration["configure"]


@pytest.mark.integration
@pytest.mark.parametrize("shell_failure", [False, True])
def test_glslang_shell_suite_retains_inputs_and_failures(tmp_path, shell_failure):
    if any(shutil.which(tool) is None for tool in ("cmake", "ctest", "bash")):
        pytest.skip("需要 CMake、CTest 与 Bash")
    source, build = tmp_path / "source", tmp_path / "build"
    tests = source / "Test"
    tests.mkdir(parents=True)
    (tests / "shader.frag").write_bytes(b"fixed shader input\n")
    (tests / "runtests").write_text(
        "#!/usr/bin/env bash\nset -eu\n"
        'case "$PWD" in */repropatch-fixtures/Test) ;; *) exit 9 ;; esac\n'
        'test "$(cat ../Test/shader.frag)" = "fixed shader input"\n'
        'printf "generated SPIR-V" > frag.spv\n'
        'mkdir -p "$1"\n'
        'cp frag.spv "$1/result.spv"\n'
        f"exit {int(shell_failure)}\n"
    )
    (tests / "runtests").chmod(0o444)
    (tests / "shader.frag").chmod(0o444)
    tests.chmod(0o555)
    script = source / "gtests.py"
    script.write_text('print("[       OK ] Math.Pass (1 ms)")\n')
    (source / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.22)\nproject(fixture NONE)\nenable_testing()\n"
        f'add_test(NAME glslang-gtests COMMAND "{sys.executable}" "{script}")\n'
        'add_test(NAME glslang-testsuite COMMAND bash runtests "${CMAKE_BINARY_DIR}/localResults"\n'
        '  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/Test/")\n'
    )
    subprocess.run(["cmake", "-S", str(source), "-B", str(build)], check=True, capture_output=True)
    before = {path.relative_to(tests).as_posix(): path.read_bytes() for path in tests.iterdir()}
    contract = {
        "mode": "glslang",
        "parser": "def parser(log):\n"
        ' return {"Math.Pass": "pass"} if "[       OK ] Math.Pass (1 ms)" in log else {}\n',
    }
    expected = {"Math.Pass": "pass"}
    if shell_failure:
        expected["ctest::glslang-testsuite"] = "fail"
    for _ in range(2):
        assert runner.native_suite(contract, source, build) == expected
    assert (build / "repropatch-fixtures/Test/frag.spv").read_text() == "generated SPIR-V"
    assert not (tests / "frag.spv").exists()
    after = {path.relative_to(tests).as_posix(): path.read_bytes() for path in tests.iterdir()}
    assert after == before
    trace = json.loads((build / "repropatch-reports/glslang-runtime-inputs.json").read_text())
    assert trace["input_files"] == {
        name: hashlib.sha256(data).hexdigest() for name, data in before.items()
    }
    assert trace["generated_test_files"] == ["CTestTestfile.cmake"]
