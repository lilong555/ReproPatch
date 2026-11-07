# 提前压缩三组正式实验结果

六道 fmt 缺陷任务、三组配置、每题两次重复，共 **36 条轨迹**。提前观察提取加状态摘要（`early_state`）的冷验收为 **10/12**，与基线相同；计入全部辅助调用后，单任务平均输入从 **232,541.08 降至 181,439.67 Token，减少 21.98%**，输入与输出合计减少 **20.64%**。单独提前观察提取（`early`）通过 9/12，平均输入增加 6.43%。

本批使用此前已暴露的六道开发任务，按冻结的任务标识哈希选取。两次重复中 `early_state` 的总体输入分别减少 22.51% 和 21.42%；任务均值的下降集中于 `fmt-3750`、`fmt-3819`，其余四题增加 0.49%–44.81%。结果支持这组配置在本批负载上的总体输入改善。

## 成功率与全量用量

| 配置 | 冷验收通过 | 平均输入 Token | 相对基线 | 平均输出 Token | 输入＋输出变化 | 模型请求 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 10/12（83.3%） | 232,541.08 | — | 6,985.83 | — | 196 |
| early | 9/12（75.0%） | 247,482.33 | +6.43% | 9,578.83 | +7.32% | 243 |
| early_state | 10/12（83.3%） | 181,439.67 | −21.98% | 8,641.25 | −20.64% | 249 |

全部 36 条评分与用量完整，基础设施异常为 0，未知用量请求为 0。总计 **688 次请求**，其中修复 588 次、辅助 100 次。七条失败全部进入均值和成功率分母。`baseline` 与 `early_state` 的十二对结果为十对共同通过、两对共同失败；`early` 额外失败一条 `fmt-3750`。

模型为 `gpt-6-luna/max`，每条最多 24 次总请求、48 次工具调用，执行源码为 [`586fe18`](https://github.com/lilong555/ReproPatch/tree/586fe18e9d073d92a9943f220919f2a6d4b53af7)。冻结合同和三组配置见[协议说明](../README.md)。`early_state` 同时采用 16K 历史水位与状态摘要，`baseline`、`early` 为 48K 水位；本次比较评价这组组合配置。

## 辅助调用与实际触发

| 配置 / 请求用途 | 请求数 | 输入 Token | 输出 Token |
| --- | ---: | ---: | ---: |
| baseline：修复 | 196 | 2,790,493 | 83,830 |
| early：修复 | 198 | 2,595,193 | 76,536 |
| early：原文行选择 | 45 | 374,595 | 38,410 |
| early_state：修复 | 194 | 1,683,477 | 53,362 |
| early_state：原文行选择 | 45 | 353,435 | 34,334 |
| early_state：历史状态摘要 | 10 | 140,364 | 15,999 |

`early` 的修复请求输入减少 195,300 Token，选择性提取新增 374,595 Token，因此全量输入增加 179,295。`early_state` 的修复请求输入减少 1,107,016 Token，两类辅助调用共消耗 493,799 Token，最终净减少 613,217 Token。

| 机制 | early | early_state |
| --- | ---: | ---: |
| 发生原文行裁剪的轨迹 | 12/12 | 12/12 |
| 原文行选择请求 / 实际裁剪 | 45 / 38 | 45 / 41 |
| 实际省略的原文 UTF-8 字节 | 70,259 | 70,809 |
| 发生历史状态摘要的轨迹 | 0/12 | 9/12 |
| 历史状态摘要次数 | 0 | 10 |
| 原文回读次数 | 0 | 0 |

`early` 的七次未裁剪选择包含五次净缩减不足和两次模型选择 KEEP；`early_state` 四次为净缩减不足。已发出的选择请求均计入用量。裁剪字节记录一次投影变化，累计输入记录后续各请求实际携带的上下文和全部辅助开销。

## 逐题结果

每格为“冷验收通过数；单任务平均输入 Token”，各格分母均为两次执行。

| 任务 | baseline | early | early_state | early_state 输入变化 |
| --- | ---: | ---: | ---: | ---: |
| fmt-2070 | 2/2；96,624 | 2/2；191,779 | 2/2；139,921.5 | +44.81% |
| fmt-3537 | 2/2；184,792 | 2/2；309,176.5 | 2/2；208,478.5 | +12.82% |
| fmt-3713 | 2/2；92,858.5 | 2/2；119,914.5 | 2/2；93,315 | +0.49% |
| fmt-3750 | 2/2；430,393 | 1/2；357,351.5 | 2/2；216,373.5 | −49.73% |
| fmt-3819 | 0/2；379,061.5 | 0/2；300,144.5 | 0/2；214,117.5 | −43.51% |
| fmt-493 | 2/2；211,517.5 | 2/2；206,528 | 2/2；216,432 | +2.32% |

`fmt-3819` 三组共六次均失败，节省的输入保留在全样本统计中。六个任务与每题两次重复分别计量，后续跨仓库验证可使用已冻结的 [Flash C++ 任务清单](../../context-workload-20261107/README.md)。

## 缓存与计价

| 配置 | 全部输入 | 其中缓存输入 | 非缓存输入 | 缓存输入占比 |
| --- | ---: | ---: | ---: | ---: |
| baseline | 2,790,493 | 2,230,144 | 560,349 | 79.92% |
| early | 2,969,788 | 1,879,680 | 1,090,108 | 63.29% |
| early_state | 2,177,276 | 992,128 | 1,185,148 | 45.57% |

输入降幅采用供应方报告的全部逻辑输入，包含缓存输入。`early_state` 的缓存占比下降，非缓存输入增加到 1,185,148 Token；模型费用保持未定价，计费结论需要结合实际供应方账单。

## 逐条失败原因

七条失败均以 `REQUEST_BUDGET_EXHAUSTED` 停止，具体冷验收失败点如下。日志与补丁全文见[失败证据](failures.md)。

| 轨迹 | 任务 / 配置 / 重复 | 冷评分 | 日志所示失败点 |
| --- | --- | --- | --- |
| trial-002 | fmt-3819 / early / 2 | ORACLE_TESTS_FAILED | `args_test.named_with_automatic_index` |
| trial-006 | fmt-3819 / early_state / 1 | ORACLE_TESTS_FAILED | `args_test.named_with_automatic_index` |
| trial-009 | fmt-3819 / early / 1 | ORACLE_TESTS_FAILED | `args_test.named_with_manual_index`、`args_test.reserve` |
| trial-018 | fmt-3819 / baseline / 1 | ORACLE_TESTS_FAILED | `args_test.reserve` |
| trial-028 | fmt-3819 / early_state / 2 | EMPTY_CANDIDATE | 结束时未形成非空候选补丁 |
| trial-032 | fmt-3819 / baseline / 2 | ORACLE_BUILD_FAILED | `basic_format_parse_context` 缺少 `advance_to_arg_id` |
| trial-035 | fmt-3750 / early / 2 | ORACLE_BUILD_FAILED | 模板实例化时找不到 `make_write_int_arg` 声明 |

这些记录描述实际执行和评分的失败位置。压缩对具体失败的因果影响由配对结果和后续单机制实验继续判断。

## 原始证据与复算

[Actions Run 42343832567](https://github.com/lilong555/ReproPatch/actions/runs/42343832567) 已完成。36/36 ZIP 摘要、tar 逐文件清单、原始评分与候选哈希核验通过；688/688 供应方响应与 SQLite 用量及预发送记录一致。三组每题的 Task、系统提示和工具定义哈希一致。首次输入存在独立基线回执的运行标识、时间、附件路径和日志差异，逐字段路径保存在用量审计中。

- [原始 CI 结果](results.json)、[实际执行清单](plan.json)、[全部原始轨迹下载入口](trajectories.md)
- [归档索引与 SHA-256](artifacts.json)、[下载校验回执](downloads.json)
- [分组复算](analysis.json)、[逐条冷评分核验](evidence.jsonl)、[逐条失败与日志](failures.md)
- [逐用途用量、逐题均值和首次输入差异](usage-audit/summary.json)、[688 次请求核验](usage-audit/attempts.jsonl)

下载每条 artifact 并解压到 `RAW_ROOT/context-raw-42343832567-trial-NNN/`，保留 `artifact.zip`、三个 tar 相关文件及对应 `download.json`。使用 Python 3.12、项目依赖和新的输出目录执行：

```bash
PYTHONPATH=src:scripts python scripts/report_context_results.py \
  --results benchmarks/context-early-20261107/full/results.json \
  --artifacts benchmarks/context-early-20261107/full/artifacts.json \
  --raw-dir "$RAW_ROOT" --output /tmp/early-cold-audit

PYTHONPATH=src:scripts python scripts/audit_completed_usage.py context \
  --results benchmarks/context-early-20261107/full/results.json \
  --artifacts benchmarks/context-early-20261107/full/artifacts.json \
  --raw-dir "$RAW_ROOT" --output /tmp/early-usage-audit
```

两条命令均为原始证据的离线复算，模型调用为零。下载回执可以从 `downloads.json` 中按 artifact 名称恢复。
