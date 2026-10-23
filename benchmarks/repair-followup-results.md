# C++ 修复周期与对照复测

相关模板调用反馈候选在 FMT-4286 的第三次尝试通过 **21/21** 项原生测试，
同候选三次完整记录为 **1/3**。首次连接中断、第二次回归失败均保留。
Codex 使用与 ReproPatch 相同的宿主 HTTP 客户端后，在 json-4537 通过 **98/98**，
使用 8 次请求、7 次工具调用。

[逐次结果](repair-followup-results.json) · [源码清单](repair-followup-source-manifest.json) ·
[原始证据](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-repair-followup-2026-10-23)

| 实例 | 策略 / 框架 | 请求 / 工具 | 公共 Oracle | Agent 结局 |
| --- | --- | ---: | --- | --- |
| json-4537 | ReproPatch 原版第三次 | 6 / 5 | 98/98，通过 | ACCEPTED |
| json-4537 | Codex 第三次 | 1 / 0 | 空补丁 | 连接中断 |
| json-4537 | mini 第三次，原生格式恢复 | 7 / 6 | 98/98，通过 | 请求返回 InternalServerError |
| json-4537 | Codex 第四次，统一 HTTP 客户端 | 8 / 7 | 98/98，通过 | CLI 退出 0 |
| FMT-4286 | 短周期候选 | 12 / 18 | 20/21，回归失败 | F2P_FAILED |
| FMT-4310 | 短周期候选 | 1 / 0 | 空补丁 | 连接中断 |
| simdjson-2178 | 短周期候选 | 12 / 15 | 97/99，两个目标失败 | F2P_FAILED |
| FMT-4286 | 相关模板反馈候选首次 | 7 / 12 | 20/21，xchar 崩溃 | 连接中断 |
| FMT-4286 | 同候选第二次 | 12 / 18 | 20/21，回归失败 | F2P_FAILED |
| FMT-4286 | 同候选第三次 | 12 / 18 | 21/21，通过 | ACCEPTED |

短周期候选核心 SHA-256 为
`d0174ace4be3116c7dfcdd79f99a340a5677a19042f26d01c0b0f3109cad05e2`。
它保留 SDK 批量工具，并精简修复提示，要求证据充分时尽早编辑和自检。
FMT 首次编辑为第 3 轮，自检为第 4 轮；三题评分为 0/3。

相关模板反馈候选核心为
`1f77a7d1421abe0a6fefe6e187fbfe464d72d0b850c3a0ac5ae5a40005ae76fd`。
编辑替换模板成员调用时，工具从授权可读源码返回最多八处相关用法。
反馈覆盖 `fill<Char>()` 的其他调用，包括 complex formatter 的填充实现。
成功尝试同时修复 bitset 的模板继承、依赖基类调用、nested formatter 及 complex 的宽字符填充，
内部独立验收和公共原生测试均通过。三次中的后两次首次编辑均为第 2 轮。

全部题目已有开发历史；本批直接衡量故障修正信号和重复表现。
同模型下 FMT 的原版、mini、Codex 历史候选均有失败，详见[六题对照](cross-framework-results.md)。
相关模板反馈候选的独立新题验证使用 json-4525，协议、源码和预算在模型运行前冻结。
生产核心保持 `6c13e9efed3f3c13206bf225c8aaed5413e438e27786af92f8adff98d63e7338`。

Codex 保留原生 CLI 0.163.0、系统提示、Shell 和补丁工具及 SSE；宿主 HTTP 使用 `httpx2`，
统一代理配置、90 秒超时、禁止自动重试，每请求输出上限为 8192。
mini 保留上游 `InterruptAgentFlow`，支持原生格式恢复。
每次 12 请求、24 工具、256 KiB 输入边界和同题资源配置保持固定。
各实验单槽执行，worker 与公共 Oracle 时间单列，框架的 worker 阶段构成分别记录。

json-4537 的全部历史累计结果为：批量候选 1/2、原版 2/3、mini 3/3、Codex 1/4。
Codex 四次分别为权限失败、连接中断、连接中断及统一 HTTP 客户端后的成功。
[最初两轮](json4537-results.md)保留原批次成绩；每次已发起尝试继续进入对应批次记录。

本批新增 **78** 次 CPA 请求，未知 usage **4** 次，已归档累计 **701** 次。
供应商实际账单未知；DeepSeek 历史费用上界为 **¥2.18923088 / ¥20**。
json-4525 的首次零模型资格检查受 Docker 服务中断影响，原始证据随本附件保存，后续资格另编号。

附件 `ReproPatch-repair-followup-2026-10-23.tar.gz` 为 12,131,730 字节，含 6,694 个文件。
SHA-256：`6c106dc914c4f4ed5d77226035a1a6036d313a65c3ea562d0aff790b26657ab4`。
Task、候选、冻结源码、原始模型请求与响应、SQLite、Oracle 和逐文件清单完整保存。
逐文件字节核验、凭据哨兵和独立解压重算通过；解压后运行
`python3 summarize-repair-followup.py` 可重新计算逐次结果。
