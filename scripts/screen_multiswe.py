"""审查全部公开 C++ 实例的静态适配条件，不执行模型或宣称运行通过。"""

import argparse
import collections
import hashlib
import json
import shlex
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SUFFIXES = {".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hh", ".hxx"}


def patch_paths(patch):
    paths = []
    special = []
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            fields = shlex.split(line)
            if len(fields) != 4 or not fields[2].startswith("a/"):
                raise ValueError("补丁路径格式不支持")
            paths.append(fields[2][2:])
            if fields[2][2:] != fields[3][2:]:
                special.append("rename")
        if line.startswith(("new file mode", "deleted file mode", "rename from", "GIT binary")):
            special.append(line.split()[0])
    return sorted(set(paths)), sorted(set(special))


def screen(record, file, line):
    paths, special = patch_paths(record["fix_patch"])
    unsupported = [
        p
        for p in paths
        if PurePosixPath(p).suffix not in SUFFIXES or PurePosixPath(p).name == "CMakeLists.txt"
    ]
    test = record["test_patch_result"]
    fixed = record["fix_patch_result"]
    # test 阶段才是已应用官方测试补丁的缺陷基线；NONE 不能视为 FAIL。
    f2p = sorted(set(test["failed_tests"]) & set(fixed["passed_tests"]))
    p2p = sorted(set(test["passed_tests"]) & set(fixed["passed_tests"]))
    reasons = []
    if not f2p:
        reasons.append("NO_RECORDED_TEST_PHASE_FAIL_TO_PASS")
    if not p2p:
        reasons.append("NO_RECORDED_PASS_TO_PASS")
    if unsupported:
        reasons.append("REFERENCE_TOUCHES_NON_EDITABLE_FILES_REVIEW_REQUIRED")
    if special:
        reasons.append("REFERENCE_CHANGES_TREE_LAYOUT_REVIEW_REQUIRED")
    if record["repo"] == "cpp-httplib":
        reasons.append("NATIVE_TEST_RUNNER_IS_NOT_CTEST")
    status = "candidate_pending_runtime" if not reasons else "needs_compatibility_review"
    return {
        "instance_id": record["instance_id"],
        "repository": record["org"] + "/" + record["repo"],
        "base_commit": record["base"]["sha"],
        "source_file": file,
        "source_line": line,
        "status": status,
        "reasons": reasons,
        "reference_paths": paths,
        "non_editable_reference_paths": unsupported,
        "layout_changes": special,
        "explicit_f2p_count": len(record["f2p_tests"]),
        "test_phase_f2p": f2p,
        "test_phase_p2p": p2p,
        "test_phase_result": {
            k: test[k] for k in ("passed_count", "failed_count", "skipped_count")
        },
        "fix_patch_sha256": hashlib.sha256(record["fix_patch"].encode()).hexdigest(),
        "test_patch_sha256": hashlib.sha256(record["test_patch"].encode()).hexdigest(),
        "runtime_validated": False,
        "model_attempts": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--revision")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks/coverage.json")
    args = parser.parse_args()
    revision_file = args.dataset / "revision.txt"
    revision = args.revision or (
        revision_file.read_text().strip() if revision_file.exists() else None
    )
    if not revision or len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        parser.error("必须提供数据集完整 revision，或在目录内提供 revision.txt")
    data_root = args.dataset / "cpp" if (args.dataset / "cpp").is_dir() else args.dataset
    files, records = [], []
    for path in sorted(data_root.glob("*_dataset.jsonl")):
        content = path.read_bytes()
        files.append(
            {"path": path.name, "size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        )
        for line, data in enumerate(content.splitlines(), 1):
            if data.strip():
                records.append(screen(json.loads(data), path.name, line))
    identifiers = [r["instance_id"] for r in records]
    if not identifiers:
        parser.error("未找到 C++ 数据文件")
    assert len(identifiers) == len(set(identifiers))
    reasons = collections.Counter(reason for row in records for reason in row["reasons"])
    candidates = [r["instance_id"] for r in records if r["status"] == "candidate_pending_runtime"]
    result = {
        "schema_version": 1,
        "dataset": "ByteDance-Seed/Multi-SWE-bench",
        "split": "cpp",
        "revision": revision,
        "source_files": files,
        "total_instances": len(records),
        "repository_counts": dict(collections.Counter(r["repository"] for r in records)),
        "status": "static_screening_only",
        "runtime_coverage": None,
        "runtime_verified_compatible": 0,
        "model_attempts": 0,
        "candidate_ids": candidates,
        "reason_counts": dict(reasons),
        "records": records,
        "notes": [
            "静态筛选不等于可运行覆盖率；仍需测试身份、基线构建、镜像及参考补丁实测",
            "参考补丁含文档不证明缺陷必需修改文档，此类实例进入人工审查，不直接判为修复失败",
            "无 F2P 记录可能源于测试阶段构建失败，不能把 NONE 当 FAIL 或据此认定任务无效",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {k: result[k] for k in ("total_instances", "candidate_ids", "reason_counts")},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
