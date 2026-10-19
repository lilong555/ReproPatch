# ReproPatch — 项目规格总纲

规格日期：2026-10-19。规格修订：`2026-10-19.2`，替代 `2026-10-19.1`。目标 Task 格式仍为 `version: 2`。

**交付性质：经现有开源生态调研修订的实施规格；本轮没有实现产品功能。** 新版保留 C++ 复现和独立验证的核心，把通用 Agent Loop、模型协议处理和评测调度交给成熟开源组件。现有源码与未通过的验收门槛见[CURRENT_STATE](docs/CURRENT_STATE.md)，逐项修订依据见[ECOSYSTEM_REVIEW](docs/ECOSYSTEM_REVIEW.md)。

## 1. 项目定位

ReproPatch 是面向 Linux、Git、Docker、CMake/CTest 的 **C++ 可复现修复与独立验收 Harness**。它固定任务、源码和执行环境，先确认原始故障，再接收 Agent 或人工产生的候选补丁，在新的源码与构建环境中独立运行 F2P/P2P，输出补丁、结论及可追溯证据。

目标用户是 C++ 仓库维护者、尝试使用现成 Coding Agent 的开发者，以及研究修复实验可靠性的工程师。产品有两个同等正式的入口：

- `run`：由现成 OpenAI Agents SDK 驱动自动修复，ReproPatch 提供受控工具、任务预算和独立验收。
- `verify-patch`：接收 Codex、mini-SWE-agent、OpenHands、其它工具或人工产生的补丁，独立复现与验收；无需模型依赖或 API key。

项目的差异是明确的 C++ 验收契约、受保护测试、固定输入、补丁完整性和失败证据。沙箱、事件、Agent Loop、独立验证环境并非 ReproPatch 首创；上游已经提供的能力不再作为自研创新点。Bug Report／CI Failure 可以整理进 Task，自动抓取 Issue、创建或合并 PR 不在 MVP 范围。

## 2. 本次修订的实质变化

| 上一版设计 | 新版决定 | 实际收益 |
|---|---|---|
| 自有 Model Protocol、Chat Completions 四角色协议、手写循环 | 直接使用 `openai-agents` 的 Runner、Responses 模型和原生 Items | 不维护另一套模型对话与工具调度协议 |
| 每个模型请求单独 Python worker、JSON 通信与 SIGALRM | SDK 原生 `ModelSettings.timeout`，外层总时间预算 | 删除自制请求进程／通信层 |
| 自行裁剪完整工具组 | MVP 达到上下文上限就停止；保留完整原生 continuation | 避免丢失推理项或工具关联；有需求再用上游 compaction |
| 四张业务表、逐操作 intent/result、半轮回滚和重做 | 外层 Run 的三表存储；只恢复安全 Checkpoint；未知副作用明确失败 | 不形成第二套通用 Agent 会话引擎 |
| 只能通过内置 Agent 进入验收 | P1 增加 `verify-patch` | 立即复用成熟 Coding Agent，无需逐个嵌入其运行时 |
| 自建评测启动／恢复清单，Harbor 留到远期 | P3 使用 Harbor 作业、外部 Agent 和显式产物收集；本项目做本地补丁验收与指标核对 | 不另建 benchmark 调度器 |
| Base64 分块 JSONL 命令日志 | 两个有界原始 stdout/stderr 文件与证据引用 | 不维护自定义二进制日志协议 |

Git、Docker、SQLite、CMake/CTest、argparse、pytest、Ruff 继续使用。它们解决的是稳定的工程问题。Python 3.12 在本次查询时仍受安全维护；不为追逐新版本一次性扩大平台矩阵。Chat Completions 也未被统一废弃，但对于本项目的新模型路径，Responses 与上游 SDK 的原生数据契约更合适。官方事实和版本证据集中于[生态审查](docs/ECOSYSTEM_REVIEW.md)，不能把“成熟”误写为“老旧”。

## 3. 可复现性与可信性的准确含义

可复现性指锁定源码 commit、镜像内容、Task、补丁、工具链、预算、SDK 和 Harness 版本，使他人能够重新执行相同条件并核查结论。远程模型输出、不同硬件上的耗时及日志顺序不保证逐字或逐位相同。

Trace Replay 只读取历史。Execution Replay 在新 Run 中重新验证保存的补丁，不重放历史 Shell、不再次调用模型。另行调用模型属于新的修复实验。

`ACCEPTED` 仅表示冻结的 F2P/P2P 验收契约通过且必需证据、清理结果完整；不证明任意输入都正确，也不授权合并。外部补丁生成过程不受 ReproPatch 管理，不能用自己的验证结论替它认证生成阶段的权限、预算或数据保护。所有补丁均采用同一验收标准。

## 4. 当前工程起点

既有源码不是空项目。最新只读核查对应分支 `work/spec-p1-01`、HEAD `ab6e4c4bbc7fea4778a993257fef1245e26543ed`；当时工作树干净，前一轮的三处清理修复已经提交，并归档了旧 Spec。产品仍为 0.1.0、Task v1，尚未完成这里的目标设计。

新发现的历史记录是 76 passed／4 skipped；显式 Docker gate 记录为 4 failed／76 deselected，原因是 Docker 能力缺失。这些是读取到的记录，本轮未重新跑测试，不能当成新 Spec 或容器隔离已通过。完整路径与来源见[CURRENT_STATE](docs/CURRENT_STATE.md)。

保留已有工作区、进程、工具、验证和测试代码中的有效实现，逐项替换通用循环与旧模型层；不同时运行新旧两套生产 Loop，也不从零重建项目。

## 5. MVP 的准确范围

MVP 支持一个本地、Git 元数据可信的仓库，一个完整 commit，一个已经在本机准备好的固定镜像；Linux/amd64、Python 3.12、本地 Docker Engine；一次一个 Run，无常驻服务。

任务必须能配置和编译，至少一个 F2P 用例在原版本正常执行后失败并匹配签名，至少一个 P2P 基线通过。最终补丁只修改显式允许的已有 UTF-8 C/C++ 文件，不支持新增、删除、重命名、链接、二进制、mode 或测试／构建注册变更。源码执行只发生在无网络、非 root、资源受限的容器；模型凭证仅在宿主控制面。

自动路径只安装一个可选的 Agent SDK extra，使用一个经认证的 Responses 端点；确定性测试直接复用 SDK 的 `ScriptedModel`。只注册六个受控工具，不启用默认 Shell、MCP、skills、handoff、远程 tracing 或 SDK SandboxAgent。网络 I/O 使用 SDK 的异步接口；工具串行，未引入并发任务调度。

外部路径复制有界补丁文件后执行同一基线与独立验证，可以先于自动路径交付。外部 trace 只是未受信任的诊断附件，不转换为本项目的可信命令证据。两条路径都输出 patch／report／events；模型自称完成不影响验收。

P1 复用现有 SQLite 事件审计，JSONL 从数据库导出，不承诺崩溃恢复。P2 才添加外层状态事务及安全 Checkpoint。MVP 不依赖 P2 或 Harbor。

## 6. 阶段与版本边界

| 阶段 | 目标版本 | 必需交付 | 非目标 |
|---|---|---|---|
| Phase 0 | 本规格修订 | 现状、开源复用审查、接口、示例、实施任务和一致性检查 | 产品代码或空框架 |
| Phase 1 | 0.2.0 | 固定 Task、Docker、安全工具、SDK 自动修复、`verify-patch`、独立 F2P/P2P、报告 | Resume、通用插件、正式评测平台 |
| Phase 2 | 0.3.0 | 外层三表状态、完整边界 Checkpoint、受限 Resume、Trace Replay、故障注入 | 未知工具重做、Exactly Once、跨版本恢复 |
| Phase 3 | 0.4.0 → 1.0.0 | 小型固定任务集、Harbor 窄集成、可重算实验、补丁 Execution Replay、CI／开源发布文档 | 自建队列或大规模调度 |
| Phase 4 | 按证据立项 | 额外运行时／模型、上游 compaction、C++ 执行器、性能优化 | 无条件实现全部候选 |

目标标签不表示功能可用。软件、Task、DB 和事件 schema 分开版本化；SDK 固定依赖版本记入实验与 checkpoint。1.0 的门槛是已声明范围内可靠，并非实现所有未来扩展。

## 7. 技术选型摘要

| 领域 | 决定 | 阶段／理由 |
|---|---|---|
| 语言／CLI／Task 模型 | Python 3.12、argparse、dataclass | 保留已有代码，不为简单 CLI 新加框架 |
| YAML | PyYAML，入口校验一次 | 标准库缺少 YAML；不手写 parser |
| 自动 Agent | 可选 `openai-agents==0.24.0` 为本次审查基线；直接使用 Runner／Responses／ScriptedModel | P1；锁定实际通过集成 gate 的版本后发布，无私有 API 或 fork |
| HTTP 客户端 | SDK 所用官方 `openai`；显式关闭重试 | P1 agent extra；不手写 HTTP／provider 兼容层 |
| 执行／版本管理 | Git CLI、Docker CLI、标准库 subprocess | P1；复用版本控制、容器及进程能力 |
| 验证 | CMake/CTest ≥3.26、标准结构化输出 | P1；ReproPatch 只定义判定与证据契约 |
| 状态 | 标准库 sqlite3；JSONL 导出 | P1 审计、P2 外层状态；不存第二份 SDK 会话 DB |
| 评测 | Harbor，可选独立环境 | P3；复用作业／外部 Agent／产物收集，之后有界本地验收；不开发在线下载器 |
| 开发 | setuptools／pip／经过验证的 constraints、pytest、Ruff | 延续工程，不因修订架构强换包管理器 |
| C++20 独立执行器 | 仍不进入 MVP | 只有测量证明 Python／Docker 控制层不足才立项 |

`openai-agents` 本身含传递依赖，不能宣称零依赖或仅一个小包；它以少维护一个通用运行时换取依赖成本。纯验证安装不加载该 extra。完整取舍见[DECISIONS](docs/DECISIONS.md)。

## 8. 文档的唯一权威

| 文档 | 负责内容 |
|---|---|
| [CURRENT_STATE](docs/CURRENT_STATE.md) | 已有代码、版本和测试证据 |
| [REQUIREMENTS](docs/REQUIREMENTS.md) | FR/NFR、任务与验收映射 |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | 边界、模块依赖、数据结构和时序 |
| [TASK_FORMAT](docs/TASK_FORMAT.md) | Task v2、配置、默认值和输入冻结 |
| [AGENT_RUNTIME](docs/AGENT_RUNTIME.md) | SDK 接入、工具、CommandResult、预算和上下文 |
| [EXECUTION_AND_SECURITY](docs/EXECUTION_AND_SECURITY.md) | 工作区、路径、容器、凭证、清理 |
| [VERIFICATION](docs/VERIFICATION.md) | 基线、补丁、独立验收和报告证据 |
| [STATE_AND_RECOVERY](docs/STATE_AND_RECOVERY.md) | 状态、身份、事件、SQL、Checkpoint 和恢复 |
| [CLI](docs/CLI.md) | 命令、参数、退出码、产物布局 |
| [TESTING_AND_EVALUATION](docs/TESTING_AND_EVALUATION.md) | 测试义务、Harbor 映射、评测分母、CI 和发布 |
| [IMPLEMENTATION_PLAN](docs/IMPLEMENTATION_PLAN.md) | 小任务、依赖、验收和 Definition of Done |
| [DECISIONS](docs/DECISIONS.md) | 重要技术决策与代价 |
| [ECOSYSTEM_REVIEW](docs/ECOSYSTEM_REVIEW.md) | 近期官方资料、版本、复用／替换／删除清单 |
| [SPEC_REVIEW](docs/SPEC_REVIEW.md) | 本轮实际文档检查和仍需实现验证的门槛 |
| [task.example.yaml](examples/task.example.yaml) | 完整格式示例；明确占位镜像，不伪装已运行任务 |

“必须”约束所属阶段的验收，“可”表示不阻塞该阶段的候选。发生冲突先按权威定义修正相关文件，不能任选一种实现解释。

## 9. 开发约束与第一步

只在 Task、工具请求、候选补丁、外部结果和持久化文件进入控制面时校验；内部信任既定不变量。SDK 工具只把可修正的参数／策略错误返回模型，基础设施异常必须传播到任务边界。无全链路兜底默认值、无静默 host fallback。

上游公开接口解决的功能不得再次复制实现。SDK 集成若需要访问私有状态或维护 fork，先停止该集成任务并修订设计；不能把适配器扩成另一个 Runtime。安全和独立验收条件也不能为方便接入框架而悄悄削弱。

后续 Coding Agent 首先执行 **P1-01：继续现有分支、对齐修订规格并解除真实 Docker 验收阻塞**。先读 CURRENT_STATE → SPEC → IMPLEMENTATION_PLAN，检查实际 Git 状态；本次观测为 clean 不代表下次可以跳过检查。随后优先完成 P1-02、P1-03、P1-06 的独立补丁验收路径，再完成 SDK 自动路径。

一次会话完成一个 Task ID，运行相应必要测试，记录实际结果，同步公开契约。不得把代码生成、未跑测试或旧 HEAD 的通过记录当作完成。本轮交付到规格为止。
