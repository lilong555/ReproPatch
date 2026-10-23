# nlohmann/json-4525 四组修复对照

同一固定任务、gpt-6-luna 端点、领域输入和 98 项公共 Oracle 下，ReproPatch Full、mini-SWE-agent 与 Codex 均完成真实修复；批量相关模板候选编译失败。候选在这项新缺陷上没有增量收益，生产默认保留 ReproPatch Full。

[逐组结构化结果](json4525-results.json) · [完整原始证据](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-json4525-results-2026-10-23) · [任务资格](json4525-qualification.md)

| 组别 | 请求 / 工具 | 生产者状态 | 公共 Oracle |
| --- | ---: | --- | --- |
| ReproPatch Full | 10 / 9 | ACCEPTED | 98/98，通过 |
| mini-SWE-agent 2.4.6 | 7 / 5 | Submitted | 98/98，通过 |
| 相关模板反馈候选 | 12 / 12 | CANDIDATE_BUILD_FAILED | 0/98，通过 |
| Codex CLI 0.163.0 | 12 / 12 | 达到请求上限，保留候选 | 98/98，通过 |

缺陷涉及 JSON 存储为无符号整数时，整数引用访问错误地读取有符号联合体成员。Full 与 mini 都将守卫改为 `m_data.m_type == value_t::number_integer`；候选尝试使用不存在的 `m_type`，导致公共构建失败。Codex 在请求上限时导出的补丁通过公共 Oracle。

四组各运行一次，单槽顺序为 Full、mini、候选、Codex。mini 与 Codex 使用 Full 首次模型输入，SHA-256 为 `15e5983d63e3b56ba50e9a3ae55bf26fc6cff32691bfcfcda142987b4eb599ef`。所有组使用相同 base、Task、镜像、修改范围、2 CPU、4 GiB 内存、3 GiB 构建临时空间及公共 Oracle；每组最多 12 请求、24 工具、每响应 8 工具、8192 输出 token 和 256 KiB 输入。各框架保留原生提示与工具协议。

批次共 41 次模型请求，usage 全部已知：685,922 输入 token、4,047 输出 token，其中缓存输入 556,288 token。CPA 实际账单费用未知。模型运行之外的预检目录冲突与容器源码污染均记录为零请求启动事件，不进入修复分数。

Full 的 worker 时间包含固定基线与内部独立验收；mini 与 Codex worker 阶段不同，运行时间按组保留，不做速度排名。该矩阵每组一次，结果用于候选采用判断，不支持显著性推断。
