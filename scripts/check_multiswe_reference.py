"""在固定官方 Catch2 镜像中复核参考补丁，直接调用上游解析器和 Report。"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

EVALUATOR_COMMIT = "4b96a678b136f87c8760fa475697f3c98d5f9e5e"
OFFICIAL_IMAGES = {
    2723: "sha256:3ced24b5f52e9909175db56f51576841e353f89468ef885f57bc4fd7b96b11e0",
    2187: "sha256:917e179081a8dc28fc21b50c4a9574ec4a1893b1599a5607916fa6a0eb308367",
    1608: "sha256:9c6e60ceb6d0e3c638f1d3d18072f12d48d65fd0f5f6b2c13050c6badc21f6ef",
    1448: "sha256:1767b483755bbcab66b36effbf3cd1517ff1d456933fa43dbb97e75323202218",
    1422: "sha256:feb18f5d8fa743f7d75dc1515cebc655e8a0fa8336329045cbcadd98e7139065",
}


def run(argv, **kwargs):
    return subprocess.check_output(argv, stderr=subprocess.PIPE, timeout=30, **kwargs)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True, help="固定公开数据集的单条原始记录")
    parser.add_argument(
        "--candidate", type=Path, required=True, help="完整参考补丁或已审查的源码部分"
    )
    parser.add_argument("--image", required=True, help="已下载的原始官方镜像 image ID")
    parser.add_argument("--evaluator-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.record.read_text())
    if (cfg["org"], cfg["repo"]) != ("catchorg", "Catch2") or cfg["number"] not in OFFICIAL_IMAGES:
        parser.error("仅支持已审查的 Catch2 官方布局")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image):
        parser.error("必须使用本地原始镜像的完整 image ID")
    if args.image != OFFICIAL_IMAGES[cfg["number"]]:
        parser.error("输入镜像与当前实例已核验的官方内容身份不一致")
    base = cfg["base"]["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        parser.error("base commit 不合法")
    candidate = args.candidate.resolve(strict=True)
    if "," in str(candidate):
        parser.error("Docker bind 路径不能包含逗号")
    patch = candidate.read_bytes()
    reference = cfg["fix_patch"].encode()
    # 该命令只作参考验收，禁止把任意候选当成已知参考修复。
    production = b"".join(
        b"diff --git " + part
        for part in reference.split(b"diff --git ")[1:]
        if not part.startswith((b"a/docs/", b"a/projects/SelfTest/Baselines/"))
    )
    if patch not in (reference, production):
        parser.error("输入不是原始参考补丁或已审查的源码参考部分")
    evaluator = args.evaluator_source.resolve(strict=True)
    if run(["git", "rev-parse", "HEAD"], cwd=evaluator).decode().strip() != EVALUATOR_COMMIT:
        parser.error("官方 evaluator 源码不是固定版本")
    run(["git", "diff", "--quiet", "HEAD", "--", "multi_swe_bench"], cwd=evaluator)
    actual = run(["docker", "image", "inspect", args.image, "--format", "{{.Id}}"])
    if actual.decode().strip() != args.image:
        parser.error("本地镜像身份不匹配")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    save(output / "record.json", cfg)
    (output / "candidate.patch").write_bytes(patch)
    save(
        output / "evaluator-source-manifest.json",
        {
            str(path.relative_to(evaluator)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((evaluator / "multi_swe_bench").rglob("*.py"))
        },
    )
    name = "repropatch-official-reference-" + uuid.uuid4().hex[:12]
    argv = [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--name",
        name,
        "--network=none",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--memory=2048m",
        "--memory-swap=2048m",
        "--cpus=2",
        "--pids-limit=128",
        "--ulimit=core=0:0",
        "--user=0:0",
        "--mount",
        f"type=bind,source={output / 'candidate.patch'},target=/candidate.patch,readonly",
        args.image,
        "/bin/bash",
        "-ec",
        f'cd /home/Catch2\ntest "$(git rev-parse HEAD)" = {base}\n'
        "git diff --quiet\ngit apply --whitespace=nowarn /candidate.patch\n"
        "sha256sum /home/test-run.sh /home/test.patch\nexec bash /home/test-run.sh",
    ]
    started = time.monotonic()
    execution = {
        "scope": "official_image_reference_check",
        "image": args.image,
        "base_commit": base,
        "candidate": "upstream_reference"
        if patch == reference
        else "upstream_production_reference",
        "candidate_sha256": hashlib.sha256(patch).hexdigest(),
        "argv": argv,
        "model_requests": 0,
        "container_deleted": False,
    }
    try:
        with (
            (output / "stdout.log").open("wb") as stdout,
            (output / "stderr.log").open("wb") as stderr,
        ):
            completed = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=600)
            execution["exit_code"] = completed.returncode
    except subprocess.TimeoutExpired:
        execution.update(exit_code=None, error="ORACLE_TIMEOUT")
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)
        remaining = run(
            ["docker", "ps", "-a", "--filter", f"name=^/{name}$", "--format", "{{.ID}}"]
        )
        execution["container_deleted"] = not remaining.strip()
        execution["duration_seconds"] = time.monotonic() - started
        save(output / "execution.json", execution)
    sys.path.insert(0, str(evaluator))
    from multi_swe_bench.harness.report import Report
    from multi_swe_bench.harness.repos.cpp.catchorg.catch2 import Catch2
    from multi_swe_bench.harness.test_result import TestResult

    # 此方法不使用 self；直接调用固定上游实现，不重写其解析或判定规则。
    observed = Catch2.parse_log(None, (output / "stdout.log").read_text())
    report = Report(
        org=cfg["org"],
        repo=cfg["repo"],
        number=cfg["number"],
        run_result=TestResult.from_dict(cfg["run_result"]),
        test_patch_result=TestResult.from_dict(cfg["test_patch_result"]),
        fix_patch_result=observed,
    )
    valid, error = report.check(force=True)
    missing = {
        group: sorted(set(cfg.get(group, {})) - set(getattr(report, group)))
        for group in ("f2p_tests", "p2p_tests", "s2p_tests", "n2p_tests")
    }
    verdict = {
        "oracle_source_commit": EVALUATOR_COMMIT,
        "valid": valid,
        "error": error,
        "expected_f2p": len(cfg["f2p_tests"]),
        "expected_p2p": len(cfg["p2p_tests"]),
        "passed_count": observed.passed_count,
        "failed_count": observed.failed_count,
        "missing": missing,
        "model_requests": 0,
    }
    verdict["accepted"] = (
        execution["exit_code"] == 0
        and execution["container_deleted"]
        and valid
        and not any(missing.values())
    )
    save(output / "oracle-verdict.json", verdict)
    print(json.dumps({"execution": execution, "verdict": verdict}, ensure_ascii=False))
    return 0 if verdict["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
