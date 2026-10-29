"""Slang 独立构建树保留上游可执行文件的 prelude 查找约定。"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
runner = importlib.import_module("native_cpp_runner")
adapter = importlib.import_module("cpp_native_adapter")


def test_slang_contract_freezes_runtime_compiler_directory():
    record = {
        "declared_f2p": ["regression"],
        "declared_p2p": ["control"],
        "fix_patch_result": {"passed_tests": ["regression", "control"]},
        "native_log_parser": "def parser(log):\n return {}\n",
        "native_test_commands": ["./build/Release/bin/slang-test -xunit -v"],
        "test_patch": "",
    }
    contract = adapter.make_contract(record, {"mode": "slang"})
    assert contract["runtime_compiler_directory"] == "/usr/lib/llvm-19/bin"
    assert contract["test_arguments"] == ["-xunit", "-v"]


def test_slang_terminal_records_fill_missing_native_failure_without_relaxing_parser():
    # 7815/7662 的冻结解析器漏掉上游大写 FAILED 终态，基线因此被误判为未执行。
    parser = "def parser(log):\n return {'existing_failure': 'fail', 'existing_success': 'pass'}\n"
    log = (
        "passed test: 'slang-unit-test-tool/CudaCompile.internal' \n"
        "FAILED test: 'tests/language-feature/enums/enum-array-indexing.slang.1 (cpu)' \n"
        "ignored test: 'tests/example.slang (vk)' \n"
        "FAILED test: 'timed-failure' 1.2ms\n"
        "passed test: 'timed-success' 2.4s\n"
        "passed test: 'existing_failure' \n"
        "FAILED test: 'existing_success' \n"
        "passed test: 'existing_success' \n"
        "failed(pending retry) 'pending'\n"
        "failed(pending retry) test: 'pending-with-test'\n"
        "compiler: FAILED test: 'diagnostic'\n"
        "FAILED test: 'not-a-terminal' compiler diagnostic suffix\n"
    )
    assert runner.slang_results(parser, log) == {
        "existing_failure": "fail",
        "existing_success": "fail",
        "slang-unit-test-tool/CudaCompile.internal": "pass",
        "tests/language-feature/enums/enum-array-indexing.slang.1 (cpu)": "fail",
        "tests/example.slang (vk)": "skip",
        "timed-failure": "fail",
        "timed-success": "pass",
    }


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            "mkdir -p reports ; ./build/Release/bin/slang-test -xunit -v "
            "> reports/slang-test-xunit.xml",
            ["-xunit", "-v"],
        ),
        (
            "cd /testbed && ./build/Release/bin/slang-test -v verbose 2>&1 | tee test-output.log",
            ["-v", "verbose"],
        ),
        (
            "./build/Release/bin/slang-test -v -xunit -expected-failure-list "
            "tests/expected-failure-no-gpu.txt > reports/slang-test-xunit.xml",
            ["-v", "-xunit", "-expected-failure-list", "tests/expected-failure-no-gpu.txt"],
        ),
        (
            "mkdir -p reports; ./build/Release/bin/slang-test -use-test-server "
            "-server-count 2 -v 2>&1 | tee reports/slang-test.log",
            ["-use-test-server", "-server-count", "2", "-v"],
        ),
        (
            "./build/Release/bin/slang-test -use-test-server -category full "
            "-expected-failure-list tests/expected-failure-github.txt "
            "-expected-failure-list tests/expected-failure-no-gpu.txt "
            "-skip-reference-image-generation -show-adapter-info "
            "-enable-debug-layers true 2>&1 | tee test-output.log",
            [
                "-use-test-server",
                "-category",
                "full",
                "-expected-failure-list",
                "tests/expected-failure-github.txt",
                "-expected-failure-list",
                "tests/expected-failure-no-gpu.txt",
                "-skip-reference-image-generation",
                "-show-adapter-info",
                "-enable-debug-layers",
                "true",
            ],
        ),
    ],
)
def test_slang_preserves_frozen_native_command_contract(command, expected):
    assert adapter.slang_test_arguments({"native_test_commands": [command]}) == expected


@pytest.mark.parametrize(
    "command",
    [
        "ctest --test-dir build/tools --output-on-failure -V 2>&1 | tee test-output.log",
        "./build/Release/bin/slang-test -xunit; ./build/Release/bin/slang-test -v",
        "./build/Release/bin/slang-test -expected-failure-list",
    ],
)
def test_slang_rejects_unreviewed_native_commands(command):
    with pytest.raises(ValueError, match="SLANG_NATIVE_COMMAND_REVIEW_REQUIRED"):
        adapter.slang_test_arguments({"native_test_commands": [command]})


@pytest.mark.parametrize("relative_build", ["baseline/native", "native-oracle"])
def test_slang_finds_prelude_from_executable_in_separate_build_tree(tmp_path, relative_build):
    source = tmp_path / "source"
    build = tmp_path / relative_build
    (source / "prelude").mkdir(parents=True)
    (source / "include").mkdir()
    (source / "tests").mkdir()
    (source / "tools/gfx").mkdir(parents=True)
    (source / "tools/gfx/gfx.slang").write_text("fixed gfx module\n")
    (source / "tools/gfx/slang.slang").write_text("fixed slang module\n")
    prelude = source / "prelude/slang-cpp-prelude.h"
    prelude.write_text("fixed prelude bytes\n")
    (source / "include/slang.h").write_text("fixed public header bytes\n")
    (source / "tests/case.slang").write_text("fixed test bytes\n")

    # 原生 CMake 已经在这两个目录中生成文件，运行时准备必须保留它们。
    (build / "prelude").mkdir(parents=True)
    generated = build / "prelude/slang-cpp-prelude.h.cpp"
    generated.write_text("generated embedded prelude\n")
    (build / "include").mkdir()
    version = build / "include/slang-tag-version.h"
    version.write_text("fixed generated version\n")
    executable = build / "Release/bin/slang-test"
    executable.parent.mkdir(parents=True)
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import os, sys\n"
        "assert (Path(sys.argv[0]).parent / 'gfx.slang').read_text() == 'fixed gfx module\\n'\n"
        "assert (Path(sys.argv[0]).parent / 'slang.slang').read_text() == 'fixed slang module\\n'\n"
        "# 上游 TestToolUtil::getRootPath 从可执行文件目录逐层向上查找。\n"
        "for root in Path(sys.argv[0]).resolve().parents:\n"
        "    header = root / 'prelude/slang-cpp-prelude.h'\n"
        "    if header.is_file():\n"
        "        assert os.environ['PATH'].split(os.pathsep)[0] == '/usr/lib/llvm-19/bin'\n"
        "        assert header.read_text() == 'fixed prelude bytes\\n'\n"
        "        assert (root / 'include/slang.h').read_text() == "
        "'fixed public header bytes\\n'\n"
        "        assert Path('tests/case.slang').read_text() == 'fixed test bytes\\n'\n"
        "        Path('tests/case.slang.actual').write_text('runtime output')\n"
        "        print('case PASS')\n"
        "        break\n"
        "else:\n"
        "    sys.exit(1)\n"
    )
    executable.chmod(0o755)
    assert subprocess.run([str(executable)], cwd=source, check=False).returncode == 1
    before = {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    contract = {
        "mode": "slang",
        "test_arguments": [],
        "runtime_compiler_directory": "/usr/lib/llvm-19/bin",
        "parser": "def parser(log):\n return {'case': 'pass'} if 'case PASS' in log else {}\n",
    }
    parent_environment = dict(os.environ)
    for _ in range(2):
        assert runner.native_suite(contract, source, build) == {"case": "pass"}
    assert dict(os.environ) == parent_environment
    assert (build / "prelude/slang-cpp-prelude.h").resolve() == prelude
    assert generated.read_text() == "generated embedded prelude\n"
    assert version.read_text() == "fixed generated version\n"
    after = {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    assert after == before
    actual = build / "repropatch-fixtures/slang/tests/case.slang.actual"
    assert actual.read_text() == "runtime output"


@pytest.mark.parametrize("number", [10738, 10697, 10768, 10664])
def test_slang_uses_recorded_official_backends(number):
    configuration = adapter.recipe(
        {"org": "shader-slang", "repo": "slang", "instance_id": f"shader-slang__slang-{number}"}
    )
    flags = configuration["configure"]
    assert "-DCMAKE_CXX_COMPILER=g++-13" in flags
    assert "-DCMAKE_CXX_STANDARD=23" in flags
    assert "-DSLANG_ENABLE_DXIL=ON" in flags
    assert "-DSLANG_ENABLE_DXIL=OFF" not in flags
    assert "-DSLANG_SLANG_LLVM_BINARY_URL=/opt/cpp-deps/slang-10738/libslang-llvm.so" in flags
    assert configuration["runtime_compiler_directory"] == "/usr/lib/llvm-18/bin"
