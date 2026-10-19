# 技术决策

**规格修订：2026-10-19.2。状态：设计选定、待分阶段实现。** 本文替换上一版自写 Agent Loop 与细粒度恢复设计，记录长期取舍。当前代码事实见 [CURRENT_STATE.md](CURRENT_STATE.md)，公开源码核查及复用依据集中于 [ECOSYSTEM_REVIEW.md](ECOSYSTEM_REVIEW.md)。这里的选择不代表新接口已经运行，也不代表已经取得性能或成功率收益。

## 决策索引

| 编号 | 选择 | 阶段 | 唯一详细契约 |
|---|---|---|---|
| ADR-001 | 核心使用标准库与 PyYAML；Agent 依赖为可选 extra | Phase 1 | [任务格式](TASK_FORMAT.md)、[CLI](CLI.md) |
| ADR-002 | 直接复用 OpenAI Agents SDK 的运行循环与 Responses 模型 | Phase 1 | [Agent Runtime](AGENT_RUNTIME.md) |
| ADR-003 | Python 控制平面；C++20 执行器由实际证据驱动 | Phase 1 / 4 | [架构](ARCHITECTURE.md) |
| ADR-004 | 宿主管理 Git Worktree，容器仅见只读源码快照 | Phase 1 | [执行与安全](EXECUTION_AND_SECURITY.md) |
| ADR-005 | Docker 执行仓库代码；密钥及模型调用留在宿主 | Phase 1 | [执行与安全](EXECUTION_AND_SECURITY.md) |
| ADR-006 | 补丁来源可替换；固定 F2P/P2P 的独立验证为产品核心 | Phase 1 | [验证](VERIFICATION.md) |
| ADR-007 | SQLite 只管理外层领域状态；JSONL 是派生导出 | Phase 1 / 2 | [状态与恢复](STATE_AND_RECOVERY.md) |
| ADR-008 | 只在安全边界恢复；未知执行片段明确失败 | Phase 2 | [状态与恢复](STATE_AND_RECOVERY.md) |
| ADR-009 | 显式 Task v2 迁移，拒绝静默改变旧任务含义 | Phase 1 | [任务格式](TASK_FORMAT.md) |
| ADR-010 | 串行工具、公开预算钩子、完整原生 Items 与 SDK 超时 | Phase 1 | [Agent Runtime](AGENT_RUNTIME.md) |
| ADR-011 | 小型对照先行，Phase 3 窄范围复用 Harbor | Phase 3 | [测试与评测](TESTING_AND_EVALUATION.md) |

## ADR-001 · Decision: 核心保留 argparse、dataclasses、PyYAML，Agent 依赖可选

**Context:** 验证外部补丁只需要读取任务、调用 Git/Docker/CTest 和生成证据，不应该先安装模型运行框架或配置 API 密钥。自动修复则需要成熟 SDK，不能为了宣传依赖少而重写其能力。

**Options:** A. 所有功能强制依赖整个 Agent SDK；B. 核心使用标准库与 PyYAML，自动修复使用可选依赖组；C. 为减少第三方依赖自写模型协议和运行循环。

**Decision:** 选择 B。CLI 使用 `argparse`；Task、预算、验证报告等项目数据使用 `dataclasses`、枚举和明确字段解析；YAML 使用 PyYAML。`verify-patch` 路径不导入 Agent SDK、不访问模型。`agent` extra 安装 `openai-agents`，项目直接使用 `AsyncOpenAI` 时也显式声明 `openai` 直接依赖。开发锁与 Run Manifest 固定实际分发版本，不依靠未锁定的“latest”。

**Rationale:** 不为现有轻量 CLI 引入 Typer；Task 解析边界无需再建一套 Pydantic 模型。SDK 内部已经依赖 Pydantic 等库，不能据此声称全项目无 Pydantic。2026-10-19 核查的 `openai-agents==0.24.0` 有 12 条直接运行依赖声明，包含 `openai>=3.0.0,<4` 与 `pydantic>=2.12.2,<3`；完整依赖由锁文件呈现。[依赖核查](ECOSYSTEM_REVIEW.md#sdk-audit)

**Trade-offs:** 使用 Agent extra 会增加安装体积和升级审查成本，但省去更昂贵的协议、测试替身和运行时维护。核心手写的 Task 解析只在信任边界建立不变量，不在每个内部函数重复检查。SDK 原生对象直接使用其公开类型，不再包装成同形项目模型。

**Scope:** Phase 1。依赖隔离必须有“只安装核心也能导入并运行 `verify-patch`”的验收；SDK 集成测试使用安装了 `agent` extra 的环境。字段与 CLI 的权威定义在索引所列文档。

## ADR-002 · Decision: 直接复用 OpenAI Agents SDK Runner，不再自写 Agent Loop

**Context:** 上一版计划自行处理模型往返、四角色消息、工具分发、测试替身与历史恢复。成熟运行时已经提供这些通用能力；保留它们仅用于证明 Harness 能力，会挤占 C++ 验证和复现工作的时间。

**Options:** A. 小型自写 Loop 加 API Adapter；B. 直接复用 OpenAI Agents SDK；C. 嵌入 mini-SWE-agent；D. 嵌入 OpenHands SDK。

**Decision:** 选择 B 作为默认自动修复引擎。直接使用公开 `Agent`、`Runner.run`、`FunctionTool` / `function_tool`、`OpenAIResponsesModel` 和原生 Responses Items；静态注册项目规定的六个安全工具。只写连接项目工具、预算和领域事件的薄集成，不维护第二套 Loop、Model Protocol、四角色编解码或提供商注册体系。测试使用公开 `agents.testing.ScriptedModel`、`ModelStep` 及原生 Item helper；CLI 的 `--engine fake` 是测试入口名称，不是一个自研模型协议。

**Rationale:** 固定版本 `v0.24.0` 的完整 Commit 为 `17d994bd3045dae71acda676a4ef4762ed8ecd94`，许可证 MIT。公开 API 已覆盖所需串行函数工具、生命周期钩子、无网络测试替身、单次模型超时和输入边界。本项目无需 fork SDK 或调用 `run_internal`；源码审查只是确认行为，不使私有实现成为集成接口。[API 核查](ECOSYSTEM_REVIEW.md#sdk-audit)

**Trade-offs:** 接受 SDK 的事件与模型对象，升级需运行少量契约测试。只认证一个实际可用的 Responses 端点/模型；不把“OpenAI-compatible”解释为任意服务都可用，不硬编码一个未经确认的默认模型。mini-SWE-agent、Codex、OpenHands 可作为外部补丁生产者；不在 MVP 同时维护多个内嵌运行时。选 SDK 的依据是与六个函数工具的契合度，不是未经实验的效果排名。

**Scope:** Phase 1，目标 `0.2`。P1-05 必须验证公开 API 的组合能满足预算、错误穿透和串行工具要求；如不能，先收窄非核心行为或提上游问题，不复制 SDK 私有循环。接口唯一规范见 [AGENT_RUNTIME.md](AGENT_RUNTIME.md)。

## ADR-003 · Decision: Python 负责控制平面，C++20 执行器后置

**Context:** 本项目的大部分工作等待模型、Git、Docker、编译和测试。C++ 求职展示需要可信的 C++ 工程实践，不能由跨语言重写本身替代。

**Options:** A. Python 完成控制平面；B. MVP 用 C++ 重写进程管理；C. 从开始维护 Python/C++ 双后端。

**Decision:** 选择 A。Python 3.12 负责 SDK 集成、任务准备、补丁、验证、证据和状态。复用标准库进程能力与 Docker CLI。Phase 1—3 不引入项目自有 C++ 执行器。

**Rationale:** 新增二进制分发、编译链、跨语言协议和故障诊断必须有实际收益。首先通过真实 C++ 缺陷、CMake/CTest、回归约束与可复现实验体现工程深度。

**Trade-offs:** 本项目首版不展示自研进程监管器。Phase 4 只有在一个已记录的进程管理故障、I/O 瓶颈或必要 Linux 系统调用需求无法由现有能力简洁解决时，才设计最小 C++20 组件；需要测量、明确协议和针对性验收。

**Scope:** Phase 1 选定；Phase 4 按证据重审。不预建第二后端、工厂或跨语言 RPC。

## ADR-004 · Decision: Git Worktree 管理候选代码，容器读取稳定快照

**Context:** Agent 需要改代码，但不可信 Shell、构建脚本和测试不能接触宿主控制文件、Git 元数据或可写的实时候选目录。

**Options:** A. 直接修改用户 checkout；B. 可写 Worktree 连同 `.git` 挂入容器；C. 宿主管理独立 Worktree，容器只读经检查的源码快照。

**Decision:** 选择 C。Git CLI 管理固定 Commit 的独立 Worktree、差异和安全清理；项目宿主编辑工具是内嵌 Agent 的唯一源码修改入口。容器只收到 `/src:ro` 独立快照，不收到 live Worktree 或 `.git`。外部补丁在全新受管 Worktree 中应用，进入代码执行前通过同一内容、路径、模式和完整清单审查。

**Rationale:** 保留 Git 的成熟版本语义，同时把权限限制落实为挂载和工具边界。所有生产者最终都交付一个可审核补丁，不需要为每种 Agent 重写验证器。

**Trade-offs:** MVP 只支持明确允许的已有文本文件修改，不支持新增、删除、重命名、二进制或模式变化。Phase 1 接受操作者信任的本地 Git 元数据，并拒绝活动的危险 filter/config；不宣称能安全导入任意恶意 `.git`。源码快照与受控 patch roundtrip 增加必要检查，但不构建新的 Git 实现。

**Scope:** Phase 1。公共 HTTPS 受控 clone 在 Phase 3 另设入口与验收。路径、清单、修改许可、快照、清理以及 Git 配置约束仅在 [EXECUTION_AND_SECURITY.md](EXECUTION_AND_SECURITY.md) 定义。

## ADR-005 · Decision: 仓库代码在 Docker 执行，模型与密钥留在宿主

**Context:** CMake configure 与编译测试本身可以执行任意仓库代码；命令名称白名单无法取代隔离。引入现成 Agent SDK 也不会自动赋予项目所需的安全边界。

**Options:** A. 宿主运行仓库命令；B. 一个宽权限容器持有源码、模型密钥和 Docker socket；C. 宿主调用模型，受限 Docker 容器执行仓库代码。

**Decision:** 选择 C。保留固定镜像、非 root、无网络、只读 rootfs、受限挂载、资源上限与可核查清理。模型密钥不进入容器、Task、工具输出和公开报告。SDK 仅启用项目的六个函数工具，默认不注册 hosted tools、ShellTool、MCP、handoff、skills、memory 或 SandboxAgent。远程 SDK tracing 关闭，Responses 使用 `store=False`，不创建远端 Conversation。

**Rationale:** SDK 负责模型协议和工具调度；ReproPatch 工具实现仍负责文件权限、容器和进程清理。复用一个完整运行时不意味着必须启用它的全部执行能力。

**Trade-offs:** 默认离线执行要求镜像预装构建依赖；Docker 共享宿主内核，不能承诺完全抵御任意敌对代码。`store=False` 和关闭 tracing 是应用配置，不等于零计费、无服务端处理或额外的数据保留承诺。外部 Agent 生成补丁期间的安全性由其运行环境负责，本项目的保证从补丁导入与受控验证开始。

**Scope:** Phase 1。不得运行宿主 `codex exec` 再宣称所有代码执行均受本项目 Docker 限制。Docker gate 未通过时不能用宿主运行代替其验收。唯一权限和生命周期规范见 [EXECUTION_AND_SECURITY.md](EXECUTION_AND_SECURITY.md)。

## ADR-006 · Decision: 补丁生产者可替换，独立验证成为一等入口

**Context:** 修复生成和修复验收有不同职责。无论来自 SDK、Codex、mini-SWE-agent、OpenHands 还是人工，候选补丁都需要相同基线和证据；让所有用户先经过自有 Agent 会形成无必要绑定。

**Options:** A. 只提供内嵌 Agent 的 `run`；B. 接受外部 Agent 自称完成或其测试日志；C. 同时提供自动修复与 `verify-patch`，共享同一独立验证器。

**Decision:** 选择 C，两条路径均属于 Phase 1。`verify-patch` 不调用模型，也必须先复现原始 Commit。冻结 F2P/P2P 集合；在干净 Commit 的新环境只应用获准补丁，重新 configure/build 并运行固定测试。外部 producer 名称和 trace 只作来源元数据与不可信附件，不能替代可信 CommandResult。

**Rationale:** SWE-bench 已提供补丁评测与 F2P/P2P 实践；Harbor 已提供 verifier 与环境边界。ReproPatch 的实际工作是把固定 C++ 任务、源码许可、CTest 证据和资源限制组合为可运行契约，而不是宣称发明独立验证。[现有验收设施](ECOSYSTEM_REVIEW.md#benchmark-reuse)

**Trade-offs:** 基线与候选各自冷构建有成本。固定测试只证明覆盖到的行为，不证明任意语义正确性，也不完全防御恶意代码操纵同容器内的测量。缺失、跳过、集合变化或证据不完整不能算通过；环境失败、超时和不确定结果必须保留其区别。外部补丁生产所耗时间与费用单列，不能混入本项目运行预算后假称可比。

**Scope:** Phase 1。CMake/CTest 最低版本与原始失败匹配、F2P/P2P、补丁规则、证据要求及资源预留以 [VERIFICATION.md](VERIFICATION.md) 为准；CLI 例子仅为目标接口。

## ADR-007 · Decision: SQLite 是外层领域状态权威，不再建会话数据库

**Context:** 当前产品已有 SQLite 事件记录，可以保留；但 SDK 原生输入输出若再归一化成项目的 Turn/ToolCall/Message 表，就会形成两个对话状态系统。数据库与 JSONL 双权威还会带来部分提交问题。

**Options:** A. 自有会话表、操作调度表与 SDK 会话库并存；B. JSONL 和 SQLite 双写为权威；C. SDK 处理对话，SQLite 仅记录外层领域事件与恢复索引。

**Decision:** 选择 C。Phase 1 保留简化事件记录及 SDK 原生输入输出附件，不承诺事务性 Resume。Phase 2 只用 `runs`、`events`、`checkpoints` 三张表管理任务状态、预算、安全边界与附件引用；不引入 per-tool `operations` 表、自己的对话协议或另一套 SDK Session 数据库。JSONL 从 SQLite 导出。原始 stdout/stderr 使用独立二进制附件，不转换为 Base64 日志分块。

**Rationale:** 本项目需要可解释任务结果与恢复资格，无需重新实现 SDK 历史、Session 或通用工具调度。`sqlite3` 事务足以满足本地元数据一致性。Native Items 保持其原生序列化，领域事件只记录相关身份、预算和证据引用。

**Trade-offs:** SQLite 事务不覆盖 Docker、Git 和文件系统，仍需先完成附件写入与摘要再提交引用；孤儿附件和受管容器需核对清理。原生附件可能含仓库内容或不透明延续数据，默认私有，不能把它们等同于可公开 trace。Phase 1 日志存在不意味着中断后能够安全续跑。

**Scope:** Phase 1 留存；Phase 2 外层状态事务。表结构、事件类型、EvidenceRef、附件持久化及导出格式仅由 [STATE_AND_RECOVERY.md](STATE_AND_RECOVERY.md) 定义。

## ADR-008 · Decision: 在下一次模型输入边界 Checkpoint，未知片段不重放

**Context:** 模型请求可能已计费、工具可能已改文件，而进程在记录之前消失。上一版设计逐操作核对、回滚并重做工具组，维护成本过高，且不能获得分布式 Exactly Once。

**Options:** A. 自动重放最后工具组；B. 自建操作调度和补偿框架；C. 仅恢复已关闭的安全片段，其余明确失败。

**Decision:** 选择 C。Phase 2 利用公开 `RunConfig.call_model_input_filter`，在前一工具组已经完成并清理后，保存下一次模型请求的完整原生输入、候选补丁/清单、累计预算和版本身份。模型请求前持久化打开执行片段；直到下一安全边界前保持打开。崩溃时若片段仍开着，即使某些工具日志完整，也不自动重发模型或重做工具组，核对并清理受管容器后以 `RECOVERY_FAILED` 结束。安全 Checkpoint 可从 base+patch 重建源码，经完整性检查后把原生 input list 交回 Runner。

**Rationale:** SDK 的公开 RunState 支持其规定的暂停/审批和序列化，但它不保存任意宿主进程执行现场，不证明未知外部副作用已完成。项目仅为可证明的安全边界增加薄恢复层；不手改 RunState 私有字段、伪造 pending tool response 或恢复内部栈。[恢复能力边界](ECOSYSTEM_REVIEW.md#sdk-boundaries)

**Trade-offs:** 恢复机会比完整操作调度少。准备、复现、验证中崩溃，以及模型结果未知时不自动接着执行；保存补丁后新建 `verify-patch` 是明确的恢复路径。预算和 deadline 不重置。`--pause-after-step` 只在同一公开边界停止，使用已有 `INTERRUPTED` 状态与空 outcome，不增加另一套暂停状态机。Trace Replay 仅查看证据；Execution Replay 新建验证运行，不重放旧 Shell 脚本或承诺模型确定性。

**Scope:** Phase 2。终态不可 Resume，状态转换及恢复算法以 [STATE_AND_RECOVERY.md](STATE_AND_RECOVERY.md) 为唯一规范。

## ADR-009 · Decision: 显式迁移 Task v2，拒绝静默兼容旧语义

**Context:** 当前 Task v1 与新规格在权限、模型引擎、独立验证和结果语义上有迁移差距。把新默认值塞进旧格式，会让同一任务文件悄悄改变含义。

**Options:** A. 猜测版本并补默认值；B. 长期并行维护两套执行语义；C. 新目标只接受显式 Task v2，旧任务给迁移说明。

**Decision:** 选择 C。新 MVP 使用 `version: 2`；原代码不因本轮改文档就声称已支持。重复键、未知字段、不支持 YAML 特性、路径和预算在解析边界检查。不从 Bug 描述、外部 producer trace 或环境变量猜验收标准。

**Rationale:** 一份权威 Schema 比兼容猜测更适合个人维护。少量自有任务可以明确迁移；外部真实需求出现以后再考虑一次性转换工具，不先建迁移框架。

**Trade-offs:** 旧任务需显式转换，镜像与 Commit 必须填真实身份。转换不能自动编造 F2P/P2P 或修改权限。运行路径的可选 Agent extra 与 Task 版本是不同概念：同一 Task v2 可用于 `verify-patch` 和 SDK 自动修复。

**Scope:** Phase 1 目标 `0.2`；Phase 2 目标 `0.3`；Phase 3 目标 `0.4` 后再经公开发布门槛到 `1.0`。唯一字段契约见 [TASK_FORMAT.md](TASK_FORMAT.md)，当前迁移事实见 [CURRENT_STATE.md](CURRENT_STATE.md)。

## ADR-010 · Decision: 复用 SDK 超时、串行调度和原生 Items，超限明确停止

**Context:** 自建模型子进程和手动删除旧消息原本用于处理超时及上下文，但公开 SDK 已提供完整单次 attempt 超时，Responses 历史也不宜被压平成四种角色后任意裁剪。

**Options:** A. 自有 worker、请求 JSON RPC 和消息裁剪；B. 公开 SDK 配置加少量预算钩子；C. 并行工具、持久终端和自动记忆框架。

**Decision:** 选择 B。使用 `ModelSettings.timeout` 处理完整单次模型 attempt；`ModelRetrySettings(max_retries=0, policy=retry_policies.never())` 与 `AsyncOpenAI(max_retries=0)` 显式关闭两层重试。SDK 使用 async I/O 与取消，工具由 `ToolExecutionConfig(max_function_tool_concurrency=1)` 串行执行，同时设置模型侧 `parallel_tool_calls=False`。`Runner.max_turns` 限制模型轮次，公开 hooks 在整批工具分发前做预算准入。上下文达到上限就停止，不手裁原生 reasoning/function Items，不自动发起摘要调用。

**Rationale:** 这些公开 API 在固定版本中存在，不需要 DeadlineModel、模型 worker 或自有 dispatch loop。`function_tool(failure_error_function=None)` 使未分类基础设施错误向任务边界传播；工具内只将已知策略拒绝等预期错误转为规定结果，不能用默认错误字符串吞掉失败。[公开接口核查](ECOSYSTEM_REVIEW.md#sdk-audit)

**Trade-offs:** SDK 模型超时使用协作式取消，不是对任意挂死本地代码的强制抢占，也不包办总预算或容器清理；那些限制仍由任务和工具层承担。`max_steps` 是模型轮次，不承诺等于真实 HTTP 请求数，不可观察的 attempts/usage 记录为未知。SDK 超时不证明服务端从未执行或计费。完整保留 Items 可能较早触发 CONTEXT_LIMIT；上游 compaction 留到 Phase 4 有需求后评估。

**Scope:** Phase 1；async 只服务 SDK I/O 与取消，不扩大为并发任务平台。具体工具、错误、上下文计量与预算规则仅在 [AGENT_RUNTIME.md](AGENT_RUNTIME.md) 定义。

## ADR-011 · Decision: 小型可审计评测先行，Phase 3 窄范围复用 Harbor

**Context:** 自建大量 fixture 调度、并发 worker、评测协议和通用报告系统容易发展成 Harbor 的重复实现；直接全量接入大型数据集又会阻塞第一个真实端到端路径。审查后也不能假定 inline BaseVerifier 的公开下载接口已有本项目所需的流式字节上限。

**Options:** A. 自建通用 Benchmark 平台；B. inline BaseVerifier 加自定义远程下载与监管；C. 小型任务先行，Harbor 原生生产/收集后，从已完成的本地产物接入现有验证器。

**Decision:** 选择 C。Phase 1 完成真实 fixture 和关键回归；Phase 2 随恢复增加故障注入；Phase 3 采用两段式 Harbor 集成：`export-harbor` 生成 producer job，显式 `verifier.disable=true`、并发 1、重试 0，并声明 `/logs/artifacts/candidate.patch` → `candidate.patch` 的 artifact；Harbor 原生运行和收集结束后，`verify-harbor --job DIR --task-map FILE` 从本地产物有界导入，串行复用 `verify-patch`。`eval` 只读聚合。Harbor 拥有 producer，ReproPatch 只拥有自己的新 baseline/verify 容器；不引入新的调度器。

**Rationale:** Harbor 已提供作业和 artifact collection，也已有独立 verifier；本项目无需重新实现。但 `BaseEnvironment.download_file` 无公开 max_bytes/stream，`exec` 无公开输出字节上限；事后检查大小不能证明远端传输有界。两段式直接利用已落盘产物，省去 inline downloader、额外 worker 或逐 provider 兼容层，同时保留既有 C++ 验证契约。[接口核查与复用方案](ECOSYSTEM_REVIEW.md#benchmark-reuse)

**Trade-offs:** 生产结束后才开始独立验收，不提供 inline reward；导入上限只约束本地交接，不承诺限制 Harbor 的远端收集。显式收集到 `<trial-dir>/artifacts/candidate.patch`，不依赖即将移除的自动目录收集。manifest 的 `ok/empty/failed/skipped` 都要进入尝试核对；收集失败本身不会使 Harbor trial 失败，不能从指标中漏掉这些样本。本集成不使用 BaseVerifier 或原生 separate verifier，不在容器内挂 Docker socket。P3-02 先以固定版本、单 fixture 证明导出/收集/导入/结果映射，不能兼容就拒绝。不同工具或提示的生产者对比应标为系统对比。

**Scope:** Phase 3，可选依赖与独立环境；MVP 不要求自动桥接每一种成熟 Agent。指标分母、尝试清单、缺失成本、基线公平性及 CI 分层见 [TESTING_AND_EVALUATION.md](TESTING_AND_EVALUATION.md)。

## 决策变更门槛

改变这些选择时，只需记录：已观察到的具体问题、上游现成能力、最小新增维护成本、以及证明改变有效的验收。若公共 API 无法满足一个非核心旧约束，先删掉该约束；只有真实安全或独立验收不变量受到影响时才阻止接入。无需为每个辅助函数创建 ADR，也不能把未来可能需要的模块提前做成空接口。
