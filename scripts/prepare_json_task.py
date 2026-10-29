"""固定 nlohmann/json 缺陷，映射完整原生测试到逐项独立验收。"""

import argparse
import hashlib
import json
from pathlib import Path

import yaml
from check_json_candidate import CASES, CONFIGURE, CTEST, IMAGE, record_file
from prepare_multiswe_task import git
from prepare_simdjson_task import archive

from repropatch.task import Task

BUILD_ADAPTER = """# 在同一测试目录配置原生工程，随后执行原生构建并传播退出状态。
execute_process(COMMAND "${CMAKE_COMMAND}" -G "${GENERATOR}"
  "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"
  "-DCMAKE_CXX_COMPILER=${CXX}"
  "-Dnlohmann_json_DIR=${JSON_DIR}"
  "-Dnlohmann_json_source=${SOURCE_DIR}"
  "-DFETCHCONTENT_SOURCE_DIR_JSON=${SOURCE_DIR}"
  -S "${PROJECT_DIR}" -B "${BUILD_DIR}"
  RESULT_VARIABLE configure_status)
if(NOT configure_status STREQUAL "0")
  message(FATAL_ERROR "JSON_CMAKE_CONFIGURE_FAILED: ${configure_status}")
endif()
execute_process(COMMAND "${CMAKE_COMMAND}" --build "${BUILD_DIR}"
  RESULT_VARIABLE build_status)
if(NOT build_status STREQUAL "0")
  message(FATAL_ERROR "JSON_CMAKE_BUILD_FAILED: ${build_status}")
endif()
"""

DIAGNOSTICS_ADAPTER = """# 原生断言或测试失败以 CTest 非零退出传播，完整输出保留。
execute_process(COMMAND "${TEST_BINARY}" --no-skip
  WORKING_DIRECTORY "${SOURCE_DIR}" RESULT_VARIABLE test_status)
if(NOT test_status STREQUAL "0")
  message(FATAL_ERROR "JSON_NATIVE_DIAGNOSTICS_FAILED: ${test_status}")
endif()
"""


def adapt(source):
    """镜像已含固定数据；每个构建节点显式执行自己的配置依赖。"""
    modern = (source / "cmake/test.cmake").is_file()
    tests = "tests" if modern else "test"
    cmake = source / ("cmake/test.cmake" if modern else "test/CMakeLists.txt")
    value = cmake.read_text()
    for old, new in (
        (
            "set_tests_properties(download_test_data PROPERTIES FIXTURES_SETUP TEST_DATA)",
            'set_tests_properties(download_test_data PROPERTIES FIXTURES_SETUP "")',
        ),
        ('LABELS "all" FIXTURES_REQUIRED TEST_DATA', 'LABELS "all" FIXTURES_REQUIRED ""'),
        ('LABELS "valgrind" FIXTURES_REQUIRED TEST_DATA', 'LABELS "valgrind" FIXTURES_REQUIRED ""'),
    ):
        # 部分版本分别为 C++11 与 C++17 注册相同的数据依赖。
        value = value.replace(old, new)
    if "FIXTURES_REQUIRED TEST_DATA" in value or "FIXTURES_SETUP TEST_DATA" in value:
        raise ValueError("JSON_DATA_FIXTURE_LAYOUT")
    needle = "\n    if (JSON_FastTests)\n"
    if (source / tests / "src/unit-diagnostics.cpp").is_file():
        if value.count(needle) != 1:
            raise ValueError("JSON_DIAGNOSTICS_TEST_LAYOUT")
        target = "test_target" if modern else "testcase"
        diagnostic = "test-diagnostics_cpp11" if modern else "test-diagnostics"
        value = value.replace(
            needle,
            """
    if (@TARGET@ STREQUAL "@DIAGNOSTIC@")
        add_test(NAME ${@TARGET@} COMMAND ${CMAKE_COMMAND}
            "-DTEST_BINARY=$<TARGET_FILE:${@TARGET@}>"
            "-DSOURCE_DIR=${CMAKE_SOURCE_DIR}"
            -P "${PROJECT_SOURCE_DIR}/@TESTS@/repropatch-diagnostics.cmake")
    elseif (JSON_FastTests)
""".replace("@TARGET@", target)
            .replace("@DIAGNOSTIC@", diagnostic)
            .replace("@TESTS@", tests),
        )
        if not modern:
            # 诊断回归依赖标准断言；优化级别 O3 保持生效。
            value += "\ntarget_compile_options(test-diagnostics PRIVATE -UNDEBUG)\n"
        (source / tests / "repropatch-diagnostics.cmake").write_text(DIAGNOSTICS_ADAPTER)
    cmake.write_text(value)
    folders = (
        "cmake_import",
        "cmake_import_minver",
        "cmake_add_subdirectory",
        "cmake_fetch_content",
        "cmake_fetch_content2",
        "cmake_target_include_directories",
    )
    for name in folders:
        path = source / tests / name / "CMakeLists.txt"
        # 原生版本按各自目录提供 CMake 集成测试。
        if not path.exists():
            if f"add_subdirectory({name})" in (source / tests / "CMakeLists.txt").read_text():
                raise ValueError("JSON_BUILD_FIXTURE_LAYOUT")
            continue
        value = path.read_text()
        compiler_option = "-DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}"
        if compiler_option not in value:
            generator = '-G "${CMAKE_GENERATOR}"'
            if value.count(generator) != 1:
                raise ValueError("JSON_BUILD_COMPILER_LAYOUT")
            value = value.replace(generator, generator + "\n    " + compiler_option)
        if value.count(compiler_option) != 1:
            raise ValueError("JSON_BUILD_COMPILER_LAYOUT")
        value = value.replace(
            compiler_option,
            compiler_option + "\n    -DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        )
        needle = "COMMAND ${CMAKE_COMMAND} --build ."
        if value.count(needle) != 1:
            raise ValueError("JSON_BUILD_FIXTURE_LAYOUT")
        value = value.replace(
            needle,
            '''COMMAND ${CMAKE_COMMAND}
    "-DPROJECT_DIR=${CMAKE_CURRENT_SOURCE_DIR}/project"
    "-DBUILD_DIR=${CMAKE_CURRENT_BINARY_DIR}"
    "-DJSON_DIR=${PROJECT_BINARY_DIR}"
    "-DSOURCE_DIR=${PROJECT_SOURCE_DIR}"
    "-DCXX=${CMAKE_CXX_COMPILER}"
    "-DGENERATOR=${CMAKE_GENERATOR}"
    -P "${PROJECT_SOURCE_DIR}/@TESTS@/repropatch-cmake-build.cmake"'''.replace("@TESTS@", tests),
        )
        if name.startswith("cmake_fetch_content"):
            needle = "-Dnlohmann_json_source=${PROJECT_SOURCE_DIR}"
            if value.count(needle) != 1:
                raise ValueError("JSON_FETCHCONTENT_LAYOUT")
            value = value.replace(
                needle, needle + "\n    -DFETCHCONTENT_SOURCE_DIR_JSON=${PROJECT_SOURCE_DIR}"
            )
        for prop in ("FIXTURES_SETUP", "FIXTURES_REQUIRED"):
            needle = prop + " " + name
            if value.count(needle) != 1:
                raise ValueError("JSON_CMAKE_FIXTURE_LAYOUT")
            value = value.replace(needle, prop + ' ""')
        path.write_text(value)
    (source / tests / "repropatch-cmake-build.cmake").write_text(BUILD_ADAPTER)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = record_file(args.record)
    case = CASES[record["number"]]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "repository"
    archive(args.repository, case["base"], source)
    for name, field in (("official-test.patch", "test_patch"), ("reference.patch", "fix_patch")):
        (output / name).write_text(record[field])
    git(source, "init", "--template=", "-q", ".")
    git(source, "apply", str(output / "official-test.patch"))
    adapt(source)
    git(source, "add", "-f", ".")
    git(
        source,
        "-c",
        "user.name=Benchmark",
        "-c",
        "user.email=benchmark@example.invalid",
        "commit",
        "-qm",
        "固定诊断回归与逐项 CTest",
    )
    prepared = git(source, "rev-parse", "HEAD").decode().strip()
    editable = sorted(
        p.relative_to(source).as_posix()
        for name in ("include", "single_include")
        for p in (source / name).rglob("*.hpp")
        if p.is_file()
    )
    required = sorted(record["run_result"]["passed_tests"])
    issue = "\n\n".join(i["title"] + "\n" + i["body"] for i in record["resolved_issues"])
    description = issue + (
        "\n\nSource /src; build /build. Tests and CMake are read-only. "
        "Fixed test data is available offline at /opt/json-test-data. "
        "The include/ and single_include/ trees expose the multi-header and amalgamated library.\n"
        "configure: " + " ".join(CONFIGURE) + "\nbuild: cmake --build /build --parallel 2\n"
        "verify: " + " ".join(CTEST)
    )
    task = {
        "version": 2,
        "id": f"nlohmann-json-{record['number']}",
        "repository": {"path": str(source), "commit": prepared},
        "environment": {
            "image": IMAGE,
            "memory_mib": 4096,
            "pids_limit": 256,
            "build_tmpfs_mib": 3072,
            "cpu_limit": 2.0,
        },
        "bug": {"description": description},
        "commands": {
            "configure": CONFIGURE,
            "build": ["cmake", "--build", "/build", "--parallel", "2"],
            "reproduce": list(CTEST),
            "verify": list(CTEST),
        },
        "tests": {
            "fail_to_pass": [
                {"name": name, "expected_exit_code": 8, "output_contains": marker}
                for name, marker in case["f2p"].items()
            ],
            "pass_to_pass": [n for n in required if n not in case["f2p"]],
            "protected_paths": ["tests/", "cmake/", "CMakeLists.txt"],
        },
        "files": {
            "readable": ["include/", "single_include/", "tests/src/", "CMakeLists.txt"],
            "editable": editable,
        },
        "budget": {
            "max_steps": 12,
            "max_tool_calls": 24,
            "wall_seconds": 6000,
            "verification_reserve_seconds": 2400,
            "model_timeout_seconds": 90,
            "command_timeout_seconds": 1800,
            "max_output_tokens": 8192,
        },
        "workspace": {"root": str(output / "workspaces")},
        "outputs": {"root": str(output / "runs")},
    }
    path = output / "task.yaml"
    path.write_text(yaml.safe_dump(task, sort_keys=False, allow_unicode=True))
    Task.load(path)
    provenance = {
        "instance_id": f"nlohmann__json-{record['number']}",
        "upstream_commit": case["base"],
        "prepared_commit": prepared,
        "image": IMAGE,
        "native_required_tests": required,
        "dataset_revision": "56ff018c04a38e27ada1e9d0a6d5839a51f88f0d",
        "test_patch_sha256": hashlib.sha256(record["test_patch"].encode()).hexdigest(),
        "reference_patch_sha256": hashlib.sha256(record["fix_patch"].encode()).hexdigest(),
        "task_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "adaptation": [
            "固定离线数据清除隐式数据 fixture",
            "构建节点显式执行原生配置依赖",
            "prepared FetchContent 从当前源码读取；外部 Oracle 保留原生 Git 克隆",
            "诊断节点执行同一原生二进制，断言终止传播为非零 CTest 退出",
        ],
        "selection": "固定数据文件顺序筛查；4537父指针、4525整数类型访问；模型结果在准备时未知",
        "model_requests": 0,
        "runtime_verified": False,
    }
    (output / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({"task": str(path), "prepared_commit": prepared, "tests": len(required)}))


if __name__ == "__main__":
    main()
