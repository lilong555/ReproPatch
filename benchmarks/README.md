# ReproPatch 评测

评测分为公开缺陷修复与 Harness 可靠性两部分。契约测试数量不计入真实修复任务分母。
当前默认预算反馈策略的两题对照为 ReproPatch `1/2`、mini `0/2`，48 次请求，
费用上界 `¥0.50842656`，2187 通过官方 Oracle，见 [预算反馈报告](repair-cycle-results.md)。
后续搜索上下文实验为两组均 `0/2`，45 请求、费用上界 `¥0.61259216`，见 [导航报告](cpp-navigation-results.md)。
两批首次结果完整保留，当前总计 185 请求、费用上界 `¥2.18923088`，累计硬上限 ¥20。
[此前 rc3 批次](rc3-rerun.md) 为两组均 `0/2`，费用上界 `¥0.54663080`。
[历史 rc2 批次](pilot-results.md) 为 RP `0/2`、mini `1/2`，费用上界 `¥0.52158136`。
两个实例的 Task v2 参考验收及五个实例的官方参考复核见 [参考任务池](reference-pool.md)。
真实任务首次输入及原生历史边界见 [上下文记录](context-check.json)；
同镜像、非 root、无网络的原生 mini 环境见 [环境说明](mini-environment.md)。
运行准备状态见 [环境记录](environment.json)。Catch2-2723 的 prepared Task 参考修复已通过
2 个 F2P 与 67 个真实 CTest P2P。独立原始官方镜像的参考检查也已通过固定上游 Report，
2 个 F2P、100 个 P2P 均齐全，包含那 33 个配置探测项；原环境 CMake 仍不兼容 ReproPatch。
目前完成两个 prepared 实例的参考验收，适配覆盖率下界为 2/129，正式 Coverage 仍待完整筛查确认。
prepared Task 的回归测试在源码中可见，后续对照须向两组提供相同输入。

## ReproPatch-CppRepair

主任务池为 [ByteDance-Seed/Multi-SWE-bench](https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-bench)，
固定 revision `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d` 的全部 **129 个 C++ 实例**。
[逐实例筛查清单](coverage.json) 包含全部分母、来源文件哈希、参考补丁哈希与审查理由。
未兼容、未验证及未发起的任务不能冒充已尝试修复失败，也不能从 Coverage 分母删除。
参考补丁涉及文档只触发人工审查，不直接断言任务必须修改文档。
测试阶段 `NONE` 不能当作 `FAIL`；保留官方测试补丁及结果，不换成较容易的自建探针后声称原样适配。

| 组别 | 用途 | 当前默认候选对照 |
| --- | --- | --- |
| ReproPatch Full | 原生修复、持久化、独立验收 | 预算反馈候选两题各一次，1/2 |
| mini-SWE-agent | 同 DeepSeek 模型的开源能力对照 | 当前两题各一次，0/2 |
| ReproPatch Ablation | 同一候选的反事实验收决策 | 历史观察保留，当前不扩大消融 |
| Codex CLI | 自带模型的产品参考，单独呈现 | 暂停 |
| OpenHands / Claude Code | 后续扩展 | 暂停 |

每个开发批次固定 **Catch2-2723、Catch2-2187 × 一个 RP 候选、mini-SWE-agent 2.4.6 × 各一次**。
累计人民币20元内的模型实验已获持续授权，账本继承全部历史消费。
本轮不补满五题；20×2×3 正式实验、扩充数据集、额外 Agent 与通用 Harbor 暂停。
模型、工具与时间限制保持原冻结 Task：12 次请求、24 次工具、8192 输出 token、90 秒请求超时。

## 本轮启动预检

复用历史 `paid-pilot/catch2723-task.yaml` 与 `catch2187-task.yaml`，只重定位仓库、工作区及输出路径。
准备脚本默认 2048 输出 token / 45 秒是准备参数，不能直接作为本轮 8192 / 90 冻结配置运行。
不改写历史 Task 或历史费用账本；新批次使用独立目录，已有账本禁止删除或重新创建额度。

预留与结算的三类单价均来自 `scripts/benchmark_budget.py` 中的 POLICY。
本次 UTC 2026-10-22 已复核[供应商价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)：
高峰非缓存输入 ¥2、缓存输入 ¥0.04、输出 ¥8 / 百万 token。跨 UTC 日必须重新核价，不能只改日期。

```bash
BATCH="$PWD/.repropatch/rc3-rerun"
TASK_2723="$BATCH/catch2723-task.yaml"
TASK_2187="$BATCH/catch2187-task.yaml"
RECORD_2723="$BATCH/catch2723-record.json"
RECORD_2187="$BATCH/catch2187-record.json"
FIXED_EVALUATOR="$PWD/.repropatch/multiswe-evaluator"

python scripts/run_benchmark_agent.py --check-only \
  --agent repropatch --task "$TASK_2723" --ledger "$BATCH/budget.sqlite3" \
  --attempt rc3-catch2723-rp-1 --output "$BATCH/2723-rp"
```

预检只读 Task 和账本，不读取 API key、不构造模型、不预留费用、不创建 Run 或输出目录。
合法配置退出 0；Task 预算、核价日期、账本 POLICY 或 mini 输入不一致退出 2，并打印稳定本地错误码。
它不代替实际 Docker、基线与 Oracle 检查。
本机 T1 的两份固定 Task 已核对规范哈希与镜像；两套 mini 权限检查通过，
RP 启动预检均返回 0，费用账本字节保持一致。当前状态和来源身份见 [readiness.json](readiness.json)。
两次 mini 正式启动前的共同输入预检也均返回 0；本轮执行已结束，既有账本和尝试目录作为证据保留。

mini 增加 `--mini-source`、`--mini-environment`、`--common-input` 和实际对齐的 `--agent-seconds`。
共同输入必须来自本轮同题 RP 的 `agent/native/0001-input.json`，先按报告 `native_trace` 的大小和 SHA-256 核验。
RP 未保存首次输入时停止该 pair，不手工编造共同输入。mini 预检核对源码、镜像、Issue、
commit、允许文件、可读集合和预算与 Task 一致。权限环境由现有 `prepare_mini_environment.py --check-scripted` 检查。
本轮每题仍先 RP、后 mini，保留原生系统提示、工具接口、容器生命周期与时间口径差异。

## 运行与计分

两组统一 DeepSeek `deepseek-flash`、供应商端点、Issue 描述、base commit、官方测试、
固定镜像 digest、资源、时间和模型预算。正式实验计划交替运行顺序；
本批次两题实际均先 ReproPatch、后 mini，差异已披露。
供应商响应中的模型标识、默认思考模式、请求参数、缓存命中和未知用量均保留。
预算、完整提示、框架源码身份、工具权限及必要适配差异在第一次收费请求之前固定。
系统提示和工具协议保留框架原生实现；工具调用次数只作开销指标，不作为跨框架等价步数。
DeepSeek 官方模型版本及价格依据见 [供应商文档](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)。

**主分数由所有组共用的官方外部 Oracle 决定**；ReproPatch 的 ACCEPTED 是附加指标，不能代替 Oracle。
不把 Agent 自述、退出码 0、仅原工作区通过或测试输出中的成功文字直接当作修复成功。
Agent 不可读取参考补丁、官方解答、测试补丁或后续 Git 历史；正式运行前必须检查官方镜像与适配器是否残留这些材料。
依赖和构建环境在准备阶段固定，修复阶段的网络权限及验证权限在各组保持一致并披露。

## ReproPatch-Reliability

验收消融复用完全相同的候选补丁，分别计算“Agent 声称成功”“原工作区测试通过”
与“ReproPatch 独立验收”的决策，再与独立 Oracle 对照。
原日志缺少明确观察时记为未知，不推断 Agent 自称成功或原工作区通过。
反事实计算不关闭实际运行的安全机制，不额外调用模型，也不伪装成独立随机试验。

错误补丁、skip、伪造通过输出及证据篡改等负例分别标注补丁语义与证据完整性，分层统计错误接受。
不能把证据受损但补丁语义未知的样本混入“语义错误补丁”的分母。
Checkpoint / Resume 先复用 [现有 13 个故障场景](../docs/evidence/p2-04/recovery-gate/summary.json)：
3 个安全边界保留候选并验收成功、9 个明确拒绝恢复、1 个原控制器持锁拒绝接管。
开放片段不重复请求或执行工具，原始 deadline 与累计预算保留。
这些是确定性故障向量，不是大样本恢复概率；当前没有独立运行的无持久化框架对照，不能声称已经胜出。

## 指标及分母

| 指标 | 定义 |
| --- | --- |
| Resolved@1 | 第一次已发起尝试经官方 Oracle 通过数 / 第一次已发起尝试数；另列服务故障 |
| Benchmark Coverage | 通过完整基线与参考补丁适配验收的实例 / 固定数据集全部 129 个实例 |
| False Acceptance Rate | Oracle 判无效但策略接受数 / Oracle 判无效数；另列错误接受数 / 全部接受数 |
| Recovery Success Rate | 预先标为可恢复的中断最终成功数 / 可恢复中断数；不可恢复场景单列正确拒绝率 |
| Cost per Resolved Task | 所有已发起尝试的模型费用 / Oracle 成功数；成功数为零或费用不全时为未知 |
| Wall-clock Time | 端到端耗时，拆出 Agent、环境准备、独立验收及外部 Oracle 开销 |

重复运行按实例和重复编号呈现，报告均值与离散程度，不把每次重试改名为新的题目。
首轮 5 题不作显著性或整体领先结论。未知 token、成本和未运行任务保留未知。

## Harbor 接入边界

使用 [Harbor 官方 Multi-SWE-bench adapter](https://github.com/harbor-framework/harbor/tree/main/adapters/multi-swe-bench)
准备任务和官方 verifier，复用 Harbor 运行、收集和原生 mini-SWE-agent / Codex 集成，不开发第二套调度器。
固定 Harbor commit `6c9d3d6609854375005a7b5c8f1906371d64c6ff`；该 adapter 的上游 evaluator 固定为
`4b96a678b136f87c8760fa475697f3c98d5f9e5e`，与数据 revision 分开记录。
当前检索用上游仓库为 `24f493f8a103e72312ded4f6b9c89f081d69cb09`，不能把它冒充实际 evaluator 版本。
ReproPatch 只提供窄 Agent / 产物桥接，保留原生 Run 与 patch/trace，再让 Harbor 官方 Oracle 独立评分。
配置生成、只读源码检查及参考补丁通过都不等于适配器端到端集成完成。
现有 [无模型 fixture pilot](harbor-pilot.md) 已通过原生作业、显式产物收集和现有 `verify-patch`，
仍未提供通用 `export-harbor` / `verify-harbor` 命令。
两题真实框架对照通过原生单 Agent 入口与公共 Oracle 串联，不代表 Harbor 调度已经集成。
Codex 非交互接口依据 [OpenAI Docs](https://learn.chatgpt.com/docs/non-interactive-mode)，
使用 `codex exec --json` 收集轨迹；不同模型参考组不纳入同模型排名。

## 本地适配 smoke

[smoke-suite.json](smoke-suite.json) 固定 fmt、pugixml、tinyxml2 的 5 个上游缺陷，
只用于环境与适配器检查，不属于 Multi-SWE-bench，不能计入其 Coverage 或 Resolved@1。
`scripts/prepare_smoke_suite.py` 将缺陷基线与公开探针置于无修复历史的新仓库，参考补丁置于仓库外。
5 个参考补丁均已由实际 Docker 独立验收通过；未发起收费模型请求。

```bash
python scripts/screen_multiswe.py --dataset .repropatch/datasets/multi-swe-bench
python scripts/prepare_smoke_suite.py
```

完整原始材料保存在带 SHA-256 的 Release Assets；Git 只保留摘要、配置与 Source Manifest。
