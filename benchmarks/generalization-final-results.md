# 三框架固定预算对照

2026-10-24，fmt-4055 与 simdjson-1899 共六次正式尝试完成，使用 61 / 72 次模型请求。
三组请求同一 CPA 端点的 gpt-6-luna，逐次保存实际请求和响应推理参数。
Codex 的单次参数校准独立记账。每题使用相同提交、镜像、编辑范围和外部原生 Oracle。

这两项预注册新实例已有 v1 尝试；本表报告冻结新配置后的 v2 复核。
[v1 历史记录](generalization-v1-results.md)完整保留 110 次请求及取消、未执行项。

| 任务 | 框架 | Oracle | 原生状态 | 请求 | 工具 | reproduce / verify |
| --- | --- | --- | --- | ---: | ---: | ---: |
| fmt-4055 | full | 0/20，NATIVE_BUILD_OR_TEST_FAILED | REJECTED | 12 | 12 | 1 / 0 |
| fmt-4055 | mini | 0/20，NO_PATCH | Submitted | 9 | 9 | - |
| fmt-4055 | codex | 0/20，NO_PATCH | BENCHMARK_REQUEST_LIMIT | 12 | 12 | - |
| simdjson-1899 | full | 93/93，通过 | ACCEPTED | 11 | 10 | 2 / 1 |
| simdjson-1899 | mini | 92/93，NATIVE_BUILD_OR_TEST_FAILED | Submitted | 5 | 5 | - |
| simdjson-1899 | codex | 92/93，NATIVE_BUILD_OR_TEST_FAILED | BENCHMARK_REQUEST_LIMIT | 12 | 12 | - |

| 框架 | 外部通过 | 请求 | 输入 tokens | 输出 tokens | 未知用量请求 |
| --- | ---: | ---: | ---: | ---: | ---: |
| full | 1/2 | 23 | 399532 | 1944 | 0 |
| mini | 0/2 | 14 | 176690 | 2712 | 0 |
| codex | 0/2 | 24 | 583746 | 3218 | 0 |

Full 记录 `native_accepted` 与 `recovered_oracle_pass`；所有框架均以外部 Oracle 为主指标。
Codex 的 CLI 退出码、预算结束原因和补丁得分分别记录。
Full 的 worker 时间包含基线、修复和独立验收；mini/Codex 的 worker 时间覆盖修复及自检，
各框架的外部 Oracle 时间单列于 JSON。两题未覆盖 nlohmann/json 的单头文件专项。

simdjson 的 Full 第 3 步首次编辑，第 4、9 步执行 F2P 自检，第 10 步检查全量回归。
最终补丁同时覆盖过小指数的早退路径与常规转换后归零的负号保留；mini 与 Codex 的候选仅覆盖早退路径。
Full 的两次 F2P 自检耗时约 86.0、85.1 秒，全量自检约 188.4 秒，均包含配置与编译。
内部独立验收另耗时约 192.2 秒，外部原生 Oracle 约 157.0 秒。
这些时间来自对应评估记录，具体修复过程与提示机制的归因分开报告。

两题各一次的观察用于展示有限预算下的实际修复行为和可复现验收。
reproduce 仍包含配置与编译；具体耗时、调用次数与结果均来自原始事件，
单独机制的收益需要配对实验进一步识别。

[冻结协议](generalization-protocol-v2.json)与[逐运行结果](generalization-final-results.json)包含源码、请求、候选、Oracle 和用量引用。
