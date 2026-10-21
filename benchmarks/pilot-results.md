# C++ 修复对照：首轮两题结果

本页记录五题试跑中已完成的 **两个真实 Catch2 缺陷，每框架每题第一次尝试**。
修复成绩由固定 Multi-SWE-bench 官方评测代码及原始官方镜像判定。
ReproPatch 使用 `0.3.0rc2`，mini-SWE-agent 使用 `2.4.6`；两组请求同一 DeepSeek
`deepseek-flash` 别名。详细用量、候选身份和原始文件索引见
[JSON](pilot-results.json) 与 [CSV](pilot-results.csv)。

## 成绩与费用

| 框架 | Catch2-2723 | Catch2-2187 | Resolved@1 | 模型请求 | 费用上界（人民币） |
| --- | --- | --- | --- | --- | --- |
| ReproPatch Full | 未修复 | 无补丁 | 0/2（0%） | 21 | ¥0.24813216 |
| mini-SWE-agent | 无补丁 | 已修复 | 1/2（50%） | 24 | ¥0.27344920 |

合计 **45 次真实模型请求，费用上界 ¥0.52158136，未知用量 0 次**，共用 ¥20 总额度。
费用按本批次冻结的供应商高峰价和原始缓存用量计算，实际账单扣费未知。
mini 每个成功任务的费用上界为 ¥0.27344920；ReproPatch 尚无成功任务，此指标为空。
这里只有两题、一次运行且同属一个项目，不能据此作整体能力领先或显著性结论。
首轮剩余三题尚未完成，正式二十题、多次运行和 Codex 产品参考组均无成绩。

mini 在 2187 上耗尽十二步后退出，但已产生有效补丁，因此计为成功。
其候选在原工作区完整 34 个 CTest、外部官方 Oracle 的 2 个 F2P 与 50 个 P2P，
以及额外 ReproPatch 独立验收中均通过。退出状态不覆盖独立测试的修复判定。

ReproPatch 在 2723 上生成了补丁，但外部 Oracle 仍观察到两个目标 F2P 失败，
100 个 P2P 均通过。其自检工具返回的单条 JSON 为 385,200 字节，超过 256 KiB
模型输入边界，随后以 `CONTEXT_LIMIT` 停止。这个反馈体积问题不等于候选已经正确。
ReproPatch 的 2187 与 mini 的 2723 未产出补丁，均记为 `NO_PATCH`，不伪造原生测试执行。

## 协议与公平性

| 项目 | 本批次实际执行 |
| --- | --- |
| 数据 | Multi-SWE-bench revision `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d`；C++ 全池 129 条 |
| ReproPatch 源码 | `0.3.0rc2`，实现 SHA-256 `31ac9b699870b99e0b6eceab24513590f0a3df868a24ee027dc8aab267496ddd` |
| mini 源码 | `04d809ceab9df28f9adaed044884180159172930`，使用原生 DefaultAgent、LiteLLM Responses 和 DockerEnvironment |
| 官方评测源码 | `4b96a678b136f87c8760fa475697f3c98d5f9e5e` |
| 生成环境 | 每题相同 prepared commit、固定镜像、2 CPU、2 GiB、非 root、无网络、相同可编辑 C++ 文件 |
| 模型 | 相同端点与 `deepseek-flash`；冻结文档映射 `DeepSeek-V4.1-Flash-1017`，供应商未提供权重构建哈希 |
| 输入 | 每题初始领域 JSON 逐字相同，包含相同 Issue、允许文件、基线观察和构建说明 |
| 请求预算 | 每次尝试最多 12 个 HTTP 模型请求、输出上限 8192 token、单请求 90 秒 |
| 工具预算 | 最多 24 个工具、每响应最多 8 个；框架原生工具协议不同，次数不能视为等价工作量 |
| 上下文 | 256 KiB 输入边界，不裁剪原生历史；模型参数 temperature、top_p、reasoning 均未显式设置 |
| Agent 时间 | RP 阶段上限 900 秒；mini 扣除同题 RP 基线准备时间并预留 10 秒后为 812 / 845 秒 |
| 外部 Oracle | 新建原始官方镜像容器、固定原始测试脚本和官方 Report；全部固定测试组均须通过 |
| 原生脚本执行 | 候选统一以 `bash -e` 启动，避免编译失败后继续使用镜像内旧二进制 |

已检查两题首个实际 HTTP 请求中的模型、输出上限及采样/思考字段，结果相同。
原生系统提示和消息封装各自保留；mini 的提示另明确同一只读目录和原位写入规则。
RP 的 Shell 使用一次性容器，编辑通过专用工具；mini 在持久容器内直接写入允许文件。
mini 可通过 Bash 读 prepared 源码，RP 结构化文件工具受 readable 集合过滤。
这些框架差异保留在报告中，不声明工具接口完全相同。

两题均先执行 RP、后执行 mini，未实现正式计划中的交替顺序。
2723 的 mini 曾遇到 Git ownership 限制并自行修正；2187 在启动前预设 `safe.directory=/src`。
首次执行记录保留，不通过重跑删除这些观察。2723 的公共 Oracle 两次权限接线失败，
另有一次空补丁路径异常，均单列为验证基础设施调试；复核的是同一候选，没有新增模型生成。

## 耗时

| 任务 | RP worker 秒 | mini worker 秒 | RP 外部 Oracle 秒 | mini 外部 Oracle 秒 |
| --- | --- | --- | --- | --- |
| 2723 | 322.455 | 34.165 | 75.859 | 未执行：无补丁 |
| 2187 | 87.061 | 74.893 | 未执行：无补丁 | 39.268 |

RP worker 包含基线准备、自检、候选导出和独立验收；mini worker 包含原生生成及工作区自检，
不含外部 Oracle 或额外 RP 验收。以上时间范围不同，不能直接用于速度排名。
2187 的 mini 候选额外 RP 独立复验耗时 81.017 秒，无模型请求。

## 同候选验收观察

两个非空真实候选分别经公共 Oracle 判为无效和有效，RP 独立验收分别拒绝和接受。
在这一子集上，错误接受为 **0/1 个无效候选**；所接受的 1 个候选没有外部 Oracle 失败。
这不是完整负例集，不能当作稳定的 False Acceptance Rate 估计。
空补丁不混入已执行独立验收的分母。

mini 的 2187 有明确的原工作区全测试通过记录；其余候选没有完整可比观察，保持未知。
本批次没有可比较的 Agent 最终成功声明，因此不计算自述策略错误接受率。
Checkpoint / Resume 的本批次恢复对照尚未执行，不用历史契约测试代替本批次指标。

## Coverage 与适配边界

已完整验收的 prepared Task 为 2/129，覆盖率下界 **1.55%**；原样兼容覆盖确认数仍为 0。
这两个任务使用固定的 CMake/CTest 及只读工作区适配，不能称为原数据原样运行。
2187 的批准快照不变，临时输出移至 `/build`。
其余实例及排除原因仍保留在 [全池筛查](coverage.json) 和 [参考任务池](reference-pool.md)，
不是已尝试修复的失败题；五个参考补丁通过也不等于五个 Agent 修复成功。

## 复核材料

完整原始 HTTP 请求体/响应体、费用 SQLite、原生轨迹、补丁、Task、Oracle 原始日志及
源码快照放在 [本批次发布附件](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-pilot-first-two-2026-10-21)。
逐文件路径、大小和 SHA-256 见 [Source Manifest](pilot-source-manifest.json)；解压后可核对
`evidence-manifest.json`。HTTP 凭据和请求头不入证据。

`scripts/run_benchmark_agent.py` 只启动单个原生 Agent 并导出补丁，
`scripts/check_multiswe_reference.py --task TASK` 对模型候选执行同一外部 Oracle。
`scripts/benchmark_budget.py` 在每次 HTTP 请求前共用一个人民币账本，未知用量保留完整预留。
计价日期过期时拒绝新请求，须复核供应商价格，不能删除旧账本来恢复额度。
本批次尚未由 Harbor 通用调度，不把这些窄入口称为完整 Harbor 集成。
