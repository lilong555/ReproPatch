"""项目原生构建合同、受保护 CTest 分组和离线源码准备。"""

import hashlib
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

from cpp_sources import CPP_SUFFIXES, PRODUCTION_AREAS, production_path
from native_cpp_runner import canonical_case, review_parser
from qualify_cpp_batch import archive, git, save
from screen_multiswe import patch_paths

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = {
    "open-source-parsers/jsoncpp": [
        "-DJSONCPP_WITH_TESTS=ON",
        "-DJSONCPP_WITH_POST_BUILD_UNITTEST=OFF",
        "-DJSONCPP_WITH_WARNING_AS_ERROR=OFF",
    ],
    "ninja-build/ninja": ["-DBUILD_TESTING=ON"],
    "stephenberry/glaze": [
        "-Dglaze_DEVELOPER_MODE=ON",
        "-Dglaze_ENABLE_SANITIZERS=OFF",
        "-Dglaze_USE_BUNDLED_ASIO=OFF",
        "-DFETCHCONTENT_SOURCE_DIR_UT=/opt/cpp-deps/ut",
        "-DFETCHCONTENT_SOURCE_DIR_YAML_TEST_SUITE=/opt/cpp-deps/yaml-test-suite",
        "-DCMAKE_PROJECT_INCLUDE=/src/repropatch-native/runtime.cmake",
    ],
    "luau-lang/luau": ["-DLUAU_BUILD_TESTS=ON", "-DLUAU_BUILD_CLI=ON"],
    "duckdb/duckdb": [
        "-DBUILD_UNITTESTS=ON",
        "-DENABLE_SANITIZER=OFF",
        "-DENABLE_UBSAN=OFF",
        "-DCMAKE_CXX_STANDARD=17",
        "-DENABLE_EXTENSION_AUTOINSTALL=OFF",
        "-DENABLE_EXTENSION_AUTOLOADING=OFF",
        "-DCMAKE_PROJECT_INCLUDE=/src/repropatch-native/runtime.cmake",
    ],
    "shader-slang/slang": [
        "-DSLANG_ENABLE_TESTS=ON",
        "-DSLANG_ENABLE_EXAMPLES=OFF",
        "-DSLANG_ENABLE_CUDA=OFF",
        "-DSLANG_ENABLE_OPTIX=OFF",
        "-DSLANG_RHI_ENABLE_CUDA=OFF",
        "-DSLANG_RHI_ENABLE_OPTIX=OFF",
        "-DSLANG_ENABLE_DXIL=OFF",
        "-DSLANG_EXCLUDE_DAWN=ON",
        "-DSLANG_SLANG_LLVM_FLAVOR=FETCH_BINARY",
        "-DSLANG_SLANG_LLVM_BINARY_URL=/opt/cpp-deps/libslang-llvm.so",
    ],
    "nlohmann/json": [
        "-DJSON_BuildTests=ON",
        "-DJSON_MultipleHeaders=ON",
        "-DJSON_TestDataDirectory=/opt/json-test-data",
    ],
    "simdjson/simdjson": [
        "-DSIMDJSON_DEVELOPER_MODE=ON",
        "-DSIMDJSON_COMPETITION=OFF",
        "-DSIMDJSON_GOOGLE_BENCHMARKS=OFF",
    ],
    "catchorg/Catch2": ["-DCATCH_DEVELOPMENT_BUILD=ON", "-DCATCH_BUILD_TESTING=ON"],
    "pocoproject/poco": ["-DENABLE_TESTS=ON", "-DENABLE_PDF=OFF", "-DCMAKE_CXX_STANDARD=20"],
}
MODES = {
    "open-source-parsers/jsoncpp": "jsoncpp",
    "ninja-build/ninja": "ninja",
    "duckdb/duckdb": "duckdb",
    "shader-slang/slang": "slang",
    "luau-lang/luau": "luau",
}


def recipe(record, *, cxx="clang++-19", cc="clang-19", optimization="O3"):
    repo = record["org"] + "/" + record["repo"]
    if repo not in OPTIONS:
        raise ValueError("NATIVE_REPOSITORY_ADAPTER_REQUIRED")
    if repo in {"nlohmann/json", "catchorg/Catch2"} and cxx == "clang++-19" and cc == "clang-19":
        # 固定历史测试的编译器，嵌套 CMake 用例沿用同一标准库。
        cxx, cc = "g++-11", "gcc-11"
    compiler_options = []
    if cxx.startswith("clang"):
        if repo == "stephenberry/glaze":
            # 上游 Clang 构建采用 libc++，避免跨标准库的模板兼容性差异。
            compiler_options = [
                "-DCMAKE_CXX_FLAGS=-stdlib=libc++ -DASIO_DISABLE_STD_NESTED_EXCEPTION"
            ]
        elif repo == "catchorg/Catch2":
            compiler_options = ["-DCMAKE_CXX_FLAGS=-Wno-error=deprecated-literal-operator"]
    return {
        "repository": repo,
        "mode": MODES.get(repo, "ctest"),
        "configure": [
            "cmake",
            "-S",
            "/src",
            "-B",
            "/build",
            "-G",
            "Ninja",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            f"-DCMAKE_CXX_COMPILER={cxx}",
            f"-DCMAKE_C_COMPILER={cc}",
            f"-DCMAKE_CXX_FLAGS_RELEASE=-{optimization} -DNDEBUG",
            f"-DCMAKE_C_FLAGS_RELEASE=-{optimization} -DNDEBUG",
            *compiler_options,
            *OPTIONS[repo],
        ],
        "memory_mib": 8192,
        "build_tmpfs_mib": 4096,
        "build_jobs": 2,
        "pids_limit": 4096 if repo == "ninja-build/ninja" else 256,
    }


def prepare_source_dependencies(record, source, pool, *, deadline):
    """源码快照携带固定离线输入，原生测试的运行产物使用构建目录。"""
    repository = record["org"] + "/" + record["repo"]
    if repository == "nlohmann/json":
        from prepare_json_task import adapt

        adapt(source)
        return []
    if repository != "simdjson/simdjson":
        return []
    from prepare_simdjson_task import adapt_environment, adapt_individual_ctest

    dependencies = []
    for name, repo, commit in (
        ("simdjson-data", "simdjson/simdjson-data", "a5b13babe65c1bba7186b41b43d4cbdc20a5c470"),
        ("cxxopts", "jarro2783/cxxopts", "794c975287355de48158d9a80ed502d26b20a472"),
    ):
        location = "dependencies/.cache/" + name
        children = materialize(repo, commit, source / location, pool, deadline=deadline)
        dependencies.append(
            {
                "path": location,
                "url": "https://github.com/" + repo,
                "commit": commit,
                "dependencies": children,
            }
        )
    adapt_environment(source)
    adapt_individual_ctest(source)
    return dependencies


def make_contract(record, configuration):
    required = sorted(record["fix_patch_result"]["passed_tests"])
    if not required or len(required) != len(set(required)):
        raise ValueError("NATIVE_REQUIRED_TEST_IDENTITY_INVALID")
    mode = configuration["mode"]
    f2p = sorted(record.get("declared_f2p", []))
    p2p = sorted(record.get("declared_p2p", []))
    if record.get("dataset") == "SWE-bench-Live/MultiLang" and (not f2p or not p2p):
        raise ValueError("NATIVE_DECLARED_TEST_SPLIT_EMPTY")
    probes = sorted(name for name in required if name.lower().startswith("have_flag_"))
    required = [name for name in required if name not in probes]
    if mode == "ctest":
        groups = {name: [name] for name in required}
    else:
        if not f2p or not p2p or sorted(f2p + p2p) != required:
            raise ValueError("NATIVE_DECLARED_TEST_IDENTITY_INVALID")
        groups = {f"native-f2p-{index:03d}": [name] for index, name in enumerate(f2p, 1)}
        groups["native-p2p"] = p2p
    parser = record.get("native_log_parser", "") if mode != "ctest" else ""
    if parser:
        review_parser(parser)
    contract = {
        "schema": "repropatch.native-cpp-contract.v1",
        "mode": mode,
        "required_native_tests": required,
        "declared_native_f2p": f2p,
        "declared_native_p2p": p2p,
        "configuration_probes": probes,
        "groups": groups,
        "parser": parser,
        "parser_sha256": hashlib.sha256(parser.encode()).hexdigest() if parser else None,
        "log_stream_policy": "ctest-stream-pairing-v1" if mode == "jsoncpp" else "native-v1",
        "configuration": configuration,
        "official_test_paths": patch_paths(record["test_patch"])[0],
    }
    if mode == "slang":
        contract["test_arguments"] = [
            "-use-test-server",
            "-server-count",
            "2",
            "-category",
            "full",
            "-expected-failure-list",
            "tests/expected-failure-github.txt",
            "-expected-failure-list",
            "tests/expected-failure-no-gpu.txt",
            "-skip-reference-image-generation",
            "-v",
        ]
    normalized = [canonical_case(mode, name) for name in required]
    if len(set(normalized)) != len(normalized):
        raise ValueError("NATIVE_TEST_ALIAS_CONFLICT")
    return contract


def materialize(repo, commit, source, pool, *, deadline):
    """只获取固定 Git 对象，递归子模块的身份按父提交的 gitlink 保存。"""
    parsed = urlsplit(repo if repo.startswith("https:") else "https://github.com/" + repo + ".git")
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or parsed.query
        or parsed.username
        or not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?", parsed.path)
    ):
        raise ValueError("CPP_DEPENDENCY_ENDPOINT_REJECTED")
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("CPP_SOURCE_COMMIT_INVALID")
    name = parsed.path.strip("/").removesuffix(".git").replace("/", "__")
    repository = pool / name
    repository.mkdir(parents=True, exist_ok=True)
    if not (repository / "HEAD").exists():
        git(repository, "init", "--bare", "--template=", "-q", ".", deadline=deadline)
    if not (repository / "refs/repropatch" / commit).is_file():
        git(
            repository,
            "fetch",
            "--depth=1",
            parsed.geturl(),
            commit + ":refs/repropatch/" + commit,
            deadline=deadline,
        )
    archive(repository, commit, source, deadline=deadline)
    dependencies = []
    modules = source / ".gitmodules"
    if modules.exists():
        config = git_submodules(repository, modules, deadline=deadline)
        for section in config.values():
            path, url = section["path"], section["url"]
            if Path(path).is_absolute() or ".." in Path(path).parts:
                raise ValueError("CPP_SUBMODULE_PATH_REJECTED")
            entry = (
                git(repository, "ls-tree", commit, "--", path, deadline=deadline).decode().split()
            )
            if len(entry) != 4 or entry[0] != "160000":
                raise ValueError("CPP_SUBMODULE_IDENTITY_INVALID")
            target = source / path
            if target.exists():
                target.rmdir()
            child = materialize(url, entry[2], target, pool, deadline=deadline)
            dependencies.append(
                {"path": path, "url": url, "commit": entry[2], "dependencies": child}
            )
    return dependencies


def git_submodules(repository, modules, *, deadline):
    """由 Git 解析子模块配置，保持缩进、附加选项与 URL 的原始语义。"""
    output = git(
        repository,
        "config",
        "--no-includes",
        "--file",
        str(modules.resolve()),
        "--null",
        "--list",
        deadline=deadline,
    ).decode()
    config = {}
    for entry in output.split("\0"):
        if not entry:
            continue
        key, value = entry.split("\n", 1)
        section, field = key.rsplit(".", 1)
        if section.startswith("submodule.") and field in {"path", "url"}:
            if field in config.setdefault(section, {}):
                raise ValueError("CPP_SUBMODULE_CONFIGURATION_DUPLICATED")
            config[section][field] = value
    if any(set(section) != {"path", "url"} for section in config.values()):
        raise ValueError("CPP_SUBMODULE_CONFIGURATION_INCOMPLETE")
    return config


def wrapper(source, contract):
    """外层 CTest 保留稳定测试身份，原生构建和测试在独立子构建树执行。"""
    protected = source / "repropatch-native"
    protected.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "scripts/native_cpp_runner.py", protected / "runner.py")
    shutil.copyfile(ROOT / "scripts/native_cpp_runtime.cmake", protected / "runtime.cmake")
    save(protected / "contract.json", contract)
    cmake = source / "CMakeLists.txt"
    original = cmake.read_text()
    if "REPROPATCH_NATIVE_WRAPPER" not in original:
        cmake.write_text(
            "cmake_minimum_required(VERSION 3.22)\n"
            "if(REPROPATCH_NATIVE_WRAPPER)\n"
            "  project(repropatch_native LANGUAGES C CXX)\n"
            "  include(${CMAKE_CURRENT_SOURCE_DIR}/repropatch-native/CTest.cmake)\n"
            "  return()\n"
            "endif()\n" + original + "\nif(REPROPATCH_DEFER_NATIVE_TESTS)\n"
            "  include(${CMAKE_CURRENT_BINARY_DIR}/repropatch-deferred.cmake OPTIONAL)\n"
            "endif()\n"
        )
    arguments = [
        arg
        for arg in contract["configuration"]["configure"][1:]
        if arg not in {"-S", "/src", "-B", "/build"}
    ]
    formatted = "\n".join(
        '  "'
        + arg.replace("/src/", "${CMAKE_CURRENT_SOURCE_DIR}/")
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        + '"'
        for arg in arguments
    )
    lines = [
        "enable_testing()",
        "file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/native/.cmake/api/v1/query)",
        'file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/native/.cmake/api/v1/query/codemodel-v2 "")',
        "execute_process(COMMAND ${CMAKE_COMMAND} -S ${CMAKE_CURRENT_SOURCE_DIR} "
        "-B ${CMAKE_CURRENT_BINARY_DIR}/native",
        formatted,
        '  "-DREPROPATCH_NATIVE_WRAPPER=OFF"',
        '  "-DREPROPATCH_DEFER_NATIVE_TESTS=OFF"',
        '  "-DCMAKE_CXX_COMPILER_LAUNCHER=${CMAKE_CXX_COMPILER_LAUNCHER}"',
        '  "-DCMAKE_C_COMPILER_LAUNCHER=${CMAKE_C_COMPILER_LAUNCHER}"',
        "  RESULT_VARIABLE status)",
        'if(NOT status STREQUAL "0")',
        '  message(FATAL_ERROR "REPROPATCH_NATIVE_CONFIGURE_FAILED: ${status}")',
        "endif()",
        "execute_process(COMMAND python3 -I "
        "${CMAKE_CURRENT_SOURCE_DIR}/repropatch-native/runner.py "
        "--contract ${CMAKE_CURRENT_SOURCE_DIR}/repropatch-native/contract.json "
        "--source ${CMAKE_CURRENT_SOURCE_DIR} --build ${CMAKE_CURRENT_BINARY_DIR}/native "
        "--prepare-native RESULT_VARIABLE status)",
        'if(NOT status STREQUAL "0")',
        '  message(FATAL_ERROR "REPROPATCH_NATIVE_TARGET_DISCOVERY_FAILED: ${status}")',
        "endif()",
        "execute_process(COMMAND ${CMAKE_COMMAND} -S ${CMAKE_CURRENT_SOURCE_DIR} "
        "-B ${CMAKE_CURRENT_BINARY_DIR}/native -DREPROPATCH_DEFER_NATIVE_TESTS=ON "
        "RESULT_VARIABLE status)",
        'if(NOT status STREQUAL "0")',
        '  message(FATAL_ERROR "REPROPATCH_NATIVE_DEFER_CONFIGURATION_FAILED: ${status}")',
        "endif()",
        "add_custom_target(native-build ALL COMMAND ${CMAKE_COMMAND} "
        "--build ${CMAKE_CURRENT_BINARY_DIR}/native --parallel 2)",
    ]
    for group in contract["groups"]:
        escaped = group.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(
            f'add_test(NAME "{escaped}" COMMAND python3 -I '
            "${CMAKE_CURRENT_SOURCE_DIR}/repropatch-native/runner.py "
            "--contract ${CMAKE_CURRENT_SOURCE_DIR}/repropatch-native/contract.json "
            "--source ${CMAKE_CURRENT_SOURCE_DIR} --build ${CMAKE_CURRENT_BINARY_DIR}/native "
            f'--group "{escaped}")'
        )
    (protected / "CTest.cmake").write_text("\n".join(lines) + "\n")


def editable_files(record, source):
    repo = record["org"] + "/" + record["repo"]
    return sorted(
        {
            path.relative_to(source).as_posix()
            for area in PRODUCTION_AREAS[repo]
            for path in (source / area).rglob("*")
            if path.is_file()
            and not path.is_symlink()
            and path.suffix in CPP_SUFFIXES
            and production_path(record, path.relative_to(source).as_posix())
        }
    )


def group_states(contract, native):
    mode = contract["mode"]
    observed = {canonical_case(mode, name): state for name, state in native.items()}
    results = {}
    for group, names in contract["groups"].items():
        states = [observed.get(canonical_case(mode, name), "missing") for name in names]
        results[group] = (
            "passed"
            if set(states) == {"passed"}
            else "failed"
            if "failed" in states and set(states) <= {"passed", "failed"}
            else "infrastructure_error"
        )
    return results


def source_manifest(source):
    return {
        path.relative_to(source).as_posix(): {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size": path.stat().st_size,
        }
        for path in sorted(source.rglob("*"))
        if path.is_file() and ".git" not in path.parts and not path.is_symlink()
    }
