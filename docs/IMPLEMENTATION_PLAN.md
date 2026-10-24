# 实施状态与验收

当前实现为 **0.3.0、Task v2**。目标规格为 [2026-10-19.2](../specs/2026-10-19.2/SPEC.md)，
原始规格与各次历史验收保留独立版本和证据。

| 交付 | 状态与验收 |
| --- | --- |
| Codex 参数与准入 | 默认 Luna max，支持显式档位；逐块留证、单次结算、整批准入后转发、退场后导出 |
| 快速自检 | reproduce 配置/编译后仅运行 F2P；verify 供预算充足时检查全量回归；Harness 最终独立验收 |
| 候选导出 | EvidenceRef、patch.diff、unverified.patch 依次选择首个非空内容；来源、大小、SHA 与原生状态分开记录 |
| v1 封存 | 110 请求；10 次评分、1 次取消、5 项未执行；协议原字节与哈希保留 |
| v2 三框架对照 | 六次已完成，61/72 正式请求；三组实际 medium；Full 1/2、mini 0/2、Codex 0/2 |
| 后续 max 配置 | Full SDK、mini 原生客户端与固定 Codex CLI 的本地请求检查通过；供应商响应校准待独立预算 |
| 发布证据 | 全部候选、失败、Oracle、请求、账本和原生轨迹按清单归档；源码与包分别核对 |

[v2 报告](../benchmarks/generalization-final-results.md)和[累计账本](../benchmarks/model-usage-audit.json)
提供实际结果。两题已有 v1 使用记录，v2 是冻结新配置的复核。可选 Dev 配对与额外模型尝试均未执行。

| 已完成契约 | 范围 |
| --- | --- |
| P1-01、P1-02 | 真实 Docker 基线、Task v2 解析与固定 commit/image |
| P1-03A、P1-03B | 源码/补丁完整性、资源限额、Run 所有权与清理 |
| P1-04、P1-05 | 公开 SDK Runner、六工具、串行整批准入 |
| P1-06、P1-07、P1-08 | 独立 verify-patch、结构化 CTest、SQLite 报告与安装验收 |
| P2-01、P2-02 | 状态/预算/事件同事务、Checkpoint 与受控暂停 |
| P2-03、P2-04 | 安全边界 Resume、只读轨迹与故障场景验证 |

当前回归与 CI 以[测试报告](TEST_REPORT.md)为准，历史模型实验由[评测索引](../benchmarks/README.md)连接。
下列条目保留核心契约的验收范围。

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
