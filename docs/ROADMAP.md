# 交付范围与状态

正式版本 **[v0.3.0](https://github.com/lilong555/ReproPatch/releases/tag/v0.3.0)** 已发布，
任务格式为 **Task v2**，聚焦固定预算下的 C++ 修复、独立验收和可复核证据。
[规格](../specs/2026-10-19.2/SPEC.md)定义执行契约，
[实施状态](IMPLEMENTATION_PLAN.md)与[测试报告](TEST_REPORT.md)记录实际交付。

| 范围 | 当前状态 | 证据 |
| --- | --- | --- |
| 受控修复与独立验收 | 完成；六工具和持久 Shell、完整源码清单、Docker 隔离、CTest 逐项裁决 | [架构](ARCHITECTURE.md)、[Shell-first](SHELL_FIRST.md) |
| Checkpoint、有限恢复、只读轨迹 | 完成；SQLite 事务保存状态、预算和事件 | P2-01 至 P2-04 |
| F2P 自检与回归策略 | 完成；调试优先 reproduce，预算允许继续修复时 verify，最终独立验收 | [v2 结果](../benchmarks/generalization-final-results.md) |
| 候选来源 | 完成；首个非空来源导出，损坏引用明确报错 | [候选契约](../tests/test_codex_benchmark.py) |
| 三框架 v2 对照 | 完成；六次首跑，61/72 次正式请求，另 1 次参数校准 | [冻结协议](../benchmarks/generalization-protocol-v2.json) |
| Luna 推理配置 | 默认 max；客户端检查、真实供应商校准与 21 题四臂实验完成 | [配置与校准范围](../benchmarks/luna-max-config.json) |
| 发布交付 | v0.3.0 已发布；514 项测试通过，11 个附件通过公开下载与 SHA-256 核验 | [发布清单](../RELEASE.json) |

v2 以三组实际 medium 配置得到 Full 1/2、mini 0/2、Codex 0/2。
Full 在 simdjson-1899 完成两次 F2P 自检后的修复并通过 93 项外部测试；fmt-4055 仍有失败记录。
两题已有 v1 尝试，历史 110 次请求单列保存。单项机制的因果收益需要预注册配对观察。

## 云端资格与效率实验

Actions 工作流、统一冷 Oracle、显式 candidate-only、Run 内 ccache、资源测量和证据归档已交付。
[云端实验](ACTIONS_RESULTS.md)以固定 GHCR digest 完成 21 题 O3 Docker 重验，其中 21 题合格；
同一目标构建 A/B 与四题 1/2/4 Job 对照均完成。免费资格源码 CI 通过 584 项，冻结模型实验源码 CI 通过 614 项。
2026-10-24 的 41 条原生资格和本地测量按当时环境保留于[原生报告](BENCHMARK_SCALE_REPORT.md)。

## 正式模型实验

[Luna max 四臂首跑](ACTIONS_FORMAL.md)已完成 21 道题、84 次模型运行。
首批两题 90 秒模型超时使用 76 请求；后续 19 题统一 180 秒使用 866 请求。
正式合计 942/1008 请求、7 次未知用量，独立校准另计 1 请求。
19 题外部 Oracle 通过数为 Full 7/19、关闭自检组 10/19、mini 11/19、Codex 11/19。
全部候选、失败、用量、网关 HTTP 524 与冷验收证据保留。

## 后续工作

| 工作 | 验收标准 |
| --- | --- |
| Shell-first 基线 | 完成；持久 Bash、合法补丁导出和独立冷 Oracle，653 项 Actions 测试通过，见 [规格](SHELL_FIRST.md) |
| 目标级增量验证 | 持久构建目录中编译相关 target、运行可见定向测试，记录分阶段耗时 |
| 编译诊断反馈 | GCC/Clang 摘要与完整日志并存，单独比较输入 Token、耗时和修复结果 |
| 六题开发实验 | 固定模型与预算，比较 Shell-only 和 C++ 快速反馈；独立集覆盖至少两个仓库 |
| 长期证据复核 | 使用归档与 SHA-256 重算用量、候选和统一冷 Oracle，保存全部首次模型结果 |
| json 扩容准备 | 复用现有离线数据与双头文件回归，逐题保存资格与失败证据；新模型批次单独冻结预算 |

Luna 默认 `max`；新的付费批次单独固定任务、源码、供应商参数与预算。
v2 的 medium 配置、六次运行与历史失败完整保留。

当前保持两 Job 默认并发，复用已有执行器、任务适配和冷验收；符号导航扩张、自动源码片段注入、
并行工具候选、通用 Harbor 和复杂恢复扩展继续封存。
