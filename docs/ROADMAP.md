# ReproPatch 工程路线

ReproPatch 0.4.0 定位为**可恢复的 C++ 修复与验证系统**，技术主线是 C++ Repair & Verification Harness，可选内置 Agent 生产补丁。工程围绕任务冻结、执行资源、候选身份、独立验收、状态恢复和证据交付组织；实验使用冻结协议为设计与优化提供后台验证。

## 0.4.0 交付能力

| 能力 | 当前合同 | 实现与验收入口 |
| --- | --- | --- |
| 任务与源码 | Task v2 固定 commit、镜像、文件权限、测试身份和预算；完整源码与补丁往返 | [Task](../src/repropatch/task.py)、[源码完整性测试](../tests/test_source_integrity.py) |
| 独立验收 | core-only `verify-patch`，基线复现、全新工作树、冷构建、逐项 F2P/P2P | [验证器](../src/repropatch/verification.py)、[工程验收](ACCEPTANCE.md) |
| 可选 Agent | 公开 SDK Runner、legacy 六工具、shell-only 持久 Bash；语法结构查询使用可选 extra | [运行时](../src/repropatch/agent_runtime.py)、[结构证据状态](SEMANTIC_STATE.md) |
| 执行控制 | Docker 固定 profile、资源限额、命令间静止检查和所属资源删除确认 | [沙箱](../src/repropatch/sandbox.py)、[持久修复容器](../src/repropatch/repair_sandbox.py) |
| 有限恢复 | SQLite 事务与完整输入 Checkpoint，同 Run、原期限和累计预算 | [恢复实现](../src/repropatch/recovery.py)、[恢复测试](../tests/test_resume.py) |
| 诊断与轨迹 | 只读 inspect/diagnose/replay；Run 外 trace 导出；派生报告重建 | [诊断](../src/repropatch/diagnostics.py)、[轨迹测试](../tests/test_trace.py) |
| 安装与演示 | wheel 内置资源；零密钥成功、拒绝、恢复三场景；core-only 外部补丁正反例 | [演示指南](DEMO.md)、[安装包门禁](../scripts/check_engineering_gate.py) |
| 持续集成 | 日常 Core/Ruff、离线 SDK、真实 Docker 与 wheel 三条工程作业 | [CI](../.github/workflows/ci.yml)、[测试报告](TEST_REPORT.md) |
| 长期证据 | 版本摘要、被测源码、包 SHA、镜像、JUnit 与原始 Run 的固定身份 | [0.4.0 摘要](evidence/v0.4.0/summary.json)、[Release](https://github.com/lilong555/ReproPatch/releases/tag/v0.4.0) |

历史 mini/Codex 原生上下文检查通过 `workflow_dispatch` 的 `native_context=true` 手动启用。工程证据长期保存于 Release 的 `ReproPatch-engineering-v0.4.0.zip` 与 `SHA256SUMS`，日常 CI Artifact 使用短期保留。

## 优化依据

每项优化从原始运行证据定位问题，在相同任务、镜像与计量口径下保留基线。结果同时核对独立验收、分阶段耗时、模型请求与用量、未知值及资源清理。

| 已有机制 | 工程作用 | 测量与核验 |
| --- | --- | --- |
| 持久 /build 与 Run 内 ccache | 降低修复阶段重复配置、编译和启动成本 | 自检耗时与缓存统计；独立验收保持冷构建 |
| 语法检索与证据索引 | 缩小源码定位范围，按需读取既有观察 | 源码 SHA、分页与截断、输入大小和检索用量 |
| 完整轮次压缩与稳定状态 | 控制长期历史增长并保持工具关联 | 压缩前后原生输入、恢复计数与未知用量 |
| F2P 优先自检 | 在剩余预算内获得目标失败反馈 | 自检 F2P/P2P、执行次数、耗时和最终验收 |
| 整批准入与验证预留 | 约束工具批次，为验收及清理保留时间 | 累计准入数、最后允许 turn、原 deadline |

## 发布后 P1

| 工作 | 完成标准 |
| --- | --- |
| 真实 fmt-4055 recipe | 固定 Task、参考补丁与 provenance；使用当前 wheel 重验正确与错误补丁，保存冷验收原件 |
| 工具参数组合校验 | 在创建 Run 前校验 shell-only 与 semantic-state 组合，明确工具合同并覆盖回归 |
| 上下文策略解耦 | 单独配置压缩策略，推广大基线观察分离；保持工具关联、累计计数与恢复一致性 |

## 发布后 P2

以下选项根据实际使用需求和 profile 立项，验收同时覆盖性能收益与工程合同。

| 可选工作 | 完成标准 |
| --- | --- |
| 目标级增量验证 | 记录 CMake target 与可见测试的选择依据、覆盖范围和分阶段耗时，最终独立验收完整执行 |
| 编译诊断结构化 | GCC/Clang 位置、类别和摘要关联完整日志，覆盖多行错误与输出截断 |
| 跨 Run 运维汇总 | 按任务、实现和镜像身份聚合失败原因、延迟与用量，保留未知值及原始证据链接 |
| 长期归档复核 | 从原件重算候选身份、摘要和用量，再执行已声明的冷验收 |
| 扩展任务合同 | 按需求分别设计基线编译错误、crash、文件增删重命名和远程多租户执行的隔离与验收 |
| 通用 Runtime 或 C++ 执行器 | 以明确应用需求与控制面 profile 形成独立设计，给出维护范围和验证结果 |

## 后台实验与历史索引

模型对照冻结任务、模型、预算、执行源码和镜像身份。首跑、恢复、复评分与基础设施故障分别保存，失败记录保持原始身份。确定性工程演示与离线 SDK 门禁的付费模型请求为零。

实验入口：[评测索引](../benchmarks/README.md)、[跨仓库资格](BENCHMARK_QUALIFICATION.md)、[统一上下文对照](../benchmarks/unified-context/final-results.md)、[云端实验](ACTIONS_RESULTS.md)。历史规格见[产品合同](../SPEC.md#历史规格)，历史测试与发布事实按[测试报告](TEST_REPORT.md)中的版本和源码复查。
