# ReproPatch 规格入口

当前权威目标规格为 **2026-10-19.2**，原文完整保存在
[specs/2026-10-19.2/SPEC.md](specs/2026-10-19.2/SPEC.md)。
新版包内 16 个文件保持原字节及目录关系，替代 2026-10-19.1 的目标设计。
[上一修订](specs/2026-10-19.1/SPEC.md) 仅作为历史保留。

当前产品代码仍为 **0.1.0、Task v1**。规格定义的 Phase 1 目标是 **0.2.0、Task v2**，
这些目标能力尚未全部实现。原始 CURRENT_STATE 是上传规格创建时的审计快照，
最新开发状态与实际检查结果见 [P1-01 记录](docs/P1-01.md) 和 [测试报告](docs/TEST_REPORT.md)。

新版选择直接复用 OpenAI Agents SDK 的 Runner、Responses Items 和 ScriptedModel，
新增不依赖模型的 `verify-patch`，并复用 Harbor 承担后续评测作业。
这些是待实施目标，当前 CLI 尚未提供新版入口，也未安装 SDK extra。

当前任务仍为 **P1-01：继续现有分支并解除 Docker 验收阻塞**。
后续顺序为 P1-02 → P1-03 → P1-06，先做独立补丁验收，再做 P1-04 → P1-05 的 SDK 自动路径，
最后完成 P1-07 → P1-08。不能继续按旧路线先扩展自制循环或恢复层。
当前 Docker gate 仍因环境能力缺失而阻塞，P1-02 未开始。

本轮变更、实际检查与未实施清单见 [新版 Spec 接入记录](docs/SPEC_UPDATE_2026-10-19.2.md)。
