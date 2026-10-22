# rc3 两题真实同模型对照

2026-10-22，Catch2-2723、Catch2-2187，ReproPatch **0.3.0rc3** 与
mini-SWE-agent **2.4.6** 各执行一次。两组使用官方 DeepSeek `deepseek-flash`，
固定相同任务、镜像与初始领域输入。逐条证据和可重算指标见 [JSON](rc3-rerun.json)。

| 实例 | 框架 | 请求 / 工具调用 | Agent 停止原因 | 候选 / Oracle | 费用上界（元） |
| --- | --- | --- | --- | --- | --- |
| Catch2-2723 | ReproPatch | 12 / 23 | STEP_BUDGET | NO_PATCH | 0.10978904 |
| Catch2-2723 | mini | 11 / 24 | TOOL_BUDGET | NO_PATCH | 0.13690896 |
| Catch2-2187 | ReproPatch | 12 / 24 | TOOL_BUDGET | NO_PATCH | 0.14648984 |
| Catch2-2187 | mini | 12 / 24 | LimitsExceeded | NO_PATCH | 0.15344296 |

本轮 Resolved@1：**ReproPatch 0/2，mini 0/2**。合计 **47 次模型 HTTP 请求，
费用上界 ¥0.54663080，未知用量 0 次**，在已授权的四次尝试、48 请求和 ¥20 总上限内完成。
费用按冻结高峰价格及供应商返回的缓存用量计算，实际账单扣费未知。
成功任务数为零，两组每成功任务费用留空。

四条记录的候选均为空，Oracle 入口统一记录 `NO_PATCH`，原生测试执行数为零。
本批次的候选验收样本数为零，错误接受率留空。两组所属容器删除均已确认。

## 执行观察

ReproPatch 在 2723 上执行了 14 次读取和 9 次搜索；2187 上执行了 13 次读取、10 次搜索和
1 次容器 Shell。两次都在代码定位阶段耗尽额度，编辑工具调用为零。
mini 的两条轨迹同样持续读取和搜索；2723 另执行了构建及局部测试命令，最终仍没有修改文件。
原生停止状态与补丁判定分别保存在结果中。

RP 最大完整原生输入分别为 **138,261 / 144,363 字节**，本轮没有出现上下文超限。
两次都未进入编辑后的自检，因此 rc3 的大规模自检反馈仍以历史轨迹的离线检查为依据，
见 [反馈上下文](feedback-context.md)。这轮直接观察到的修复瓶颈是定位阶段的步骤与工具额度。

| 实例 | RP 基线秒 | RP 修复阶段秒 | RP worker 总秒 | mini worker 秒 |
| --- | --- | --- | --- | --- |
| 2723 | 74.172 | 36.039 | 112.791 | 69.426 |
| 2187 | 37.034 | 54.062 | 93.142 | 43.670 |

RP 修复阶段按 SQLite 的 REPAIRING 状态区间计时，包含阶段末清理；worker 总时间包含准备及基线。
mini worker 包含容器准备、原生生成、工作区命令与清理，公共 Oracle 单列。
两种 worker 时间覆盖范围不同，本表用于观察开销组成。

## 固定条件与公平性

| 项目 | 本轮条件 |
| --- | --- |
| 执行源码 | `77da9ccb25c059a5af3d5148479881fe5a303120` |
| RP 核心实现 SHA-256 | `2715236f2161b39e6eb6b117b4d6926720a9df21dfb0d158f501712124ebbf20` |
| mini 源码 | `04d809ceab9df28f9adaed044884180159172930`，原生 DefaultAgent / DockerEnvironment / LiteLLM Responses |
| 数据集 | Multi-SWE-bench revision `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d` |
| Oracle 源码 | `4b96a678b136f87c8760fa475697f3c98d5f9e5e`，同一官方入口及固定原始镜像 |
| 生成环境 | 每题相同 prepared commit、镜像、2 CPU、2 GiB、非 root、无网络及可编辑文件集合 |
| 请求额度 | 每次最多 12 个 HTTP 请求；8192 输出 token；90 秒请求超时 |
| 工具额度 | 每次最多 24 个工具，每响应最多 8 个 |
| 输入边界 | 256 KiB，保留原生历史 |
| 时间额度 | RP 阶段 900 秒；mini 扣除基线并预留 10 秒后为 815 / 852 秒 |
| 顺序 | 每题先 RP、后 mini，各一次 |

每题 mini 的初始领域 JSON 来自同次 RP 报告注册的首次输入，大小和 SHA-256 已核验。
两组首个实际 HTTP 请求中的模型、输出上限及采样/思考字段逐项相同；未显式设置 temperature、
top_p 或 reasoning，响应记录模型标识均为 `deepseek-flash`。
核价文档映射为 `DeepSeek-V4.1-Flash-1017`，供应商模型列表显示 `DeepSeek-V4.1-Flash`。
供应商未返回权重构建哈希，别名对应关系按本批次冻结记录保存。

两组保留原生系统提示和工具接口。RP 经专用编辑工具持久化源码，Shell 使用一次性只读源码容器；
mini 在持续容器中原位修改允许文件，读取 prepared 源码。工具调用数用于记录开销。
两套 mini 环境均预设 `safe.directory=/src`，源码 Git 仅含单条基线提交。

## 历史与覆盖范围

| 独立批次 | ReproPatch | mini | 请求数 | 费用上界 |
| --- | --- | --- | --- | --- |
| [rc2 首次对照](pilot-results.md) | 0/2 | 1/2 | 45 | ¥0.52158136 |
| 本轮 rc3 | 0/2 | 0/2 | 47 | ¥0.54663080 |

两批分别保留首次结果。样本为同一项目的两题、每组各一次，报告呈现这些固定尝试的实际结局。
不同日期的模型别名、默认策略与生成轨迹均可能影响表现；这里保留批次差异，后续研究可据此设计重复实验。
已验证适配为 **2/129（1.55%）**，完整兼容性筛查待完成，其余实例状态见
[全池清单](coverage.json) 与 [参考任务池](reference-pool.md)。本阶段四次尝试及展示交付完成。

## 下载与复核

[原始证据与 SHA-256](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-rc3-rerun-2026-10-22)
包含两份 Task、原始记录、HTTP 请求体/响应体、SQLite 账本、原生轨迹、空候选、Oracle 决策、
执行源码及逐文件哈希清单。凭据与请求头均未写入证据。
源码身份另见 [Source Manifest](rc3-rerun-source-manifest.json)。

```bash
sha256sum -c ReproPatch-rc3-rerun-2026-10-22.tar.gz.sha256
tar -xzf ReproPatch-rc3-rerun-2026-10-22.tar.gz
python3 rc3-rerun/summarize.py
```

汇总脚本只读原始账本、轨迹与 Oracle 决策，核验引用后写出 `rc3-rerun/rc3-rerun.json`。
运行准备与预算规则见 [Benchmark 入口](README.md)，免费独立补丁演示见 [项目首页](../README.md)。
