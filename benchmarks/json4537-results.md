# nlohmann/json 四组真实修复与泛化

固定第四仓库 nlohmann/json-4537，批量修复候选已通过全部 **98 项原生测试**。
两轮全部尝试的结果为候选 **1/2**、ReproPatch 原版 **1/2**、mini-SWE-agent **2/2**、
Codex CLI **0/2**。候选和原版各有一次首次请求连接中断；Codex 首轮中继脚本权限失败，
第二轮第 6 次请求连接中断。这批证明候选能够修复第四仓库的缺陷，后续对照继续衡量稳定收益。

[逐次数据](json4537-results.json) ·
[完整证据](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-json4537-results-2026-10-23) ·
[环境资格与工具链](json4537-qualification.md)

| 批次 | 组别 | 请求 / 工具 | 候选评分 | Agent 结局 |
| --- | --- | ---: | --- | --- |
| 首轮 | 批量修复候选 | 1 / 0 | 空补丁 | 连接中断 |
| 首轮 | ReproPatch 原版 | 7 / 6 | 98/98，通过 | ACCEPTED |
| 首轮 | Codex CLI | 0 / 0 | 空补丁 | 中继脚本读取权限失败 |
| 首轮 | mini-SWE-agent | 8 / 7 | 98/98，通过 | 适配器包装 FormatError 后终止 |
| 第二轮 | 批量修复候选 | 9 / 11 | 98/98，通过 | ACCEPTED |
| 第二轮 | ReproPatch 原版 | 1 / 0 | 空补丁 | 连接中断 |
| 第二轮 | Codex CLI | 6 / 5 | 空补丁 | 请求连接中断 |
| 第二轮 | mini-SWE-agent | 8 / 8 | 98/98，通过 | Submitted |

缺陷涉及对象范围插入后 JSON_DIAGNOSTICS 的父对象指针及 invariant 断言。
批量候选同时修复 `include/nlohmann/json.hpp` 与 `single_include/nlohmann/json.hpp`，
内部独立验收和公共 Oracle 均通过。公共 Oracle 从原始 base commit 应用官方测试补丁和候选，
使用固定上游 parser 评分全部 98 项测试。

候选在第四仓库选题前冻结，核心 SHA-256 为
`3e137a39883ac87f35092b5497bfe86063bd179002c2b4b48e3beef15fd4a3ef`；
原版为 `6c13e9efed3f3c13206bf225c8aaed5413e438e27786af92f8adff98d63e7338`。
任务来自固定数据 revision `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d` 的
nlohmann 文件首条；原始源码 commit `e6cafa573aac6ed9227f752a5371c0b3f436307d`，
prepared commit `4bc894bccc39dccb96a42e68abde806f4427687f`。
累计动态资格覆盖 **7/129（5.43%）**、四个仓库；完整静态筛查保持全部 129 条记录。

四组共享 `gpt-6-luna`、HTTPS 端点、允许修改集合、2 CPU、4 GiB 内存、3 GiB 构建临时空间，
每次 12 请求、24 工具、8192 输出 token、256 KiB 输入边界和 90 秒请求超时。
单槽按候选、原版、Codex、mini 顺序运行，每组结束后独立评分。
mini 和 Codex 复用同轮原版首次领域输入，核验已注册的哈希；各框架保留原生系统提示和工具协议。
Codex 固定 0.163.0、原生 SSE，mini 固定 2.4.6。

首轮 mini 的 FormatError 来自提交输出格式，上游 Agent 原本支持恢复；该轮适配器将其包装成
RuntimeError。已保存候选仍通过评分。修正适配器保留上游 `InterruptAgentFlow`，独立编号复测另批记录。
第二轮使用原冻结适配器且正常提交。Codex 首轮原报告 `container_deleted=false` 原样保存，
附件另含后续 Docker 清理复核。

本批新增 **40** 次 CPA 请求，未知 usage **3** 次；已归档累计 **623** 次。
供应商实际账单费用未知，DeepSeek 历史费用上界维持 **¥2.18923088 / ¥20**。
worker 和公共 Oracle 的时间逐次单列；worker 的阶段构成随框架变化。
生产核心保持原版，批量候选继续接受真实修复检验。

附件 `ReproPatch-json4537-results-2026-10-23.tar.gz` 为 7,460,692 字节，含 6,188 个文件；
SHA-256：`254f55e367cc7b0260dc4f3d4bebac1073bf4acd255829c37ca88ecd11d4a092`。
逐文件大小与哈希、凭据哨兵、独立解压重算均通过。
解压后运行 `python3 summarize-json4537.py` 可重算逐次结果。
