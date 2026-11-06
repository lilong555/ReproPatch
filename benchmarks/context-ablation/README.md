# 上下文消融实验

固定使用历史结果 `paired_tasks` 中的 19 个 fmt 缺陷任务，每题执行五组策略、各重复两次，共 190 条独立轨迹。任务来源为 Multi-SWE-bench，样本性质为已暴露的开发任务。各组共享同一源码、模型、工具、系统提示、执行预算和独立冷评分流程。

| 分组 | 结构化诊断 | 精确结果去重 | 状态感知压缩 |
| --- | --- | --- | --- |
| baseline | 关闭 | 关闭 | 关闭 |
| diagnostics | 开启 | 关闭 | 关闭 |
| dedup | 关闭 | 开启 | 关闭 |
| state | 关闭 | 关闭 | 开启 |
| combined | 开启 | 开启 | 开启 |

## 固定条件

- 模型：`gpt-6-luna`，推理档位 `max`，通过 Azure CPA 的 SSH 回环入口调用。
- 执行器：原生 ReproPatch，legacy 六工具，开启中间自检与单任务编译缓存。
- 上下文：128,000 token 窗口，48,000 触发压缩，21,600 目标，保留最近两轮，工具返回上限 24 KiB。
- 每次尝试：24 次模型请求、48 次工具调用、7,200 秒总预算、1,200 秒验证预留；摘要请求计入同一请求预算。
- 调度：GitHub Actions 最多 8 个独立 worker，任务与分组顺序预注册在 [protocol.json](protocol.json)。
- 评分：复用固定镜像、原始资格记录与 `score_benchmark_attempt.py`，对冻结候选补丁执行独立冷评分。

`inputs/` 保存原资格批次 `40194807297` 的两份归档；每次准备核对原始 SHA-256 及文件清单，再重建任务源码。完整执行配置和源码文件哈希写入工作流的冻结清单，并在每个 worker 中再次核验。

## 运行

```bash
gh workflow run formal-benchmark.yml \
  --repo lilong555/ReproPatch \
  --ref experiment/context-ablation-20261106 \
  -f cross_stage=context-ablation \
  -f context_scope=smoke \
  -f authorization=unlimited
```

`smoke` 执行一个固定任务的五组联调，`full` 执行全部 190 次尝试。两类运行使用独立的 Attempt ID。正式运行采用 `context_scope=full`，每次工作流生成自己的冻结清单和结果归档。

## 结果产物

- `context-plan-<run>`：任务顺序、分组开关、预算、源码身份与工作流身份。
- `context-raw-<run>-<trial>`：真实请求用量、SQLite 事件、工具原文、压缩记录、候选补丁、冷评分和文件哈希清单。
- `context-summary-<run>-<trial>`：单次结果与准备、执行、归档阶段状态。
- `context-results-<run>`：全部注册尝试的结果表、分组统计、配对差异、上下文失败分类及策略实际触发覆盖率。

汇总保留失败与缺失尝试，未知用量单独记录。Token 统计与冷评分成功率共同呈现；字节投影指标单独保留。每组正式样本数为 38，配对比较按任务和重复编号对齐。

## 连接检查

[cpa-concurrency-probe.json](cpa-concurrency-probe.json) 记录一次 8 路同时发起的短请求检查：8 次均返回 HTTP 200 和 `OK`，单请求观测耗时 2.125–6.884 秒。连接检查单独计数；正式轨迹的用量、延迟和失败情况由实验原始记录汇总。
