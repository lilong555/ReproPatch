# 交付范围与状态

正式版本 **[v0.3.0](https://github.com/lilong555/ReproPatch/releases/tag/v0.3.0)** 已发布，
任务格式为 **Task v2**，聚焦固定预算下的 C++ 修复、独立验收和可复核证据。
[规格](../specs/2026-10-19.2/SPEC.md)定义执行契约，
[实施状态](IMPLEMENTATION_PLAN.md)与[测试报告](TEST_REPORT.md)记录实际交付。

| 范围 | 当前状态 | 证据 |
| --- | --- | --- |
| 受控修复与独立验收 | 完成；六工具、完整源码清单、Docker 隔离、CTest 逐项裁决 | [架构](ARCHITECTURE.md) |
| Checkpoint、有限恢复、只读轨迹 | 完成；SQLite 事务保存状态、预算和事件 | P2-01 至 P2-04 |
| F2P 自检与回归策略 | 完成；调试优先 reproduce，预算允许继续修复时 verify，最终独立验收 | [v2 结果](../benchmarks/generalization-final-results.md) |
| 候选来源 | 完成；首个非空来源导出，损坏引用明确报错 | [候选契约](../tests/test_codex_benchmark.py) |
| 三框架 v2 对照 | 完成；六次首跑，61/72 次正式请求，另 1 次参数校准 | [冻结协议](../benchmarks/generalization-protocol-v2.json) |
| Luna 推理配置 | 后续对照默认 max，三个原生客户端的离线请求检查通过 | [配置与校准范围](../benchmarks/luna-max-config.json) |
| 发布交付 | v0.3.0 已发布；514 项测试通过，11 个附件通过公开下载与 SHA-256 核验 | [发布清单](../RELEASE.json) |

v2 以三组实际 medium 配置得到 Full 1/2、mini 0/2、Codex 0/2。
Full 在 simdjson-1899 完成两次 F2P 自检后的修复并通过 93 项外部测试；fmt-4055 仍有失败记录。
两题已有 v1 尝试，历史 110 次请求单列保存。单项机制的因果收益需要预注册配对观察。

## 云端资格与效率实验

Actions 工作流、统一冷 Oracle、显式 candidate-only、Run 内 ccache、资源测量和证据归档已交付。
[云端实验](ACTIONS_RESULTS.md)以固定 GHCR digest 完成 21 题 O3 Docker 重验，其中 21 题合格；
同一目标构建 A/B 与四题 1/2/4 Job 对照均完成。完整开发态 CI 通过 584 项。
2026-10-24 的 41 条原生资格和本地测量按当时环境保留于[原生报告](BENCHMARK_SCALE_REPORT.md)。

## 后续实验

| 工作 | 验收标准 |
| --- | --- |
| json 扩容 | 复用离线数据与双头文件回归，先验证 10–20 道有依据的新缺陷，保留失败 |
| 四臂执行与预算 | Full、关闭中途执行与测试反馈的 Full、mini、Codex 使用相同任务与最终 Oracle；固定请求、Token 和金额硬上限 |
| 冻结模型首跑 | 两题、四臂、每次最多 12 请求的提案上限为 96 请求；max 校准独立记账，首跑全部保留 |

Luna 后续默认 `max`，真实供应商响应校准与付费模型批次待执行。
现有零模型工作流执行额度为 0；新的模型批次先固定任务、源码、供应商参数与预算。
v2 的 medium 配置、六次运行与历史失败完整保留。

当前保持两 Job 默认并发，复用已有执行器、任务适配和冷验收；符号导航扩张、自动源码片段注入、
并行工具候选、通用 Harbor 和复杂恢复扩展继续封存。
