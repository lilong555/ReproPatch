"""以原始 Usage 锚点离线重放旧拒绝载荷，供应商请求数固定为零。"""

import argparse
import json
from dataclasses import replace
from pathlib import Path

from audit_context_history import load_archive, sql_rows
from benchmark_budget import BudgetLimit, LocalUsageLedger

from repropatch.context import ContextPolicy, TokenEstimator, encoded


def replay(source, reconstructed, output):
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for task, arm in (("2292", "full"), ("3158", "full"), ("3158", "mini"), ("3158", "codex")):
        archive = next(source.glob(f"*-fmtlib__fmt-{task}-{arm}/*.tar.gz"))
        files, archive_sha = load_archive(archive)
        estimator = TokenEstimator()
        rows = sql_rows(files[f"ledgers/{arm}.sqlite3"], "SELECT * FROM requests ORDER BY rowid")
        for row in rows:
            request = json.loads(files[f"{arm}/http-native/{row['id']}-request.json"])
            response = json.loads(files[f"{arm}/http-native/{row['id']}-response.json"])
            if row["usage"]:
                estimator.observe(request, response)
        exact = arm != "codex"
        if exact:
            raw = (reconstructed / f"fmtlib__fmt-{task}-{arm}-request.json").read_bytes()
        else:
            # 原代理未保存拒绝正文，明确使用最后已发请求派生的受控边界夹具。
            request["input"].append(
                {"role": "user", "content": "OFFLINE_TRANSPORT_BOUNDARY " * 2500}
            )
            raw = encoded(request)
        attempts = []
        for name, policy in (
            ("legacy", replace(ContextPolicy.legacy(), request_cap=24)),
            ("unified", ContextPolicy()),
        ):
            ledger = LocalUsageLedger.create_scoped(
                output / f"{arm}-{task}-{name}.sqlite3", {"offline": 24}, context_policy=policy
            )
            with ledger.connect() as db:
                db.execute(
                    "INSERT INTO context_anchors VALUES (?,?)",
                    ("offline", encoded(estimator.to_dict()).decode()),
                )
            reason = "ADMITTED_OFFLINE"
            try:
                ledger.reserve("offline", raw)
            except BudgetLimit as error:
                reason = error.reason
            with ledger.connect() as db:
                stored, telemetry = db.execute("SELECT payload,telemetry FROM pre_send").fetchone()
            assert stored == raw
            attempts.append({"policy": name, "result": reason, **json.loads(telemetry)})
        assert attempts[0]["result"] == "LOCAL_TRANSPORT_LIMIT"
        assert attempts[1]["result"] == "ADMITTED_OFFLINE"
        results.append(
            {
                "instance_id": f"fmtlib__fmt-{task}",
                "arm": arm,
                "archive_sha256": archive_sha,
                "exact_rejected_body": exact,
                "evidence_scope": "原始拒绝正文重建"
                if exact
                else "旧 Codex 拒绝正文缺失；最后已发请求派生的边界夹具",
                "replay": attempts,
            }
        )
    result = {"passed": True, "new_model_requests": 0, "attempts": results}
    (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--reconstructed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    replay(args.source, args.reconstructed, args.output)
