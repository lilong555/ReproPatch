# Luna max 五组统一上下文对照结果

21 道 fmt 缺陷的 105 个槽位均取得有效冷评分：**93 项通过、12 项失败**。
实际配置为 `gpt-6-luna`、`max`、统一上下文压缩、每次最多 24 请求、48 工具及 180 秒单请求总期限；任务与 O3 Docker 镜像持续冻结。

| 实验臂 | 21 题冷评分通过 | 19 题完整尝试配对通过 |
| --- | ---: | ---: |
| ReproPatch Full | 20/21 | 18/19 |
| 关闭自检 | 15/21 | 15/19 |
| Shell-only | 21/21 | 19/19 |
| mini-SWE-agent | 20/21 | 18/19 |
| Codex CLI | 17/21 | 16/19 |

三次人工中断的原始状态保留。Full / fmt-3158 的 Checkpoint 20、Shell-only / fmt-1171 的 Checkpoint 24 已通过零模型冷评分；完整尝试配对采用相同 19 题。
19 题配对中，Full 相对关闭自检组净多通过 3 题，中途自检已知累计 1,725.13 秒。逐题差异与全部停止原因见 JSON；本组为相同 fmt 任务上的配置复核。

## 最后一批

| 任务 | 实验臂 | Oracle | 停止原因 | 请求 |
| --- | --- | --- | --- | ---: |
| fmt-2292 | Shell-only | PASS | REQUEST_BUDGET_EXHAUSTED | 24 |

Full / fmt-2292 的续跑通过全部 18 项原生测试；mini / fmt-1361 用满 24 请求后，候选在独立冷构建中编译失败。

## 累计用量与归档

正式累计 **2,074/2,520 请求**，剩余 446；独立校准 11 次单列。118 次收费尝试及两份补充冷评分归档保留，14 次历史请求用量未知。
已知输入 44,867,030 Token、输出 1,016,330 Token，其中缓存输入 37,979,904、推理输出 779,584。缓存与推理作为总量中的细分项呈现，费用以供应商账单核对。
累计核验 118 份模型归档、58,352 份原始文件和 2,074 个唯一请求 ID。复验仅覆盖基础设施错误，按冻结尝试承接结果；历史失败与人工中断记录持续可查。
执行源码完整 CI 通过 **735 项**：519 Core、176 SDK、40 真实 Docker，固定 mini/Codex 原生压缩验证通过。

[最终 JSON](final-results.json) · [逐题 CSV](final-attempts.csv) · [首轮报告](results.md) · [首次故障复验](completion-results.md)
[最后一批 Actions](https://github.com/lilong555/ReproPatch/actions/runs/40519869787) · [累计归档核验](../../docs/evidence/context-unified-2026-10-27/final-campaign-verification.json) · [完整 CI](https://github.com/lilong555/ReproPatch/actions/runs/40515296353)

在补充证据包的 `source` 目录重算最终 JSON 和逐题 CSV：

```bash
python scripts/summarize_context_completion.py \
  --protocol benchmarks/context-revalidation-protocol-continuation-2b.json \
  --results ../evidence/results \
  --verification ../evidence/verification.json \
  --output ../replay
```
