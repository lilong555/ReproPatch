"""Glaze 系统 Asio 的标准库声明在基线和冷验收中保持一致。"""

import importlib
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
adapter = importlib.import_module("cpp_native_adapter")
qualification = importlib.import_module("qualify_cross_repo")


def test_glaze_exception_header_reaches_baseline_and_cold_oracle(tmp_path, monkeypatch):
    configuration = adapter.recipe({"org": "stephenberry", "repo": "glaze"})
    executor = qualification.NativeExecutor(
        "native", None, tmp_path, time.monotonic() + 30, configuration
    )
    commands = []

    def capture_configure(command, source, build, phase, stage):
        assert stage == "configure"
        commands.append(command)
        return {"exit_code": 1}

    monkeypatch.setattr(executor, "run", capture_configure)
    executor.native_oracle(tmp_path, "native-oracle", {})
    for command in [executor.configure, *commands]:
        flags = next(
            arg.partition("=")[2] for arg in command if arg.startswith("-DCMAKE_CXX_FLAGS=")
        )
        tokens = shlex.split(flags)
        index = tokens.index("-include")
        assert tokens[index + 1] == "exception"
        assert "-stdlib=libc++" in tokens
        assert "-DCMAKE_CXX_FLAGS_RELEASE=-O3 -DNDEBUG" in command
    assert len(commands) == 1


@pytest.mark.integration
def test_glaze_exception_preinclude_supplies_missing_asio_declarations(tmp_path):
    compiler = shutil.which("c++")
    if compiler is None:
        pytest.skip("需要 C++ 编译器")
    configuration = adapter.recipe({"org": "stephenberry", "repo": "glaze"})
    flags = next(
        arg.partition("=")[2]
        for arg in configuration["configure"]
        if arg.startswith("-DCMAKE_CXX_FLAGS=")
    )
    tokens = shlex.split(flags)
    index = tokens.index("-include")
    source = tmp_path / "exception-consumer.cpp"
    source.write_text(
        "int main() {\n"
        "  auto error = std::make_exception_ptr(42);\n"
        "  try { std::rethrow_exception(error); }\n"
        "  catch (int value) { return value == 42 ? 0 : 1; }\n"
        "  return 2;\n"
        "}\n"
    )
    binary = tmp_path / "exception-consumer"
    command = [compiler, "-std=c++17", str(source), "-o", str(binary)]
    missing_header = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert missing_header.returncode != 0
    included_header = subprocess.run(
        [*command, *tokens[index : index + 2]], capture_output=True, text=True, timeout=30
    )
    assert included_header.returncode == 0, included_header.stderr
    assert subprocess.run([str(binary)], timeout=10).returncode == 0


@pytest.mark.parametrize("cxx,cc", [("g++-14", "gcc-14"), ("c++", "cc")])
def test_glaze_gcc_recipe_keeps_native_standard_library(cxx, cc):
    configuration = adapter.recipe({"org": "stephenberry", "repo": "glaze"}, cxx=cxx, cc=cc)
    assert not any(arg.startswith("-DCMAKE_CXX_FLAGS=") for arg in configuration["configure"])
