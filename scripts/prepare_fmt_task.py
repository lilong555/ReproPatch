"""将固定 FMT 编译回归映射为 CTest，保持原始测试和参考补丁独立保存。"""

import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path

import yaml
from prepare_multiswe_task import git

from repropatch.task import Task

BASE_COMMIT = "01914f0389ef6ff151c289670f6910e059d5063f"
TEST_PATCH_SHA256 = "9038d83d8a393ef1dec82b5ee8eec43b5abcac43cea26e264ba506d0f3851079"
REFERENCE_SHA256 = "f3a54f9ae8cc967cda9faefc6a4b7fc2ed3da8daf5e83c6340018845018605c1"
IMAGE = "sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a"
CASES = {
    4310: {
        "base_commit": BASE_COMMIT,
        "test_patch_sha256": TEST_PATCH_SHA256,
        "reference_sha256": REFERENCE_SHA256,
        "compile_target": "base-test",
        "compile_signature": "no member named",
    },
    4286: {
        "base_commit": "e3ddede6c4ee818825c4e5a6dfa1d384860c27d9",
        "test_patch_sha256": "87b52d25b995bbc7eb42a034bc9b80418ecd66575af92f033a739d7287443971",
        "reference_sha256": "cb30e0912b415a30796aeed3e3a80b3678119c67839d4683cd363f51a10f1288",
        "compile_target": "xchar-test",
        "compile_signature": "error:",
    },
    4057: {
        "base_commit": "ccea338070c795fd966a4dc08b19268b6fbad5ef",
        "test_patch_sha256": "4fe5920891ea0a3d3b49d171f62ef2f843638248ace826d511e261a999c0db49",
        "reference_sha256": "8463a77c84862b6944eca1b677974668180f8e7c880d88508f5ab0316d9457d6",
        "compile_target": "ranges-test",
        "compile_signature": "error:",
    },
}
NATIVE_TESTS = (
    "args-test",
    "assert-test",
    "base-test",
    "chrono-test",
    "color-test",
    "compile-fp-test",
    "compile-test",
    "enforce-checks-test",
    "format-impl-test",
    "format-test",
    "gtest-extra-test",
    "no-builtin-types-test",
    "os-test",
    "ostream-test",
    "posix-mock-test",
    "printf-test",
    "ranges-test",
    "scan-test",
    "std-test",
    "unicode-test",
    "xchar-test",
)


def native_tests(record):
    """按固定上游版本保留完整原生测试集合。"""
    return tuple(
        name for name in NATIVE_TESTS if record["number"] != 4057 or name != "no-builtin-types-test"
    )


CONFIGURE = [
    "cmake",
    "-S",
    "/src",
    "-B",
    "/build",
    "-DFMT_DOC=OFF",
    "-DFMT_TEST=ON",
    "-DCMAKE_BUILD_TYPE=Release",
]
CTEST = ["ctest", "--test-dir", "/build", "--output-on-failure", "--no-tests=error"]
CTEST_ADAPTER = """  if (name STREQUAL "base-test")
    # 编译回归在 CTest 内构建原生目标，保留同一个回归用例和运行结果。
    set_target_properties(base-test PROPERTIES EXCLUDE_FROM_ALL TRUE)
    add_test(NAME base-test COMMAND ${CMAKE_COMMAND}
      "-DBUILD_DIR=${CMAKE_BINARY_DIR}"
      "-DTEST_BINARY=$<TARGET_FILE:base-test>"
      -P "${PROJECT_SOURCE_DIR}/test/repropatch-build-test.cmake")
  else ()
    add_test(NAME ${name} COMMAND ${name})
  endif ()
"""
COMPILE_TEST = """# 构建或测试失败原样传播；源码和此脚本均由 Task 保护。
execute_process(
  COMMAND "${CMAKE_COMMAND}" --build "${BUILD_DIR}" --target base-test --parallel 2
  RESULT_VARIABLE build_status)
if (NOT build_status STREQUAL "0")
  message(FATAL_ERROR "FMT_COMPILE_REGRESSION: ${build_status}")
endif ()
execute_process(COMMAND "${TEST_BINARY}" RESULT_VARIABLE test_status)
if (NOT test_status STREQUAL "0")
  message(FATAL_ERROR "FMT_RUNTIME_REGRESSION: ${test_status}")
endif ()
"""


def read_record(path):
    record = json.loads(Path(path).read_text())
    case = CASES.get(record["number"])
    if (
        case is None
        or (record["org"], record["repo"]) != ("fmtlib", "fmt")
        or record["base"]["sha"] != case["base_commit"]
        or hashlib.sha256(record["test_patch"].encode()).hexdigest() != case["test_patch_sha256"]
        or hashlib.sha256(record["fix_patch"].encode()).hexdigest() != case["reference_sha256"]
        or sorted(record["run_result"]["passed_tests"]) != list(native_tests(record))
        or sorted(record["fix_patch_result"]["passed_tests"]) != list(native_tests(record))
    ):
        raise ValueError("FMT_RECORD_IDENTITY_MISMATCH")
    return record


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = read_record(args.record)
    case = CASES[record["number"]]
    target = case["compile_target"]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    repository = output / "repository"
    repository.mkdir()
    raw = git(args.repository, "archive", case["base_commit"])
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        archive.extractall(repository, filter="data")
    test_patch = output / "official-test.patch"
    test_patch.write_text(record["test_patch"])
    (output / "reference.patch").write_text(record["fix_patch"])
    write_json(output / "record.json", record)
    git(repository, "init", "--template=", "-q", ".")
    git(repository, "apply", str(test_patch))
    cmake = repository / "test/CMakeLists.txt"
    original = cmake.read_text()
    needle = "  add_test(NAME ${name} COMMAND ${name})\n"
    if original.count(needle) != 1:
        raise ValueError("FMT_CMAKE_LAYOUT_CHANGED")
    cmake.write_text(original.replace(needle, CTEST_ADAPTER.replace("base-test", target)))
    (repository / "test/repropatch-build-test.cmake").write_text(
        COMPILE_TEST.replace("base-test", target)
    )
    git(repository, "add", "-f", ".")
    git(repository, "commit", "-qm", "固定编译回归与 CTest 入口")
    prepared = git(repository, "rev-parse", "HEAD").decode().strip()
    editable = sorted(
        path.relative_to(repository).as_posix()
        for directory in ("include", "src")
        for path in (repository / directory).rglob("*")
        if path.is_file() and path.suffix in {".h", ".hpp", ".cc", ".cpp"}
    )
    issues = "\n\n".join(item["title"] + "\n" + item["body"] for item in record["resolved_issues"])
    prompt = issues + (
        "\n\nEnvironment: source /src; temporary build /build. Tests and CMake files "
        f"are read-only. The {target} CTest node builds and runs the original "
        "regression executable; a compiler error is reported as a test failure.\n"
        "configure: " + " ".join(CONFIGURE) + "\n"
        "build: cmake --build /build --parallel 2\n"
        "verify: " + " ".join(CTEST)
    )
    task = {
        "version": 2,
        "id": f"fmtlib-fmt-{record['number']}",
        "repository": {"path": str(repository), "commit": prepared},
        "environment": {"image": IMAGE, "build_tmpfs_mib": 1024},
        "bug": {"description": prompt},
        "commands": {
            "configure": CONFIGURE,
            "build": ["cmake", "--build", "/build", "--parallel", "2"],
            "reproduce": list(CTEST),
            "verify": list(CTEST),
        },
        "tests": {
            "fail_to_pass": [
                {
                    "name": target,
                    "expected_exit_code": 8,
                    "output_contains": case["compile_signature"],
                },
            ],
            "pass_to_pass": [name for name in native_tests(record) if name != target],
            "protected_paths": ["test/", "CMakeLists.txt", "support/"],
        },
        "files": {
            "readable": ["include/", "src/", "test/", "CMakeLists.txt"],
            "editable": editable,
        },
        "budget": {
            "max_steps": 12,
            "max_tool_calls": 24,
            "wall_seconds": 2400,
            "verification_reserve_seconds": 1200,
            "model_timeout_seconds": 90,
            "command_timeout_seconds": 600,
            "max_output_tokens": 8192,
        },
        "workspace": {"root": str(output / "workspaces")},
        "outputs": {"root": str(output / "runs")},
    }
    path = output / "task.yaml"
    path.write_text(yaml.safe_dump(task, sort_keys=False, allow_unicode=True))
    Task.load(path)
    write_json(
        output / "provenance.json",
        {
            "instance_id": f"fmtlib__fmt-{record['number']}",
            "dataset_revision": "56ff018c04a38e27ada1e9d0a6d5839a51f88f0d",
            "upstream_commit": case["base_commit"],
            "prepared_commit": prepared,
            "image": IMAGE,
            "test_patch_sha256": case["test_patch_sha256"],
            "reference_patch_sha256": case["reference_sha256"],
            "task_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "official_test_phase": "NONE: 编译失败发生在上游测试执行前",
            "adaptation": f"原生 {target} 目标在 CTest 节点内编译及执行",
            "protected_adapter": "test/repropatch-build-test.cmake",
            "native_tests": list(native_tests(record)),
            "runtime_verified": False,
            "model_requests": 0,
        },
    )
    print(json.dumps({"task": str(path), "prepared_commit": prepared}))


if __name__ == "__main__":
    main()
