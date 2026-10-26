"""校验历史归档并逐次审计上下文拒绝、供应商用量与独立 Oracle。"""

import argparse
import csv
import hashlib
import json
import sqlite3
import tarfile
import tempfile
from collections import Counter
from pathlib import Path

LEGACY_TRANSPORT_BYTES = 256 * 1024


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def digest(content):
    return hashlib.sha256(content).hexdigest()


def opaque_bytes(value):
    if isinstance(value, dict):
        return sum(
            len(item.encode())
            if key == "encrypted_content" and isinstance(item, str)
            else opaque_bytes(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return sum(opaque_bytes(item) for item in value)
    return 0


def sql_rows(content, query):
    with tempfile.TemporaryDirectory(prefix="repropatch-audit-") as temporary:
        path = Path(temporary) / "ledger.sqlite3"
        path.write_bytes(content)
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute(query)]


def load_archive(path):
    checksum = path.with_suffix(path.suffix + ".sha256")
    content = path.read_bytes()
    if checksum.is_file() and digest(content) != checksum.read_text().split()[0]:
        raise ValueError(f"ARCHIVE_SHA_MISMATCH: {path}")
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        if len({m.name for m in members}) != len(members):
            raise ValueError("ARCHIVE_DUPLICATE_MEMBER")
        manifest = json.load(archive.extractfile("archive-manifest.json"))
        files = {}
        for row in manifest["files"]:
            member = archive.getmember(row["path"])
            if not member.isfile():
                raise ValueError("ARCHIVE_NON_FILE")
            data = archive.extractfile(member).read()
            if len(data) != row["size_bytes"] or digest(data) != row["sha256"]:
                raise ValueError(f"EVIDENCE_SHA_MISMATCH: {path}:{row['path']}")
            files[row["path"]] = data
    return files, digest(content)


def sdk_next_input(files, prefix, step):
    native = json.loads(files[prefix + f"agent/native/{step:04d}-input.json"])
    output = json.loads(files[prefix + f"agent/native/{step:04d}-output.json"])["output"]
    items = native["input"] + output
    for line in files[prefix + "events.jsonl"].splitlines():
        event = json.loads(line)
        if event["step_id"] == step and event["type"] == "tool_finished":
            payload = event["payload"]
            value = json.loads(files[prefix + payload["result_ref"]["path"]])
            items.append(
                {
                    "type": "function_call_output",
                    "call_id": payload["provider_call_id"],
                    "output": json.dumps(
                        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    ),
                }
            )
    return {**native, "input": items}


def audited_attempt(files, attempt, archive_sha):
    arm = attempt["arm"]
    score = attempt["score"]
    worker = json.loads(files[f"{arm}/result.json"])
    ledger = sql_rows(
        files[f"ledgers/{arm}.sqlite3"],
        "SELECT rowid AS sequence,* FROM requests ORDER BY rowid",
    )
    successful = [r for r in ledger if r["status_code"] == 200 and r["usage"]]
    last = successful[-1] if successful else None
    requests = []
    for record in ledger:
        name = f"{arm}/http-native/{record['id']}-request.json"
        raw = files.get(name)
        if raw is None or digest(raw) != record["request_sha256"]:
            raise ValueError(f"REQUEST_EVIDENCE_MISSING: {attempt['attempt_id']}:{name}")
        body = json.loads(raw)
        usage = json.loads(record["usage"]) if record["usage"] else {}
        requests.append(
            {
                "sequence": record["sequence"],
                "request_id": record["id"],
                "transport_bytes": len(raw),
                "opaque_state_bytes": opaque_bytes(body),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "cached_input_tokens": usage.get("input_tokens_details", {}).get("cached_tokens"),
                "reasoning_tokens": usage.get("output_tokens_details", {}).get("reasoning_tokens"),
                "status_code": record["status_code"],
            }
        )
    row = {
        "attempt_id": attempt["attempt_id"],
        "instance_id": attempt["instance_id"],
        "arm": arm,
        "archive_sha256": archive_sha,
        "original_reason": worker.get("native_reason"),
        "original_error_code": worker.get("error_code"),
        "audited_stop_reason": None,
        "oracle_result": "PASS"
        if score["accepted"] is True
        else "FAIL"
        if score["accepted"] is False
        else score["status"],
        "oracle_executed": score.get("oracle_executed", False),
        "candidate_sha256": score.get("candidate_sha256"),
        "last_success_req_seq": last["sequence"] if last else None,
        "last_success_tokens": json.loads(last["usage"])["input_tokens"] if last else None,
        "issued_requests": len(ledger),
        "unknown_usage_requests": sum(r["usage"] is None for r in ledger),
        "first_rejected_bytes": None,
        "rejection_layer": None,
        "measurement_object": None,
        "threshold": None,
        "rejected_request_sent_upstream": None,
        "evidence_note": None,
        "peak_single_input_tokens": max((r["input_tokens"] or 0 for r in requests), default=0),
        "peak_transport_bytes": max((r["transport_bytes"] for r in requests), default=0),
        "opaque_state_peak_bytes": max((r["opaque_state_bytes"] for r in requests), default=0),
        "requests": requests,
    }
    reason = worker.get("error_code") or worker.get("native_reason")
    report = None
    prefix = None
    if arm in {"full", "no-checks", "shell-only"}:
        prefix = f"{arm}/runs/{worker['native_run_id']}/"
        report = json.loads(files[prefix + "report.json"])
        db_run = sql_rows(files[prefix + "events.sqlite3"], "SELECT * FROM runs")[0]
        reason = db_run["agent_stop_reason"] or report["agent"]["agent_stop_reason"]
        row["native_agent_stop_reason"] = reason
        row["native_report_reason"] = report["reason_code"]
        row["attempted_model_steps"] = db_run["steps_used"]
        last_input = files.get(prefix + f"agent/native/{db_run['steps_used']:04d}-input.json")
        # 最后一次逻辑模型步未发送时，用前一真实正文的静态参数重建完整请求。
        if reason == "MODEL_ERROR" and db_run["steps_used"] == len(ledger) + 1 and last_input:
            native = json.loads(last_input)
            previous = json.loads(files[f"{arm}/http-native/{ledger[-1]['id']}-request.json"])
            reconstruction_matches = 0
            for entry in ledger:
                saved = json.loads(files[f"{arm}/http-native/{entry['id']}-request.json"])
                prior_native = json.loads(
                    files[prefix + f"agent/native/{entry['sequence']:04d}-input.json"]
                )
                rebuilt = {**previous, **prior_native}
                if rebuilt != saved or len(encode(rebuilt)) != len(encode(saved)):
                    raise ValueError("REQUEST_RECONSTRUCTION_PARAMETERS_CHANGED")
                reconstruction_matches += 1
            raw = encode({**previous, **native})
            if len(raw) > LEGACY_TRANSPORT_BYTES:
                reason = "LOCAL_TRANSPORT_LIMIT"
                row.update(
                    first_rejected_bytes=len(raw),
                    first_rejected_sha256=digest(raw),
                    rejection_layer="LocalUsageLedger.reserve",
                    measurement_object="完整 HTTP JSON Body",
                    threshold=LEGACY_TRANSPORT_BYTES,
                    rejected_request_sent_upstream=False,
                    evidence_note=(
                        "正文由归档 SDK 输入和静态参数重建；"
                        f"{reconstruction_matches} 次已发请求逐次重建一致"
                    ),
                    reconstructed_request=raw.decode(),
                )
            elif ledger and ledger[-1]["usage"] is None:
                reason = "USAGE_UNSETTLED"
                row.update(
                    rejection_layer="LocalUsageLedger.reserve",
                    measurement_object="前次请求 usage 闭合状态",
                    threshold=0,
                    rejected_request_sent_upstream=False,
                    evidence_note="前次上游请求无有效 usage；账本在下一逻辑步拒绝",
                )
    if reason in {"CONTEXT_LIMIT", "FORMAL_REQUEST_PARAMETERS"}:
        layer, measured = (
            ("Codex.Model.do_POST", "JSON input 数组，ensure_ascii=False，默认分隔符")
            if arm == "codex"
            else ("ModelTransport.query", 'canonical_json({"input": prepared})')
            if arm == "mini"
            else (
                "agent_runtime.input_filter",
                'canonical_json({"instructions": ..., "input": ...})',
            )
        )
        row.update(
            rejection_layer=layer,
            measurement_object=measured,
            threshold=LEGACY_TRANSPORT_BYTES,
            rejected_request_sent_upstream=False,
            evidence_note="旧入口在保存正文前拒绝；原始正文未归档，已知字节数下界为262145",
            first_rejected_bytes_lower_bound=LEGACY_TRANSPORT_BYTES + 1,
        )
        native = None
        if arm in {"full", "no-checks", "shell-only"}:
            step = row["attempted_model_steps"]
            for prior in range(1, step):
                observed = json.loads(files[prefix + f"agent/native/{prior + 1:04d}-input.json"])
                if sdk_next_input(files, prefix, prior) != observed:
                    raise ValueError("SDK_HISTORY_RECONSTRUCTION_MISMATCH")
            native = sdk_next_input(files, prefix, step)
            note = f"由最后响应及全部已归档工具结果重建；前{step - 1}个历史边界一致"
        elif arm == "mini":
            messages = json.loads(files["mini/trajectory.json"])["messages"]
            prepared = []
            for message in messages:
                if message.get("role") == "exit":
                    continue
                output = (
                    message.get("output", []) if message.get("object") == "response" else [message]
                )
                prepared.extend({k: v for k, v in item.items() if k != "extra"} for item in output)
            for entry in ledger:
                body = json.loads(files[f"{arm}/http-native/{entry['id']}-request.json"])
                if prepared[: len(body["input"])] != body["input"]:
                    raise ValueError("MINI_HISTORY_RECONSTRUCTION_MISMATCH")
            native = {"input": prepared}
            note = f"按固定mini消息扁平化规则重建；{len(ledger)}个已发送前缀一致"
        if native is not None:
            previous = json.loads(files[f"{arm}/http-native/{ledger[-1]['id']}-request.json"])
            raw = encode({**previous, **native})
            measured_bytes = len(encode(native))
            if measured_bytes <= LEGACY_TRANSPORT_BYTES:
                raise ValueError("RECONSTRUCTED_REJECTION_BELOW_THRESHOLD")
            row.update(
                first_rejected_bytes=measured_bytes,
                first_rejected_sha256=digest(raw),
                reconstructed_transport_bytes=len(raw),
                reconstructed_request=raw.decode(),
                evidence_note=note,
            )
        reason = "LOCAL_TRANSPORT_LIMIT"
    mapped = {
        "MODEL_FINISHED": "COMPLETED",
        "Submitted": "COMPLETED",
        "FINISHED": "COMPLETED",
        "STEP_BUDGET": "REQUEST_BUDGET_EXHAUSTED",
        "LimitsExceeded": "REQUEST_BUDGET_EXHAUSTED",
        "BENCHMARK_REQUEST_LIMIT": "REQUEST_BUDGET_EXHAUSTED",
        "TOOL_BUDGET": "TOOL_BUDGET_EXHAUSTED",
        "MODEL_REQUEST_TIMEOUT": "MODEL_TIMEOUT",
        "MODEL_CONNECTION_ERROR": "MODEL_SERVER_ERROR",
        "MODEL_REQUEST_FAILED:Timeout": "MODEL_TIMEOUT",
        "AGENT_TIME_LIMIT": "AGENT_DEADLINE",
    }
    reason = mapped.get(reason, reason)
    if reason == "REQUEST_BUDGET_EXHAUSTED":
        row.update(
            rejection_layer="LocalUsageLedger.reserve"
            if arm == "codex"
            else "DefaultAgent.step_limit"
            if arm == "mini"
            else "agent_runtime.input_filter",
            measurement_object="累计请求数" if arm == "codex" else "累计模型步数",
            threshold=attempt["request_cap"],
            rejected_request_sent_upstream=False,
        )
    if reason in {"MODEL_ERROR", "MODEL_REQUEST_ERROR", "CLI_ERROR", "ERROR"}:
        if report and report["reason_code"].startswith("MODEL_"):
            reason = mapped.get(report["reason_code"], report["reason_code"])
        failed_requests = [r for r in ledger if r["usage"] is None]
        if failed_requests:
            latest = failed_requests[-1]
            status = latest["status_code"]
            reason = (
                "MODEL_RATE_LIMIT"
                if status == 429
                else ("MODEL_SERVER_ERROR" if status and status >= 500 else reason)
            )
            row.update(
                rejection_layer="供应商 HTTP / 传输",
                measurement_object="HTTP 响应与 usage",
                rejected_request_sent_upstream=True,
                evidence_note=(
                    f"上游请求 {latest['sequence']}，HTTP状态={status}；"
                    f"原错误={worker.get('error_code')}"
                ),
            )
        if arm == "codex":
            transports = [
                json.loads(data)
                for name, data in files.items()
                if name.startswith("codex/http-native/") and name.endswith("-transport.json")
            ]
            if transports:
                row["transport_errors"] = [
                    t
                    for t in transports
                    if t.get("error_type") or (t.get("last_byte_seconds") or 0) > 190
                ]
                if any((t.get("last_byte_seconds") or 0) > 190 for t in transports):
                    reason = "MODEL_TIMEOUT"
                    row.update(
                        rejection_layer="Codex CLI / UnixHTTP relay",
                        measurement_object="等待完整 SSE 的时长（秒）",
                        threshold=190,
                        rejected_request_sent_upstream=True,
                        evidence_note="CLI等待截止后代理继续读取；最终账本保留供应商结算",
                    )
            row["proxy_errors"] = worker.get("errors", [])
    row["audited_stop_reason"] = reason or "UNKNOWN"
    if reason in {"MODEL_TIMEOUT", "MODEL_REQUEST_FAILED"} and row["rejection_layer"] is None:
        row.update(
            rejection_layer="供应商客户端",
            measurement_object="模型等待时间或连接状态",
            threshold=180,
            rejected_request_sent_upstream=True,
            evidence_note="供应商客户端错误与最终账本联合判定",
        )
    if reason not in {"COMPLETED", "REQUEST_BUDGET_EXHAUSTED", "LOCAL_TRANSPORT_LIMIT"}:
        row["evidence_note"] = row["evidence_note"] or (
            f"Agent原始停止={reason}；工具或基础设施停止细节见原始事件日志"
        )
    return row


def audit(source, output):
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    archives = []
    for path in sorted(source.glob("*/formal-evidence.tar.gz")):
        files, sha = load_archive(path)
        summary = json.loads(files["summary.json"])
        archives.append({"name": path.parent.name, "sha256": sha, "verified_files": len(files)})
        for attempt in summary["attempts"]:
            row = audited_attempt(files, attempt, sha)
            reconstructed = row.pop("reconstructed_request", None)
            if reconstructed:
                target = output / "reconstructed"
                target.mkdir(exist_ok=True)
                name = row["instance_id"] + "-" + row["arm"] + "-request.json"
                (target / name).write_text(reconstructed)
                row["reconstructed_request_file"] = "reconstructed/" + name
            rows.append(row)
    identities = [r["attempt_id"] for r in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("DUPLICATE_ATTEMPT")
    totals = {
        "attempts": len(rows),
        "issued_requests": sum(r["issued_requests"] for r in rows),
        "unknown_usage_requests": sum(r["unknown_usage_requests"] for r in rows),
        "stop_reasons": dict(Counter(r["audited_stop_reason"] for r in rows)),
        "oracle_results": dict(Counter(r["oracle_result"] for r in rows)),
    }
    report = {
        "schema": "repropatch.context-audit.v1",
        "new_model_requests": 0,
        "totals": totals,
        "archives": archives,
        "attempts": rows,
    }
    (output / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    columns = [
        "instance_id",
        "arm",
        "original_reason",
        "audited_stop_reason",
        "oracle_result",
        "last_success_req_seq",
        "last_success_tokens",
        "first_rejected_bytes",
        "rejection_layer",
        "measurement_object",
        "threshold",
        "rejected_request_sent_upstream",
        "evidence_note",
    ]
    with (output / "audit.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# 历史上下文与停止原因审计",
        "",
        f"共 {len(rows)} 次尝试，新增模型请求 0；归档逐文件 SHA 校验通过。",
        f"最终账本累计请求 {totals['issued_requests']}，"
        f"未知用量 {totals['unknown_usage_requests']}。",
        "",
        "| 组别 | Oracle 通过 | 传输截断 | 截断且通过 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for arm in ("full", "no-checks", "shell-only", "mini", "codex"):
        group = [r for r in rows if r["arm"] == arm]
        rejected = [r for r in group if r["audited_stop_reason"] == "LOCAL_TRANSPORT_LIMIT"]
        lines.append(
            f"| {arm} | {sum(r['oracle_result'] == 'PASS' for r in group)}/{len(group)} | "
            f"{len(rejected)} | {sum(r['oracle_result'] == 'PASS' for r in rejected)} |"
        )
    lines += [
        "",
        "每次尝试的计量对象、阈值、发送状态和证据来源见 [审计表](audit.csv)。",
        "旧入口未保存的拒绝正文在表中保留空值及字节下界；重建正文单独标注并保存。",
    ]
    (output / "audit.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(totals, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.source, args.output)
