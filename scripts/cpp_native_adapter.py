"""项目原生构建合同、受保护 CTest 分组和离线源码准备。"""

import hashlib
import json
import re
import shlex
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from cpp_sources import CPP_SUFFIXES, PRODUCTION_AREAS, patch_sections, production_path
from native_cpp_runner import canonical_case, review_parser
from qualify_cpp_batch import archive, git, save
from screen_multiswe import patch_paths

from repropatch.workspace import git_blob, git_tree

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = {
    "fmtlib/fmt": ["-DFMT_DOC=OFF", "-DFMT_TEST=ON"],
    "open-source-parsers/jsoncpp": [
        "-DJSONCPP_WITH_TESTS=ON",
        "-DJSONCPP_WITH_POST_BUILD_UNITTEST=OFF",
        "-DJSONCPP_WITH_WARNING_AS_ERROR=OFF",
    ],
    "ninja-build/ninja": ["-DBUILD_TESTING=ON"],
    "KhronosGroup/glslang": ["-DGLSLANG_TESTS=ON", "-DBUILD_WERROR=OFF"],
    "rui314/mold": ["-DBUILD_TESTING=ON", "-DMOLD_ENABLE_QEMU_TESTS=OFF"],
    "actor-framework/actor-framework": [
        "-DCAF_ENABLE_TESTING=ON",
        "-DCAF_ENABLE_EXAMPLES=ON",
        "-DCAF_ENABLE_RUNTIME_CHECKS=ON",
    ],
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
        "-DFETCHCONTENT_SOURCE_DIR_VULKAN_HEADERS=/src/external/repropatch-vulkan-headers",
        "-DFETCHCONTENT_SOURCE_DIR_VULKAN-HEADERS=/src/external/repropatch-vulkan-headers",
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
    "KhronosGroup/glslang": "glslang",
    "duckdb/duckdb": "duckdb",
    "shader-slang/slang": "slang",
    "luau-lang/luau": "luau",
}
NATIVE_TEST_DATA = ("dependencies/.cache/simdjson-data/",)


def initialize_snapshot_git(destination, repository, commit, *, deadline=None):
    """为冷验收源码提供真实的固定 HEAD，保持工作区字节不变。"""
    git(destination, "init", "--template=", "-q", ".", deadline=deadline)
    git(
        destination,
        "fetch",
        "--no-tags",
        str(repository.resolve()),
        commit,
        deadline=deadline,
    )
    git(destination, "update-ref", "--no-deref", "HEAD", commit, deadline=deadline)


def recipe(record, *, cxx="clang++-19", cc="clang-19", optimization="O3"):
    repo = record["org"] + "/" + record["repo"]
    if repo not in OPTIONS:
        raise ValueError("NATIVE_REPOSITORY_ADAPTER_REQUIRED")
    options = list(OPTIONS[repo])
    runtime = {}
    if record.get("instance_id") == "simdjson__simdjson-644":
        options.append("-DENABLE_FUZZING=OFF")
    if record.get("instance_id") == "duckdb__duckdb-23422":
        # 官方任务采用 GCC 13 与 C++23；完整套件预留 14 GiB 容器内存。
        if cxx == "clang++-19" and cc == "clang-19":
            cxx, cc = "g++-13", "gcc-13"
        options = [option for option in options if not option.startswith("-DCMAKE_CXX_STANDARD=")]
        options.append("-DCMAKE_CXX_STANDARD=23")
    if record.get("instance_id") in {
        "shader-slang__slang-10738",
        "shader-slang__slang-10697",
        "shader-slang__slang-10768",
        "shader-slang__slang-10664",
        "shader-slang__slang-10856",
        "shader-slang__slang-7815",
        "shader-slang__slang-10663",
    }:
        # 按官方环境记录选择编译器、LLVM 后端与实际可用的 DXC。
        instance = record["instance_id"]
        legacy = instance in {"shader-slang__slang-10856", "shader-slang__slang-7815"}
        has_dxc = instance not in {"shader-slang__slang-7815", "shader-slang__slang-10663"}
        llvm = "slang-7815" if instance == "shader-slang__slang-7815" else "slang-10738"
        if cxx == "clang++-19" and cc == "clang-19":
            cxx, cc = ("g++-11", "gcc-11") if legacy else ("g++-13", "gcc-13")
        replaced = ("-DSLANG_ENABLE_DXIL=", "-DSLANG_SLANG_LLVM_BINARY_URL=")
        options = [option for option in options if not option.startswith(replaced)]
        options += [
            "-DCMAKE_CXX_FLAGS=-pipe",
            "-DSLANG_ENABLE_DXIL=" + ("ON" if has_dxc else "OFF"),
            "-DSLANG_ENABLE_XLIB=OFF",
            f"-DSLANG_SLANG_LLVM_BINARY_URL=/opt/cpp-deps/{llvm}/libslang-llvm.so",
        ]
        if instance != "shader-slang__slang-7815":
            options.append("-DCMAKE_CXX_STANDARD=23")
        if has_dxc:
            options.append("-DFETCHCONTENT_SOURCE_DIR_DXC=/opt/cpp-deps/slang-10738/dxc")
        runtime["runtime_compiler_directory"] = (
            "/usr/lib/llvm-14/bin" if legacy else "/usr/lib/llvm-18/bin"
        )
    if repo in {"nlohmann/json", "catchorg/Catch2"} and cxx == "clang++-19" and cc == "clang-19":
        # 固定历史测试的编译器，嵌套 CMake 用例沿用同一标准库。
        cxx, cc = "g++-11", "gcc-11"
    if repo == "stephenberry/glaze" and cxx == "clang++-19" and cc == "clang-19":
        # 官方清单包含两个仅在 GNU 编译器下注册的安装测试。
        cxx, cc = "g++-14", "gcc-14"
    compiler_options = []
    if repo == "catchorg/Catch2":
        # 审批报告沿用源码相对路径，输入副本的位置保持独立。
        flags = "-fmacro-prefix-map=/src/="
        if cxx.startswith("clang"):
            flags += " -Wno-error=deprecated-literal-operator"
        if record.get("instance_id") == "catchorg__Catch2-1608":
            flags += " -DCATCH_CONFIG_NO_POSIX_SIGNALS"
        compiler_options = ["-DCMAKE_CXX_FLAGS=" + flags]
    elif record.get("instance_id") in {
        "nlohmann__json-1303",
        "nlohmann__json-1343",
        "nlohmann__json-1446",
        "nlohmann__json-1555",
        "nlohmann__json-2319",
        "nlohmann__json-2332",
        "nlohmann__json-2019",
        "nlohmann__json-2352",
    }:
        # 旧测试框架的信号栈使用静态 SIGSTKSZ；进程信号交由 CTest 记录。
        compiler_options = [
            "-DCMAKE_CXX_FLAGS=-DCATCH_CONFIG_NO_POSIX_SIGNALS -DDOCTEST_CONFIG_NO_POSIX_SIGNALS"
        ]
        if record["instance_id"] in {
            "nlohmann__json-1303",
            "nlohmann__json-1343",
            "nlohmann__json-1446",
            "nlohmann__json-1555",
        }:
            # C++20 allocator 接口兼容旧测试的继承写法，UTF-8 字面量沿用 char 类型。
            options.append("-DCMAKE_CXX_STANDARD=20")
            compiler_options[0] += " -fno-char8_t"
    elif cxx.startswith("clang") and repo == "stephenberry/glaze":
        # 上游 Clang 构建采用 libc++，避免跨标准库的模板兼容性差异。
        # 系统 Asio 使用 make_exception_ptr，却未直接包含 <exception>。
        # 同一构建合同为基线和参考冷验收补齐声明，不修改上游源码或测试。
        compiler_options = [
            "-DCMAKE_CXX_FLAGS=-stdlib=libc++ -DASIO_DISABLE_STD_NESTED_EXCEPTION"
            " -include exception"
        ]
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
            *options,
        ],
        **runtime,
        # 原生 gzip 回归单次写入超过 4 GiB；CSV 缓冲增长需要额外峰值空间。
        "memory_mib": 14336
        if record.get("instance_id") == "duckdb__duckdb-23422"
        else 12288
        if repo in {"duckdb/duckdb", "shader-slang/slang"}
        else 8192,
        "build_tmpfs_mib": 4096,
        # Slang 原生临时文件固定写入 /tmp，主机可调用模块需要执行权限。
        "tmp_executable": repo == "shader-slang/slang",
        "build_jobs": 4 if repo == "shader-slang/slang" else 2,
        # DuckDB 原生并发 DROP 回归同时创建 300 个线程，256 会中断测试进程。
        "pids_limit": 4096 if repo in {"ninja-build/ninja", "duckdb/duckdb"} else 256,
        # 冷编译与完整原生套件共享阶段期限；DuckDB 的 O3 编译可耗时约 25 分钟。
        "phase_timeout_seconds": 3600 if repo == "duckdb/duckdb" else 1800,
        "qualification_timeout_seconds": 9000 if repo == "duckdb/duckdb" else 5400,
    }


def prepare_source_dependencies(record, source, pool, *, deadline):
    """源码快照携带固定离线输入，原生测试的运行产物使用构建目录。"""
    repository = record["org"] + "/" + record["repo"]
    if record.get("instance_id") == "catchorg__Catch2-1608":
        # 官方提交将审批期望值放在修复补丁中；这些文件属于受保护的测试输入。
        sections = [
            (name, section)
            for name, section in patch_sections(record["fix_patch"])
            if re.fullmatch(r"projects/SelfTest/Baselines/[^/]+\.approved\.txt", name)
        ]
        if not sections:
            raise ValueError("CATCH_APPROVAL_EXPECTATIONS_REQUIRED")
        patch = "".join(section for _, section in sections)
        # 固定独立 Git 根目录，确保补丁路径相对于本题源码解析。
        git(source, "init", "--template=", "-q", ".", deadline=deadline)
        with tempfile.TemporaryDirectory(prefix="repropatch-approvals-") as temporary:
            path = Path(temporary) / "expectations.patch"
            path.write_text(patch)
            git(source, "apply", str(path), deadline=deadline)
        return [
            {
                "kind": "official_test_expectations",
                "paths": [name for name, _ in sections],
                "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
            }
        ]
    if repository == "KhronosGroup/glslang":
        # 官方 known_good 清单固定全部源码依赖，GoogleTest 标签解析到固定提交。
        dependencies = []
        for entry in json.loads((source / "known_good.json").read_text())["commits"]:
            commit = entry["commit"]
            if commit == "v1.14.0" and entry["subrepo"] == "google/googletest":
                commit = "f8d7d77c06936315286eb55f8de22cd23c188571"
            location = entry["subdir"]
            if Path(location).is_absolute() or ".." in Path(location).parts:
                raise ValueError("CPP_DEPENDENCY_PATH_REJECTED")
            target = source / location
            if target.exists():
                target.rmdir()
            children = materialize(entry["subrepo"], commit, target, pool, deadline=deadline)
            dependencies.append(
                {
                    "path": location,
                    "url": "https://github.com/" + entry["subrepo"],
                    "commit": commit,
                    "dependencies": children,
                }
            )
        return dependencies
    if repository == "nlohmann/json":
        from prepare_json_task import adapt

        adapt(source)
        return []
    if repository == "shader-slang/slang":
        # 生成器在输入文件旁写临时头文件，原生 CMake 使用构建树内的同字节副本。
        module = source / "source/slang-core-module/CMakeLists.txt"
        if module.exists():
            content = module.read_text()
            marker = 'set(core_module_meta_source_dir "${slang_SOURCE_DIR}/source/slang")'
            if content.count(marker) != 1:
                raise ValueError("SLANG_META_GENERATOR_LAYOUT_REVIEW_REQUIRED")
            replacement = (
                "set(core_module_meta_source_dir "
                '"${CMAKE_CURRENT_BINARY_DIR}/repropatch-meta-input")\n'
                'file(MAKE_DIRECTORY "${core_module_meta_source_dir}")\n'
                "file(GLOB repropatch_meta_inputs "
                '"${slang_SOURCE_DIR}/source/slang/*.meta.slang")\n'
                'file(COPY ${repropatch_meta_inputs} DESTINATION "${core_module_meta_source_dir}")'
            )
            module.write_text(content.replace(marker, replacement))
        # Vulkan 原生头文件固定到官方 v1.4.318，离线配置直接使用源码副本。
        location = "external/repropatch-vulkan-headers"
        commit = "b39ab380a44b6c8df462c34e976ea9ce2d2c336b"
        repo = "KhronosGroup/Vulkan-Headers"
        children = materialize(repo, commit, source / location, pool, deadline=deadline)
        return [
            {
                "path": location,
                "url": "https://github.com/" + repo,
                "commit": commit,
                "dependencies": children,
            }
        ]
    if repository != "simdjson/simdjson":
        return []
    if record.get("instance_id") == "simdjson__simdjson-644":
        # 此版本的六个原生测试直接使用仓库内数据。
        # JSON 对照库仅保留编译接口，独立项目的测试与性能数据位于其发行仓库。
        for relative in ("dependencies/json/test", "dependencies/json/benchmarks"):
            path = source / relative
            if path.exists():
                shutil.rmtree(path)
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


def duckdb_test_arguments(record):
    """只读取数据集命令的原生筛选器，保留显式全选与默认集合的区别。"""
    for command in record.get("native_test_commands", []):
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        tokens = list(lexer)
        for index, token in enumerate(tokens):
            if Path(token).name != "unittest":
                continue
            arguments = []
            for argument in tokens[index + 1 :]:
                if argument in {";", "&&", "||", "|", "&"}:
                    break
                arguments.append(argument)
            if "--list-tests" in arguments:
                continue
            selectors = []
            position = 0
            while position < len(arguments):
                argument = arguments[position]
                if argument in {"--reporter", "--out", "--durations", "--use-colour"}:
                    position += 2
                elif argument.startswith("--out="):
                    position += 1
                elif argument == "*":
                    selectors.append(argument)
                    position += 1
                else:
                    raise ValueError("DUCKDB_NATIVE_ARGUMENTS_REVIEW_REQUIRED")
            if selectors not in ([], ["*"]):
                raise ValueError("DUCKDB_NATIVE_ARGUMENTS_REVIEW_REQUIRED")
            return selectors
    raise ValueError("DUCKDB_NATIVE_COMMAND_MISSING")


def slang_test_arguments(record):
    """只提取数据集冻结的原生 argv；目录准备、重定向与 tee 由运行器接管。"""
    commands = record.get("native_test_commands", [])
    if len(commands) != 1:
        raise ValueError("SLANG_NATIVE_COMMAND_REVIEW_REQUIRED")
    lexer = shlex.shlex(commands[0], posix=True, punctuation_chars=";&|<>")
    lexer.whitespace_split = True
    tokens = list(lexer)
    executables = {
        "./build/Release/bin/slang-test",
        "build/Release/bin/slang-test",
        "/testbed/build/Release/bin/slang-test",
    }
    positions = [index for index, token in enumerate(tokens) if token in executables]
    if len(positions) != 1 or any("$" in token or "`" in token for token in tokens):
        raise ValueError("SLANG_NATIVE_COMMAND_REVIEW_REQUIRED")
    position = positions[0]
    prefix = tokens[:position]
    while prefix:
        boundary = next((i for i, token in enumerate(prefix) if token in {";", "&&"}), None)
        if boundary is None or prefix[:boundary] not in (
            ["cd", "/testbed"],
            ["mkdir", "-p", "reports"],
            ["mkdir", "-p", "/testbed/reports"],
        ):
            raise ValueError("SLANG_NATIVE_COMMAND_REVIEW_REQUIRED")
        prefix = prefix[boundary + 1 :]
    remaining = tokens[position + 1 :]
    end = next(
        (
            index
            for index, token in enumerate(remaining)
            if token in {";", "&&", "|", ">", "2"}
            and (token != "2" or remaining[index + 1 : index + 2] == [">&"])
        ),
        len(remaining),
    )
    arguments, suffix = remaining[:end], remaining[end:]
    if suffix[:3] == ["2", ">&", "1"]:
        suffix = suffix[3:]
    if suffix:
        if suffix[0] == ">" and len(suffix) == 2:
            output = suffix[1]
        elif suffix[:2] == ["|", "tee"] and len(suffix) == 3:
            output = suffix[2]
        else:
            raise ValueError("SLANG_NATIVE_COMMAND_REVIEW_REQUIRED")
        if not re.fullmatch(r"(?:/testbed/)?(?:reports/)?[A-Za-z0-9._-]+", output):
            raise ValueError("SLANG_NATIVE_COMMAND_REVIEW_REQUIRED")
    flags = {
        "-xunit",
        "-use-test-server",
        "-skip-reference-image-generation",
        "-show-adapter-info",
        "-skip-api-detection",
    }
    operands = {
        "-server-count",
        "-category",
        "-expected-failure-list",
        "-enable-debug-layers",
        "-api",
        "-exclude",
        "-exclude-prefix",
    }
    index = 0
    while index < len(arguments):
        flag = arguments[index]
        index += 1
        if flag == "-v":
            if arguments[index : index + 1] in (["verbose"], ["info"], ["failure"]):
                index += 1
        elif flag in operands:
            if index == len(arguments) or arguments[index].startswith("-"):
                raise ValueError("SLANG_NATIVE_COMMAND_REVIEW_REQUIRED")
            index += 1
        elif flag not in flags:
            raise ValueError("SLANG_NATIVE_COMMAND_REVIEW_REQUIRED")
    return arguments


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
        # 保留各实例的输出格式、测试服务器和官方预期失败列表。
        contract["test_arguments"] = slang_test_arguments(record)
        contract["log_stream_policy"] = "slang-terminal-records-v1"
        # 镜像已有 Clang 19；Slang 的下游探测器按 clang++/clang 名称查找。
        contract["runtime_compiler_directory"] = configuration.get(
            "runtime_compiler_directory", "/usr/lib/llvm-19/bin"
        )
    elif mode == "duckdb":
        contract["test_arguments"] = duckdb_test_arguments(record)
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
        "--build ${CMAKE_CURRENT_BINARY_DIR}/native --parallel "
        + str(contract["configuration"].get("build_jobs", 2))
        + ")",
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


def text_readable_paths(source, prefixes, revision="HEAD"):
    """文本工具读取 UTF-8 源码，原生测试保留完整的离线语料。"""
    tracked = {entry.path: entry.oid for entry in git_tree(source, revision)}
    readable = set()

    def compact(names, prefix, selected):
        if not selected:
            return set()
        if len(names) == len(selected):
            return {prefix}
        groups = {}
        for name in names:
            slash = name.find("/", len(prefix))
            child = name[: slash + 1] if slash >= 0 else name
            groups.setdefault(child, set()).add(name)
        return {
            path
            for child, members in groups.items()
            for path in compact(members, child, members & selected)
        }

    for prefix in prefixes:
        names = [
            name
            for name in tracked
            if (name.startswith(prefix) if prefix.endswith("/") else name == prefix)
        ]
        selected = set()
        for name in names:
            if name.startswith(NATIVE_TEST_DATA):
                continue
            content = git_blob(source, tracked[name])
            if b"\x00" in content:
                continue
            try:
                content.decode("utf-8")
            except UnicodeError:
                continue
            selected.add(name)
        readable.update(compact(names, prefix, selected))
    return sorted(readable)


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
