# 早期上下文压缩对照实验

本实验比较原始上下文、早期观察提取、早期观察提取与状态摘要三组策略。目标是在相同修复任务、总请求预算和独立冷验收下，衡量较早裁剪工具回执带来的累计 Token 变化、辅助模型成本及修复成功率。

**实验已完成。** [正式 36 条结果](full/README.md)中 baseline / early / early_state 分别通过 **10/12、9/12、10/12**；`early_state` 平均输入降低 **21.98%**，输入与输出合计降低 **20.64%**，包括全部辅助调用。其状态摘要在 9/12 条中触发 10 次，输入改善集中于两道较长任务。`early` 平均输入增加 6.43%。[预检三条](smoke/README.md)单独统计。[逐条失败](full/failures.md)和[全部原始轨迹](full/trajectories.md)均已保留。

冻结合同为 [protocol.json](protocol.json)，campaign 为 `context-early-20261107-v1`，协议 SHA-256 为 `4b49a755f6689b6bbaa780c2534e77d019b30ea5d930fe55610490f19abe52c1`。现有 19 题五组实验的 190 条轨迹保存在原批次；本目录记录独立三组实验。

执行源码固定为 [`586fe18`](https://github.com/lilong555/ReproPatch/tree/586fe18e9d073d92a9943f220919f2a6d4b53af7)，对应 Git 标签 `context-early-20261107-v1`。统一预检 **526 项通过**，测试期间执行源码、测试与工作流哈希保持一致。

| 执行范围 | 轨迹数 / 请求上限 | Actions 入口 |
|---|---:|---|
| smoke | 3 / 72 | [Run 42343788196](https://github.com/lilong555/ReproPatch/actions/runs/42343788196) |
| full | 36 / 864 | [Run 42343832567](https://github.com/lilong555/ReproPatch/actions/runs/42343832567) |

两批使用相同源码。正式运行核验上述 smoke 的完整计量、评分与早期辅助调用后执行；修复失败、空补丁和 KEEP 均保留。结果与原始轨迹由各批次自动汇总为 `context-results-<run_id>` 和 `context-raw-<run_id>-<trial>`，完整调度身份见 [dispatch.json](dispatch.json)。

## 负载与证据

[历史机会分布](../context-opportunities-20261107/README.md)覆盖原批次全部 190 条轨迹。基线 38 条轨迹中，48K 历史压缩阈值的覆盖为 0/38；251 条较早工具回执超过 500 个 `o200k_base` 代理 Token，经过两步后仍被后续修复请求携带。

其中 207 条为文件读取候选：61 条具备后继同版本逐行重叠或成功编辑锚点关系，其余 146 条需要结合当时修复状态选择保留内容。历史长度与后续携带量用于识别干预位置，本轮使用实际模型请求与冷验收评价完整运行效果。

[AgentDiet v2](https://arxiv.org/abs/2509.23586v2)的单步长度门槛与两步延迟为早期处理提供方法依据；[ACON v3](https://arxiv.org/abs/2510.00615v3)提供较早历史压缩的参照。本轮触发估计使用现有运行时的 `ceil(UTF-8 bytes / 3)`，历史审计另外保留该口径的敏感性统计。

从原资格合同中的 19 道已暴露开发任务，按 `SHA256(ASCII("early-context-pilot-v1/" + instance_id))` 升序选取前六道：

| 顺序 | 缺陷任务 |
|---|---|
| 1 | `fmtlib__fmt-2070` |
| 2 | `fmtlib__fmt-3819` |
| 3 | `fmtlib__fmt-3750` |
| 4 | `fmtlib__fmt-3713` |
| 5 | `fmtlib__fmt-493` |
| 6 | `fmtlib__fmt-3537` |

选择规则仅使用任务标识。原资格归档、任务源码 Commit、镜像 Digest、官方测试与冷评分方式由父合同继承并核验 SHA-256。该先导批次评估 fmt 场景下的机制表现，后续跨仓库验证可使用 Multi-SWE-bench Flash 的其他 C++ 仓库。

## 三组配置

| 配置 | 早期观察提取 | 状态感知摘要 | 历史触发 / 目标 Token | 原文回读 |
|---|---|---|---|---|
| `baseline` | 关闭 | 关闭 | 48,000 / 21,600 | 开启 |
| `early` | 开启 | 关闭 | 48,000 / 21,600 | 开启 |
| `early_state` | 开启 | 开启 | 16,000 / 7,200 | 开启 |

三组均使用原生 legacy 六工具与 `read_observation`，结构化诊断和精确结果去重均关闭。初始基线反馈在三组中采用内容等价的独立 `baseline_observation` 用户消息，任务合同保留在固定输入中。首个已发出修复请求的输入、系统提示及工具定义分别计算哈希；汇总分别给出三项一致性，以及三项共同满足时的 `byte_identical_first_request`。缺失首请求时保留未知状态。

早期观察提取处理超过 500 个运行时估计 Token、且已有两次后继完整修复响应的观察。辅助模型仅返回原文行区间，运行时据此构造保留片段，并保存工具状态、源码身份及可回读引用。每个修复响应最多一次提取、每条轨迹最多四次，发起前至少保留两次总请求额度。提取请求使用 `request_purpose=compact` 与空工具集。

三组的所有辅助阶段均受 `min(task.budget.max_steps, context_policy.request_cap)` 限制，提取和历史摘要完成后至少保留一次修复请求额度。发送前拒绝记为一次尝试、辅助发送计数为 0；已发出的失败请求计入请求数并保留未知用量，账本继续执行用量结算约束。

`early_state` 同时启用 16K 历史水位与状态摘要。其对照结果评价这组预注册配置的整体效果；`early` 与 `baseline` 的比较评价早期观察提取的增量效果。

## 执行规模与计量

| 执行范围 | 任务 × 分组 × 重复 | 轨迹数 | 总请求上限 |
|---|---:|---:|---:|
| `smoke` | 1 × 3 × 1 | 3 | 72 |
| `full` | 6 × 3 × 2 | 36 | 864 |

Smoke 固定使用 `fmtlib__fmt-2070`。两类运行采用独立 Attempt ID，任务与分组顺序按冻结种子的 SHA-256 排序。

- 模型为 `gpt-6-luna`，推理档位 `max`，最多输出 8,192 Token，单请求超时 600 秒。
- 每条轨迹共 24 次模型请求，涵盖修复、选择性提取及历史摘要；工具调用上限 48 次。
- 总执行预算 7,200 秒，验证预留 1,200 秒；工具输出上限 24 KiB，保留最近两轮。
- GitHub Actions 最多 8 个并行 worker，CPA 与任务均采用零自动重试。
- 最终候选由原 `score_benchmark_attempt.py` 在固定镜像和独立干净工作区中进行冷评分。

结果按冷验收成功率、累计 Token 用量、实际压缩覆盖顺序呈现。正式运行每组固定分母为 12 条，全部 36 个注册槽位均保留；逐题记录评分失败、执行异常、准备失败与缺失原件。配对单位为“任务 × 重复”，输出三组两两差值及可用配对数。

供应方实际输入和输出 Token 分别合计，包含全部辅助调用；缓存输入作为输入的组成部分单列。用量缺失时保留缺失状态，并分别列出全样本均值与已观测样本均值。候选字节量、实际裁剪字节量和运行时输入估计各自记录。上下文溢出字段作为执行诊断保留。

每条轨迹保留候选数、提取尝试、实际触发、跳过原因、裁剪字节、辅助请求与用量，以及原文回读成功和拒绝次数。完整原始回执、辅助输入输出与源码身份随轨迹归档。

`early_auxiliary_usage` 单列早期选择性提取的开销；修复与历史摘要的逐请求用途和实际用量保存在 `raw-usage.json`。组内累计输入和输出涵盖这三类请求。

## 零请求预检与冻结清单

[registration.json](registration.json)记录 CPA 合同登记与 39 个临时状态 claim 检查，覆盖 smoke 和 full；登记时生产环境的本 campaign claim 与模型请求均为 0。其 `allocation_revalidation` 保留当前执行协议与登记记录的任务、分组、Attempt ID、额度及服务端源码一致性核对。

离线计划与验证文件位于 `preflight/`：

- `smoke-plan.json`、`full-plan.json`：三条与 36 条完整执行清单、协议身份及执行源码哈希。
- `source-manifest.json`：本地源码快照与文件哈希；正式工作流按实际运行 Commit 重新冻结。
- `validation.json`、`pytest.txt`、`pytest.xml`：零网络预检命令、结果与测试日志。

预检覆盖原资格包重建、六题三组的 worker `--check-only`、合同篡改拒绝、组间预算一致性、缺失结果保留、原文回读与 SDK 状态机。MockTransport 验证四次辅助请求与二十次修复请求合计为 24，下一次请求由本地账本拒绝。

本地可执行：

```bash
PYTHONPATH=src:scripts python -m pytest -q \
  tests/test_context_early*.py \
  tests/test_context_ablation.py \
  tests/test_context_trigger_campaign.py

PYTHONPATH=src:scripts python scripts/context_ablation.py plan \
  --protocol benchmarks/context-early-20261107/protocol.json \
  --scope smoke --output .repropatch/early-smoke-plan.json

PYTHONPATH=src:scripts python scripts/context_ablation.py plan \
  --protocol benchmarks/context-early-20261107/protocol.json \
  --scope full --output .repropatch/early-full-plan.json
```

`plan` 仅校验合同并生成清单，输出路径要求尚未存在。离线计划的 `github_run_id` 为 `null`；实际 workflow 生成绑定自身 Run ID 的执行清单。

## GitHub Actions 入口

`EARLY_CONTEXT_REF` 指向包含本目录合同及实现的已提交分支。先执行三组 smoke，再用相同代码快照执行 full。Full 的计划阶段自动核验指定 smoke：源码与协议相同、三条运行均有完整用量和冷评分、两个 early 组均发出过辅助提取请求。`KEEP` 决策与冷评分失败均作为有效观测保留；机械预检条件只验证实验链路。

```bash
gh workflow run formal-benchmark.yml \
  --repo lilong555/ReproPatch \
  --ref "$EARLY_CONTEXT_REF" \
  -f cross_stage=context-ablation \
  -f cross_protocol=benchmarks/context-early-20261107/protocol.json \
  -f context_scope=smoke

gh workflow run formal-benchmark.yml \
  --repo lilong555/ReproPatch \
  --ref "$EARLY_CONTEXT_REF" \
  -f cross_stage=context-ablation \
  -f cross_protocol=benchmarks/context-early-20261107/protocol.json \
  -f context_scope=full \
  -f context_smoke_run="$EARLY_CONTEXT_SMOKE_RUN_ID"
```

两条命令分别启动独立批次，`EARLY_CONTEXT_SMOKE_RUN_ID` 为三组 smoke 的 Actions Run ID。请求额度来自本目录冻结协议，CPA 依据 campaign、scope 和 Attempt ID 验证。已有上下文与定位实验使用同一 Actions 并发组串行排期，各批次内部最多八路执行。

机械预检回执由以下入口生成：

```bash
PYTHONPATH=src:scripts python scripts/check_early_smoke.py \
  --run-id "$EARLY_CONTEXT_SMOKE_RUN_ID" \
  --protocol benchmarks/context-early-20261107/protocol.json \
  --output .repropatch/early-prerequisite/receipt.json
```

校验器读取工作流中的 `GITHUB_SHA` 和 `GITHUB_REPOSITORY` 核对执行身份，并输出放行或拒绝原因。

运行入口为 `https://github.com/lilong555/ReproPatch/actions/runs/<run_id>`。原始轨迹和汇总可按 artifact 名下载：

```bash
gh run download "$EARLY_CONTEXT_RUN_ID" --repo lilong555/ReproPatch \
  --pattern 'context-raw-*' --dir early-context-raw

gh run download "$EARLY_CONTEXT_RUN_ID" --repo lilong555/ReproPatch \
  --pattern 'context-results-*' --dir early-context-results

gh run download "$EARLY_CONTEXT_RUN_ID" --repo lilong555/ReproPatch \
  --pattern 'context-plan-*' --dir early-context-plan
```

每条 `context-raw-<run>-<trial>` 包含文件 SHA-256 清单、SQLite 事件、请求账本、原始工具输出、候选补丁和冷评分记录；保留期为 30 天。`context-results-<run>` 输出完整 `results.json` 与分组 `summary.md`。
