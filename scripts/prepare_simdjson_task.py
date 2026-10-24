"""固定 simdjson 实例、离线依赖和原生 CTest，生成泛化任务。"""

import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path

import yaml
from prepare_fmt_task import IMAGE
from prepare_multiswe_task import git

from repropatch.task import Task

DATA_COMMIT = "a5b13babe65c1bba7186b41b43d4cbdc20a5c470"
CASES = {
    2178: {
        "base": "bf7834179c1f8fc523c9fd73d29b46348ae1d576",
        "test_sha": "4f01c78195b6d33b3c7af22d599e1b311e7f2936b9c5865a9c258a49aae0b092",
        "reference_sha": "50c86f0f6681b1b3298e253d1c741572d868c78371f64459d29daa5da1dac18c",
        "f2p": ("pointercheck", "ondemand_json_pointer_tests"),
        "failure_marker": "issue 2154",
        "native_count": 99,
    },
    1899: {
        "base": "5809e51ae405d763700ec19083009a2a1cdbfdbc",
        "test_sha": "6538c27467d7756d925288815c8bcaa89d1e70e4ccf1b6e45d4bba09d859e5bf",
        "reference_sha": "d07fef0e6a7a12b4d31d79dc3d399f315925ef97624eaf82c0c44ce698047b6a",
        "f2p": ("basictests",),
        "failure_marker": "Failed",
        "native_count": 93,
    },
}
CONFIGURE = [
    "cmake",
    "-S",
    "/src",
    "-B",
    "/build",
    "-DSIMDJSON_DEVELOPER_MODE=ON",
    "-DSIMDJSON_COMPETITION=OFF",
    "-DSIMDJSON_GOOGLE_BENCHMARKS=OFF",
    "-DCMAKE_BUILD_TYPE=Release",
]
CTEST = ["ctest", "--test-dir", "/build", "--output-on-failure", "--no-tests=error"]


def record_file(path, number=None):
    if path.suffix == ".jsonl":
        if number is None:
            raise ValueError("SIMDJSON_JSONL_REQUIRES_NUMBER")
        record = next(
            row
            for row in map(json.loads, path.read_text().splitlines())
            if row.get("number") == number
        )
    else:
        record = json.loads(path.read_text())
        number = record["number"] if number is None else number
    case = CASES[number]
    if (record["org"], record["repo"], record["number"], record["base"]["sha"]) != (
        "simdjson",
        "simdjson",
        number,
        case["base"],
    ) or any(
        hashlib.sha256(record[k].encode()).hexdigest() != h
        for k, h in (("test_patch", case["test_sha"]), ("fix_patch", case["reference_sha"]))
    ):
        raise ValueError("SIMDJSON_RECORD_IDENTITY")
    required = set(record["run_result"]["passed_tests"])
    if (
        len(required) != case["native_count"]
        or required != set(record["fix_patch_result"]["passed_tests"])
        or not set(case["f2p"]) <= required
    ):
        raise ValueError("SIMDJSON_NATIVE_TEST_IDENTITY")
    return record


def archive(repository, commit, target):
    with tarfile.open(fileobj=io.BytesIO(git(repository, "archive", commit))) as data:
        data.extractall(target, filter="data")


def adapt_environment(source):
    """保留原生测试，将编译输出和大样本临时文件放进可写构建空间。"""
    quickstart = source / "examples/quickstart/add_quickstart_test.cmake"
    original = quickstart.read_text()
    needle = "${PROJECT_SOURCE_DIR}/src/simdjson.cpp ${SOURCE_FILE}\n"
    if original.count(needle) != 1:
        raise ValueError("SIMDJSON_QUICKSTART_LAYOUT")
    quickstart.write_text(
        original.replace(
            needle,
            "${PROJECT_SOURCE_DIR}/src/simdjson.cpp ${SOURCE_FILE} "
            "-o ${PROJECT_BINARY_DIR}/${TEST_NAME}\n",
        )
    )
    cmake = source / "tests/dom/CMakeLists.txt"
    with cmake.open("a") as stream:
        stream.write(
            "\nset_tests_properties(testjson2json PROPERTIES ENVIRONMENT "
            '"TMPDIR=${PROJECT_BINARY_DIR}")\n'
        )


def adapt_individual_ctest(source):
    """构建阶段已生成依赖；为逐项验收清除指向构建目标和源码文件的排序属性。"""
    dom = source / "tests/dom/CMakeLists.txt"
    with dom.open("a") as stream:
        stream.write('\nset_property(TEST testjson2json PROPERTY DEPENDS "")\n')
    quickstart = source / "examples/quickstart/add_quickstart_test.cmake"
    value = quickstart.read_text()
    needle = (
        "    APPEND PROPERTY DEPENDS simdjson-source "
        "${PROJECT_SOURCE_DIR}/examples/quickstart/${SOURCE_FILE}\n"
    )
    if value.count(needle) != 1:
        raise ValueError("SIMDJSON_DEPENDENCY_LAYOUT")
    quickstart.write_text(value.replace(needle, '    PROPERTY DEPENDS ""\n'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--data-repository", type=Path, required=True)
    parser.add_argument("--cxxopts-repository", type=Path, required=True)
    parser.add_argument("--number", type=int, choices=sorted(CASES), default=2178)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    case = CASES[args.number]
    record = record_file(args.record, args.number)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "repository"
    archive(args.repository, case["base"], source)
    archive(args.data_repository, DATA_COMMIT, source / "dependencies/.cache/simdjson-data")
    cxxopts = git(args.cxxopts_repository, "rev-parse", "794c975^{commit}").decode().strip()
    archive(args.cxxopts_repository, cxxopts, source / "dependencies/.cache/cxxopts")
    for name, value in (
        ("official-test.patch", record["test_patch"]),
        ("reference.patch", record["fix_patch"]),
    ):
        (output / name).write_text(value)
    (output / "record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    git(source, "init", "--template=", "-q", ".")
    git(source, "apply", str(output / "official-test.patch"))
    adapt_environment(source)
    adapt_individual_ctest(source)
    git(source, "add", "-f", ".")
    git(source, "commit", "-qm", "固定上游回归与离线依赖")
    prepared = git(source, "rev-parse", "HEAD").decode().strip()
    editable = sorted(
        p.relative_to(source).as_posix()
        for area in ("include", "src")
        for p in (source / area).rglob("*")
        if p.is_file() and p.suffix in {".h", ".cpp"}
    )
    required = sorted(record["run_result"]["passed_tests"])
    f2p = case["f2p"]
    description = "\n\n".join(i["title"] + "\n" + i["body"] for i in record["resolved_issues"])
    task = {
        "version": 2,
        "id": f"simdjson-simdjson-{args.number}",
        "repository": {"path": str(source), "commit": prepared},
        "environment": {"image": IMAGE, "build_tmpfs_mib": 1024},
        "bug": {
            "description": description + "\n\nSource /src; temporary build /build. "
            "Tests, CMake files and offline dependencies are read-only.\nconfigure: "
            + " ".join(CONFIGURE)
            + "\nbuild: cmake --build /build --parallel 2\nverify: "
            + " ".join(CTEST)
        },
        "commands": {
            "configure": CONFIGURE,
            "build": ["cmake", "--build", "/build", "--parallel", "2"],
            "reproduce": list(CTEST),
            "verify": list(CTEST),
        },
        "tests": {
            "fail_to_pass": [
                {
                    "name": n,
                    "expected_exit_code": 8,
                    "output_contains": case["failure_marker"],
                }
                for n in f2p
            ],
            "pass_to_pass": sorted(set(required) - set(f2p)),
            "protected_paths": ["tests/", "examples/", "cmake/", "dependencies/", "CMakeLists.txt"],
        },
        "files": {
            "readable": ["include/", "src/", "tests/", "CMakeLists.txt"],
            "editable": editable,
        },
        "budget": {
            "max_steps": 12,
            "max_tool_calls": 24,
            "wall_seconds": 3600,
            "verification_reserve_seconds": 1800,
            "model_timeout_seconds": 90,
            "command_timeout_seconds": 900,
            "max_output_tokens": 8192,
        },
        "workspace": {"root": str(output / "workspaces")},
        "outputs": {"root": str(output / "runs")},
    }
    path = output / "task.yaml"
    path.write_text(yaml.safe_dump(task, sort_keys=False, allow_unicode=True))
    Task.load(path)
    provenance = {
        "instance_id": f"simdjson__simdjson-{args.number}",
        "upstream_commit": case["base"],
        "prepared_commit": prepared,
        "image": IMAGE,
        "native_required_tests": required,
        "test_patch_sha256": hashlib.sha256(record["test_patch"].encode()).hexdigest(),
        "reference_patch_sha256": hashlib.sha256(record["fix_patch"].encode()).hexdigest(),
        "dependencies": {"simdjson-data": DATA_COMMIT, "cxxopts": cxxopts},
        "dataset_revision": "56ff018c04a38e27ada1e9d0a6d5839a51f88f0d",
        "selection": (
            "第三仓库固定数据文件首条；核心6c13冻结后选定"
            if args.number == 2178
            else "预注册新任务样本；策略源码冻结后选定"
        ),
        "model_requests": 0,
    }
    (output / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({"task": str(path), "prepared_commit": prepared}))


if __name__ == "__main__":
    main()
