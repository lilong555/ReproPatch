# 规格交付审查记录

审查日期：2026-10-19。对应规格修订：2026-10-19.1。**此记录核查文档契约，不是产品功能测试报告。** 本轮到 Phase 0 完成为止；没有改动既有产品源码，没有运行 Docker、付费模型或旧 pytest。

## 1. 交付与来源

交付包含 SPEC.md、13 份 docs 文档和一个 Task v2 YAML，共 15 个源文件；完整压缩包另附。本规格基于实际找到的既有实现，HEAD、未提交修改和历史测试证据列于 [CURRENT_STATE](CURRENT_STATE.md)。本轮再次查看旧仓库 Git status，仍为原有三个修改文件；没有把旧源码复制进规格包。

官方资料只用于影响实现取舍的决策，链接、来源范围和结论在 [DECISIONS](DECISIONS.md)。没有宣称 ReproPatch 已超过任何现成 Harness，没有编造真实修复率、性能提升或发布记录。

## 2. 完整性核查

| 用户要求 | 权威文档与已提供内容 |
|---|---|
| 产品、需求和验收 | REQUIREMENTS：FR-001–FR-030、NFR-001–NFR-017，关联模块、任务和验收 |
| 架构、数据与时序 | ARCHITECTURE：依赖方向、持久化边界、Mermaid 总体图与时序；STATE 的状态图 |
| Task 与配置 | TASK_FORMAT 和 task.example.yaml：完整字段、默认值、严格输入边界、v1→v2迁移、冻结 hash |
| Agent Runtime | AGENT_RUNTIME：Model／Mock、工具 schema、消息组、预算、上下文、明确停止原因 |
| 隔离与工具执行 | EXECUTION_AND_SECURITY：Worktree、只读快照、Docker 生命周期、资源、进程清理与权限 |
| 复现与独立验收 | VERIFICATION：F2P/P2P、CTest 身份、源码／patch 往返、判定矩阵、准确报告字段 |
| 状态、恢复和重放 | STATE_AND_RECOVERY：事件、四表 SQL、操作身份、Checkpoint、未知副作用、恢复终态、两类 replay |
| CLI 与产物 | CLI：命令所属阶段、参数、退出码、目录、典型目标工作流 |
| 测试、评测与CI | TESTING_AND_EVALUATION：T01–T12行为义务、对照、分母、成本、实际 Docker gate、发布条件 |
| 全生命周期实施 | IMPLEMENTATION_PLAN：Phase 0–4，每阶段范围／依赖／风险／交付物，23项任务及9个必需字段 |
| 技术决策与规模控制 | DECISIONS：11项长期决策、官方框架复用与自研边界 |

## 3. 实际检查方法与结果

在规格目录上执行静态检查：130 个 Markdown 本地链接与章节锚点存在；32 个代码围栏块检查通过且围栏成对；JSON／JSONL／YAML 示例可解析；Python 接口片段可做语法解析；Phase 2 SQL 在内存 SQLite 中可执行。完整 task.example.yaml 的顶层字段、固定 OID、占位镜像格式、CTest 模板、F2P/P2P 不相交和预算约束符合 TASK_FORMAT。

开发任务映射检查确认 23 个唯一 Task ID，跨文档引用均有定义；每项包含 Task ID、所属 Phase、目标、前置依赖、涉及文件或模块、具体工作、验收标准、需要运行的测试、预计复杂度。需求编号完整且无跳号。所有权威数据名称与 Phase 边界经过交叉阅读；未解决的关键文档矛盾为零。

SQL 除语法外核对了一个实际约束场景：CREATED 可以保存尚未冻结的输入；缺少冻结字段进入 REPRODUCING 会被约束拒绝；补齐字段后允许进入。这是规格内 SQL 的契约检查，不是实现已有恢复能力的证据。Mermaid 图做结构与术语人工检查，没有声称运行了产品 UI 或完整图形渲染测试。

## 4. 审查中已直接修复的问题

| 问题 | 收敛后的规则 |
|---|---|
| 最后一次模型响应中的工具被 step 预算误跳过 | max_steps 只禁止新模型请求；已有调用仅检查 tool/time 余额 |
| 最终回复恢复后可能再次请求模型 | 可见回复、停止原因和 next_action 同事务保存，恢复直接冻结候选 |
| 完整工具组落盘但 Checkpoint 未提交 | 核对全树 post 状态后补交 Checkpoint，不重做或重复扣预算 |
| 未完成组回退后可能丢失修改仍去验收 | 预算不足直接 RECOVERY_FAILED，保留观察候选，不验收丢失修改的回退树 |
| 线程取消不能限制真实模型总耗时 | 单个可终止请求子进程＋本地硬计时器，无隐式重试或 worker 池 |
| 文件 hash 与源码树摘要含义混淆 | EvidenceRef 哈希对应产物 bytes；source_tree_sha256 对应规范 SourceManifest |
| 报告字段、JUnit 引用和清理状态不完整 | 固定 report.json v1／EvaluationEvidence，引用统一，使用 evaluation 最终清理证据 |
| 恰好达到输出上限存在两种判定 | stdout+stderr 观察字节数达到 4 MiB 即 output_limit，证据不完整 |
| Baseline 无最终报告的中断样本可能消失 | attempts 在启动前持久化，从清单＋DB＋证据重算，保留已启动分母 |
| 真实任务需求映射到 Fixture 任务 | FR-027 对应 P3-01R；Fixture 与真实实例分别验收 |
| range-sum P2P 可能也触发同一缺陷 | 固定缺陷分支和非零输入，逐项明确原始／正确输出 |
| 最终事实已提交但报告导出失败 | 运行 outcome 保持，CLI 用 ARTIFACT_EXPORT_FAILED 退出3，inspect显示报告不完整 |
| 状态、路径与术语漂移 | BASELINE_CONFIRMED、exported_through_seq、EvidenceRef、reason_code 和产物目录统一 |

这些修正用于减少实现歧义，没有加入插件系统、分布式调度、通用快照服务或多提供商兼容层。

## 5. 尚待实施的真实门槛

- 既有三项未提交修改的运行验证仍未完成；历史非 Docker 测试不能替代当前代码验证。
- Docker 的权限、子进程清理、只读快照和正常修复主链必须在真实 Linux Docker 环境验收。
- 示例镜像 SHA 明确是占位；实施时须由 init 脚本填写实际镜像身份和可用源码位置。
- CTest JUnit 的真实镜像样本、SDK 单请求总 deadline、Task v2及独立P2P验证都须通过各自实现任务。
- 真实模型端点／模型由实施时操作者指定并授权。MVP要求兼容性 smoke；公开稳定版本还要求可核查的真实模型修复案例，不承诺修复率。
- Checkpoint／Resume／Execution Replay／评测均按后续阶段交付；本规格的存在不表示这些命令已可用。

这些是明确安排到后续任务的实现验收条件，不是需要用户现在选择架构的悬而未决问题。第一项实施仍是 [P1-01](IMPLEMENTATION_PLAN.md#p1-01--核验现有改动与真实docker基线)，完成后再迁移 Task v2。本轮在规格交付后停止。
