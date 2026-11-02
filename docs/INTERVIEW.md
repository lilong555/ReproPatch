# v0.4.0 面试材料

## 项目定位

ReproPatch 是可恢复的 C++ 修复与验证系统。输入是已准备的仓库、固定 commit、构建镜像、授权文件和 F2P/P2P 测试；系统先确认缺陷存在，再接收外部补丁或运行可选 Agent，在独立环境验收，并保存可查询的状态与原始证据。

个人实现集中在组件之间的执行合同：输入冻结、候选往返、测试身份、工具准入、预算、资源生命周期、SQLite 状态和 Checkpoint 恢复。公开 Agents SDK 提供模型工具循环，Git、Docker、CMake/CTest 提供底层基础设施，Tree-sitter 提供可选语法解析。

前四分钟按[演示指南](DEMO.md)展示三场景；随后每项设计用三至四分钟沿源码和失败用例展开。版本与原始运行身份见 [v0.4.0 证据摘要](evidence/v0.4.0/summary.json)，简历文本见[项目总览](PROJECT_REPORT.md#简历表达)。

## 设计一：候选冻结与独立验收

**问：一次候选怎样形成可信的交付结局？**

`Worktree.freeze_candidate` 保存 `patch.diff`、完整 `SourceManifest` 和变更集合，清单记录路径、SHA-256、字节大小和 Git mode。`verify_candidate` 经 `prepare_candidate_validation` 校验基线资格与证据，创建固定 commit 的新工作树，再调用 `apply_candidate`。

`apply_candidate` 先比较独立工作树的原始清单与基线清单，应用授权补丁，然后比较实际完整源码、规范 diff、变更集合和候选指纹。检查通过后，`evaluate_checks` 在独立容器中配置、冷构建、发现测试并执行 F2P/P2P；`candidate_result` 将结构化观察归为接受、拒绝或证据不足。

**问：为什么同时保存补丁和源码清单？**

补丁表达修改操作，清单表达实际送验的源码身份。两者的往返核对覆盖文件集合、原始字节和 mode，也能发现受保护文件变化、Git diff 隐藏变化及补丁与冻结产物分歧。全新工作树重建候选，让验收证据明确对应固定基线和这份修改。

**问：测试退出码怎样成为验收证据？**

基线要求 configure/build 成功、F2P 符合声明的退出码与失败签名、P2P 通过。验收结合 CTest inventory、测试身份和逐项 JUnit，核对测试实际执行、状态及基线映射。`negative_values` 失败会得到 `REJECTED / F2P_FAILED`；接受还要求构建、声明测试、证据和清理条件完整。

**问：缓存怎样兼顾效率和可信度？**

修复阶段可复用持久 `/build` 或 Run 内 ccache，用于获取反馈。最终验收采用新工作树、全新容器和冷构建目录，`independent.compiler_cache` 为 `null`。效率比较固定任务与环境，观察配置、编译、自检和验收的阶段耗时。

源码：[verify_candidate](../src/repropatch/verification.py)、[apply_candidate](../src/repropatch/workspace.py)。测试：[候选完整性](../tests/test_source_integrity.py)、[验证器](../tests/test_verification.py)、[真实 Docker](../tests/test_docker_integration.py)。演示：查看正确与错误候选的清单、独立 JUnit 和日志引用。

## 设计二：文件持久化与 SQLite 事务

**问：Checkpoint 的提交顺序是什么？**

`save_checkpoint` 首先确认修复资源已静止、工作区归属成立、源码审计通过，随后保存完整下一 SDK 输入、补丁、源码清单、配置与工具指纹，并同步文件和目录。附件全部持久化之后，`EventLog.transaction` 在同一事务中提交 `checkpoint_committed`、Checkpoint 引用和状态；安全暂停同时进入 `INTERRUPTED`。

`EventLog.emit` 将事件插入、Run reducer 更新和 Checkpoint 记录组织在同一 SQLite 事务中。数据库采用 `BEGIN IMMEDIATE`、`synchronous=FULL`，Run 锁约束单写者。模型请求、工具执行和附件写入发生在数据库事务之外，各自保存执行事实。

**问：附件写完、数据库提交前发生故障，会怎样恢复？**

`read_checkpoint` 从数据库已提交的 Checkpoint 引用读取 manifest，并检查附件摘要、计数、指纹和期限。提交前留下的目录保留为孤立证据；恢复选择继续以数据库事实为依据。恢复流程核验其归属后将孤立目录保存到恢复诊断目录。

**问：恢复为什么选择完整模型输入边界？**

该边界已经包含本轮完整模型与工具结果，下一输入和源码状态可以共同校验。请求结果未知时记录 `MODEL_RESULT_UNKNOWN`，工具片段未闭合时记录 `OPEN_AGENT_SEGMENT`，保留已有证据并给出恢复原因。安全边界上的恢复重建源码并继续剩余步骤，历史副作用保持其原执行身份。

**问：暂停之后哪些状态继续生效？**

`_resume_harness` 校验 Harness 实现、Python、SDK、Task、镜像、instructions、工具 schema 和附件；恢复原 Run、原生下一输入、已存基线、累计步骤与工具预算。`RunClock.restore` 沿用原 deadline，暂停时间计入 wall deadline。持久 Shell 重建已审计源码，`/build`、`/tmp` 与编译缓存重新开始。

演示的恢复合同检查同 Run、基线与编辑各一次、事件前缀相同、步骤 3→5、工具 3→4 和期限连续。SQLite 保存已提交事实；`inspect`、`diagnose`、`replay` 只读查询，`report` 重建派生报告与索引。

源码：[save_checkpoint 与恢复](../src/repropatch/recovery.py)、[EventLog](../src/repropatch/events.py)。测试：[Checkpoint 故障窗口](../tests/test_checkpoints.py)、[状态事务](../tests/test_recovery.py)、[恢复身份与预算](../tests/test_resume.py)。演示：并列查看 recovery 的暂停记录、manifest 和恢复后事件前缀。

## 设计三：资源拥有者确认退出

**问：超时怎样同时结束命令和执行资源？**

`run_process_bytes` 使用独立宿主进程会话、`selectors` 双流读取和单调时限。`run_logged_process` 保存原始 stdout/stderr、摘要与命令身份。超时、取消或输出硬限额触发收尾：先回收本地进程组以解除管道背压，再调用 `on_stop`，由持有容器身份的 `DockerSandbox.close` 清理执行资源，最后等待本地客户端退出。

**问：怎样证明删除的是本 Run 的容器？**

`DockerSandbox._verify_owner` 核对容器 ID、名称和 Run 标签。`close` 在独立清理期限内先 inspect 并确认归属，再执行强制删除，之后再次 inspect，确认容器消失并保存 `cleanup_confirmed`。清理异常保存原因和资源证据，接受结局要求清理条件完整。

**问：如何区分程序返回 125/126/127 与 Docker 启动失败？**

这些数值由执行身份进一步解释。`exec_start_failed` 保存原始双流引用，按容器与时间范围查询 `exec_create`、`exec_start`、`exec_die`，要求唯一 exec ID、完整事件顺序和匹配退出码，再通过 exec inspect 核对容器、实际进程、argv 和终止状态。身份确认后将退出码作为程序结果；启动或身份异常进入基础设施诊断。

**问：Shell 命令返回后，如何处理后台派生进程？**

`PersistentRepairSandbox.execute` 执行前确认空闲，执行后 pause 容器，再由 `assert_idle` 核对冻结状态、资源配置与初始存活 PID 集合。额外派生进程产生 `SHELL_PROCESS_LEAK` 并触发清理。容器静止后，宿主审计和同步授权源码；可写挂载限于授权文件，其他源码保持只读。

源码：[run_process_bytes](../src/repropatch/process.py)、[DockerSandbox](../src/repropatch/sandbox.py)、[PersistentRepairSandbox](../src/repropatch/repair_sandbox.py)、[资源记录](../src/repropatch/resources.py)。测试：[进程与沙箱](../tests/test_process_sandbox.py)、[exec 身份](../tests/test_exec_identity.py)、[持久 Shell](../tests/test_shell_docker.py)。演示：查看命令 `status`、原始双流、容器 ID 与最终清理证据。

## 收束表达

项目体现 Python 系统编排、Agent 工具执行合同、C++ 构建测试基础设施和状态一致性。工程优化以分阶段成本和验收结局为依据，历史模型实验保存原版本、任务与运行身份。面试主线用确定性完整 C++ 示例说明机制，真实模型与上游仓库轨迹通过[历史评测索引](../benchmarks/README.md)展开。
