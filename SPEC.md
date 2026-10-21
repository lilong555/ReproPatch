# ReproPatch 规格入口

权威目标规格为 **2026-10-19.2**：[完整规格](specs/2026-10-19.2/SPEC.md)。
归档 16 个文件保持输入包原文；其中 CURRENT_STATE 为规格创建时的审计快照。
当前产品能力以 [README](README.md) 和 [测试报告](docs/TEST_REPORT.md) 为准。

当前候选版本为 **0.3.0rc2，Task v2**。
P1-01 至 P1-08 已完成，包含 P1-03A、P1-03B 两项独立验收。
两条路径共用结构化 CTest、固定 inventory 身份、原始字节清单和实际补丁往返；
外部 `verify-patch` 不导入模型或 SDK、不读取模型密钥。
rc2 的 21 项定向回归与真实任务上下文检查通过；rc1 历史完整验收为
315 项核心测试、147 项 SDK 契约、21 项真实 Docker 测试，不冒充 rc2 的完整回归。
P2-01 的三表、状态与预算事务、请求前执行片段及崩溃窗口已验收。
P2-02 的公开完整输入 Checkpoint、不可变附件提交、受控暂停和核心重导出已验收。
0.2.0rc1 的 DeepSeek `deepseek-flash` 完整 V-LIVE 通过，实际修复结局为 `ACCEPTED`。

公开 SDK 基础契约见 [P1-04](docs/P1-04.md)。六工具与预算契约见 [P1-05](docs/P1-05.md)。
SQLite 权威事件、原子导出与查询见 [P1-07](docs/P1-07.md)，当前外层事务见 [P2-01](docs/P2-01.md)。
P2-03 的安全边界恢复、未知片段拒绝、原预算及容器清理已验收。
P2-04 的只读轨迹、JSONL 导出和恢复故障门槛已验收，Phase 2 完成。
下一任务为 **P3-01：固定 Fixture Suite**。
当前任务边界见 [实施计划](docs/IMPLEMENTATION_PLAN.md)，原始完成标准见
[归档计划](specs/2026-10-19.2/docs/IMPLEMENTATION_PLAN.md)，每个工作回合推进一个 Task ID。

0.2.0 的 MVP 门槛已通过；0.3.0rc2 为可靠性候选版本，开发包见公开 GitHub 仓库的预发布页面。
Execution Replay 和 Harbor 接入属于后续任务。
离线发布审计、真实 smoke 任务、实际补丁与验收结果见 [发布验收](docs/P1-08.md)。
