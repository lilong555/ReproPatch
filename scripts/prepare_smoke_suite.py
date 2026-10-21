"""从固定上游提交准备五题适配 smoke，不计公开 Benchmark 成绩。"""

import argparse
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def git(directory, *args):
    return subprocess.check_output(["git", "-C", str(directory), *args])


def prepare(suite, case, upstream, output):
    source = upstream / case["project"]
    assert (
        git(source, "rev-parse", case["fix_commit"] + "^").decode().strip() == case["base_commit"]
    )
    repository = output / "repositories" / case["id"]
    repository.mkdir(parents=True, exist_ok=False)
    with tarfile.open(fileobj=io.BytesIO(git(source, "archive", case["base_commit"]))) as archive:
        archive.extractall(repository, filter="data")
    evaluator = repository / "benchmark"
    evaluator.mkdir()
    original_cmake = repository / "CMakeLists.txt"
    (evaluator / "upstream-CMakeLists.txt").write_bytes(original_cmake.read_bytes())
    original_cmake.write_text(
        "cmake_minimum_required(VERSION 3.20)\n"
        "project(upstream_benchmark LANGUAGES CXX)\n"
        "enable_testing()\nadd_subdirectory(benchmark)\n"
    )
    cases = ROOT / "benchmarks/cases"
    for target, origin in (
        ("regression.cpp", cases / (case["id"] + ".cpp")),
        ("control.cpp", cases / case["project"] / "control.cpp"),
    ):
        (evaluator / target).write_bytes(origin.read_bytes())
    project = case["project"]
    sources = {"fmt": "", "pugixml": "../src/pugixml.cpp", "tinyxml2": "../tinyxml2.cpp"}[project]
    includes = {"fmt": "../include", "pugixml": "../src", "tinyxml2": ".."}[project]
    cmake = f"""cmake_minimum_required(VERSION 3.20)
project(upstream_regression LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${{CMAKE_BINARY_DIR}}")
enable_testing()
add_executable(control control.cpp {sources})
add_executable(regression EXCLUDE_FROM_ALL regression.cpp {sources})
foreach(target control regression)
  target_include_directories(${{target}} PRIVATE {includes})
  target_compile_definitions(${{target}} PRIVATE FMT_HEADER_ONLY)
endforeach()
foreach(name regression ordinary boundary)
  add_test(NAME ${{name}} COMMAND ${{CMAKE_COMMAND}}
    -DCASE=${{name}} -DBUILD=${{CMAKE_BINARY_DIR}}
    -P ${{CMAKE_CURRENT_SOURCE_DIR}}/run.cmake)
endforeach()
"""
    (evaluator / "CMakeLists.txt").write_text(cmake)
    (evaluator / "run.cmake").write_text("""if(CASE STREQUAL "regression")
  set(target regression)
else()
  set(target control)
endif()
execute_process(COMMAND "${CMAKE_COMMAND}" --build "${BUILD}"
  --target "${target}" --parallel 2
  RESULT_VARIABLE built OUTPUT_VARIABLE output ERROR_VARIABLE error)
if(NOT built STREQUAL "0")
  message("${output}\\n${error}")
  message(FATAL_ERROR "upstream regression reproduced: compile failure")
endif()
if(CASE STREQUAL "boundary")
  execute_process(COMMAND "${BUILD}/${target}" boundary
    RESULT_VARIABLE result OUTPUT_VARIABLE output ERROR_VARIABLE error)
else()
  execute_process(COMMAND "${BUILD}/${target}"
    RESULT_VARIABLE result OUTPUT_VARIABLE output ERROR_VARIABLE error)
endif()
if(NOT result STREQUAL "0")
  message("${output}\\n${error}")
  message(FATAL_ERROR "upstream regression reproduced: ${result}")
endif()
""")
    git(repository, "init", "-q")
    git(repository, "add", ".")
    git(
        repository,
        "-c",
        "user.name=Benchmark",
        "-c",
        "user.email=benchmark@example.invalid",
        "commit",
        "-qm",
        "固定上游缺陷与只读验收探针",
    )
    commit = git(repository, "rev-parse", "HEAD").decode().strip()
    editable = sorted(
        p.relative_to(repository).as_posix()
        for p in repository.rglob("*")
        if p.is_file()
        and p.suffix in {".cpp", ".h", ".hpp"}
        and (
            p.relative_to(repository).parts[0] in {"src", "include"}
            or p.name in {"tinyxml2.cpp", "tinyxml2.h"}
        )
    )
    readable = editable + ["benchmark/", "CMakeLists.txt"]
    task = {
        "version": 2,
        "id": case["id"],
        "repository": {"path": str(repository), "commit": commit},
        "environment": {
            "image": suite["image"],
            "cpu_limit": 2.0,
            "memory_mib": 2048,
            "pids_limit": 128,
            "build_tmpfs_mib": 1024,
        },
        "bug": {
            "description": case["description"]
            + " 可运行固定 verify 命令检查；只修改允许的生产源码，勿修改测试与构建配置。"
        },
        "commands": {
            "configure": ["cmake", "-S", "/src", "-B", "/build", "-DCMAKE_BUILD_TYPE=Debug"],
            "build": ["cmake", "--build", "/build", "--parallel", "2"],
            "reproduce": [
                "ctest",
                "--test-dir",
                "/build",
                "--output-on-failure",
                "--no-tests=error",
            ],
            "verify": ["ctest", "--test-dir", "/build", "--output-on-failure", "--no-tests=error"],
        },
        "tests": {
            "fail_to_pass": [
                {
                    "name": "regression",
                    "expected_exit_code": 8,
                    "output_contains": "upstream regression reproduced",
                }
            ],
            "pass_to_pass": ["ordinary", "boundary"],
            "protected_paths": ["benchmark/", "CMakeLists.txt"],
        },
        "files": {"readable": readable, "editable": editable},
        "budget": {
            "max_steps": 12,
            "max_tool_calls": 24,
            "wall_seconds": 420,
            "verification_reserve_seconds": 120,
            "model_timeout_seconds": 45,
            "command_timeout_seconds": 60,
            "max_output_tokens": 2048,
        },
        "workspace": {"root": str(output / "workspaces")},
        "outputs": {"root": str(output / "runs")},
    }
    tasks = output / "tasks"
    tasks.mkdir(exist_ok=True)
    path = tasks / (case["id"] + ".yaml")
    path.write_text(yaml.safe_dump(task, allow_unicode=True, sort_keys=False))
    patch = git(source, "diff", case["base_commit"], case["fix_commit"], "--", *editable)
    assert patch
    gold = output / "reference-patches"
    gold.mkdir(exist_ok=True)
    (gold / (case["id"] + ".patch")).write_bytes(patch)
    return {
        **case,
        "prepared_commit": commit,
        "task": str(path),
        "task_yaml_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "reference_patch_sha256": hashlib.sha256(patch).hexdigest(),
        "upstream_url": case["repository"].removesuffix(".git") + "/commit/" + case["fix_commit"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, default=ROOT / ".repropatch/upstream")
    parser.add_argument("--output", type=Path, default=ROOT / ".repropatch/benchmark")
    args = parser.parse_args()
    suite = json.loads((ROOT / "benchmarks/smoke-suite.json").read_text())
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    records = [
        prepare(suite, case, args.upstream.resolve(), args.output) for case in suite["tasks"]
    ]
    manifest = {"suite": suite["name"], "status": "prepared_not_executed", "tasks": records}
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({"prepared": len(records), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
