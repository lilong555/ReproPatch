# 当前实施计划

目标规格：[2026-10-19.2](../specs/2026-10-19.2/SPEC.md)。
原始 16 个规格文件保持原文；本文件定义当前任务状态及 P1-03 的独立验收边界。
原始 [P1-03](../specs/2026-10-19.2/docs/IMPLEMENTATION_PLAN.md) 允许按补丁往返与容器清理拆分。

rc3 两题真实对照与可复核展示已完成，当前阶段进入展示与投递。

| 已完成任务 | 交付 |
| --- | --- |
| T1 | POLICY 单源计价、只读 `--check-only`、两份冻结 Task 与原生环境；5 项定向检查及现有 CI 通过。 |
| T2 | 四次已授权真实尝试，47 请求、费用上界 ¥0.54663080；ReproPatch 与 mini 均 0/2。 |
| T3 | [新批次报告](../benchmarks/rc3-rerun.md)、JSON、原始证据与账本可重算；四条空候选记录为 NO_PATCH。 |
| T4 | 免费正确/错误补丁、查询及轨迹导出通过；当前事实与证据入口明确，代码 CI 为 493 项通过；本阶段开发结束。 |

补满五题、120 次正式实验、通用 Harbor、更多恢复阶段、Execution Replay、上下文压缩和 C++20 执行器暂停。
原始规格保留历史原文，本轮范围以上述四项为准。

| 任务 | 状态 | 验收范围 |
| --- | --- | --- |
| P1-01 | 完成 | 真实 Docker 基线、原分支及规格归档。见 [验收](P1-01.md)。 |
| P1-02 | 完成 | Task v2 解析、输入冻结、固定 commit/image、权限集合、规范任务 hash。见 [契约](P1-02.md)。 |
| P1-03A | 完成 | 源码与补丁字节完整性。见 [契约](P1-03A.md) 与 [测试报告](TEST_REPORT.md)。 |
| P1-03B | 完成 | 执行资源、日志硬限额、Run 所有权、清理确认和保留策略。 |
| P1-06 | 完成 | 共享独立验证器、无模型 verify-patch、结构化 CTest 和固定 inventory。 |
| P1-04 | 完成 | 可选 Agents SDK、公开 Runner/Responses 与 ScriptedModel 契约。见 [P1-04](P1-04.md)。 |
| P1-05 | 完成 | SDK 六工具、统一预算、串行整批准入及取消边界。见 [P1-05](P1-05.md)。 |
| P1-07 | 完成 | SQLite 单一事件权威、原子导出、报告与查询。见 [P1-07](P1-07.md)。 |
| P1-08 | 完成 | 离线发布门槛、DeepSeek Responses 工具往返及真实自动修复通过；本地 0.2.0rc1 候选。见 [P1-08](P1-08.md)。 |
| P2-01 | 完成 | schema v2 三表、状态/预算/事件同事务、模型请求前 segment_open、进程崩溃与单写者边界。见 [P2-01](P2-01.md)。 |
| P2-02 | 完成 | SDK 完整输入边界 Checkpoint、持久化文件与原子引用、--pause-after-step、保留源码与清理、核心重导出。见 [P2-02](P2-02.md)。 |
| P2-03 | 完成 | 安全边界 Resume、原始预算与累计用量、未知片段拒绝、源码重建与分歧保护、所属容器核对清理。见 [P2-03](P2-03.md)。 |
| P2-04 | 完成 | 只读 Trace Replay、原始 JSONL 导出、T09 故障统计及 T10 无执行边界。见 [P2-04](P2-04.md)。 |

## P1-03A 完成标准

- 完整源码清单固定路径、内容 SHA-256、字节数与 Git mode，覆盖空文件、二进制资源及可执行文件。
- 拒绝链接、特殊文件、未声明文件集合、额外空目录、权限变更和大小超限；原仓库源码、index 不变。
- 创建工作树前审查 Git 本地配置和提交属性；记录 Git 返回的真实管理目录与工作树身份。
- 编辑只处理授权的已有 C/C++ UTF-8 文本，原子替换保留 BOM、换行字节及权限。
- 候选 patch/manifest 保存 Run 内 EvidenceRef；引用的大小与 SHA-256 必须符合实际文件。
- 新工作树实际应用保存的规范补丁；源码清单与再次导出的 patch 均相同才允许独立执行。
- 必要单测、字节边界与篡改测试、真实 Docker 的编码组合往返和干净 wheel 安装通过。

## P1-03B 完成标准

前置：P1-03A；权威契约为 [执行与安全](../specs/2026-10-19.2/docs/EXECUTION_AND_SECURITY.md)。

- Run 使用独占 0700 控制目录、明确所有权记录及锁；实际 Git common/manager、worktree 和容器身份可核验。
- stdout/stderr 分别保存原始 bytes 和 EvidenceRef；每命令合计 4 MiB，达限立即终止并拒绝成功。
  每 Run 审计预算 256 MiB；完整 patch 与 manifest 不接受截断。
- 容器使用 Task 的 CPU、内存、PID、tmpfs 限额；超时、输出超限、中断及异常均清理整个容器。
  清理后再次 inspect；无法确认删除必须终止，不能继续下一阶段或报告通过。
- 仅操作本 Run 的资源；保留原始失败与清理诊断，不猜测 Git 管理目录、不全局 prune。
- 快照位于本 Run 工作区、按评估独立创建并以只读 mount 使用；评估后释放，依 retain 策略保留所属资源。
- 真实 Docker 验证派生进程、双流超限、只读边界与清理确认；注入所有权及清理失败，确认不误删、不误验收。

父任务 P1-03 的 A、B 两组标准已通过；Phase 1、Phase 2 与本阶段 T1—T4 交付均已完成。
P1-03B 契约与证据见 [执行生命周期](P1-03B.md) 和 [测试报告](TEST_REPORT.md)。
既有 P1/P2 完成标准保留；后续扩展以当前范围决定是否启动。每次实施推进一个具有独立验收标准的任务。

## P1-06 完成标准

- `verify-patch` 仅用核心依赖，按普通文件完整复制有界输入；producer trace 保持 opaque、未验证来源。
- 候选策略在执行前检查；任何接受必须同时有本次合格基线、真实 patch 往返和全新 independent。
- 两条入口共用 configure/build/JSON inventory/逐项 JUnit；测试身份包含 name、argv 和全部有类型属性。
- 基线 F2P 普通失败与原始签名、P2P 实际通过；缺失/skip/disabled/错误 XML/资源终止不能充当通过。
- 结局区分 ACCEPTED、REJECTED、NOT_REPRODUCED、INCONCLUSIVE、ERROR、CANCELLED，并保留具体原因。
- 正确/错误外部补丁、真实 skip、测试删除、正则字符名字及既有 Docker 生命周期验收通过；干净核心 wheel 安装通过。

契约与当前限制见 [P1-06](P1-06.md)，执行证据见 [测试报告](TEST_REPORT.md)。

## P1-04 完成标准

- `agent` 可选依赖固定经实测的 SDK 组合；核心模块导入、安装与纯验证不加载 SDK。
- 单次公开 `Runner.run` 接入原生 `ScriptedModel` 和 `OpenAIResponsesModel`，无新增对话循环或模型基类。
- 无副作用异步 function tool 完成调用、回传和结束；reasoning/opaque continuation 保持原生 Items。
- 显式关闭客户端及模型重试、tracing、远程存储与并行工具；模型和外层时间上限有限。
- 公开 `on_llm_end` 可在整批工具执行前拒绝；串行分派、异常传播与取消边界经离线测试。
- raw_usage 缺失保持 null；合成用量仅属于 fake，不能代表真实模型费用。
- 凭据在显式授权后读取，供应商日志和异常体不进入交付证据；不执行真实付费请求。

当前边界见 [SDK 契约](P1-04.md)，原始证据见 [测试报告](TEST_REPORT.md)。

## P1-05 完成标准

- 自动修复只使用公开 Runner 与 Responses/ScriptedModel；CLI 提供 sdk/fake 两引擎，无手写模型协议或 HTTP 循环。
- 六个静态 async function tools 的 schema 由 SDK 生成；文件策略错误可纠正，基础设施错误终止运行。
- 请求前检查 256 KiB 上下文、阶段期限与步骤；开始计 turn，响应工具整批准入并一次性扣额度，串行分派。
- 原生输入/输出与不透明 continuation 保存在私有 EvidenceRef，领域事件只记引用和已观测用量。
- 工具内 Git 与容器命令受阶段剩余时间限制；Shell 使用独立只读源码容器，逐次清理确认。
- 预算停止不消除已有候选；模型/协议错误保留未验补丁，用户取消不继续独立执行。
- SDK 读改自查结束、真实 Docker Shell/超时/预算和两种干净 wheel 安装验收通过。

## P1-07 完成标准

- Phase 1 的 Run 使用 schema v1 events 表与统一信封、事务内序号；JSONL 从一致性快照派生。P2 三表见 P2-01。
- 领域事件关联模型步骤、本地工具调用及命令 UUID，原生和命令结果仅用私有 EvidenceRef 引用。
- 清理和证据核验先于终态提交，最终事实附件及终态事件共同确定报告；导出失败不修改结局。
- JSONL、JSON、Markdown 和 run.json 分别原子导出；报告丢失可重建，未知用量不补零。
- inspect 只读查询未完成和失败 Run；report 不执行模型或源码，失败结局的正常查询退出 0。
- 数据库缺失、损坏和未知格式不重建；历史 kind 审计按原版读取，不预建恢复表。
- 导出失败、证据损坏、事务失败、核心无 SDK 查询与真实 Docker 路径通过。
