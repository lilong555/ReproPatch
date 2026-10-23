# 批量修复策略与 simdjson 四组复测

固定 `gpt-6-luna`、HTTPS 端点和每次 12 请求预算，批量修复候选在 simdjson-2178
的两次尝试均通过全部 99 项原生测试。第二轮原版候选也通过；mini 和 Codex 复测各通过
97 项，两个目标回归仍失败。FMT-4286 的批量候选构建失败。

[逐次数据](batched-repair-results.json) · [源码清单](batched-repair-source-manifest.json) ·
[原始证据](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-batched-repair-2026-10-23)

| 实验 | 框架或候选 | 请求 / 工具 | 原生 Oracle | Agent 结局 |
| --- | --- | ---: | --- | --- |
| FMT-4286 | 批量修复候选 | 12 / 16 | 构建失败 | REJECTED |
| simdjson 首轮候选 | 批量修复候选 | 9 / 13 | 99/99，通过 | 模型连接中断 |
| FMT-4286 | 模板用法反馈候选 | 1 / 0 | 空补丁 | 模型连接中断 |
| simdjson 第二轮 | 批量修复候选 | 11 / 17 | 99/99，通过 | 模型连接中断 |
| simdjson 第二轮 | ReproPatch 原版 | 12 / 12 | 99/99，通过 | 终验阶段宿主中断 |
| simdjson 第二轮 | mini-SWE-agent | 7 / 7 | 97/99，目标回归失败 | Submitted |
| simdjson 第二轮 | Codex CLI 初次启动 | 0 / 0 | 空补丁 | 代理目录权限失败 |
| simdjson 第二轮 | Codex CLI 权限修正后独立复测 | 11 / 10 | 97/99，目标回归失败 | CLI 退出 0 |

批量候选核心 SHA-256 为
`3e137a39883ac87f35092b5497bfe86063bd179002c2b4b48e3beef15fd4a3ef`，
原版为 `6c13e9efed3f3c13206bf225c8aaed5413e438e27786af92f8adff98d63e7338`。
候选允许同一响应成组搜索、读取和编辑，工具依次执行、整批准入；修复中优先调用 F2P
检查，目标故障通过后执行完整检查，停止后保留独立终验。12 请求、24 工具、8192 输出 token、
256 KiB 输入边界和文件权限保持冻结。生产核心保持原版，候选继续接受跨仓库验证。

simdjson 和 FMT 的历史结果在选题时已知；该批衡量已知故障上的修复信号及重复表现。
第四仓库 nlohmann/json 的环境资格与后续模型实验另批记录。历史六题首次结果和
[五个诊断反馈候选](diagnostic-feedback-results.md)保持各自原始成绩。

第二轮原版已完成 12 次模型请求并保存候选，宿主中断发生在独立验收中。
SQLite 保留 `VERIFYING` 状态，候选直接交给公共 Oracle 重新评分，模型请求重放数为 0。
mini 和 Codex 使用该运行的首次领域输入，引用由 SQLite `model_started` 事件注册并核验 SHA-256。
两组有效 Agent 时间为 1586 秒，基线耗时为 203.364392 秒。

Codex 初次启动受宿主 `umask=0077` 影响，模型代理目录为 0700，上游请求数为 0。
适配器显式设置目录 0755 后，零请求传输预检通过，再以独立编号执行真实模型复测。
原始失败记录随证据保存。Codex 保留原生 CLI 0.163.0 和 SSE，mini 固定 2.4.6；
同题四组共享 Task、镜像、修改范围和 99 项原生 Oracle。

前两组、随后基线组按两槽运行；Codex 权限修正后单独执行。
部分 Oracle 与零模型环境资格检查同时运行，worker 和 Oracle 的耗时分别记录，计时受资源共享影响。
连接中断产生的候选同样由外部 Oracle 判定，四条非空 simdjson 候选逐一保留。

该批新增 **63** 次 CPA 请求，未知用量 **3** 次；已归档累计 **583** 次。
供应商账单费用未知，DeepSeek 历史费用上界为 **¥2.18923088 / ¥20**。

原始附件 `ReproPatch-batched-repair-2026-10-23.tar.gz` 为 14,234,226 字节，
含 7,431 个文件；SHA-256：
`fa5bda676e1165df360851d874fe26efad97ce364dfeed9441cee08aeec8da95`。
附件包含 Task、候选、账本、原始模型请求和响应、SQLite、Oracle、冻结源码及逐文件清单。
逐文件大小与哈希、凭据哨兵、独立解压重算均通过；解压后运行
`python3 summarize-batched-repair.py` 可重算结构化结果。
