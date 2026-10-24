# 泛化实验 v1 历史记录

2026-10-24，v1 共保留 110 次模型请求：10 次尝试完成外部 Oracle 评分，
1 次由控制端取消，5 次未执行。已知用量覆盖 109 次请求，另 1 次用量未知。
全部 16 个预注册位置均列在下表；v2 使用独立 attempt ID 和账本。

v1 的 Full 与 mini 响应推理强度为 medium，Codex 请求与响应为 none。
mini 原始运行源码固定为 2.4.6；Codex 固定为 0.163.0。
这些记录保留历史配置和原始失败，供核查实验演进与资源消耗。

| Attempt | 执行状态 | 外部 Oracle | 请求 | 工具 |
| --- | --- | --- | ---: | ---: |
| `fmt4055-full-1` | SCORED | FAIL | 12 | 12 |
| `fmt4055-candidate-1` | SCORED | FAIL | 12 | 18 |
| `fmt4055-mini-1` | SCORED | FAIL | 10 | 10 |
| `fmt4055-codex-1` | SCORED | NO_PATCH | 12 | 12 |
| `fmt4055-codex-2` | SCORED | NO_PATCH | 12 | 12 |
| `fmt4055-mini-2` | SCORED | PASS | 11 | 11 |
| `fmt4055-candidate-2` | SCORED | FAIL | 12 | 14 |
| `fmt4055-full-2` | SCORED | FAIL | 12 | 12 |
| `simd1899-mini-1` | SCORED | FAIL | 4 | 4 |
| `simd1899-codex-1` | SCORED | FAIL | 12 | 12 |
| `simd1899-full-1` | CANCELLED | NOT_RUN | 1 | 0 |
| `simd1899-candidate-1` | NOT_RUN | NOT_RUN | 0 | - |
| `simd1899-candidate-2` | NOT_RUN | NOT_RUN | 0 | - |
| `simd1899-full-2` | NOT_RUN | NOT_RUN | 0 | - |
| `simd1899-codex-2` | NOT_RUN | NOT_RUN | 0 | - |
| `simd1899-mini-2` | NOT_RUN | NOT_RUN | 0 | - |

取消记录为 `simd1899-full-1`：Harness 返回 `CANCELLED / USER_CANCELLED`，
已确认容器清理，产生 1 次请求、0 次工具调用，候选为空。

原协议 SHA-256：`00ed4717b4bd45064ba23137e416ba5ce5b2194330d0b1064d083f17000ae2e3`。
逐请求哈希、用量、原始状态与 Oracle 引用见 [generalization-v1-results.json](generalization-v1-results.json)。
