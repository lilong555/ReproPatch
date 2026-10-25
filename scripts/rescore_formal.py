"""恢复冻结源码的 Git 身份，使用原有冷 Oracle 评分，模型调用数为零。"""

import argparse
import hashlib
import json
import os
import subprocess
import tarfile
from pathlib import Path

from actions_benchmark import save, sha
from prepare_multiswe_task import git
from qualify_cpp_batch import ADAPTER, BUILD_TEST, archive, records, validate_record
from verify_qualification_evidence import verify_tree

ROOT = Path(__file__).resolve().parents[1]
SOURCE_RUN = 40212667694
PROTOCOL = ROOT / "benchmarks/formal-max-full-180s-protocol.json"
CHECKPOINT = ROOT / "benchmarks/actions-scale/oracle-checkpoint.json"


def gh(*args):
    return subprocess.check_output(["gh", *map(str, args)], cwd=ROOT, text=True)


def code_sha():
    digest = hashlib.sha256()
    for name in (
        "rescore_formal.py",
        "check_qualified_cpp_candidate.py",
        "score_benchmark_attempt.py",
        "qualify_cpp_batch.py",
        "prepare_multiswe_task.py",
    ):
        digest.update(name.encode() + (ROOT / "scripts" / name).read_bytes())
    return digest.hexdigest()


def plan(scope, output):
    p = json.loads(PROTOCOL.read_text())
    run = json.loads(gh("api", f"repos/lilong555/ReproPatch/actions/runs/{SOURCE_RUN}"))
    assert run["head_sha"] == "9d9e4be7ddcb9573edc5c7540b3e1808713d5744"
    assets = json.loads(
        gh("api", f"repos/lilong555/ReproPatch/actions/runs/{SOURCE_RUN}/artifacts?per_page=100")
    )["artifacts"]
    by_task = {
        a["name"].removeprefix(f"formal-evidence-{SOURCE_RUN}-"): a
        for a in assets
        if a["name"].startswith(f"formal-evidence-{SOURCE_RUN}-")
    }
    selected = p["tasks"] if scope == "all" else scope.split(",")
    assert set(selected) <= set(p["tasks"]) and len(selected) == len(set(selected))
    checkpoint = json.loads(CHECKPOINT.read_text())
    reusable = (
        checkpoint["completed_tasks"]
        if checkpoint.get("code_sha256") == code_sha() and checkpoint["source_run_id"] == SOURCE_RUN
        else []
    )
    todo = [t for t in selected if t not in reusable]
    result = {
        "source_run_id": SOURCE_RUN,
        "requested_tasks": selected,
        "tasks": todo,
        "artifacts": {t: by_task.get(t) for t in selected},
        "reused_tasks": [t for t in selected if t in reusable],
        "previous_run_id": checkpoint.get("run_id"),
        "code_sha256": code_sha(),
        "model_requests": 0,
    }
    save(output, result)
    with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
        stream.write("tasks=" + json.dumps(todo or ["__none__"]) + "\n")
        stream.write("count=" + str(len(todo)) + "\n")


def restore_repository(directory, dataset, upstream):
    q = json.loads((directory / "result.json").read_text())
    record = next(r for r in records(dataset) if r["instance_id"] == q["instance_id"])
    source = directory / "repository"
    archive(upstream, record["base"]["sha"], source)
    git(source, "init", "--template=", "-q", ".")
    git(source, "apply", str(directory / "control/test.patch"))
    targets, _ = validate_record(record)
    condition = " OR ".join(f'name STREQUAL "{name}"' for name in targets)
    cmake = source / "test/CMakeLists.txt"
    cmake.write_text(
        cmake.read_text().replace(
            "  add_test(NAME ${name} COMMAND ${name})\n",
            ADAPTER.replace("__CONDITION__", condition),
        )
    )
    (source / "test/repropatch-build-test.cmake").write_text(BUILD_TEST)
    git(source, "add", "-f", ".")
    git(source, "commit", "-qm", "Freeze official regression tests and target-build CTest adapter")
    assert git(source, "rev-parse", "HEAD").decode().strip() == q["prepared_commit"]
    assert not verify_tree(directory, json.loads((directory / "manifest.json").read_text()))


def rescore(instance, plan_file, output):
    from types import SimpleNamespace

    from score_benchmark_attempt import score

    p = json.loads(plan_file.read_text())
    asset = p["artifacts"][instance]
    assert asset, "MISSING_SOURCE_EVIDENCE"
    download = ROOT / ".repropatch/frozen-model-input"
    gh(
        "run",
        "download",
        SOURCE_RUN,
        "--repo",
        "lilong555/ReproPatch",
        "--name",
        asset["name"],
        "--dir",
        download,
    )
    package = download / "formal-evidence.tar.gz"
    digest = sha(package)
    assert digest == (download / "formal-evidence.tar.gz.sha256").read_text().split()[0]
    frozen = ROOT / ".repropatch/frozen-model-source"
    with tarfile.open(package) as data:
        manifest = json.load(data.extractfile("archive-manifest.json"))
        assert len(data.getmembers()) == len(manifest["files"]) + 1
        for entry in manifest["files"]:
            content = data.extractfile(entry["path"]).read()
            assert len(content) == entry["size_bytes"]
            assert hashlib.sha256(content).hexdigest() == entry["sha256"]
        data.extractall(frozen, filter="data")
    qualified = frozen / "qualified-contract"
    restore_repository(
        qualified, ROOT / ".repropatch/inputs/dataset", ROOT / ".repropatch/inputs/fmt"
    )
    original = json.loads((frozen / "summary.json").read_text())
    rows = []
    for row in original["attempts"]:
        arm = row["arm"]
        verdict = score(
            SimpleNamespace(
                worker_result=frozen / arm / "result.json",
                qualification=qualified / "result.json",
                candidate=None,
                attempt_id=row["attempt_id"],
                dataset=ROOT / ".repropatch/inputs/dataset",
                repository=ROOT / ".repropatch/inputs/fmt",
                output=output / arm,
                check_only=False,
                timeout=900,
                build_jobs=2,
            )
        )
        rows.append({**row, "initial_score": row["score"], "score": verdict})
        result = {
            "source_run_id": SOURCE_RUN,
            "instance_id": instance,
            "source_artifact_id": asset["id"],
            "source_archive_sha256": digest,
            "protocol_sha256": sha(PROTOCOL),
            "code_sha256": code_sha(),
            "model_requests": 0,
            "original_usage": original["usage"],
            "attempts": rows,
            "rescoring_complete": len(rows) == 4
            and all(r["score"]["classification"] in {"resolved", "candidate"} for r in rows),
        }
        save(output / "summary.json", result)
        print(instance, arm, verdict["status"], flush=True)


def aggregate(source, plan_file, output):
    p = json.loads(plan_file.read_text())
    if p["reused_tasks"]:
        gh(
            "run",
            "download",
            p["previous_run_id"],
            "--repo",
            "lilong555/ReproPatch",
            "--pattern",
            "rescored-summary-*",
            "--dir",
            source / "previous",
        )
    found = {}
    for file in source.rglob("summary.json"):
        value = json.loads(file.read_text())
        if value.get("source_run_id") == SOURCE_RUN and value.get("code_sha256") == code_sha():
            key = value["instance_id"]
            assert key not in found, "DUPLICATE_RESCORE"
            found[key] = value
    save(
        output / "results.json",
        {
            **p,
            "summaries": found,
            "missing_tasks": sorted(set(p["requested_tasks"]) - found.keys()),
        },
    )
    lines = [
        "# 冻结候选的冷 Oracle 评分",
        "",
        "本次模型调用：0。",
        "",
        "| 任务 | 实验臂 | Oracle | 状态 |",
        "| --- | --- | --- | --- |",
    ]
    for task in p["requested_tasks"]:
        for row in found.get(task, {}).get("attempts", []):
            s = row["score"]
            lines.append(f"| {task} | {row['arm']} | {s['accepted']} | {s['status']} |")
    (output / "results.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("plan", "rescore", "aggregate"))
    parser.add_argument("--scope", default="all")
    parser.add_argument("--instance")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.stage == "plan":
        plan(args.scope, args.output)
    elif args.stage == "rescore":
        rescore(args.instance, args.plan, args.output)
    else:
        aggregate(args.source, args.plan, args.output)


if __name__ == "__main__":
    main()
