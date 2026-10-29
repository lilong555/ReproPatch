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
@pytest.mark.parametrize("reference_value", [1, 2])
def test_compile_regression_keeps_p2p_and_passes_original_cold_oracle(
    tmp_path, monkeypatch, reference_value
):
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
    (upstream / "include/glaze/value.hpp").write_text(f"constexpr int value = {reference_value};\n")
    cmake = upstream / "CMakeLists.txt"
    cmake.write_text(cmake.read_text() + "# 官方修复的构建注释\n")
    patch = qualification.git(upstream, "diff").decode()
    qualification.git(upstream, "restore", "include/", "CMakeLists.txt")

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
        "dataset": "ByteDance-Seed/Multi-SWE-bench",
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
    assert result["qualification_policy"] == "baseline-native-v1"
    assert result["omitted_reference_paths"] == ["CMakeLists.txt"]
    assert set(result["phases"]) == {"baseline", "native_oracle"}
    assert [row["phase"] for row in result["commands"] if row["stage"] == "build"] == [
        "baseline",
        "native-oracle",
    ]
    if reference_value == 2:
        assert result["status"] == "NATIVE_ORACLE_BUILD_FAILED"
        assert result["cleanup"]["status"] == "SUCCEEDED"
        assert not (directory / "prepared.bundle").exists()
        return
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
    evidence = importlib.import_module("verify_qualification_evidence")
    required = evidence.required_task_artifacts(result)
    assert (
        evidence.verify_tree(
            directory, json.loads((directory / "manifest.json").read_text()), required
        )
        == []
    )
    legacy_required = evidence.required_task_artifacts(
        {key: value for key, value in result.items() if key != "qualification_policy"}
    )
    assert "reference-results.xml" in legacy_required
    assert "reference-results.xml" not in required
    assert evidence.verify_tree(
        directory,
        json.loads((directory / "manifest.json").read_text()),
        required | {"reference-results.xml"},
    )
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


@pytest.mark.integration
def test_glslang_preserves_individual_cases_and_additional_ctest_failures(tmp_path):
    import subprocess

    if any(shutil.which(tool) is None for tool in ("cmake", "ctest")):
        pytest.skip("需要 CMake 与 CTest")
    source, build = tmp_path / "source", tmp_path / "build"
    source.mkdir()
    script = source / "tests.py"
    script.write_text('print("[       OK ] Math.Pass (1 ms)")\n')
    (source / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.22)\nproject(fixture NONE)\nenable_testing()\n"
        f'add_test(NAME glslang-gtests COMMAND "{sys.executable}" "{script}")\n'
        "add_test(NAME additional COMMAND ${CMAKE_COMMAND} -E false)\n"
    )
    subprocess.run(["cmake", "-S", str(source), "-B", str(build)], check=True, capture_output=True)
    contract = {
        "mode": "glslang",
        "parser": "def parser(log):\n"
        ' return {"Math.Pass": "pass"} if "[       OK ] Math.Pass (1 ms)" in log else {}\n',
    }
    assert runner.native_suite(contract, source, build) == {
        "Math.Pass": "pass",
        "ctest::additional": "fail",
    }
    assert runner.native_suite(contract, source, build, ["Math.Pass"]) == {"Math.Pass": "pass"}


def test_duckdb_temporary_outputs_use_build_directory(tmp_path):
    source = tmp_path / "source"
    build = tmp_path / "build"
    source.mkdir()
    (source / "test").mkdir()
    (source / "test/input.txt").write_text("固定原生输入")
    (source / "data").mkdir()
    (source / "data/missing-link").symlink_to("missing-directory/input.txt")
    (source / "data/cycle").symlink_to(".")
    (build / "test").mkdir(parents=True)
    executable = build / "test/unittest"
    executable.write_text(
        "#!/usr/bin/env python3\nimport os, sys\nfrom pathlib import Path\n"
        f"os.chdir({str(source)!r})\n"
        'os.chdir(sys.argv[sys.argv.index("--test-dir") + 1])\n'
        'assert "*" in sys.argv\n'
        'directory = Path("duckdb_unittest_tempdir")\n'
        "directory.mkdir(parents=True)\n"
        '(directory / "runtime.txt").write_text("generated")\n'
        'assert Path("test/input.txt").read_text() == "固定原生输入"\n'
        'Path("test/generated.txt").write_text("generated")\n'
        'Path(sys.argv[sys.argv.index("--out") + 1]).write_text('
        "'<testsuites><testsuite><testcase name=\"control\"/></testsuite></testsuites>')\n"
    )
    executable.chmod(0o755)
    contract = {
        "mode": "duckdb",
        "test_arguments": ["*"],
        "parser": "def parser(log):\n import xml.etree.ElementTree as ET\n"
        " return {case.attrib['name']: 'pass' for case in ET.fromstring(log).iter('testcase')}\n",
    }
    assert runner.native_suite(contract, source, build) == {"control": "pass"}
    assert (
        build / "repropatch-fixtures/duckdb/duckdb_unittest_tempdir/runtime.txt"
    ).read_text() == "generated"
    assert (build / "repropatch-fixtures/duckdb/test/generated.txt").exists()
    assert not (source / "test/generated.txt").exists()
    assert (build / "repropatch-fixtures/duckdb/data/missing-link").is_symlink()
    assert (build / "repropatch-fixtures/duckdb/data/cycle").readlink() == Path(".")


@pytest.mark.integration
def test_slang_generator_keeps_temporary_headers_in_build_tree(tmp_path, monkeypatch):
    import subprocess

    if any(shutil.which(tool) is None for tool in ("cmake", "ninja", "c++")):
        pytest.skip("需要 CMake、Ninja 与 C++ 编译器")
    adapter = importlib.import_module("cpp_native_adapter")
    source, build = tmp_path / "source", tmp_path / "build"
    inputs = source / "source/slang"
    module = source / "source/slang-core-module"
    inputs.mkdir(parents=True)
    module.mkdir()
    template = inputs / "core.meta.slang"
    template.write_text("constexpr int value = 1;\n")
    (source / "generator.cpp").write_text(
        "#include <filesystem>\n#include <fstream>\n#include <iterator>\n"
        "int main(int argc, char** argv) {\n"
        "std::filesystem::path input(argv[1]), output(argv[argc-1]);\n"
        "std::ifstream stream(input);\n"
        "std::string text((std::istreambuf_iterator<char>(stream)), {});\n"
        'std::ofstream temporary(input.string() + ".temp.h");\n'
        "if (!temporary) return 3; temporary << text;\n"
        "std::filesystem::create_directories(output);\n"
        'std::ofstream(output / (input.filename().string() + ".h")) << text;\n'
        "return 0; }\n"
    )
    (source / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.20)\nproject(slang CXX)\n"
        "add_executable(slang-generate generator.cpp)\n"
        "add_subdirectory(source/slang-core-module)\n"
    )
    (module / "CMakeLists.txt").write_text(
        'set(core_module_meta_source_dir "${slang_SOURCE_DIR}/source/slang")\n'
        'file(GLOB inputs "${core_module_meta_source_dir}/*.meta.slang")\n'
        'set(output "${CMAKE_CURRENT_BINARY_DIR}/output/core.meta.slang.h")\n'
        "add_custom_command(OUTPUT ${output}\n"
        " COMMAND slang-generate ${inputs} --target-directory ${CMAKE_CURRENT_BINARY_DIR}/output\n"
        " DEPENDS slang-generate ${inputs})\n"
        "add_custom_target(generate ALL DEPENDS ${output})\n"
    )
    monkeypatch.setattr(adapter, "materialize", lambda *args, **kwargs: [])
    adapter.prepare_source_dependencies(
        {"org": "shader-slang", "repo": "slang"}, source, tmp_path / "pool", deadline=0
    )
    subprocess.run(
        ["cmake", "-S", str(source), "-B", str(build), "-G", "Ninja"],
        check=True,
        capture_output=True,
    )
    inputs.chmod(0o555)
    try:
        subprocess.run(["cmake", "--build", str(build)], check=True, capture_output=True)
    finally:
        inputs.chmod(0o755)
    assert (
        build / "source/slang-core-module/output/core.meta.slang.h"
    ).read_bytes() == template.read_bytes()
    assert (
        build / "source/slang-core-module/repropatch-meta-input/core.meta.slang.temp.h"
    ).is_file()
    assert list(inputs.iterdir()) == [template]


def test_slang_native_outputs_keep_original_test_inputs(tmp_path):
    source, build = tmp_path / "source", tmp_path / "build"
    tests = source / "tests"
    tests.mkdir(parents=True)
    original = tests / "case.slang"
    original.write_text("固定输入")
    executable = build / "Release/bin/slang-test"
    executable.parent.mkdir(parents=True)
    executable.write_text(
        "#!/usr/bin/env python3\nfrom pathlib import Path\n"
        'assert Path("tests/case.slang").read_text() == "固定输入"\n'
        'Path("tests/case.slang.actual").write_text("原生反馈")\n'
        'print("tests/case.slang PASS")\n'
    )
    executable.chmod(0o755)
    tests.chmod(0o555)
    try:
        observed = runner.native_suite(
            {
                "mode": "slang",
                "test_arguments": [],
                "parser": 'def parser(log):\n return {"tests/case.slang": "pass"}\n',
            },
            source,
            build,
        )
    finally:
        tests.chmod(0o755)
    assert observed == {"tests/case.slang": "pass"}
    assert (build / "repropatch-fixtures/slang/tests/case.slang.actual").read_text() == "原生反馈"
    assert list(tests.iterdir()) == [original]


@pytest.mark.integration
@pytest.mark.parametrize("actual", ["expected", "wrong"])
def test_catch2_approval_preserves_inputs_and_runs_in_build_directory(tmp_path, actual):
    import subprocess

    if any(shutil.which(tool) is None for tool in ("cmake", "ctest", "c++")):
        pytest.skip("需要 CMake、CTest 与 C++ 编译器")
    source = tmp_path / "source"
    build = tmp_path / "build"
    scripts = source / "tools/scripts"
    baselines = source / "tests/SelfTest/Baselines"
    scripts.mkdir(parents=True)
    baselines.mkdir(parents=True)
    (baselines / "expected.approved.txt").write_text("expected tests/SelfTest/fixture.cpp")
    (source / "tests/SelfTest/fixture.cpp").write_text(
        "#include <iostream>\nint main(int, char** argv) { "
        'std::cout << argv[1] << " " << __FILE__; }\n'
    )
    (scripts / "scriptCommon.py").write_text(
        "from pathlib import Path\ncatchPath = Path(__file__).resolve().parents[2]\n"
    )
    script = scripts / "approvalTests.py"
    script.write_text(
        "import subprocess, sys\nfrom scriptCommon import catchPath\n"
        "root = catchPath / 'tests/SelfTest/Baselines'\n"
        "actual = subprocess.check_output(sys.argv[1:], text=True)\n"
        "(root / 'actual.tmp').write_text(actual)\n"
        "sys.exit(0 if (root / 'expected.approved.txt').read_text() == actual else 1)\n"
    )
    (source / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.22)\nproject(fixture LANGUAGES CXX)\nenable_testing()\n"
        "add_executable(SelfTest tests/SelfTest/fixture.cpp)\n"
        f'add_test(NAME ApprovalTests COMMAND "{sys.executable}" "{script}" '
        f'$<TARGET_FILE:SelfTest> "{actual}")\n'
        "set_tests_properties(ApprovalTests PROPERTIES TIMEOUT 5)\n"
    )
    originals = {
        str(path.relative_to(source)): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    }
    flags = qualification.recipe({"org": "catchorg", "repo": "Catch2"})["configure"]
    flags = next(arg for arg in flags if arg.startswith("-DCMAKE_CXX_FLAGS="))
    flags = flags.replace("/src/", str(source) + "/")
    subprocess.run(
        ["cmake", "-S", str(source), "-B", str(build), flags], check=True, capture_output=True
    )
    subprocess.run(["cmake", "--build", str(build)], check=True, capture_output=True)
    contract = {"mode": "ctest", "configuration": {"repository": "catchorg/Catch2"}}
    expected = {"ApprovalTests": "pass" if actual == "expected" else "fail"}
    assert runner.native_suite(contract, source, build) == expected
    assert runner.native_suite(contract, source, build, selected=["ApprovalTests"]) == expected
    assert {
        str(path.relative_to(source)): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    } == originals
    copied = build / "repropatch-fixtures/tools/scripts/approvalTests.py"
    assert copied.read_bytes() == script.read_bytes()
    assert (
        build / "repropatch-fixtures/tests/SelfTest/Baselines/actual.tmp"
    ).read_text() == actual + " tests/SelfTest/fixture.cpp"
    trace = json.loads((build / "repropatch-reports/ctest-runtime-commands.json").read_text())
    assert trace["original_script"] == str(script)
    assert trace["executed_script"] == str(copied)


def test_native_filesystem_failure_is_infrastructure_error(tmp_path):
    with pytest.raises(RuntimeError, match="NATIVE_FILESYSTEM_INFRASTRUCTURE_ERROR"):
        runner.execute(
            [sys.executable, "-c", "raise OSError(30, 'Read-only file system')"],
            tmp_path,
            tmp_path / "failure.log",
        )


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
    assert not sources.production_path(
        {"org": "actor-framework", "repo": "actor-framework"},
        "libcaf_net/caf/net/actor_shell.test.cpp",
    )
