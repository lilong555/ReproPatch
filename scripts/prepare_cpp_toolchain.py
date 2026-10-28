"""准备固定提交的离线测试数据与共享编译依赖。"""

import argparse
import time
from pathlib import Path

from cpp_native_adapter import materialize, source_manifest
from qualify_cpp_batch import save

DEPENDENCIES = {
    "ut": ("openalgz/ut", "a69c7866d6e1af01d14aab81cf790b9b210cabe2"),
    "json-test-data": ("nlohmann/json_test_data", "a015e5be2d5dfffcf98d00d9df39c9285efc7887"),
    "simdjson-data": ("simdjson/simdjson-data", "a5b13babe65c1bba7186b41b43d4cbdc20a5c470"),
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
    save(args.output / "dependencies.json", identities)


if __name__ == "__main__":
    main()
