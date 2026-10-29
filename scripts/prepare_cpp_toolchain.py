"""准备固定提交的离线测试数据与共享编译依赖。"""

import argparse
import time
import zipfile
from pathlib import Path

from cpp_native_adapter import materialize, source_manifest
from cpp_sources import download
from qualify_cpp_batch import save

DEPENDENCIES = {
    "ut": ("openalgz/ut", "a69c7866d6e1af01d14aab81cf790b9b210cabe2"),
    "json-test-data": ("nlohmann/json_test_data", "a015e5be2d5dfffcf98d00d9df39c9285efc7887"),
    "simdjson-data": ("simdjson/simdjson-data", "a5b13babe65c1bba7186b41b43d4cbdc20a5c470"),
    "yaml-test-suite": ("yaml/yaml-test-suite", "6ad3d2c62885d82fc349026c136ef560838fdf3d"),
}
SLANG_LLVM_URL = "https://github.com/shader-slang/slang/releases/download/v2026.5.2/slang-2026.5.2-linux-x86_64.zip"
SLANG_LLVM_ARCHIVE_SHA256 = "c2362cd79462ac2b30ef25836953f231adf4c2dbef40430d482b992925adda77"


def prepare_slang_llvm(output, pool):
    """固定官方 LLVM 后端附件，只将编译依赖放入共享镜像。"""
    archive = pool / "slang-2026.5.2-linux-x86_64.zip"
    download(SLANG_LLVM_URL, archive, SLANG_LLVM_ARCHIVE_SHA256)
    with zipfile.ZipFile(archive) as data:
        members = [name for name in data.namelist() if Path(name).name == "libslang-llvm.so"]
        if len(members) != 1:
            raise ValueError("SLANG_LLVM_LIBRARY_IDENTITY_INVALID")
        (output / "libslang-llvm.so").write_bytes(data.read(members[0]))
    return {
        "url": SLANG_LLVM_URL,
        "archive_sha256": SLANG_LLVM_ARCHIVE_SHA256,
        "files": {"libslang-llvm.so": source_manifest(output)["libslang-llvm.so"]},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pool", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    identities = {}
    for name, (repo, commit) in DEPENDENCIES.items():
        directory = args.output / name
        children = materialize(repo, commit, directory, args.pool, deadline=time.monotonic() + 900)
        identities[name] = {
            "repository": repo,
            "commit": commit,
            "gitlinks": children,
            "files": source_manifest(directory),
        }
    identities["slang-llvm"] = prepare_slang_llvm(args.output, args.pool)
    save(args.output / "dependencies.json", identities)


if __name__ == "__main__":
    main()
