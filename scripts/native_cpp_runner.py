"""执行受保护的原生 C++ 测试组，保存完整报告并核对冻结的用例身份。"""

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

PARSER_IMPORTS = {"re", "json", "html", "xml.etree", "xml.etree.ElementTree"}


def review_parser(code):
    """原始解析器仅处理文本、JSON 和 XML，执行发生在隔离容器内。"""
    tree = ast.parse(code)
    if (
        len(tree.body) != 1
        or not isinstance(tree.body[0], ast.FunctionDef)
        or tree.body[0].name != "parser"
    ):
        raise ValueError("NATIVE_PARSER_LAYOUT_REVIEW_REQUIRED")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            alias.name not in PARSER_IMPORTS for alias in node.names
        ):
            raise ValueError("NATIVE_PARSER_IMPORT_REJECTED")
        if isinstance(node, ast.ImportFrom) and (node.module not in PARSER_IMPORTS or node.level):
            raise ValueError("NATIVE_PARSER_IMPORT_REJECTED")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ValueError("NATIVE_PARSER_ATTRIBUTE_REJECTED")
        if isinstance(node, ast.Name) and node.id in {
            "open",
            "eval",
            "exec",
            "compile",
            "__import__",
            "globals",
            "locals",
            "getattr",
            "setattr",
            "delattr",
            "breakpoint",
        }:
            raise ValueError("NATIVE_PARSER_IO_REJECTED")
    return tree


def parser_results(code, log):
    tree = review_parser(code)
    namespace = {}
    exec(compile(tree, "frozen-native-log-parser", "exec"), namespace)
    results = namespace["parser"](log)
    if not isinstance(results, dict) or any(
        not isinstance(k, str) or v not in {"pass", "fail", "skip"} for k, v in results.items()
    ):
        raise ValueError("NATIVE_PARSER_RESULT_INVALID")
    return results


def jsoncpp_results(code, log):
    """按 CTest 输出流关联 TESTING 与显式结果，保留原始解析器。"""
    pending, completed = {}, []
    for line in log.splitlines():
        stream = re.match(r"^\s*(\d+)\s*:\s*(.*)$", line)
        if not stream:
            continue
        number, content = stream.groups()
        start = re.match(r"TESTING\s*:\s*(.+?\.json)(?:\s|$)", content)
        if start:
            pending[number] = start[1]
        ending = re.fullmatch(r"(?:.*\.json\s+)?(OK|FAILED|FAIL|ERROR)\s*", content)
        if ending and number in pending:
            path = pending.pop(number)
            completed.append(f"{number}: TESTING: {path} {ending[1]}")
    return parser_results(code, log + "\n" + "\n".join(completed))


def canonical_case(mode, name):
    name = name.replace("/build/native/", "./build/").replace("/src/", "/testbed/")
    if mode == "ninja":
        parts = name.split(".")
        if len(parts) > 1 and parts[-1] == parts[-2]:
            name = ".".join(parts[:-1])
    if mode == "duckdb":
        match = re.search(r"(?:^|[:.])(?:/testbed/)?(test/.+)$", name)
        if match:
            return match[1]
    return name


def ctest_results(log, mode):
    results = {}
    xml = ET.fromstring(log)
    for case in xml.findall(".//testcase"):
        name = canonical_case(mode, case.attrib["name"])
        state = (
            "skip"
            if case.find("skipped") is not None
            else "fail"
            if case.find("failure") is not None or case.find("error") is not None
            else "pass"
        )
        if name in results:
            raise ValueError("NATIVE_CASE_IDENTITY_DUPLICATED")
        results[name] = state
    return results


def normalize_results(mode, results):
    normalized = {}
    for name, state in results.items():
        key = canonical_case(mode, name)
        if key in normalized and normalized[key] != state:
            rank = {"pass": 0, "skip": 1, "fail": 2}
            state = max((normalized[key], state), key=rank.get)
        normalized[key] = state
    return normalized


def match_case_names(expected, observed):
    """优先使用原始身份，大小写别名必须唯一并写入报告。"""
    folded = {}
    for name in observed:
        folded.setdefault(name.casefold(), []).append(name)
    aliases = {}
    for name in expected:
        if name in observed:
            aliases[name] = name
        else:
            matches = folded.get(name.casefold(), [])
            if len(matches) > 1:
                raise ValueError("NATIVE_CASE_ALIAS_AMBIGUOUS")
            if matches:
                aliases[name] = matches[0]
    if len(set(aliases.values())) != len(aliases):
        raise ValueError("NATIVE_CASE_ALIAS_CONFLICT")
    return aliases


def prepare_native(contract, source, build):
    """通过 CMake File API 识别官方新增测试所属目标，构建延迟到对应 CTest 节点。"""
    replies = build / ".cmake/api/v1/reply"
    indexes = sorted(replies.glob("index-*.json"))
    if not indexes:
        raise ValueError("NATIVE_CMAKE_FILE_API_MISSING")
    index = json.loads(indexes[-1].read_text())
    model = json.loads((replies / index["reply"]["codemodel-v2"]["jsonFile"]).read_text())
    changed = set(contract["official_test_paths"])
    deferred = []
    binaries = {}
    for target in model["configurations"][0]["targets"]:
        metadata = json.loads((replies / target["jsonFile"]).read_text())
        for artifact in metadata.get("artifacts", []):
            binaries[Path(artifact["path"]).name] = metadata["name"]
        paths = {
            item["path"].removeprefix(str(source) + "/") for item in metadata.get("sources", [])
        }
        if metadata["type"] == "EXECUTABLE" and paths & changed:
            if not re.fullmatch(r"[A-Za-z0-9_.+-]+", metadata["name"]):
                raise ValueError("NATIVE_BUILD_TARGET_IDENTITY_INVALID")
            deferred.append(metadata["name"])
    result = subprocess.run(
        ["ctest", "--test-dir", str(build), "--show-only=json-v1"],
        capture_output=True,
        text=True,
        check=True,
    )
    inventory = json.loads(result.stdout)
    commands = {test["name"]: test.get("command", []) for test in inventory["tests"]}
    (build / "repropatch-deferred.cmake").write_text(
        "\n".join(
            f"set_property(TARGET {target} PROPERTY EXCLUDE_FROM_ALL TRUE)"
            for target in sorted(deferred)
        )
        + "\n"
    )
    (build / "native-command-contract.json").write_text(
        json.dumps(
            {"deferred_targets": deferred, "commands": commands, "binary_targets": binaries},
            indent=2,
        )
        + "\n"
    )


def group_targets(contract, build, selected):
    metadata = json.loads((build / "native-command-contract.json").read_text())
    targets = set()
    mode = contract["mode"]
    if mode in {"jsoncpp", "ninja", "duckdb", "slang"}:
        targets.update(
            {
                "jsoncpp": ["jsoncpp_test"],
                "ninja": ["ninja_test"],
                "duckdb": ["unittest"],
                "slang": ["slang-test", "slang-test-server"],
            }[mode]
        )
    elif mode == "luau":
        targets.update(
            binary
            for binary in ("Luau.UnitTest", "Luau.Conformance", "Luau.CLI.Test")
            if any(binary + "::" in name for name in selected)
        )
    else:
        by_lower = {name.lower(): name for name in metadata["commands"]}
        for name in selected:
            actual = by_lower.get(name.lower())
            if actual is None:
                raise ValueError("NATIVE_CTEST_IDENTITY_MISSING")
            command = metadata["commands"][actual]
            if command:
                targets.update(
                    metadata["binary_targets"].get(Path(arg).name, "") for arg in command
                )
            else:
                targets.add(metadata["binary_targets"].get(name, name))
    return sorted(targets & set(metadata["deferred_targets"]))


def execute(argv, cwd, report, *, env=None):
    """所有命令采用参数数组，完整标准输出与标准错误写入阶段证据。"""
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("wb") as stream:
        environment = {**os.environ, **(env or {}), "PYTHONUNBUFFERED": "1"}
        result = subprocess.run(
            argv, cwd=cwd, env=environment, stdout=stream, stderr=subprocess.STDOUT
        )
    data = report.read_text(errors="replace")
    print(data, end="", flush=True)
    if result.returncode in {125, 126, 127} or result.returncode < 0:
        raise RuntimeError("NATIVE_PROCESS_INFRASTRUCTURE_ERROR")
    return result.returncode, data


def native_suite(contract, source, build, selected=None):
    """冷 Oracle 执行完整原生套件；F2P 工具执行原生目标或原生筛选器。"""
    mode = contract["mode"]
    reports = build / "repropatch-reports"
    reports.mkdir(exist_ok=True)
    if mode == "ctest":
        xml = reports / "ctest.xml"
        command = [
            "ctest",
            "--test-dir",
            str(build),
            "--output-on-failure",
            "--no-tests=error",
            "--output-junit",
            str(xml),
        ]
        if selected:
            inventory = subprocess.run(
                ["ctest", "--test-dir", str(build), "--show-only=json-v1"],
                capture_output=True,
                text=True,
                check=True,
            )
            names = {test["name"]: None for test in json.loads(inventory.stdout)["tests"]}
            aliases = match_case_names(selected, names)
            if set(aliases) != set(selected):
                raise ValueError("NATIVE_CTEST_IDENTITY_MISSING")
            command += ["-R", "^(" + "|".join(re.escape(name) for name in aliases.values()) + ")$"]
        code, _ = execute(command, build, reports / "ctest.log")
        if code not in {0, 8} or not xml.exists():
            raise RuntimeError("NATIVE_CTEST_NOT_EXECUTED")
        raw = xml.read_text()
        print(raw, flush=True)
        return ctest_results(raw, mode)
    if (
        mode == "jsoncpp"
        and selected
        and all(name.startswith("jsoncpp_test::") for name in selected)
    ):
        command = [str(build / "bin/jsoncpp_test")]
        for name in selected:
            command += ["--test", name.split("::", 1)[1]]
        _, log = execute(command, build, reports / "jsoncpp.log")
        return jsoncpp_results(contract["parser"], log)
    if mode == "jsoncpp":
        inventory = subprocess.run(
            ["ctest", "--test-dir", str(build), "--show-only=json-v1"],
            capture_output=True,
            text=True,
            check=True,
        )
        tests = json.loads(inventory.stdout)["tests"]
        fixtures = build / "repropatch-fixtures/test"
        shutil.copytree(source / "test", fixtures, dirs_exist_ok=True)
        output, commands = [], []
        for index, test in enumerate(tests, 1):
            command = []
            for argument in test["command"]:
                path = Path(argument)
                if (
                    path.is_absolute()
                    and path.resolve().is_relative_to((source / "test").resolve())
                    and path.is_dir()
                ):
                    argument = str(
                        fixtures / path.resolve().relative_to((source / "test").resolve())
                    )
                command.append(argument)
            code, log = execute(command, fixtures, reports / f"jsoncpp-{index}.log")
            output.append(f"Start {index}: {test['name']}\n")
            output.extend(f"{index}: {line}\n" for line in log.splitlines())
            status = "Passed" if code == 0 else "Failed"
            output.append(f"{index}/{len(tests)} Test #{index}: {test['name']} ... {status}\n")
            commands.append({"original": test["command"], "executed": command, "exit_code": code})
        (reports / "jsoncpp-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        return jsoncpp_results(contract["parser"], "".join(output))
    if mode == "ninja":
        report = reports / "gtest.json"
        command = [str(build / "ninja_test"), "--gtest_output=json:" + str(report)]
        if selected:
            command += ["--gtest_filter=" + ":".join(selected)]
        _, log = execute(command, build, reports / "gtest.log")
        if report.exists():
            log += "\n" + report.read_text()
        if not selected:
            for folder in ("misc", "tests/restat"):
                _, output = execute(
                    [
                        "python3",
                        "-m",
                        "unittest",
                        "discover",
                        "-v",
                        "-s",
                        str(source / folder),
                        "-p",
                        "*_test.py" if folder == "misc" else "test_*.py",
                    ],
                    build,
                    reports / (folder.replace("/", "-") + ".log"),
                )
                log += "\n" + output
        return parser_results(contract["parser"], log)
    if mode == "luau":
        output = []
        for binary in ("Luau.UnitTest", "Luau.Conformance", "Luau.CLI.Test"):
            cases = [name for name in (selected or []) if binary + "::" in name]
            if selected and not cases:
                continue
            xml = reports / (binary + ".xml")
            command = [
                str(build / binary),
                "--reporters=junit",
                "--no-colors=true",
                "--out=" + str(xml),
            ]
            if cases:
                command += ["--test-case=" + ",".join(name.rsplit("::", 1)[1] for name in cases)]
            _, log = execute(command, source, reports / (binary + ".log"))
            if not xml.exists():
                raise RuntimeError("NATIVE_JUNIT_MISSING")
            output.append(xml.read_text())
            print(output[-1], flush=True)
        return parser_results(contract["parser"], "\n".join(output))
    if mode == "duckdb":
        xml = reports / "duckdb.xml"
        command = [str(build / "test/unittest")]
        if selected:
            command += [",".join(canonical_case(mode, name) for name in selected)]
        command += ["--reporter", "junit", "--out", str(xml)]
        environment = {
            **os.environ,
            "DUCKDB_INSTALL_LIB": str(build / "src/libduckdb.so"),
            "DUCKDB_TEST_DIRECTORY": str(build / "duckdb_unittest_tempdir"),
        }
        _, _ = execute(command, source, reports / "duckdb.log", env=environment)
        if not xml.exists():
            raise RuntimeError("NATIVE_JUNIT_MISSING")
        log = xml.read_text()
        print(log, flush=True)
        return parser_results(contract["parser"], log)
    if mode == "slang":
        command = [str(build / "Release/bin/slang-test"), *contract["test_arguments"]]
        if selected:
            prefixes = sorted({re.sub(r"\s+\([^)]*\)$", "", name) for name in selected})
            if len(prefixes) != 1:
                raise ValueError("SLANG_TARGET_FILTER_REVIEW_REQUIRED")
            command += [prefixes[0]]
        _, log = execute(command, source, reports / "slang.log")
        return parser_results(contract["parser"], log)
    raise ValueError("NATIVE_REPOSITORY_ADAPTER_REQUIRED")


def run_group(contract, source, build, group):
    selected = contract["groups"][group]
    targets = group_targets(contract, build, selected)
    if targets:
        code, output = execute(
            ["cmake", "--build", str(build), "--target", *targets, "--parallel", "2"],
            build,
            build / "repropatch-reports" / (group.replace("/", "_") + "-build.log"),
        )
        if code:
            if not re.search(r"error:|undefined reference|ld: .*error", output, re.I):
                print("REPROPATCH_NATIVE_NOT_EXECUTED: 原生目标构建中断", flush=True)
                return 3
            print("REPROPATCH_NATIVE_REGRESSION_FAILED: 编译回归", flush=True)
            return 1
    full = group == "native-p2p"
    observed = normalize_results(
        contract["mode"], native_suite(contract, source, build, None if full else selected)
    )
    expected = {canonical_case(contract["mode"], name): name for name in selected}
    aliases = match_case_names(expected, observed)
    missing = set(expected) - aliases.keys()
    if missing:
        print("REPROPATCH_NATIVE_NOT_EXECUTED: " + json.dumps(sorted(missing)), flush=True)
        return 3
    failures = sorted(name for name in expected if observed[aliases[name]] != "pass")
    if failures:
        print("REPROPATCH_NATIVE_REGRESSION_FAILED: " + json.dumps(failures), flush=True)
        return 1
    print(
        "REPROPATCH_NATIVE_CASE_PASSED: " + json.dumps({"group": group, "cases": len(expected)}),
        flush=True,
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--group")
    parser.add_argument("--oracle", action="store_true")
    parser.add_argument("--prepare-native", action="store_true")
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    temporary = args.build / "repropatch-tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(temporary)
    if args.prepare_native:
        prepare_native(contract, args.source, args.build)
        return 0
    if args.group:
        return run_group(contract, args.source, args.build, args.group)
    if not args.oracle:
        parser.error("选择一个测试组或完整冷 Oracle")
    observed = normalize_results(contract["mode"], native_suite(contract, args.source, args.build))
    expected = {
        canonical_case(contract["mode"], name): name for name in contract["required_native_tests"]
    }
    aliases = match_case_names(expected, observed)
    missing = sorted(set(expected) - aliases.keys())
    extra_failures = sorted(
        name for name, state in observed.items() if name not in aliases.values() and state == "fail"
    )
    result = {
        "tests": {
            original: {"pass": "passed", "fail": "failed", "skip": "skipped"}[
                observed[aliases[key]]
            ]
            for key, original in expected.items()
            if key in aliases
        },
        "case_aliases": {key: value for key, value in aliases.items() if key != value},
        "missing": missing,
        "additional_failures": extra_failures,
    }
    (args.build / "native-results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        "REPROPATCH_NATIVE_INVENTORY: "
        + json.dumps({"expected": len(expected), "observed": len(observed)}),
        flush=True,
    )
    return (
        3
        if missing or extra_failures
        else 0
        if all(state == "passed" for state in result["tests"].values())
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
