# 上游故障复验与中断候选评分结果

7 次独立复验有 **4 项通过、3 项上游错误**；中断候选冷评分通过 2/2。
本轮已发 102 次请求，冷评分模型请求为 0；实际配置为 Luna `max`、180 秒模型总期限、原 O3 Docker 镜像。

| 任务 | 实验臂 | 当前 Oracle | 停止原因 | 请求 |
| --- | --- | --- | --- | ---: |
| fmt-2292 | 关闭自检 | PASS | COMPLETED | 23 |
| fmt-3727 | mini | PASS | COMPLETED | 19 |
| fmt-2292 | Full | INFRASTRUCTURE_FAILED | MODEL_SERVER_ERROR | 11 |
| fmt-2292 | Shell-only | INFRASTRUCTURE_FAILED | MODEL_SERVER_ERROR | 4 |
| fmt-493 | mini | PASS | COMPLETED | 12 |
| fmt-1361 | Shell-only | PASS | REQUEST_BUDGET_EXHAUSTED | 24 |
| fmt-1361 | mini | INFRASTRUCTURE_FAILED | MODEL_TIMEOUT | 9 |

Full / fmt-3158 的 Checkpoint 20、Shell-only / fmt-1171 的 Checkpoint 24 取得独立冷评分，原始 `USER_CANCELLED` 停止状态继续保留。

## 当前评分视图

| 实验臂 | 21 题全部记录 | 19 题完整配对 | 剩余基础设施错误 |
| --- | ---: | ---: | ---: |
| Full | 19/21 | 17/19 | 1 |
| 关闭自检 | 15/21 | 15/19 | 0 |
| Shell-only | 20/21 | 18/19 | 1 |
| mini | 20/21 | 18/19 | 1 |
| Codex | 17/21 | 16/19 | 0 |

当前 105 个槽位有 **91 项通过、11 项候选失败、3 项基础设施错误**，全部已有评分记录。三次人工中断状态持续保留，完整尝试配对集采用相同 19 题。

三项剩余错误均有原始上游 **HTTP 524** 证据：Full / fmt-2292、Shell-only / fmt-2292、mini / fmt-1361。

正式累计 **1997/2520 请求**，13 次用量未知，独立校准 11 次单列。114 次收费尝试全部保留；首轮及两次计量故障复验的旧记录继续可查。
已知输入 43,126,953 Token、输出 954,955 Token；其中缓存输入 36,534,528、推理输出 729,997，费用未知。

[首轮报告](results.md)、[首轮 JSON](results.json)、[本轮 JSON](completion-results.json)和[当前逐题 CSV](completion-attempts.csv)分别提供原始事实与复验后的评分视图。
[Actions 原始批次](https://github.com/lilong555/ReproPatch/actions/runs/40504279080)和[逐归档核验](../../docs/evidence/context-unified-2026-10-27/completion-verification.json)提供血缘、请求账本、候选 SHA-256 及冷评分证据。

解开补充证据包，在 `source` 目录使用核心 Python 环境重算：

```bash
python scripts/summarize_context_completion.py \
  --protocol benchmarks/context-revalidation-protocol.json \
  --results ../evidence/results \
  --verification ../evidence/verification.json \
  --output ../replay
```
