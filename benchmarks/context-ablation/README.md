# 上下文消融实验

固定使用历史结果 `paired_tasks` 中的 19 个 fmt 缺陷任务，每题执行五组策略、各重复两次，共 190 条独立轨迹。任务来源为 Multi-SWE-bench，样本性质为已暴露的开发任务。各组共享同一源码、模型、工具、系统提示、执行预算和独立冷评分流程。

[完整结果](full/README.md) 保存五组成功率与 Token 用量、19 题明细、30 条失败记录及 190 条原始轨迹入口。

| 分组 | 结构化诊断 | 精确结果去重 | 状态感知压缩 |
| --- | --- | --- | --- |
| baseline | 关闭 | 关闭 | 关闭 |
| diagnostics | 开启 | 关闭 | 关闭 |
| dedup | 关闭 | 开启 | 关闭 |
| state | 关闭 | 关闭 | 开启 |
| combined | 开启 | 开启 | 开启 |

## 策略与观测

结构化诊断在校验大小与 SHA-256 后读取完整日志，保留编译器位置、模板实例化关联、源码摘录及 GTest Expected/Actual 正文，合并重复诊断并移除可确认的正常进度。真正截断、来源缺失或解析上限触发时返回原生回执，并记录原因。

精确结果去重覆盖同源码、同参数的完整只读文件/搜索/目录回执，以及同执行阶段的检查回执。工具仍实际执行，当前进度与原文引用随返回保留；源码变化和历史压缩使去重状态失效。状态摘要采用有界投影，保留当前检查和修复状态，记录裁剪原因及实际省略数量。

每条回执记录尝试数、候选数、实际触发、跳过原因和字节变化。请求账本单列 `peak_estimated_input_tokens` 与估算观测覆盖度，供应方实际 Token 用量保持独立统计。

`combined` 对同一回执先尝试精确去重，成功后诊断记录 `superseded_by_dedup`；否则继续尝试诊断投影。组合效应按整条轨迹的真实用量、触发覆盖和冷评分统计，单策略字节节省各自报告。

## 固定条件

- 模型：`gpt-6-luna`，推理档位 `max`，通过 Azure CPA 的 SSH 回环入口调用。
- 执行器：原生 ReproPatch，legacy 六工具，开启中间自检与单任务编译缓存。
- 上下文：128,000 token 窗口，48,000 触发压缩，21,600 目标，保留最近两轮，工具返回上限 24 KiB。
- 每次尝试：24 次模型请求、48 次工具调用、7,200 秒总预算、1,200 秒验证预留，单次模型请求等待上限 600 秒；摘要请求计入同一请求预算。
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

## 回执策略批次

[trigger-protocol.json](trigger-protocol.json) 使用独立 campaign `context-ablation-trigger-20261106`，绑定原协议 SHA-256，复用相同任务、模型、预算与 48,000 压缩阈值。`receipt-context-v2` 的 smoke 固定为 `fmtlib__fmt-2310` 五组各一次，共 120 次请求额度；全量规模保持 190 条。共享 Actions 并发组将同类批次串行调度，批次内保持最多 8 个 worker。

```bash
gh workflow run formal-benchmark.yml \
  --repo lilong555/ReproPatch \
  --ref fix/context-trigger-20261106 \
  -f cross_stage=context-ablation \
  -f cross_protocol=benchmarks/context-ablation/trigger-protocol.json \
  -f context_scope=smoke \
  -f authorization=unlimited
```

[真实回执离线复算](trigger-replay/README.md) 覆盖四归档、89 条回执和四次诊断触发，保存逐条原文身份及返回字节。模型 smoke 用于检查实际触发覆盖、请求行为与冷评分，完整分组收益由同批次配对数据判断。

[回执策略预检结果](trigger-smoke/README.md)保存五组真实模型轨迹及跳过原因：诊断提取实际触发 2 次，其他机制保持零触发；五条运行的用量与冷评分完整。

## 结果产物

- `context-plan-<run>`：任务顺序、分组开关、预算、源码身份与工作流身份。
- `context-raw-<run>-<trial>`：真实请求用量、SQLite 事件、工具原文、压缩记录、候选补丁、冷评分和文件哈希清单。
- `context-summary-<run>-<trial>`：单次结果与准备、执行、归档阶段状态。
- `context-results-<run>`：全部注册尝试的结果表、分组统计、配对差异、上下文失败分类及策略实际触发覆盖率。

汇总保留失败与缺失尝试，未知用量单独记录。Token 统计与冷评分成功率共同呈现；字节投影指标单独保留。每组正式样本数为 38，配对比较按任务和重复编号对齐。

## 连接检查

[cpa-concurrency-probe.json](cpa-concurrency-probe.json) 记录一次 8 路同时发起的短请求检查：8 次均返回 HTTP 200 和 `OK`，单请求观测耗时 2.125–6.884 秒。连接检查单独计数；正式轨迹的用量、延迟和失败情况由实验原始记录汇总。

## 联调结果

[五组联调 42216432142](https://github.com/lilong555/ReproPatch/actions/runs/42216432142) 使用单次请求等待上限 180 秒，完成 4 条冷评分，另有 1 条在第 12 次模型请求处超时。原始 [结果表](smoke/summary.md) 与 [完整汇总](smoke/results.json) 独立保存。正式实验的单次请求等待上限为 600 秒，任务源码、测试定义、模型、每条请求额度、总执行预算和五组处理机制保持一致。
