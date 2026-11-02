# ReproPatch 0.4.0 产品合同

**ReproPatch｜可恢复的 C++ 修复与验证系统**。技术主线为 C++ Repair & Verification Harness，可选内置 Agent 负责生产补丁；人工与外部工具产出的补丁通过同一验证器验收。

本文件定义 0.4.0 当前能力与验收合同。操作入口见 [README](README.md)，详细配置见[工程指南](docs/ENGINEERING.md)，执行与信任关系见 [SECURITY](SECURITY.md)。

## 版本与身份

| 对象 | 当前合同 |
| --- | --- |
| 产品与安装入口 | 0.4.0，[v0.4.0 Release](https://github.com/lilong555/ReproPatch/releases/tag/v0.4.0) |
| Task 格式 | `version: 2`，由 [Task](src/repropatch/task.py)解析、校验并冻结 |
| 状态库 | SQLite schema 2；已提交事件、状态、预算与 Checkpoint 引用为运行事实 |
| 执行身份 | 完整 Git commit、实际镜像 ID、Task 摘要、实现摘要；Agent 另记录 Python/SDK、模型配置、指令与工具 schema |

发布身份与包校验值见 [RELEASE.json](RELEASE.json)，被测源码与原始证据见[0.4.0 工程摘要](docs/evidence/v0.4.0/summary.json)。历史报告使用各自记录的源码、镜像和分发包身份。

## 输入与支持范围

系统用于单用户、本地 Linux amd64 Docker 工作流。宿主运行 Python 3.12+ 和 Git；CMake、编译器与 CTest 在已准备镜像中执行。WSL2 使用 Linux Docker 引擎，源码与 Run 目录位于发行版文件系统。

Task 固定本地仓库的完整 commit、镜像 ID/digest、构建命令、测试名单与失败签名、文件权限、预算及产物路径。操作者准备仓库和镜像，并通过 `tests.protected_paths` 保护验收测试、输入与脚本；所有 CMakeLists.txt 和 .cmake 自动加入保护集合。

基线 configure/build 成功，至少一个 F2P 正常执行后失败并匹配声明的 CTest 退出码和原始输出签名，至少一个 P2P 基线通过。CTest inventory 与逐项 JUnit 提供测试身份及观察。基线编译失败记录 `ERROR / BASELINE_BUILD_FAILED`；crash、超时或证据缺失等未形成完整基线观察的运行按 `BASELINE_INCOMPLETE` 等原因归类。

候选修改限定为 `files.editable` 显式授权的已有 UTF-8 C/C++ 文件，保持完整文件集合、Git mode 和受保护输入。单源文件上限 16 MiB、整树 256 MiB、可编辑文本 1 MiB、补丁 8 MiB。新增、删除、重命名、通用基线编译错误与 crash 修复，以及远程多租户执行列入[发布后扩展](docs/ROADMAP.md)。

## 运行与验收

`verify-patch` 接收有界外部补丁与可选生产者附件，使用 core 安装执行基线复现和独立验收。外部 trace 作为原始诊断附件保存，外部生产费用与用量保留已知或未知状态。

`run` 使用可选公开 Agents SDK 生产候选。默认 legacy 注册六个工具：目录、读取、搜索、精确编辑、固定自检与临时 `run_shell`；shell-only 注册持久容器中的 `bash`。legacy 配合 `--semantic-state` 和 `semantic` extra 增加语法结构与证据查询，并选用完整轮次压缩策略。零密钥 Demo 通过 SDK 的 ScriptedModel 展示真实 Docker 修复、拒绝和暂停恢复。

完整流程为：冻结输入与源码清单 → 复现基线失败 → 生产或导入补丁 → 冻结候选 → 在独立工作树应用补丁并核对字节与 mode 往返 → 全新容器冷构建与声明测试验收 → 清理所属资源并导出证据。

修复自检提供模型反馈；最终结局由共享 `verify_candidate` 决定。Run 内 ccache 与持久 /build 服务修复提速，基线和独立验收使用全新构建目录与冷环境。

`ACCEPTED / VERIFICATION_PASSED` 表示候选通过声明的 F2P/P2P、测试身份与源码核验，并具备完整必需证据及已确认资源清理。候选编译或测试失败归为 `REJECTED`；验收超时、资源终止、证据问题与清理未确认分别记录对应原因。阶段状态与 `outcome/reason_code` 分开保存。

实现入口：[Task](src/repropatch/task.py)、[Worktree 与 CandidatePatch](src/repropatch/workspace.py)、[Verification](src/repropatch/verification.py)、[Harness](src/repropatch/harness.py)。

## 预算、状态与恢复

Task 预算控制累计模型步骤、准入工具数、单请求与单命令超时、总 wall 期限、独立验收预留和单次输出 Token。模型响应整批准入，最多八次工具调用，串行执行。`max_steps: null` 与 `max_tool_calls: null` 开放累计次数，时间限制与持续计量继续生效。

SQLite 事务提交事件、状态和累计预算。Checkpoint 在完整模型输入边界保存原生下一输入、基线证据、补丁、源码清单、计数与 deadline：先持久化附件和目录，再在同一数据库事务提交引用并闭合执行片段。恢复读取数据库中的已提交引用。

`resume` 核验同一 Run 的实现版本与摘要、Python/SDK、Task、镜像、模型配置、指令、工具 schema、附件及源码重建结果，沿用原 deadline 与累计预算；暂停等待计入原期限，已核验基线继续沿用。shell-only 恢复重建修复容器，/build、/tmp 和编译缓存从空环境开始。

请求结果未知、工具片段未闭合、输入变化、附件损坏、源码分歧和资源归属未确认分别记录 `MODEL_RESULT_UNKNOWN`、`OPEN_AGENT_SEGMENT`、`INPUT_CHANGED`、`CHECKPOINT_CORRUPT`、`WORKSPACE_DIVERGED`、`OWNED_RESOURCE_UNCONFIRMED` 等恢复诊断。任意崩溃自动接管、执行重放与跨版本恢复属于独立扩展事项。

实现入口：[save_checkpoint 与 resume_run](src/repropatch/recovery.py)、[EventLog](src/repropatch/events.py)、[资源归属](src/repropatch/resources.py)。

## 查询与交付证据

`inspect` 查看已提交事实与证据完整性；`diagnose` 分析阶段、命令、用量和恢复条件；`replay --mode trace` 只读查询按事件顺序组织的轨迹。`export-trace` 输出到 stdout 或 Run 外的新文件。`report` 持锁重建派生报告与索引；`resume` 执行续跑并产生后续事件。

Run 保存 Task 原始及冻结文件、SQLite、原始 stdout/stderr、CTest inventory、逐项 JUnit、候选补丁与源码清单、SDK 原生附件及 Checkpoint。EvidenceRef 用路径、大小和 SHA-256 关联原始证据。`events.jsonl`、`report.json`、`report.md` 与 `run.json` 由已提交事实派生，导出错误单独保存。

## 工程验收

验收按行为覆盖 Core/Ruff、离线 SDK 契约、真实 Docker 与安装 wheel。安装包演示检查成功、拒绝、同 Run 恢复及只读查询；core-only 环境通过隔离 Python 执行正确与错误外部补丁，预期退出码分别为 0 和 1。容器归属、删除确认、证据完整性与被测源码身份进入发布检查。

[CI](.github/workflows/ci.yml)日常运行三条工程作业；历史原生上下文检查由 `workflow_dispatch` 的 `native_context=true` 启用。发布记录包含最终 tag、源码与被测源码关系、实现摘要、镜像 ID、wheel/sdist SHA-256、JUnit 和原始场景证据。长期原件通过 Release 工程附件及 SHA256SUMS 交付，完整标准见[工程验收](docs/ACCEPTANCE.md)。

## 历史规格

[2026-10-19.2 规格包](specs/2026-10-19.2/SPEC.md)、[2026-10-19.1 规格包](specs/2026-10-19.1/SPEC.md)与[历史根规格入口原文](specs/repropatch-spec-2026-10-19-entry.md)保存各自的设计、阶段计划和验收身份。历史根入口中的相对链接以仓库根目录为基点。当前操作合同集中于本文件、[工程指南](docs/ENGINEERING.md)和[安全模型](SECURITY.md)，发布后 P1/P2 工作见[ROADMAP](docs/ROADMAP.md)。
