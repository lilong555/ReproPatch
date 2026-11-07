"""Read-only audit of final-patch exploration checks and independent scoring.

No model, shell command from a trace, or container is executed. Every registered
attempt remains in the result, including missing or invalid evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import tarfile
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from audit_context_triggers import Archive, AuditError, digest, load_events, parse_json

from repropatch.workspace import SourceManifest

LOG = logging.getLogger(__name__)
SCHEMA = "repropatch.final-patch-verification-audit.v1"
COLD_STATUSES = {"ORACLE_PASSED", "ORACLE_BUILD_FAILED", "ORACLE_TESTS_FAILED"}


class VerificationArchive(Archive):
    """Use the existing bounded inventory verifier, retaining scoring metadata."""

    def __init__(self, path):
        super().__init__(path)
        if not self.inventory_verified:
            raise AuditError("archive_inventory_required")
        selected = {
            name
            for name in self.identities
            if name.startswith("score/") or name in {"summary.json", "worker/candidate.patch"}
        }
        with tarfile.open(path, "r|gz") as archived:
            for member in archived:
                if member.name not in selected:
                    continue
                expected_size, expected_hash = self.identities[member.name]
                if not member.isfile() or member.size != expected_size:
                    raise AuditError("scoring_member_changed")
                stream = archived.extractfile(member)
                raw = stream.read(expected_size + 1)
                if len(raw) != expected_size or digest(raw) != expected_hash:
                    raise AuditError("scoring_member_hash_mismatch")
                self.files[member.name] = raw
                selected.remove(member.name)
        if selected:
            raise AuditError("scoring_members_missing")


def require(condition, message):
    if not condition:
        raise AuditError(message)


def xml_results(raw):
    """Return actual CTest testcase observations; zero cases remain empty."""
    if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
        raise AuditError("xml_declaration_rejected")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as error:
        raise AuditError("invalid_test_xml") from error
    result = {}
    for case in root.iter("testcase"):
        name = case.get("name")
        require(isinstance(name, str) and bool(name), "unnamed_testcase")
        require(name not in result, "duplicate_testcase")
        state = "passed"
        if case.find("failure") is not None or case.find("error") is not None:
            state = "failed"
        elif case.find("skipped") is not None or case.get("status") in {"notrun", "disabled"}:
            state = "skipped"
        result[name] = state
    return result


def command_passed(command):
    return (
        isinstance(command, dict)
        and command.get("status") == "exited"
        and command.get("exit_code") == 0
        and not command.get("error_code")
        and not command.get("timed_out")
    )


def check_record(archive, root, event):
    """Validate a structured run_command evaluation against XML and source."""
    ref = event["payload"]["result_ref"]
    raw = archive.read_ref(ref, root)
    value = parse_json(raw)
    data = value.get("data", {})
    record = {
        "event_seq": event["seq"],
        "step_id": event.get("step_id"),
        "tool_call_id": event.get("tool_call_id"),
        "result_path": root + ref["path"],
        "result_sha256": ref["sha256"],
        "status": "tool_error",
        "source_tree_sha256": None,
        "source_identity_verified": False,
        "test_count": 0,
        "tests": [],
        "tests_xml_verified": False,
        "reported_passed": data.get("passed"),
    }
    if value.get("ok") is not True or data.get("evaluation_role") != "agent_check":
        return record
    evidence_ref = data.get("evidence")
    if not isinstance(evidence_ref, dict):
        record["status"] = "missing_evaluation"
        return record
    evidence = parse_json(archive.read_ref(evidence_ref, root))
    record.update(
        evaluation_path=root + evidence_ref["path"],
        evaluation_sha256=evidence_ref["sha256"],
        evaluation_id=evidence.get("evaluation_id"),
        image_id=evidence.get("image_id"),
        isolated=evidence.get("isolated"),
        compiler_cache=evidence.get("compiler_cache", {}).get("kind"),
        source_tree_sha256=evidence.get("source_tree_sha256"),
    )
    require(evidence.get("evaluation_id") == data.get("evaluation_id"), "evaluation_id_mismatch")
    source_ref = evidence.get("source_manifest")
    if source_ref:
        source = SourceManifest.from_dict(parse_json(archive.read_ref(source_ref, root)))
        require(source.sha256 == evidence.get("source_tree_sha256"), "evaluation_source_mismatch")
        require(source.sha256 == data.get("source_tree_sha256"), "tool_evaluation_source_mismatch")
        record.update(
            source_identity_verified=True,
            source_manifest_path=root + source_ref["path"],
            source_manifest_sha256=source_ref["sha256"],
        )
    tests = evidence.get("tests", [])
    commands = {c["command_id"]: c for c in evidence.get("commands", []) if c.get("command_id")}
    xml_proven, names = True, set()
    for test in tests:
        name = test.get("name")
        require(isinstance(name, str) and name not in names, "invalid_test_names")
        names.add(name)
        observed = {
            k: test.get(k)
            for k in ("name", "group", "observed_status", "ctest_exit_code", "identity_sha256")
        }
        test_ref = test.get("result")
        results = {}
        if test_ref:
            results = xml_results(archive.read_ref(test_ref, root))
            observed.update(
                xml_path=root + test_ref["path"],
                xml_sha256=test_ref["sha256"],
                xml_case_count=len(results),
                xml_status=results.get(name),
            )
        command = commands.get(test.get("command_id"))
        observed["command"] = command.get("argv") if command else None
        observed["xml_proves_pass"] = (
            results.get(name) == "passed"
            and len(results) == 1
            and test.get("observed_status") == "passed"
            and test.get("ctest_exit_code") == 0
            and command_passed(command)
        )
        xml_proven = xml_proven and observed["xml_proves_pass"]
        record["tests"].append(observed)
    record["test_count"] = len(tests)
    record["tests_xml_verified"] = bool(tests) and xml_proven
    record["configure_command"] = (evidence.get("configure") or {}).get("argv")
    record["build_command"] = (evidence.get("build") or {}).get("argv")
    record["build_passed"] = command_passed(evidence.get("build"))
    record["configure_passed"] = command_passed(evidence.get("configure"))
    record["cleanup_confirmed"] = evidence.get("cleanup_confirmed")
    if not record["configure_passed"]:
        record["status"] = "configure_failed"
    elif not record["build_passed"]:
        record["status"] = "build_failed"
    elif not tests:
        record["status"] = "zero_tests"
    elif all(t.get("observed_status") == "passed" for t in tests):
        record["status"] = (
            "passed" if xml_proven and data.get("passed") is True else "pass_evidence_incomplete"
        )
    elif any(t.get("observed_status") == "failed" for t in tests):
        record["status"] = "tests_failed"
    else:
        record["status"] = "tests_incomplete"
    return record


def select_final_check(checks, source_sha256):
    matching = [
        c
        for c in checks
        if c.get("source_identity_verified") and c.get("source_tree_sha256") == source_sha256
    ]
    return max(matching, key=lambda c: c["event_seq"]) if matching else None


def classify_pair(last, cold_status, cold_tests):
    if last is None:
        return {"eligible": False, "false_accept": False, "disagreement": None}
    eligible = last.get("status") == "passed" and cold_status in COLD_STATUSES
    false_accept = eligible and cold_status != "ORACLE_PASSED"
    failing = sorted(n for n, s in cold_tests.items() if s == "failed")
    visible = {t["name"] for t in last.get("tests", [])}
    shared = sorted(set(failing) & visible)
    extra = sorted(set(failing) - visible)
    category = None
    if false_accept:
        category = (
            "cold_build_failure"
            if cold_status == "ORACLE_BUILD_FAILED"
            else "shared_test_name_failure"
            if shared
            else "additional_test_failure"
            if extra
            else "unclassified_cold_failure"
        )
    return {
        "eligible": eligible,
        "false_accept": false_accept,
        "disagreement": category,
        "cold_failed_tests": failing,
        "shared_failed_tests": shared,
        "additional_failed_tests": extra,
    }


def audit_attempt(attempt, artifact, raw_dir):
    row = {
        k: attempt[k]
        for k in ("job_key", "trial_index", "instance_id", "arm", "repeat", "attempt_id")
    }
    row.update(
        schema=SCHEMA,
        audit_status="evidence_missing",
        artifact_url=artifact["url"],
        artifact_id=artifact["id"],
        archive_sha256=None,
        archive_inventory_verified=False,
        candidate_available=False,
        candidate_identity_verified=False,
        final_source_identity_verified=False,
        cold_identity_verified=False,
        cold_status=attempt.get("score", {}).get("status"),
        cold_accepted=attempt.get("accepted"),
        final_check_status="not_observed",
        exploration_check_count=0,
        checks=[],
        final_patch_check_count=0,
        eligible=False,
        false_accept=False,
        disagreement=None,
        missing_reason=None,
    )
    folder = Path(raw_dir) / artifact["name"]
    path = folder / "context-attempt.tar.gz"
    try:
        if not path.is_file():
            row["missing_reason"] = "raw_archive_missing"
            return row
        zipped = folder / "artifact.zip"
        if zipped.is_file():
            require(
                digest(zipped.read_bytes()) == artifact["digest"].removeprefix("sha256:"),
                "github_zip_sha_mismatch",
            )
            row["github_zip_verified"] = True
        else:
            row["github_zip_verified"] = False
        archive = VerificationArchive(path)
        row.update(
            archive_sha256=archive.sha256, archive_inventory_verified=archive.inventory_verified
        )
        summary = archive.json("summary.json")
        for key in ("job_key", "instance_id", "arm", "repeat", "attempt_id", "candidate_sha256"):
            require(summary.get(key) == attempt.get(key), "attempt_identity_mismatch:" + key)
        roots = [
            n.removesuffix("events.jsonl")
            for n in archive.files
            if n.startswith("worker/runs/") and n.endswith("/events.jsonl")
        ]
        require(len(roots) == 1, "worker_run_ambiguous")
        root = roots[0]
        events = load_events(archive, root, root.split("/")[2])
        frozen = [
            e
            for e in events
            if e["type"] == "verification_finished" and e["payload"].get("candidate")
        ]
        if not frozen:
            row.update(
                audit_status="no_frozen_candidate", missing_reason="candidate_export_not_observed"
            )
            return row
        candidate = frozen[-1]["payload"]["candidate"]
        raw_patch = archive.read_ref(candidate["patch"], root)
        source = SourceManifest.from_dict(parse_json(archive.read_ref(candidate["manifest"], root)))
        require(source.sha256 == candidate["source_tree_sha256"], "candidate_source_mismatch")
        row.update(
            candidate_available=bool(raw_patch.strip()),
            candidate_sha256=digest(raw_patch),
            candidate_bytes=len(raw_patch),
            source_tree_sha256=source.sha256,
            base_commit=candidate["base_commit"],
            changed_files=candidate["changed_files"],
            candidate_export_event=frozen[-1]["seq"],
            final_source_identity_verified=True,
            candidate_manifest_path=root + candidate["manifest"]["path"],
        )
        if not raw_patch.strip():
            row.update(audit_status="empty_candidate", missing_reason="empty_candidate")
            return row
        worker = archive.json("worker/result.json")
        score = archive.json("score/score.json")
        require(
            digest(archive.read("worker/result.json")) == score["worker_result_sha256"],
            "scored_worker_mismatch",
        )
        for obj in (attempt, summary, worker, score):
            require(
                obj.get("candidate_sha256") == row["candidate_sha256"], "candidate_sha_mismatch"
            )
        for name in (
            "worker/candidate.patch",
            "score/candidate.patch",
            "score/oracle/candidate.patch",
        ):
            require(
                digest(archive.read(name)) == row["candidate_sha256"], "candidate_copy_mismatch"
            )
        require(
            worker.get("prepared_commit")
            == score.get("prepared_commit")
            == candidate["base_commit"],
            "candidate_base_mismatch",
        )
        row["candidate_identity_verified"] = True
        cold = archive.json("score/oracle/oracle-verdict.json")
        require(
            digest(archive.read("score/oracle/oracle-verdict.json"))
            == score["oracle_verdict_sha256"],
            "cold_verdict_mismatch",
        )
        require(
            digest(archive.read("score/oracle/manifest.json")) == score["oracle_manifest_sha256"],
            "cold_manifest_mismatch",
        )
        require(cold.get("candidate_sha256") == row["candidate_sha256"], "cold_candidate_mismatch")
        require(cold.get("prepared_commit") == candidate["base_commit"], "cold_base_mismatch")
        require(
            cold.get("image_id") == worker.get("image_id") == score.get("image_id"),
            "cold_image_mismatch",
        )
        require(
            cold.get("cold_build") is True and cold.get("compiler_cache") == "disabled",
            "cold_build_contract_missing",
        )
        require(
            score.get("accepted") == attempt.get("accepted") == cold.get("accepted"),
            "cold_acceptance_mismatch",
        )
        require(
            score.get("status") == attempt.get("score", {}).get("status") == cold.get("status"),
            "cold_status_mismatch",
        )
        qualification = archive.json("score/qualification.json")
        require(
            digest(archive.read("score/qualification.json")) == score.get("qualification_sha256"),
            "qualification_mismatch",
        )
        row.update(
            cold_identity_verified=True,
            cold_status=cold["status"],
            cold_accepted=cold["accepted"],
            cold_image_id=cold["image_id"],
            cold_compiler_cache=cold["compiler_cache"],
            cold_manifest_sha256=score["oracle_manifest_sha256"],
            cold_verdict_sha256=score["oracle_verdict_sha256"],
            test_patch_sha256=qualification.get("test_patch_sha256"),
            cold_tests={**(cold.get("f2p") or {}), **(cold.get("p2p") or {})},
            cold_configure=cold.get("configure"),
            cold_commands=[
                {k: c.get(k) for k in ("stage", "argv", "exit_code", "log", "log_sha256")}
                for c in cold.get("commands", [])
            ],
        )
        cold_xml_path = "score/oracle/native-oracle-results.xml"
        row["cold_xml_verified"] = False
        if cold_xml_path in archive.files:
            actual = xml_results(archive.read(cold_xml_path))
            require(
                all(actual.get(name) == state for name, state in row["cold_tests"].items()),
                "cold_xml_status_mismatch",
            )
            require(bool(actual), "cold_xml_zero_tests")
            row.update(
                cold_xml_verified=True,
                cold_xml_test_count=len(actual),
                cold_xml_path=cold_xml_path,
                cold_xml_sha256=digest(archive.read(cold_xml_path)),
            )
        elif cold["status"] in {"ORACLE_PASSED", "ORACLE_TESTS_FAILED"}:
            raise AuditError("cold_xml_missing")
        for event in events:
            if event["type"] == "tool_finished" and event["payload"].get("name") == "run_command":
                row["checks"].append(check_record(archive, root, event))
        row["exploration_check_count"] = len(row["checks"])
        row["final_patch_check_count"] = sum(
            c.get("source_identity_verified") and c.get("source_tree_sha256") == source.sha256
            for c in row["checks"]
        )
        last = select_final_check(row["checks"], source.sha256)
        if last:
            row.update(
                final_check_status=last["status"],
                final_check_event=last["event_seq"],
                final_check_tool=last["tool_call_id"],
                final_check_test_count=last["test_count"],
                final_check_evidence=last.get("evaluation_path"),
                final_check_xml_verified=last.get("tests_xml_verified"),
            )
        else:
            row["final_check_status"] = (
                "final_patch_not_tested" if row["checks"] else "no_exploration_check"
            )
        row.update(classify_pair(last, row["cold_status"], row["cold_tests"]))
        row["audit_status"] = "verified"
        row["tests_changed_in_candidate"] = [
            p
            for p in row["changed_files"]
            if p.startswith(("test/", "tests/")) or p.endswith("CMakeLists.txt")
        ]
        return row
    except Exception as error:
        row.update(
            audit_status="evidence_error",
            missing_reason=type(error).__name__ + ": " + str(error),
            eligible=False,
            false_accept=False,
        )
        return row


def summarize(rows):
    eligible = [r for r in rows if r["eligible"]]
    false_accepts = [r for r in eligible if r["false_accept"]]
    return {
        "expected": len(rows),
        "audit_statuses": dict(Counter(r["audit_status"] for r in rows)),
        "candidate_available": sum(r["candidate_available"] for r in rows),
        "candidate_identity_verified": sum(r["candidate_identity_verified"] for r in rows),
        "final_source_identity_verified": sum(r["final_source_identity_verified"] for r in rows),
        "cold_identity_verified": sum(r["cold_identity_verified"] for r in rows),
        "exploration_checks": sum(r["exploration_check_count"] for r in rows),
        "final_patch_exploratorily_checked": sum(r["final_patch_check_count"] > 0 for r in rows),
        "final_check_statuses": dict(Counter(r["final_check_status"] for r in rows)),
        "eligible_exploration_pass": len(eligible),
        "false_accepts": len(false_accepts),
        "false_accept_fraction": len(false_accepts) / len(eligible) if eligible else None,
        "disagreement_categories": dict(Counter(r["disagreement"] for r in false_accepts)),
        "false_accept_jobs": [r["job_key"] for r in false_accepts],
        "cold_passes": sum(r.get("cold_accepted") is True for r in rows),
        "cold_failures": sum(r.get("cold_accepted") is False for r in rows),
        "exploration_cold_crosstab": {
            state: {
                "cold_pass": sum(
                    r["final_check_status"] == state and r.get("cold_accepted") is True
                    for r in rows
                ),
                "cold_fail": sum(
                    r["final_check_status"] == state and r.get("cold_accepted") is False
                    for r in rows
                ),
            }
            for state in sorted({r["final_check_status"] for r in rows})
        },
    }


def write_report(output, rows, summary):
    totals = summary["overall"]
    fraction = totals["false_accept_fraction"]
    rate = f"{fraction:.2%}" if fraction is not None else "暂无可判定分母"
    lines = [
        "# 最终补丁探索检查与独立冷评分",
        "",
        f"完整审计 {len(rows)} 条冻结轨迹。{totals['eligible_exploration_pass']} 条最终补丁的"
        "最近一次结构化自检有源码身份和实际 CTest XML 支撑，通过该检查后，"
        f"独立冷评分拒绝 {totals['false_accepts']} 条；观测误接受比例为 {rate}。",
        "",
        "该比例使用“同一最终补丁最近自检通过且冷评分可判定”作为分母。各运行的完整状态、未检查和失败记录均保留。",
        "",
        "## 完整分母",
        "",
        "| 指标 | 数量 |",
        "| --- | ---: |",
    ]
    labels = [
        ("预定轨迹", "expected"),
        ("候选补丁可用", "candidate_available"),
        ("候选多份哈希与评分身份一致", "candidate_identity_verified"),
        ("最终源码清单身份核验", "final_source_identity_verified"),
        ("独立冷评分身份核验", "cold_identity_verified"),
        ("最终补丁有结构化探索检查", "final_patch_exploratorily_checked"),
        ("最近探索检查通过且冷评分可判定", "eligible_exploration_pass"),
        ("探索通过后独立冷评分拒绝", "false_accepts"),
    ]
    lines.extend(f"| {label} | {totals[key]} |" for label, key in labels)
    lines += [
        "",
        "## 分组结果",
        "",
        "| 组别 | 全部轨迹 | 最终补丁有检查 | 自检通过分母 | 冷评分拒绝 | 比例 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm, result in summary["arms"].items():
        ratio = result["false_accept_fraction"]
        lines.append(
            f"| {arm} | {result['expected']} | {result['final_patch_exploratorily_checked']} | "
            f"{result['eligible_exploration_pass']} | {result['false_accepts']} | {ratio:.2%} |"
            if ratio is not None
            else f"| {arm} | {result['expected']} | "
            f"{result['final_patch_exploratorily_checked']} | 0 | 0 | — |"
        )
    lines += [
        "",
        "## 最终自检状态",
        "",
        "| 状态 | 轨迹数 | 冷评分通过 | 冷评分失败 |",
        "| --- | ---: | ---: | ---: |",
    ]
    lines.extend(
        f"| {name} | {count} | {totals['exploration_cold_crosstab'][name]['cold_pass']} | "
        f"{totals['exploration_cold_crosstab'][name]['cold_fail']} |"
        for name, count in totals["final_check_statuses"].items()
    )
    lines += [
        "",
        "## 不一致记录",
        "",
        "| 轨迹 | 任务 / 组别 | 探索事件 | 冷评分 | 可见测试同名失败 | 新增测试失败 | 原始轨迹 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        if row["false_accept"]:
            lines.append(
                f"| {row['job_key']} | {row['instance_id']} / {row['arm']} / r{row['repeat']} | "
                f"{row.get('final_check_tool')} | {row['cold_status']} | "
                f"{', '.join(row.get('shared_failed_tests', [])) or '—'} | "
                f"{', '.join(row.get('additional_failed_tests', [])) or '—'} | "
                f"[下载]({row['artifact_url']}) |"
            )
    if not totals["false_accepts"]:
        lines.append("| 无观测不一致 | — | — | — | — | — | — |")
    lines += [
        "",
        "## 口径与复算",
        "",
        "审计读取工具调用结束事件，核验原始回执、完整评价、源码清单和 CTest XML 的 SHA-256。"
        "探索检查以实际非空测试及其退出状态为据。最终补丁通过工作区导出、worker、score 和 oracle "
        "四处候选哈希连接；源码清单同时保留文件模式。最后检查之后的源码变化在最终源码匹配中自然剔出，"
        "相关运行列为最终补丁尚未检查。",
        "",
        "独立冷评分固定同一候选补丁与镜像，使用新构建目录并关闭编译缓存。F2P/P2P 集合及每项失败"
        "保留在记录中。同名测试失败先作为不一致观察记录；构建残留、测试修改和波动归因需要额外复现证据。",
        "",
        "`run_command(reproduce)` 运行 F2P，`run_command(verify)` 运行 F2P/P2P；"
        "两者的实际测试范围逐项保存。纯编译成功、空测试、自述成功均有各自状态。"
        "主表使用严格源码哈希层；所有证据错误保留具体原因。",
        "",
        "```bash",
        "PYTHONPATH=src:scripts python scripts/audit_false_positives.py \\",
        "  --raw-dir /path/to/context-raw \\",
        "  --results benchmarks/context-ablation/full/results.json \\",
        "  --artifacts benchmarks/context-ablation/full/artifacts.json \\",
        "  --output-dir /tmp/final-patch-audit",
        "```",
        "",
        "`attempts.jsonl` 保存完整逐条证据，`attempts.csv` 用于筛选，"
        "`summary.json` 保存分组统计及输入哈希。"
        "原始归档来自 [Actions 42219312911]"
        "(https://github.com/lilong555/ReproPatch/actions/runs/42219312911)，下载入口逐条保留。",
        "",
        "已有测试篡改与回归构造案例见 [运行时证据](../runtime-evidence-20261106/report.md)。"
        "这些主动注入的案例单独报告；本页统计来自冻结队列自然产生的最终候选。",
        "",
    ]
    (output / "README.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument(
        "--results", type=Path, default=Path("benchmarks/context-ablation/full/results.json")
    )
    parser.add_argument(
        "--artifacts", type=Path, default=Path("benchmarks/context-ablation/full/artifacts.json")
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    require(not args.output_dir.exists(), "output_directory_exists")
    attempts = json.loads(args.results.read_text())["attempts"]
    artifacts = json.loads(args.artifacts.read_text())
    index = {a["name"].rsplit("-trial-", 1)[-1]: a for a in artifacts["raw_artifacts"]}
    attempts.sort(key=lambda a: a["trial_index"])
    if args.limit is not None:
        require(args.limit > 0, "limit_must_be_positive")
        attempts = attempts[: args.limit]
    require(len({a["job_key"] for a in attempts}) == len(attempts), "duplicate_registered_attempt")
    jobs = [(a, index[a["job_key"].removeprefix("trial-")], args.raw_dir) for a in attempts]
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(lambda job: audit_attempt(*job), jobs):
            rows.append(row)
            if len(rows) % 20 == 0 or row["audit_status"] != "verified":
                LOG.info(
                    "audited %s/%s: %s %s",
                    len(rows),
                    len(jobs),
                    row["job_key"],
                    row["audit_status"],
                )
    summary = {
        "schema": SCHEMA,
        "source_run_id": artifacts["run_id"],
        "source_commit": artifacts["source_commit"],
        "scope": "smoke" if args.limit else "full",
        "input_hashes": {
            "results.json": digest(args.results.read_bytes()),
            "artifacts.json": digest(args.artifacts.read_bytes()),
            "audit_false_positives.py": digest(Path(__file__).read_bytes()),
        },
        "overall": summarize(rows),
        "arms": {
            arm: summarize([r for r in rows if r["arm"] == arm])
            for arm in sorted({r["arm"] for r in rows})
        },
    }
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "attempts.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    )
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    fields = [
        "job_key",
        "instance_id",
        "arm",
        "repeat",
        "audit_status",
        "candidate_sha256",
        "source_tree_sha256",
        "candidate_identity_verified",
        "final_patch_check_count",
        "final_check_status",
        "final_check_test_count",
        "cold_status",
        "eligible",
        "false_accept",
        "disagreement",
        "missing_reason",
        "artifact_url",
    ]
    with (args.output_dir / "attempts.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    write_report(args.output_dir, rows, summary)
    print(json.dumps(summary["overall"], ensure_ascii=False, indent=2), flush=True)
    return int(any(r["audit_status"] in {"evidence_error", "evidence_missing"} for r in rows))


if __name__ == "__main__":
    raise SystemExit(main())
