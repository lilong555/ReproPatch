# 技术决策与有限调研

**状态：设计已选定，分阶段待实现。** 本文记录影响维护成本、可信验收和恢复语义的长期选择，不表示相应功能已经完成。当前代码、历史测试记录及迁移差距以 [CURRENT_STATE.md](CURRENT_STATE.md) 为准；阶段门槛以 [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) 为准。

这里的 Decision 是工程选择，不是性能结论。没有通过实验的改进不得写成收益数字。修改决策时，应在同一条记录中补充改变原因与影响范围；不要为命名、单个辅助函数等局部细节另建 ADR。

## 决策索引

| 编号 | 选择 | 开始适用 | 详细契约 |
|---|---|---|---|
| ADR-001 | 标准库 CLI 与内部数据结构；只在边界校验 | Phase 1 | [CLI](CLI.md)、[任务格式](TASK_FORMAT.md) |
| ADR-002 | PyYAML 与官方模型 API SDK；一个小 Adapter | Phase 1 | [Agent Runtime](AGENT_RUNTIME.md) |
| ADR-003 | Python 负责控制平面；C++ 执行器按证据后置 | Phase 1 / 4 | [架构](ARCHITECTURE.md) |
| ADR-004 | Git Worktree 管理候选代码；容器读取独立快照 | Phase 1 | [执行与安全](EXECUTION_AND_SECURITY.md) |
| ADR-005 | Docker 执行仓库代码；宿主调用模型 | Phase 1 | [执行与安全](EXECUTION_AND_SECURITY.md) |
| ADR-006 | 固定基线、固定测试、干净环境独立验收 | Phase 1 | [验证](VERIFICATION.md) |
| ADR-007 | SQLite 为事件权威；JSONL 仅为导出 | Phase 1 / 2 | [状态与恢复](STATE_AND_RECOVERY.md) |
| ADR-008 | 仅在完成边界 Checkpoint；未知结果先核对 | Phase 2 | [状态与恢复](STATE_AND_RECOVERY.md) |
| ADR-009 | 明确迁移到 Task v2，不静默兼容旧语义 | Phase 1 | [任务格式](TASK_FORMAT.md) |
| ADR-010 | 串行执行、有限工具、明确预算和上下文上限 | Phase 1 | [Agent Runtime](AGENT_RUNTIME.md) |
| ADR-011 | 小型可审计评测先行；Harbor 集成按需后置 | Phase 3 / 4 | [测试与评测](TESTING_AND_EVALUATION.md) |

## ADR-001 · Decision: 采用 argparse、dataclasses 与明确的边界校验

**Context:** 项目已有轻量 Python CLI 与模块。MVP 的外部输入主要是 Task YAML、CLI 参数、模型工具请求和执行结果；内部数据形状有限，没有复杂 Web API 或大规模配置体系。

**Options:** A. 标准库 `argparse`、`dataclasses` 和少量显式解析；B. Typer 与 Pydantic；C. 通用配置 DSL、依赖注入及多层 Service/Repository。

**Decision:** 继续使用 `argparse`；内部消息、预算、结果等使用清楚的 dataclass、枚举或字典。Task 解析完成时建立数据不变量；工具请求作为另一外部边界独立校验。内部函数直接使用已校验结构，不反复检查相同条件。

**Rationale:** 参数和数据规模足以用标准库维护，不需要为了获得自动帮助或类型提示更换现有 CLI。集中校验可以保留必要保护，同时避免每层捕获、转换、再次校验。

**Trade-offs:** 需要自行写一份清晰的字段解析及错误定位；复杂嵌套输入增长后，手写转换可能不再划算。若未来真实维护成本证明 Pydantic 更省代码，可以整体替换解析边界，但不能并存两套模型。不得把“少依赖”理解为省略未知字段、重复键、路径和预算校验。

**Scope:** Phase 1 起。完整字段、默认值与约束只在 [TASK_FORMAT.md](TASK_FORMAT.md) 定义；这里不维护第二套 Schema。

## ADR-002 · Decision: 复用 PyYAML 与官方 openai SDK，只维护一层 Model Adapter

**Context:** Python 标准库没有 YAML 解析器；模型调用还涉及 HTTP、认证、协议响应和服务端错误。自行实现 YAML 或通用模型协议层没有项目价值。

**Options:** A. PyYAML 加官方 `openai` Python SDK；B. 自写 YAML/HTTP 客户端；C. 引入多提供商代理库或完整 Agent Framework。

**Decision:** MVP 的直接运行依赖为 PyYAML 与官方 `openai` SDK。PyYAML 负责解析，任务边界拒绝不支持的 YAML 特性及重复键。模型仅接入一个真实的 Chat Completions 工具调用接口，Adapter 保留在 `models.py`，将内部消息与工具结构转换成 SDK 请求，并提取结果、usage 和明确错误。Simple Fake/Mock Model 实现相同最小 Protocol。显式设置 SDK `max_retries=0`，每次发出的模型请求均进入尝试次数与预算记录。真实 SDK 请求在单个可终止的宿主请求子进程中完成，以执行总 deadline；采用标准库进程和计时器，不引入 worker 池或 RPC 框架。

**Rationale:** 官方文档区分用于直接 API 请求的语言 SDK 与用于 Agent 编排的 Agents SDK；本项目只需要前者完成模型通信。[S1b](#s1b-openai-sdk) Adapter 的价值是限制协议影响范围及提供可测试替身，不是包装 SDK 的每个方法。保留现有 `setuptools` / `pip` / virtualenv 流程即可，不强制引入新的包管理工具。

**Trade-offs:** “OpenAI-compatible”不等于支持所有提供商。仅承诺经明确能力检查且符合本接口的端点；缺失工具调用或必须字段时明确报错，不猜测多个协议、不静默回退到纯文本解析。API usage 可以缺失，成本记录必须保留 unknown；请求超时也不能视为从未产生计费。

**Scope:** Phase 1。额外模型接口在 Phase 4 由真实需求推动。Adapter 数据契约、错误类型、密钥配置及重试边界以 [AGENT_RUNTIME.md](AGENT_RUNTIME.md) 为准。

## ADR-003 · Decision: Python 实现控制平面，C++20 执行器按需求后置

**Context:** 任务编排、模型通信、Git/Docker 调用和持久化主要等待外部服务或进程；项目目标包含 C++ Infrastructure 展示，但语言使用本身不能替代工程收益。

**Options:** A. Python 完成 MVP，后续有证据再加 C++；B. 立即用 C++ 重写进程与工具调用；C. 一开始同时维护 Python/C++ 两个执行后端。

**Decision:** Python 3.12 负责 CLI、Agent Loop、验证、状态与外部工具调用。Phase 1—3 不需要本项目的 C++ 执行组件。Phase 4 只有在测量证明进程监管、批量 I/O 或特定 Linux 系统调用需求难以用现有能力简洁满足时，才提出单独 C++20 执行器。

**Rationale:** `subprocess`、Docker、Git 和 SQLite 已覆盖当前需求。将简单 Python 逻辑移到 C++ 会增加编译、分发、跨语言协议和诊断成本。真正的 C++ 能力首先来自对 C++ 构建、测试、缺陷与修复可信度的理解。

**Trade-offs:** MVP 不展示自研底层进程监管器。未来提出执行器时，必须先记录一个现存故障或测量瓶颈、现有方案限制、最小协议及回归门槛；不能仅以“更快”“更可靠”作为理由。也不默认同时保留两个等价后端。

**Scope:** Phase 1 选择 Python；Phase 4 重新评估 C++。模块依赖由 [ARCHITECTURE.md](ARCHITECTURE.md) 统一定义。

## ADR-004 · Decision: Git Worktree 管理候选修改，容器只读独立源码快照

**Context:** 任务必须固定 Commit，不污染用户工作区；Agent Shell 与编译脚本来自不可信内容，不能接触控制平面、Git 元数据或实时可写候选目录。

**Options:** A. 直接修改用户 checkout；B. 将可写 Worktree 连同 `.git` 挂入容器；C. 宿主维护独立 Worktree，向容器提供已检查的只读源码快照。

**Decision:** 选择 C。复用 Git CLI 创建、比较和删除本任务的 Worktree。源码修改通过宿主控制的文件工具完成，容器只接收稳定 `/src:ro` 快照，绝不挂载 live Worktree 或 `.git`。允许修改范围是精确的已跟踪源文件集合；MVP 不支持新增、删除、重命名、二进制和模式修改。

**Rationale:** Worktree 提供固定基线和可审查差异，快照阻断 Shell 直接改源码及控制文件的通路。路径与文件类型校验、快照清单、补丁审核各自发生在相应信任边界，不在所有内部读取函数重复实现。

**Trade-offs:** 只读快照与复制增加少量准备工作；Shell 对只读源文件的写入被拒绝，源码修改必须使用 `edit_file`。Phase 1 只接受操作者信任的本地 Git 元数据，并检查、拒绝活动的危险 filter/config；清理 Git 环境、禁用 hooks/外部 diff 等由执行规范定义。这不是面向任意恶意 `.git` 的导入器，不能宣称安全接收所有未知本地仓库。用户未提交的改动不会隐式成为任务基线。

**Scope:** Phase 1。Phase 3 可加入受控的公共 HTTPS clone，但必须单独定义网络、凭据、Git 配置和来源记录边界。导入命令、可信配置条件、路径规则及资源清理的唯一规范见 [EXECUTION_AND_SECURITY.md](EXECUTION_AND_SECURITY.md)。

## ADR-005 · Decision: Docker 执行仓库代码，模型通信留在宿主控制平面

**Context:** CMake 配置、编译器及测试本身都能执行仓库提供的代码；“只允许编译命令”不能形成安全边界。模型 API 需要网络和密钥，代码执行不应因此获得相同权限。

**Options:** A. 宿主直接运行构建与测试；B. 一个宽权限常驻容器完成所有阶段；C. 宿主进行模型调用，独立受限容器执行各阶段代码。

**Decision:** 选择 C。Docker CLI 是唯一 MVP 执行后端。容器使用固定镜像身份、非 root 用户、只读 rootfs、无网络、资源上限和受限 tmpfs，不挂载 Docker socket、宿主凭据或任意用户目录。一次复现或验证中的 configure/build/tests 在同一临时容器内串行执行；每个 Agent `run_shell` 使用独立容器。任一命令超时使所属容器进入终止与清理流程，禁止继续复用。

**Rationale:** 分离网络/密钥与不可信代码执行，且直接复用容器生命周期和资源控制。独立 Shell 调用消除跨调用后台进程、环境变量和当前目录的隐含状态；需要连续构建和调试时可在一次受限 Shell 调用中组合命令。

**Trade-offs:** 没有依赖下载时的便利性，任务镜像必须预装依赖；每次冷构建有成本。Docker 共享宿主内核，不是对任意敌对代码的完整安全证明。运行主机及 Docker daemon 仍需符合威胁模型；针对强敌对多租户场景应使用专用机器/VM，而不是扩大本项目的默认权限。

**Scope:** Phase 1。不能把 Docker gate 未通过的本机执行结果当成隔离验证结果。完整容器参数、快照/输出上限、超时与清理语义以 [EXECUTION_AND_SECURITY.md](EXECUTION_AND_SECURITY.md) 为准。

## ADR-006 · Decision: 先复现固定故障，再于干净基线独立验收候选补丁

**Context:** 模型自称完成、Agent 自测返回 0、在被修改环境内重跑命令，都不足以证明原始问题已修复。测试被跳过、选择范围被改变或构建缓存污染，也可能产生错误验收。

**Options:** A. 接受模型结论；B. 在 Agent 环境直接执行一条验收命令；C. 冻结 Task 与测试集合，复现基线后在全新环境只应用候选补丁并验证。

**Decision:** 选择 C。基线必须表现为声明的 F2P 正常失败且匹配规定退出码与字面输出标记，所有 P2P 正常通过。候选从固定 Commit 创建干净环境，经补丁范围与内容审查、`git apply --check` 及应用后重新 configure/build，逐个运行固定 F2P/P2P。缺失、跳过或改变测试清单不能通过验收。配置、测试、补丁摘要与原始运行证据一同进入报告。

**Rationale:** SWE-bench Multilingual 明确以 F2P/P2P 验证修复与既有行为；其思想可以直接用于小型 C++ 任务。[S4](#s4-swe-bench) 新环境只引入允许的补丁，便于解释结论由哪些代码和测试产生。CTest 已提供测试发现和 JUnit 输出，不另造测试运行框架。

**Trade-offs:** 两次构建增加必要成本，且只证明声明测试覆盖的行为。隐藏测试不是默认保证；能读测试的模型可能针对测试过拟合。即使固定测试文件，任意恶意被测代码仍可能干扰同一执行环境中的测量，不能据此承诺抵御所有 oracle 规避。基础设施故障、超时及证据损坏需要保留“无法确定”，不能都算补丁错误或成功。

**Scope:** Phase 1 必须实现。测试协议、结果映射、不可判定条件及验收资源预留的唯一规范见 [VERIFICATION.md](VERIFICATION.md)。

## ADR-007 · Decision: SQLite 是事件权威，JSONL 只是派生导出

**Context:** 现有实现已有 SQLite 审计记录；直接丢弃不划算，但 MVP 也不应被完整恢复架构阻塞。SQLite 与 JSONL 双写都作为权威会产生写入顺序和部分失败问题。

**Options:** A. JSON/JSONL 同时承担状态和日志；B. SQLite 与 JSONL 双写为双权威；C. SQLite 单一事件权威，JSONL 由数据库导出，恢复能力分阶段增加。

**Decision:** 选择 C。Phase 1 保留简化 SQLite 事件存储，运行状态在内存管理，最终报告原子写入；不因此承诺事务性任务恢复。Phase 2 才升级到每次运行的 runs/events/operations/checkpoints 结构，用 SQLite 事务提交相关状态与事件。JSONL 按事件顺序导出，失败可以重新导出。

**Rationale:** 原生 `sqlite3` 满足单机事务需求，无需 ORM、外部数据库或事件总线。复用既有事件能力可以减少迁移工作，同时明确“留下日志”和“能够安全 Resume”是不同验收阶段。

**Trade-offs:** 数据库事务不覆盖 Docker、Git 或普通文件系统。涉及产物时先写临时文件并完成同步/原子替换，再在事务中记录引用；崩溃可能留下孤儿文件，恢复阶段必须识别。Phase 1 中断后的最终报告可能不存在，不能用不完整事件擅自推定成功。不同 Run 各自保存数据库即可，不需要全局多用户数据库。

**Scope:** Phase 1 事件留存；Phase 2 事务性状态与恢复。事件 Schema、迁移、文件引用和损坏处理以 [STATE_AND_RECOVERY.md](STATE_AND_RECOVERY.md) 为准。

## ADR-008 · Decision: 在完整完成边界 Checkpoint，未知副作用先核对而不盲重试

**Context:** 持久化“准备执行”与真实执行之间必然存在崩溃窗口。模型请求可能已计费但结果未保存；文件修改或容器命令也可能已产生作用。再次执行不是可靠恢复的同义词。

**Options:** A. 恢复时重新执行最后一步；B. 宣称 Exactly Once；C. 完成边界 Checkpoint、记录操作意图/结果、按操作类别核对未知状态。

**Decision:** 选择 C。在模型响应及其完整工具调用组全部处理完毕后提交 Checkpoint，保存源码补丁、上下文、累计预算及 Task/image/base 身份，不保存容器或构建目录。未知命令先通过已记录容器身份核对并终止；未知编辑用前后内容摘要核对。若模型响应已完整持久化、仅工具组未完成，可以回滚到完成边界，复用已保存响应重做最多一个工具组；为重做创建新 operation 并再次计入工具预算，不重新请求模型。未知模型结果不自动重发请求，以明确恢复失败结束；用户若愿意再试，应创建新运行。

**Rationale:** 可核对的完成边界比伪装成任意指令可续跑更可靠。容器 ID、资源归属和编辑摘要提供具体核对依据；模型请求 ID 本身不构成服务端去重或 Exactly Once 保证。恢复保留已花费次数和不确定计费，不退款式重置预算。

**Trade-offs:** 最后一个未完成工具组可能需要回退到之前的 Checkpoint，工作会丢失，但历史与费用不会被抹去。没有有效 Checkpoint、关键证据丢失或模型结果未知时，恢复会失败；这比默默重复付费调用或未知写操作更清楚。用户中断期间仍计入任务总 deadline。终态运行不可原地复活。

**Scope:** Phase 2；Phase 1 不提供 Resume 承诺。状态名、允许重试的操作分类、恢复失败原因、Trace Replay 与 Execution Replay 只在 [STATE_AND_RECOVERY.md](STATE_AND_RECOVERY.md) 定义。Replay 不承诺模型文本或 stdout 逐字重现。

## ADR-009 · Decision: 使用显式 Task v2 迁移，拒绝静默解释旧行为

**Context:** 当前实现与本 Spec 在任务字段、工具权限、独立验证和结果语义上存在迁移差距。将新规则塞进旧格式的默认值，会让旧任务看似有效但含义改变。

**Options:** A. 自动猜测版本并尽量兼容；B. 维护两套完整执行语义；C. 新格式必须声明 `version: 2`，旧格式给出明确迁移指引。

**Decision:** 选择 C。Task v2 是新 MVP 的唯一执行契约。版本、必需字段、未知字段、重复键、不支持的 YAML 特性和路径歧义在解析边界一次性处理。不从 Bug 文本、旧字段或环境变量暗中补出验收标准。示例中的占位镜像必须明确标注不可运行；任务初始化后写入真实不可变镜像身份与 Commit。

**Rationale:** 一套清楚的 Schema 比长期并存隐含兼容分支更适合个人维护。版本错误应直接给出涉及字段与文档位置，不应通过“尽量跑起来”降低安全性或改变验收含义。

**Trade-offs:** 旧任务需要显式迁移。短期手工迁移少量 Fixture 比建立自动迁移框架更简单；若以后真实用户任务数量证明需要迁移工具，再实现有输入/输出测试的一次性转换。转换不能自动猜测缺失 F2P/P2P 或信任范围。

**Scope:** Phase 1，目标 v0.2.0。当前 v0.1.0 不是新 MVP 已验收的证据。详细映射归 [CURRENT_STATE.md](CURRENT_STATE.md)，唯一字段契约归 [TASK_FORMAT.md](TASK_FORMAT.md)。

## ADR-010 · Decision: 保持串行 Agent Loop、有限工具和简单确定性上下文管理

**Context:** 个人维护的单任务工具不需要分布式调度或多 Agent 协调；并发修改文件、多个后台命令和隐含 Shell 会话会显著扩大状态与恢复空间。

**Options:** A. 同步串行循环；B. 异步并行工具与持久终端；C. 多 Agent/插件注册/任务队列。

**Decision:** 选择 A。一个 Run 同时最多执行一个模型调用或工具操作；模型返回多个工具请求时按顺序执行。工具集合固定，源码仅经 `edit_file` 修改，Shell 限于 Docker。以模型尝试步数、工具尝试次数、总时间及验证预留限制运行；不再添加与模型步数重复的调用预算字段。上下文超限时只裁剪最旧的完整工具轮组，无法继续容纳则明确停止，不做摘要模型、多级 memory 或向量检索。

**Rationale:** mini-SWE-agent 的线性历史与独立 action 说明这些结构可形成有效的最小 Agent 基线。[S2](#s2-mini-swe-agent) 对 ReproPatch 而言，顺序执行还能简化产物归属、Checkpoint 和预算核算；限制是具体的工程选择，不能假称性能最优。

**Trade-offs:** 没有工具并行带来的潜在速度收益，长上下文可能丢失早期细节。非幂等工具不做自动重试。更精细的上下文管理、并发和持久 Shell 必须以测量出的具体失败或成本问题启动，并重新审查一致性与恢复语义。

**Scope:** Phase 1。工具名、消息格式、输出截断、预算值、停止原因及候选补丁交接见 [AGENT_RUNTIME.md](AGENT_RUNTIME.md)，不在此重复定义。

## ADR-011 · Decision: 小型可审计评测先行，通用 Benchmark 集成按需后置

**Context:** 全量公开 Benchmark 会带来镜像、仓库安装、测试解析、时间和费用成本；只展示一个容易的 Fixture 又不足以说明真实适用性。项目首先需要证明端到端流程与错误验收防护实际有效。

**Options:** A. MVP 立即支持多个大型 Benchmark；B. 只保留单个演示且不做对照；C. Fixture 完整流程起步，随后固定小型真实 C++ 任务集和受控策略对照。

**Decision:** 选择 C。Phase 1 先验证一个真实端到端 Fixture，以及错误补丁、超时和隔离边界。Phase 2 随恢复功能增加故障注入测试。Phase 3 固定小型 C++ 集合，以相同模型配置、任务、种子记录和预算比较 baseline/enhanced，分开报告复现、修复、错误验收、恢复和成本。优先使用 SWE-bench 上游数据和评测能力，不复制所有仓库特有解析器。Harbor Adapter 列入 Phase 4 的可选任务。

**Rationale:** OpenHands、Codex、Harbor 已提供相当多的通用 Agent 与评测设施。[S1](#s1-codex)、[S3](#s3-openhands-software-agent-sdk)、[S5](#s5-harbor) 本项目应以具体 C++ 契约和可核查执行证据形成价值，而不是再造通用运行平台。小样本可逐项人工审阅，失败也能被解释。

**Trade-offs:** 小型任务集无法推导全行业成功率；同一模型参数也不能保证采样逐字确定。报告必须给分母、重复运行和缺失计费信息，不编造改进百分比。Harbor 接入以后优先采用控制平面外置的 external agent 方式，避免为运行 Docker-owning CLI 而在任务容器里挂 Docker socket；该集成不应反过来污染本地 Task v2。

**Scope:** Phase 1 的必要测试；Phase 3 的正式评测；Phase 4 的 Harbor/更大任务集。指标定义、必要测试的回归目的和 CI 分层见 [TESTING_AND_EVALUATION.md](TESTING_AND_EVALUATION.md)。

## 现有方案调研：只保留影响上述选择的证据

**统一查阅日期：2026-10-19。** 下列均为已查阅的项目官方文档或官方仓库。未明确展示发布时间的页面仅记录查阅日期；不将搜索引擎的抓取日期当作发布日期。官方能力说明与“ReproPatch 应如何取舍”是两类信息，后者为本项目的工程判断。这里不引用排行榜数字，也不据此宣称本项目优于任何方案。

### S1. Codex

官方 [Codex as a platform](https://developers.openai.com/blog/codex-as-a-platform)（发布于 **2026-08-19**）说明 Harness 管理对话状态、工具、执行边界、审批与跨轮次工作，并提供 SDK/app-server 集成。它支持借鉴模型与控制平面的职责分离，也表明不能把这些通用能力当作 ReproPatch 的原创。直接嵌入现成 Harness 适合构建应用；本项目为研究自己定义的执行与恢复语义，MVP 保留小型循环，以后可把 Codex 作为外部对照。

### S1b. OpenAI SDK

官方 [SDKs and CLI](https://developers.openai.com/api/docs/libraries) 明确区分直接调用 API 的语言 SDK 与承担编排、工具交接等能力的 Agents SDK。本项目采用 `openai` Python API SDK；没有将 Agents SDK 或 Codex SDK 作为同义依赖。当前能力承诺由自己的单一 Chat Completions Adapter 界定，不将官方某个 API 的功能自动推定为全部兼容服务的功能。

### S2. mini-SWE-agent

官方 [Overview](https://mini-swe-agent.com/latest/) 和 [源码仓库](https://github.com/SWE-agent/mini-swe-agent) 强调 Bash、线性消息历史及相互独立的 action。可直接借鉴串行循环和无持久 Shell 的取舍，后续将固定版本作为外部基线。ReproPatch 增加结构化文件工具是为了明确路径、输出和修改权限；不复制其多环境、多提供商兼容体系，也不在工具/提示不同的情况下声称公平优胜。

### S3. OpenHands Software Agent SDK

官方 [Architecture Overview](https://docs.openhands.dev/sdk/arch/overview) 与 [源码仓库](https://github.com/OpenHands/software-agent-sdk) 展示 Agent、Conversation、LLM、工具、Workspace、事件、上下文压缩和安全组件；本地与远程沙箱模式具有不同包及服务依赖。整体复用可以缩短通用应用开发，但在本项目 MVP 中会与自己的预算、状态和恢复层重叠。先保留窄实现；若后续需要成熟远程工具，再评估替换而非再叠一套生命周期。

### S4. SWE-bench

官方 [Evaluation Guide](https://www.swebench.com/SWE-bench/guides/evaluation/) 说明在 Docker 中应用候选补丁并运行测试。[Multilingual](https://www.swebench.com/multilingual.html) 明确 F2P/P2P 协议，包含 C++ 仓库，评测代码集成于 [官方仓库](https://github.com/SWE-bench/SWE-bench)。本项目复用验收思想，后续导入任务优先复用上游测试逻辑；公开实例仍须逐个核对 Commit、镜像、许可证及预算内可运行性，列入候选不等于已经复现。

### S5. Harbor

官方 [Task Overview](https://docs.harborframework.com/tasks/overview) 定义任务、环境、测试脚本与 reward；[Verifier](https://docs.harborframework.com/tasks/verifier) 已支持新 verifier sandbox 和声明产物转移，说明独立验证并非本项目首创。[Custom Agents](https://docs.harborframework.com/agents/custom-agents) 区分容器内 installed agent 与环境外 external agent。Phase 4 可按实际需求复用其跨任务集评测，不自行重建通用调度；Adapter 应保持密钥与模型循环外置。

## 决策变更的最小门槛

修改以上选择前，只需回答四个具体问题：哪个已观察到的问题需要改变；现有成熟工具是否已经解决；新增维护成本由什么实际收益抵消；需要哪项用户可观察的验收来证明改变有效。没有相应证据的候选功能留在后续范围，不先创建空接口、注册中心或备用实现。
