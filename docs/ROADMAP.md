# 交付范围与状态

当前实现为 **0.3.0、Task v2**，聚焦固定预算下的 C++ 修复、独立验收和可复核证据。
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
| 发布交付 | 0.3.0 源码、包与证据按独立身份核对；公开发布需授权 | [发布清单](../RELEASE.json) |

v2 以三组实际 medium 配置得到 Full 1/2、mini 0/2、Codex 0/2。
Full 在 simdjson-1899 完成两次 F2P 自检后的修复并通过 93 项外部测试；fmt-4055 仍有失败记录。
两题已有 v1 尝试，历史 110 次请求单列保存。单项机制的因果收益需要预注册配对观察。

已有能力保留：只读接口追踪、可编辑状态反馈、剩余预算反馈、紧凑诊断和独立验收。
符号导航扩张、自动源码片段注入、并行工具候选、额外任务适配、通用 Harbor 和执行器扩展均已封存。
当前交付完成后，以已保存的失败证据和明确授权决定是否开展新的实验。

后续 Luna 实验使用独立协议、源码身份和预算，先核对供应商响应中的 max。
已有 v2 配置与成绩保持冻结，全部模型用量见[原始账本审计](../benchmarks/model-usage-audit.json)。
