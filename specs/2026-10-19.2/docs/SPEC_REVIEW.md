# 规格修订与交付审查记录

审查日期：2026-10-19。对应规格修订：`2026-10-19.2`，替代 `2026-10-19.1`。**本文核查规格、示例与来源，不是产品功能测试报告。** 本轮重新调研现有 Agent／Harness，实际修改整套设计文档；没有修改产品源码、安装新版 SDK 验收产品、运行 Docker 或调用付费模型。

## 1. 交付与真实起点

交付包含 SPEC.md、14 份 docs 文档和一个 Task v2 YAML，共 **16 个源文件**；压缩包保留项目相对目录。新增 ECOSYSTEM_REVIEW，其余已有文档与示例均按修订同步。没有把原产品源码、临时研究文件或旧版规格混入交付包。

现有代码不是空仓库。本轮只读核查对应 `work/spec-p1-01`、HEAD `ab6e4c4bbc7fea4778a993257fef1245e26543ed`、干净工作树。上一轮三项清理修改已经提交；因此删去旧版“先保存三个未提交文件”的过时安排。当前产品仍是 0.1.0／Task v1。保存的 **76 passed／4 skipped** 与显式 Docker gate 的 **4 failed／76 deselected** 是读到的历史记录，本轮没有重测；Docker 缺失的门槛仍未解除。准确路径和证据区分见 [CURRENT_STATE](CURRENT_STATE.md)。

## 2. 完整性与权威定义

| 用户要求 | 权威文档与检查内容 |
|---|---|
| 定位、需求与验收 | [REQUIREMENTS](REQUIREMENTS.md)：FR-001–FR-032、NFR-001–NFR-017，关联模块、实施任务和验收义务 |
| 架构、边界和时序 | [ARCHITECTURE](ARCHITECTURE.md)：SDK／控制面／代码容器边界，两个入口、持久化职责、总体与时序 Mermaid |
| Task 与配置 | [TASK_FORMAT](TASK_FORMAT.md) 和 [YAML 示例](../examples/task.example.yaml)：完整 v2 契约、默认值、固定输入、路径与预算；不扩展成工作流 DSL |
| Agent 运行时 | [AGENT_RUNTIME](AGENT_RUNTIME.md)：实际采用的 SDK 公开 API、原生 Items、六工具、整批准入、超时、上下文和停止语义 |
| 执行与安全 | [EXECUTION_AND_SECURITY](EXECUTION_AND_SECURITY.md)：Git／Docker 复用、只读代码快照、源码改动边界、密钥、资源和清理 |
| 独立验收 | [VERIFICATION](VERIFICATION.md)：run／verify-patch 入口、F2P/P2P、测试身份、Patch 往返及精确报告字段 |
| 状态、恢复和重放 | [STATE_AND_RECOVERY](STATE_AND_RECOVERY.md)：状态图、P1 审计、P2 三表、安全输入边界、未知片段拒绝与两类 Replay |
| CLI 与输出 | [CLI](CLI.md)：实现阶段、参数、退出码、受控暂停、产物和错误示例 |
| 测试与评测 | [TESTING_AND_EVALUATION](TESTING_AND_EVALUATION.md)：T01–T12 行为义务、真实 Docker gate、Harbor 两段式产物接入、主验证关联与分母 |
| 可执行开发计划 | [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md)：Phase 0–4、24 个有独立验收点的 Task、前置依赖和 Definition of Done |
| 复用和技术取舍 | [ECOSYSTEM_REVIEW](ECOSYSTEM_REVIEW.md) 与 [DECISIONS](DECISIONS.md)：固定来源、替换／删除清单、11 项长期决策及实际代价 |

核心契约仍各有唯一权威，交叉文档只引用必要字段。P1 不依赖 P2 恢复或 P3 Harbor；核心 verify-patch 安装不依赖任何模型 SDK。

## 3. 本次消除的重复实现

| 审查结论 | 已落实修订 |
|---|---|
| 通用模型循环和工具调用协议已有成熟开源实现 | 用 OpenAI Agents SDK 的 Runner、Responses 原生 Items 和 ScriptedModel，删除自有 Model Protocol、四角色消息及生产 Loop 设计 |
| SDK 已提供模型请求 timeout 与重试控制 | 删除每请求 Python worker、SIGALRM 和 JSON 通信层；外层保留任务总 deadline 与 Docker 进程清理 |
| 第二套会话与逐工具恢复会扩大项目规模 | P2 只有 runs/events/checkpoints；只恢复完整且已提交的公开输入边界，开放片段明确 RECOVERY_FAILED |
| 现成 Coding Agent 不应被迫嵌入私有循环 | P1 将 verify-patch 作为正式入口，外部模型、工具、轨迹权限与项目自己的验证证据明确分开 |
| 自建 benchmark 调度与远端下载层没有必要 | P3 使用 Harbor 原生 producer／artifact collection，随后从已结束本地结果有界导入并独立验证；eval 只读聚合 |
| 手工裁剪原生推理和工具历史容易破坏协议 | MVP 上下文超限即停止；有真实需求再评估上游 compaction |
| 自定义 Base64 日志协议收益不足 | stdout／stderr 分别保存有界原始 bytes，复用 EvidenceRef，不建立分块消息协议 |

Python 3.12、Git、Docker、SQLite、CMake/CTest、argparse、pytest、Ruff 继续使用。没有把成熟工具误判为过时，也没有用 MCP、多 Agent、插件系统、C++ 重写或新包管理器替换已经适用的简单方案。

## 4. 源码与公开接口核查范围

Agents SDK 结论绑定官方 `v0.24.0`／Commit `17d994bd3045dae71acda676a4ef4762ed8ecd94`；mini-SWE-agent 与 OpenHands 也记录已查 release／Commit。Codex、pi、Harbor 的近期官方文档用于确定能力与限制，未将 main 快照伪装为已验收 release。资料索引集中在 ECOSYSTEM_REVIEW；没有使用社区二手文章代替关键接口依据。

除 API 名称外，核查了这些会改变实现的细节：

- SDK 的 timeout、明确关闭 retry、默认 tracing 的关闭、保留原生 encrypted continuation；不能用模型名字猜测支持能力。
- `preserve_raw_usage=True` 及原始字段存在性。SDK 归一化出的零不是实际零用量，未知值必须保留 null。
- 六个注册工具使用 async callback。普通同步函数可能被 SDK 放入线程，取消等待不等于停止线程副作用；不能据此承诺可取消的源码编辑。
- 工具批次必须在副作用前整批准入；SDK 在 end hook 前拒绝的畸形响应，不承诺一定存在完整 raw output。最后一个允许的模型 turn 仍可执行已准入工具。
- 原生 ScriptedModel／ModelStep 与公开 Responses 类型可形成确定性 fixture；不复制上游 Mock 接口或读取私有 cursor。
- Harbor 的公开下载接口没有已确认的流式大小限制；因此采用原生收集后的本地导入，不宣称 ReproPatch 的 8 MiB 上限能约束此前的外部下载。collection failed 也不能自动等同于 Harbor trial failed。

这些是静态接口与控制流审查，不替代安装固定版本后的 SDK、Docker 和 Harbor 集成 gate。

## 5. 实际文档检查

本轮对全部 Markdown 与 YAML 执行了静态检查：189个本地相对链接和章节锚点存在，30个代码块的围栏成对；JSON／JSONL／YAML 可解析，Python 接口片段可语法解析；两段 SQL 均在内存 SQLite 中成功创建。Mermaid 按节点、时序、状态名称做人工结构核查，没有声称进行了完整图形渲染或产品 UI 测试。

Task 示例检查覆盖顶层字段、v2、完整 OID 和镜像 ID 的语法、非空且不相交的 F2P/P2P、固定 CTest 命令模板、内存与时间预算关系。占位镜像仍明确标识；语法正确不代表镜像或源码已在执行主机存在。

开发任务核查确认 **24 个唯一 Task ID**，每项有 Task ID、所属 Phase、目标、前置依赖、涉及文件或模块、具体工作、验收标准、需要运行的测试、预计复杂度；跨文档引用均有定义，显式任务依赖无环。FR／NFR 编号连续、映射明确；第一条交付链为 P1-01 → P1-02 → P1-03 → P1-06，然后接 SDK 路径，不为自动修复先重建整个项目。

SQL 契约检查使用文档原文执行了代表场景：允许尚未冻结的 CREATED；拒绝无冻结输入进入执行阶段；冻结后允许 REPRODUCING；终态必须有 outcome／reason；verify-patch 的引擎只能是 none，也不能进入 REPAIRING。它们验证的是目标数据约束，不能当成现有恢复实现通过的证据。

## 6. 交叉审查中直接修正的歧义

| 可能造成错误的歧义 | 最终规则 |
|---|---|
| CLI、报告和数据库分别叫 repair／verify_patch／run | 统一 input_mode 为 run／verify-patch，数据库 engine_kind 对应报告 engine.kind |
| SDK RunState 与项目运行状态同名 | 明确项目外层枚举和 SDK 快照类型不同，pending 快照不能自动成为安全 Checkpoint |
| Harbor导入批次、eval输入位置和混合退出结果不闭合 | 固定单批次index.json与runs布局，eval显式选择该批次；来源索引不取代Run事实或成为恢复队列 |
| 安全恢复后预算不足可能非法跳转 | 先完成恢复回到 REPAIRING，再走同一预算停止／候选交接路径 |
| Ctrl-C 与主动暂停混用 | SIGINT 是 CANCELLED；P2 只有显式 pause 参数在已提交安全边界进入 INTERRUPTED |
| 验收成功先落库，再发现容器未清理 | 必要清理在结局提交之前；提交后的导出失败保留原 outcome，CLI 报 ARTIFACT_EXPORT_FAILED |
| 外部输入补丁与规范补丁被要求文本完全一致 | 分别保存 producer.patch 和 candidate.patch；以应用结果的源码 manifest 和往返字节确认等价 |
| 只统计收到 patch／生成 report 的尝试 | 保留已启动的无产物、收集失败、中断与未验证条目；未知启动事实单列 |
| 多次验证后选择最好结果 | 预先声明主验证关联，A/B 只使用该关联；重验单列，不增加模型修复样本数 |
| 空样本被显示成 0% 或 100% | 所有比率的零分母／未知分母均为 null，并保留已知计数与原因 |

## 7. 仍需实际实现的门槛

1. **P1-01：真实 Docker 基线。** 当前主机能力记录尚不满足该 gate；需要在可用 Linux Docker 环境验证，不能以 host fallback 替代。
2. **P1-02／P1-03／P1-06：Task v2 与独立补丁验收。** 固定真实镜像、源码、F2P/P2P、权限和字节往返；纯核心安装须验证无 SDK 导入。
3. **P1-04／P1-05：固定 SDK 的最小集成 gate。** 证明公开 hooks 的顺序、工具串行与错误传播、deadline、预算、原生 Items 和未知 usage；无私有 API 或 fork。
4. **P1-08：MVP。** 两条路径、错误拒绝和清理 gate 实际通过；真实端点／模型由操作者指定并授权，公开稳定版另外要求可核查的真实修复案例。没有成功率承诺。
5. **P2／P3：有阶段依据的可靠性和评测。** Resume 只覆盖声明边界；Harbor 先锁版本和单 fixture 试点，再扩大任务集。不能因规格存在就声称命令已经可用。

这些是已分配任务的实施条件，不是需要用户现在反复选择架构的未决问题。后续从 [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md) 的 P1-01 开始，本轮在规格交付后停止。
