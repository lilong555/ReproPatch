"""跨仓库编译回归、授权范围和原生测试身份的可执行验证。"""

import importlib
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
qualification = importlib.import_module("qualify_cross_repo")
sources = importlib.import_module("cpp_sources")
runner = importlib.import_module("native_cpp_runner")


@pytest.mark.integration
def test_compile_regression_keeps_p2p_and_passes_original_cold_oracle(tmp_path, monkeypatch):
    if any(shutil.which(tool) is None for tool in ("cmake", "ninja", "c++")):
        pytest.skip("需要 CMake、Ninja 和 C++ 编译器")
    upstream = tmp_path / "upstream"
    (upstream / "include/glaze").mkdir(parents=True)
    (upstream / "tests").mkdir()
    (upstream / "include/glaze/value.hpp").write_text("constexpr int value = 0;\n")
    (upstream / "tests/regression.cpp").write_text(
        '#include "glaze/value.hpp"\nint main() { return value != 0; }\n'
    )
    (upstream / "tests/control-data.txt").write_text("fixture-input")
    (upstream / "tests/control.cpp").write_text(
        "#include <fstream>\n#include <string>\nint main() {\n"
        'std::ifstream input(GLZ_TEST_DIRECTORY "/control-data.txt");\n'
        "std::string value; input >> value;\n"
        'std::ofstream(GLZ_TEST_DIRECTORY "/runtime-note.txt") << value;\n'
        'return value == "fixture-input" ? 0 : 1; }\n'
    )
    (upstream / "tests/library.cpp").write_text("int fixture_library() { return 0; }\n")
    (upstream / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.22)\nproject(fixture LANGUAGES CXX)\n"
        "enable_testing()\n"
        "add_custom_target(clangd_cache ALL COMMAND ${CMAKE_COMMAND} -E false)\n"
        "add_executable(regression tests/regression.cpp)\n"
        "target_include_directories(regression PRIVATE include)\n"
        "add_executable(control tests/control.cpp)\n"
        "target_compile_definitions(control PRIVATE "
        'GLZ_TEST_DIRECTORY="${CMAKE_SOURCE_DIR}/tests")\n'
        "add_library(fixture_lib SHARED tests/library.cpp)\n"
        "set_target_properties(fixture_lib PROPERTIES "
        'LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/bin")\n'
        "add_test(NAME regression COMMAND regression)\n"
        "add_test(NAME control COMMAND control)\n"
    )
    qualification.git(upstream, "init", "--template=", "-q", ".")
    qualification.git(upstream, "add", ".")
    qualification.git(upstream, "commit", "-qm", "基线")
    base = qualification.git(upstream, "rev-parse", "HEAD").decode().strip()
    (upstream / "tests/regression.cpp").write_text(
        '#include "glaze/value.hpp"\nstatic_assert(value == 1);\n'
        "int main() { return value != 1; }\n"
    )
    test_patch = qualification.git(upstream, "diff", "--", "tests/").decode()
    qualification.git(upstream, "restore", "tests/")
    (upstream / "include/glaze/value.hpp").write_text("constexpr int value = 1;\n")
    patch = qualification.git(upstream, "diff", "--", "include/").decode()
    qualification.git(upstream, "restore", "include/")

    def materialize(repo, commit, source, pool, deadline):
        qualification.archive(upstream, commit, source, deadline=deadline)
        return []

    monkeypatch.setattr(qualification, "materialize", materialize)
    record = {
        "instance_id": "stephenberry__glaze-999999",
        "org": "stephenberry",
        "repo": "glaze",
        "base": {"sha": base},
        "test_patch": test_patch,
        "fix_patch": patch,
        "dataset": "SWE-bench-Live/MultiLang",
        "dataset_revision": sources.LIVE_REVISION,
        "declared_f2p": ["regression"],
        "declared_p2p": ["control"],
        "fix_patch_result": {"passed_tests": ["regression", "control"]},
        "resolved_issues": [{"title": "值应为 1", "body": ""}],
    }
    args = SimpleNamespace(
        output=tmp_path / "qualification",
        repository=upstream,
        backend="native",
        image=None,
        cxx="c++",
        cc="cc",
        task_timeout=90,
    )
    result = qualification.qualify(record, args)
    directory = args.output / record["instance_id"]
    assert result["status"] == "HOST_QUALIFIED", json.dumps(result, ensure_ascii=False)
    assert result["f2p"] == ["regression"] and result["p2p"] == ["control"]
    assert result["phases"]["baseline"]["tests"] == {"control": "passed", "regression": "failed"}
    assert result["phases"]["native_oracle"]["native_tests"] == {
        "control": "passed",
        "regression": "passed",
    }
    assert result["native_oracle"]["adapter_used"] is False
    assert (directory / "prepared.bundle").is_file()
    assert (
        "static_assert(value == 1)" in (directory / "repository/tests/regression.cpp").read_text()
    )
    assert "value = 0" in (directory / "repository/include/glaze/value.hpp").read_text()
    assert result["cleanup"]["status"] == "SUCCEEDED"
    assert not (directory / "control/reference-source").exists()
    assert not (directory / "repository/tests/runtime-note.txt").exists()
    assert not (directory / "repository/bin").exists()
    candidate = importlib.import_module("check_native_cpp_candidate")
    monkeypatch.setattr(candidate, "load_records", lambda directory: [record])
    verdict = candidate.check(
        SimpleNamespace(
            output=tmp_path / "score",
            qualification=directory / "result.json",
            candidate=directory / "control/reference.patch",
            dataset=tmp_path,
            timeout=90,
        )
    )
    assert verdict["status"] == "ORACLE_PASSED", verdict
    assert verdict["accepted"] is True


def test_parser_rejects_process_and_filesystem_code():
    with pytest.raises(ValueError, match="IMPORT_REJECTED"):
        runner.review_parser(
            "def parser(log):\n import subprocess\n return subprocess.check_output(log)\n"
        )
    with pytest.raises(ValueError, match="IO_REJECTED"):
        runner.review_parser("def parser(log):\n return open(log).read()\n")


def test_git_submodule_options_keep_url_identity(tmp_path):
    import time

    from cpp_native_adapter import git_submodules

    qualification.git(tmp_path, "init", "--template=", "-q", ".")
    modules = tmp_path / ".gitmodules"
    modules.write_text(
        '[submodule "external/miniz"]\n'
        "\tpath = external/miniz\n"
        "\turl = https://github.com/richgel999/miniz\n"
        "  ignore = untracked\n"
        '[submodule "external/other"]\n'
        "  path = external/other\n"
        "\turl = https://github.com/example/other.git\n"
    )
    parsed = git_submodules(tmp_path, modules, deadline=time.monotonic() + 5)
    assert parsed["submodule.external/miniz"] == {
        "path": "external/miniz",
        "url": "https://github.com/richgel999/miniz",
    }
    modules.write_text(modules.read_text() + "url = https://github.com/example/duplicate\n")
    with pytest.raises(ValueError, match="CONFIGURATION_DUPLICATED"):
        git_submodules(tmp_path, modules, deadline=time.monotonic() + 5)


def test_slang_backend_uses_verified_archive_and_only_backend_library(tmp_path, monkeypatch):
    import hashlib
    import zipfile

    import prepare_cpp_toolchain as toolchain

    pool = tmp_path / "pool"
    output = tmp_path / "tools"
    pool.mkdir()
    output.mkdir()
    archive = pool / "slang-2026.5.2-linux-x86_64.zip"
    with zipfile.ZipFile(archive, "w") as data:
        data.writestr("lib/libslang-llvm.so", b"fixed-llvm-backend")
        data.writestr("bin/slangc", b"upstream-compiler")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    monkeypatch.setattr(toolchain, "SLANG_LLVM_ARCHIVE_SHA256", digest)
    identity = toolchain.prepare_slang_llvm(output, pool)
    assert sorted(p.name for p in output.iterdir()) == ["libslang-llvm.so"]
    assert identity["archive_sha256"] == digest
    assert (
        identity["files"]["libslang-llvm.so"]["sha256"]
        == hashlib.sha256(b"fixed-llvm-backend").hexdigest()
    )
    archive.write_bytes(archive.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="SOURCE_SHA256_MISMATCH"):
        toolchain.prepare_slang_llvm(output, pool)


def test_jsoncpp_interleaved_stream_requires_explicit_case_result():
    code = (
        "def parser(log):\n import re\n return {m[1]: 'pass' if m[2] == 'OK' else 'fail' "
        "for m in re.finditer(r'TESTING: (.*?\\.json) (OK|FAILED)', log)}\n"
    )
    log = (
        "1: TESTING: /src/test/data/pass.json child-command\n"
        "2: TESTING: /src/test/data/fail.json child-command\n"
        "1: child diagnostic\n2: FAILED\n1: OK\n"
        "1: TESTING: /src/test/data/incomplete.json child-command\n"
    )
    assert runner.jsoncpp_results(code, log) == {
        "/src/test/data/pass.json": "pass",
        "/src/test/data/fail.json": "fail",
    }


def test_case_aliases_are_unique_and_keep_actual_inventory_names():
    assert runner.match_case_names(["SelfTest"], {"selftest": "pass"}) == {"SelfTest": "selftest"}
    with pytest.raises(ValueError, match="AMBIGUOUS"):
        runner.match_case_names(["SelfTest"], {"selftest": "pass", "SELFTEST": "pass"})


def test_ninja_report_alias_keeps_the_failing_observation():
    actual = runner.normalize_results(
        "ninja",
        {
            "jobserver.Class.test_pipe": "pass",
            "jobserver.Class.test_pipe.test_pipe": "fail",
        },
    )
    assert actual == {"jobserver.Class.test_pipe": "fail"}


def test_opaque_case_prefix_aliases_are_reversible_and_keep_paths():
    assert (
        runner.canonical_case("duckdb", "unittest.global::test/sql/bug.test") == "test/sql/bug.test"
    )
    assert (
        runner.canonical_case(
            "luau", "/build/native/Luau.UnitTest::/src/tests/user.cpp::regression"
        )
        == "./build/Luau.UnitTest::/testbed/tests/user.cpp::regression"
    )


def test_production_scope_excludes_dictionary_and_test_sources():
    assert sources.production_path(
        {"org": "shader-slang", "repo": "slang"}, "source/slang/slang-check-expr.cpp"
    )
    assert sources.production_path(
        {"org": "nlohmann", "repo": "json"}, "single_include/nlohmann/json.hpp"
    )
    assert not sources.production_path(
        {"org": "open-source-parsers", "repo": "jsoncpp"}, "src/test_lib_json/main.cpp"
    )
    assert not sources.production_path(
        {"org": "BYVoid", "repo": "OpenCC"}, "data/dictionary/STPhrases.txt"
    )
