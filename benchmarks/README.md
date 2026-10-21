# ReproPatch 评测

评测分为公开缺陷修复与 Harness 可靠性两部分。契约测试数量不计入真实修复任务分母。
当前公开数据只完成静态兼容性筛查，尚无正式模型对照成绩。

## ReproPatch-CppRepair

主任务池为 [ByteDance-Seed/Multi-SWE-bench](https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-bench)，
固定 revision `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d` 的全部 **129 个 C++ 实例**。
[逐实例筛查清单](coverage.json) 包含全部分母、来源文件哈希、参考补丁哈希与审查理由。
未兼容、未验证及未发起的任务不能冒充已尝试修复失败，也不能从 Coverage 分母删除。
参考补丁涉及文档只触发人工审查，不直接断言任务必须修改文档。
测试阶段 `NONE` 不能当作 `FAIL`；保留官方测试补丁及结果，不换成较容易的自建探针后声称原样适配。

| 组别 | 用途 | 首轮状态 |
| --- | --- | --- |
| ReproPatch Full | 原生修复、持久化、独立验收 | 必选，等待兼容实例运行确认 |
| mini-SWE-agent | 同 DeepSeek 模型的开源能力对照 | 必选，等待适配 |
| ReproPatch Ablation | 同一候选的反事实验收决策 | 必选，不新增收费模型尝试 |
| Codex CLI | 自带模型的产品参考，单独呈现 | 待环境、模型与独立预算明确 |
| OpenHands / Claude Code | 后续扩展 | 首轮不接入 |

先使用 **5 个经基线和参考补丁实测的公开实例**、每框架每题 1 次完成试跑，
当前模型预算 **人民币 20 元合计**，仅用于 DeepSeek 两组。
正式计划为 **20 个兼容实例 × 2 个框架 × 3 次 = 120 次**，待 Coverage 和试跑结果明确后固定任务并另定预算。
兼容实例不足时报告不足及原因，不用另一个任务池补足后仍沿用原数据集名称。

两组统一 DeepSeek `deepseek-flash`、供应商端点、Issue 描述、base commit、官方测试、
固定镜像 digest、资源、时间和模型预算，交替运行顺序。
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
