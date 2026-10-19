# Agent / Harness 生态核查与复用审计

**查阅日期：2026-10-19。对应规格：2026-10-19.2。状态：官方文档与源码审查完成，新的 SDK / Harbor 集成尚未实现或运行。**

本次只调查会改变 ReproPatch 设计的能力：运行循环、工具执行、会话与恢复、外部补丁接入、独立验证及评测编排。资料来自项目官方文档、官方发布记录和官方源码；没有执行付费模型调用、安装 SDK 验证运行结果，或编造修复率与性能数据。当前项目实现和历史测试记录以 [CURRENT_STATE.md](CURRENT_STATE.md) 为准。

**审计结论：ReproPatch 应以 C++ 可复现任务与独立验收为核心，直接复用成熟 Agent Runtime。** 默认自动修复使用 OpenAI Agents SDK；Phase 1 同时提供不依赖模型的 `verify-patch`，接受成熟 Agent 或人工生成的补丁。自己的代码主要承担任务、源码许可、隔离、资源、候选补丁和证据，不再承担通用模型协议、对话循环或细粒度恢复调度。

## 1. 会影响选型的变化

| 官方能力已覆盖的领域 | 核查发现 | 对项目的影响 |
|---|---|---|
| Agent 循环与模型协议 | Agents SDK 已有 Runner、Responses 模型、函数工具、输入边界、生命周期钩子和公开测试模型 | 删除自写 Loop、四角色消息转换、通用 Model Adapter 和自制 Mock 协议；见 [S1](#s1) |
| Coding Agent 可编程接入 | Codex 已有稳定 Python SDK，OpenHands 有 Conversation/自定义工具，pi 有可定制 SDK | “没有成熟可嵌入 Agent”不能作为自研理由；选择一种默认，其他先做外部补丁来源；见 [S2](#s2)、[S4](#s4)、[S5](#s5) |
| 单次请求超时及重试 | Agents SDK 的公开 ModelSettings 能限制完整模型 attempt 并关闭 Runner 重试 | 删除模型子进程、请求 JSON RPC 和 DeadlineModel；仍由工具层处理 Docker 清理；见 [SDK 核查](#sdk-audit) |
| 测试替身 | 公开 `agents.testing.ScriptedModel` 支持原生输出 Items、usage、异常和 responder | 只保留小型 fixture 文件加载器，不再创建自有 FakeModel/ReplayModel 类体系 |
| 独立 verifier | Harbor 支持 separate verifier 环境和显式产物转移，SWE-bench 已有补丁验收与 F2P/P2P | 不把独立验证宣称为原创；集中补齐 C++ 任务与可信证据契约；见 [S6](#s6)、[S7](#s7) |
| 评测基础设施 | Harbor 已提供任务、环境、Agent 和 verifier 的编排接口 | Phase 3 做窄范围适配，不自建通用任务调度、worker 池或另一种通用轨迹标准 |

这是对已查到能力的工程归纳，不是“2026 年所有 Agent 已采用同一架构”的行业统计。成熟库具备某个能力，不代表其默认配置已经满足 ReproPatch 的权限与验收约束。

## 2. 明确的复用决策

| 能力 | 直接复用对象 | ReproPatch 保留的最小职责 | 阶段 |
|---|---|---|---|
| Agent 往返与函数工具调用 | OpenAI Agents SDK `Runner`、`Agent`、`function_tool` | 静态注册六个受控工具；连接任务预算和领域事件 | Phase 1 |
| 模型通信 | `OpenAIResponsesModel` + `AsyncOpenAI` | 配置已认证端点、显式模型、密钥和公开 retry/timeout 选项 | Phase 1 |
| 无网络模型测试 | `agents.testing.ScriptedModel` | 将小型脚本转换为 `ModelStep`；不重新定义模型消息协议 | Phase 1 |
| 补丁生产 | 默认 SDK；也接受 Codex、mini-SWE-agent、OpenHands、pi、人工补丁 | `verify-patch` 导入并审查补丁；来源 trace 仅是附件 | Phase 1 |
| 版本与工作区 | Git CLI / Worktree | 固定基线、受管目录身份、修改许可、补丁 roundtrip 检查 | Phase 1 |
| 构建与测试 | Docker CLI、CMake、CTest | 固定环境、F2P/P2P 判定、测试清单、权限和证据 | Phase 1 |
| 持久化 | SQLite 原生事务、SDK 原生 Items 序列化 | 外层三表与安全 Checkpoint；不拥有第二套会话系统 | Phase 2 |
| 大于少量 fixture 的评测编排 | Harbor 原生 producer job 与 artifact collection | 导出作业、从已完成本地产物有界导入、复用验证器与指标聚合 | Phase 3 |

**必须自行实现的部分是项目特定的组合逻辑。** 例如“固定 Commit 与镜像、允许修改集合、逐项 F2P/P2P、完整测试集合、候选补丁身份及原始证据一起决定验收结果”没有一个所调查的 SDK 可以在不配置、不适配的情况下替项目完成。应调用成熟 Git、Docker、CTest 能力来实现这些规则，而不是把相关底层工具重写一遍。具体数据结构只有 [TASK_FORMAT.md](TASK_FORMAT.md)、[VERIFICATION.md](VERIFICATION.md) 等权威文件定义。

<a id="sdk-audit"></a>
## 3. 默认运行时：固定版本源码核查

### 3.1 版本、许可与依赖

官方 GitHub `releases/latest` 与对应 tag ref 均核对到以下版本，完整 SHA 指向已发布源码：

| 项目 | 核查值 |
|---|---|
| 分发包 | `openai-agents` |
| 当日观察到的最新正式 release | `v0.24.0` |
| Release 发布时间 | `2026-10-15T02:20:12Z` |
| 完整 Commit | `17d994bd3045dae71acda676a4ef4762ed8ecd94` |
| 核心许可证 | MIT |
| Python 下限 | `>=3.10`，兼容项目选择的 Python 3.12 |
| OpenAI SDK 约束 | `openai>=3.0.0,<4` |

证据是 [官方 release](https://github.com/openai/openai-agents-python/releases/tag/v0.24.0)、[固定版本 pyproject.toml](https://github.com/openai/openai-agents-python/blob/17d994bd3045dae71acda676a4ef4762ed8ecd94/pyproject.toml) 与 [LICENSE](https://github.com/openai/openai-agents-python/blob/17d994bd3045dae71acda676a4ef4762ed8ecd94/LICENSE)。

该版本声明 12 条直接运行依赖：`openai`、`pydantic`、`griffelib`、`typing-extensions`、`requests`、`websockets`、`mcp`，以及声明安全下限的 `httpx2`、`pyjwt`、`python-multipart`、`starlette`、`urllib3`。这是 pyproject 中的直接声明数量，不是最终安装包总数、体积或攻击面评分。项目不启用 MCP 等功能，也不代表相关传递依赖没有安装。

因此采用 **核心 PyYAML + 标准库，Agent SDK 可选 extra**。使用 extra 的环境将完整依赖解析固定到开发锁；Run Manifest 记录实际 SDK 与模型客户端版本。调用 `AsyncOpenAI` 的项目模块显式声明 `openai` 依赖，不依赖偶然的传递导入。只安装核心必须仍能使用外部补丁验证。

### 3.2 公开 API 与替代关系

以下名称均在上述固定 Commit 中确认。表中的“可用”指有公开接口与相应源码，不代表 ReproPatch 已完成集成测试。

| 目标 | 已确认的公开接口 | 可以删除的自研内容 / 注意点 |
|---|---|---|
| 完整运行循环 | `Runner.run(starting_agent, input, *, context, max_turns, hooks, run_config, ...)` | 不再维护自己的 while-loop；`input` 可直接是原生 Items |
| 模型实现 | `OpenAIResponsesModel(model=..., openai_client=...)` | 不再维护 Chat Completions/Responses 双向编解码 |
| 单次模型期限 | `ModelSettings(timeout=...)` | 覆盖完整一次 attempt；协作式 asyncio 取消，不包办总运行时间、工具时间或 retry backoff |
| 明确禁止自动重试 | `ModelRetrySettings(max_retries=0, policy=retry_policies.never())`；客户端 `max_retries=0` | 两个层次显式配置，不因“只调用一次 Runner”就假定只有一次付费请求 |
| 实际函数工具串行 | `RunConfig(tool_execution=ToolExecutionConfig(max_function_tool_concurrency=1))` | 不能只用模型侧 `parallel_tool_calls=False` 代替执行限制；两者同时配置 |
| 工具安全包装 | `function_tool(failure_error_function=None)` | 基础设施异常传播到任务边界；已知策略拒绝由项目工具按约定返回，不被 SDK 默认错误字符串掩盖 |
| 预算与事件 | `RunHooks.on_llm_start/end`、`on_tool_start/end` | 只记录必要领域事件与批量工具准入，不重写 dispatch |
| 下一请求安全边界 | `RunConfig.call_model_input_filter` | 保存完整原生 next-input；不修改 SDK 私有 RunState |
| 测试模型 | `ScriptedModel`、`ModelStep`、`assistant_message`、`function_call` | 不存在需要承诺的公开 `FakeModel` 或 `ReplayModel` 类；`--engine fake` 映射到 ScriptedModel |
| 使用量证据 | `ModelSettings(preserve_raw_usage=True)`、`ModelResponse.raw_usage` | 有数据才记录；上游已丢弃或未返回时仍可能是 None，不能据默认 0 推定免费 |
| 远程记录控制 | `RunConfig.tracing_disabled`、`ModelSettings(store=False)` | SDK tracing 与模型服务存储是不同配置；项目不创建远程 Conversation |

API 证据集中在固定版本的 [run_config.py](https://github.com/openai/openai-agents-python/blob/17d994bd3045dae71acda676a4ef4762ed8ecd94/src/agents/run_config.py)、[model_settings.py](https://github.com/openai/openai-agents-python/blob/17d994bd3045dae71acda676a4ef4762ed8ecd94/src/agents/model_settings.py)、[retry.py](https://github.com/openai/openai-agents-python/blob/17d994bd3045dae71acda676a4ef4762ed8ecd94/src/agents/retry.py)、[lifecycle.py](https://github.com/openai/openai-agents-python/blob/17d994bd3045dae71acda676a4ef4762ed8ecd94/src/agents/lifecycle.py)、[tool.py](https://github.com/openai/openai-agents-python/blob/17d994bd3045dae71acda676a4ef4762ed8ecd94/src/agents/tool.py) 和 [testing/model.py](https://github.com/openai/openai-agents-python/blob/17d994bd3045dae71acda676a4ef4762ed8ecd94/src/agents/testing/model.py)。公开导出可查 [agents/__init__.py](https://github.com/openai/openai-agents-python/blob/17d994bd3045dae71acda676a4ef4762ed8ecd94/src/agents/__init__.py) 与 [testing/__init__.py](https://github.com/openai/openai-agents-python/blob/17d994bd3045dae71acda676a4ef4762ed8ecd94/src/agents/testing/__init__.py)。

<a id="sdk-boundaries"></a>
### 3.3 不要求 fork 的前提与真实边界

当前选定范围没有发现必须 fork 或调用私有 API 的障碍：一个 Agent、六个函数工具、关闭自动重试、串行执行、公开输入钩子和外层终止即可覆盖目标。SDK 普通 async 模型请求已有期限，不再设计模型 worker 或薄 DeadlineModel。

必须保留以下实际限制：

- `max_turns` 定义为模型轮次，不能把它重命名成“确定的实际 HTTP 请求数”。可观察 attempts 单独记录，不可观察值为 null。
- 协作式模型取消与 Docker 进程清理是两个问题。宿主文件操作和容器执行仍需项目自己的边界与清理流程；SDK 不会因函数返回而证明容器已经终止。
- 工具组预算必须通过少量契约测试证明：整批超限时零工具执行、非法参数不获得无成本重试、未知工具不被执行、基础设施错误向任务边界传播。P1-05 做这些测试，不测试 SDK 所有功能。
- 原生输入、输出和不透明延续 Items 由 SDK 类型及其原生序列化处理。超限停止，不删 reasoning/function Items，不为了缩小历史重建四角色协议。SDK 支持 compaction 不等于 MVP 必须开启。
- 公开 `RunState.to_json/to_string`、`from_json/from_string` 可以序列化 SDK 定义的运行状态；它们不证明外部副作用已提交，不保存正在执行的宿主进程，也不等于 SIGKILL 恢复。其版本兼容、上下文恢复和信任要求仍须遵守。[固定版本 RunState](https://github.com/openai/openai-agents-python/blob/17d994bd3045dae71acda676a4ef4762ed8ecd94/src/agents/run_state.py)

ReproPatch Phase 2 采用公开 next-input 边界保存 Checkpoint，外层执行片段未知就恢复失败，不读取 SDK 私有字段或手工构造“未执行”的工具输出。可恢复边界、暂停和预算的唯一算法见 [STATE_AND_RECOVERY.md](STATE_AND_RECOVERY.md)。

## 4. 为什么没有默认嵌入 mini-SWE-agent 或 OpenHands

这两者都可以被真实复用。没有选择它们作为默认，不应写成“框架太重，所以必须自己实现一切”。

### 4.1 mini-SWE-agent

官方 release `v2.4.6` 发布于 **2026-07-23**；核对 Commit 为 `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`，MIT，Python `>=3.10`。其 `DefaultAgent` 公开 `run/step/query/execute_actions/save`，环境负责执行 action，适合直接作为小型外部基线。固定版本还提供 LiteLLM Responses 模型，不能继续称其只支持旧 Chat Completions。[S3](#s3)

固定源码也显示具体不匹配处：默认工具调用路径使用 Bash 工具；现成模型编码/解析按 Bash action 工作。要保持本项目六个宿主文件工具及只读 Shell 快照，仍需改造工具编码与环境桥接。模型请求有独立 tenacity 重试，默认 Docker 生命周期和轨迹 JSON 保存也不是 ReproPatch 的恢复协议。其安装声明有 14 条直接依赖，包含 LiteLLM、Pydantic、Typer、Textual、datasets、openai 等；短循环不等于最终安装依赖很少。

**采用方式：** 保持上游默认结构，在单独运行环境生成 patch，再调用同一 `verify-patch`。对照实验记录 Bash 工具、提示、模型与预算差异；不以修改上游私有循环的方式制造一个名义上的“直接复用”。

### 4.2 OpenHands Software Agent SDK

官方 release `v1.55.1` 发布于 **2026-10-16**；核对 Commit 为 `5fa4dea24c52fe3ac53fa4e3e67a1376b72189e2`，MIT，Python `>=3.12`。公开 `Agent`、`Conversation`、`LLM`、自定义 Action/Observation/ToolExecutor 与工具注册接口足以构建受控工具，原生会话也有事件、持久化、暂停和继续能力。该项目不是只有必须部署的平台服务；只用 SDK 与自定义工具可以不启用远端 server。[S4](#s4)

固定 core pyproject 有 18 条直接依赖，包含 LiteLLM、Pydantic、FastMCP、HTTP 客户端、事件/日志和解析相关库；工具包、workspace/server 是额外选择。原生工具并发默认 1，但 SDK 的会话事件存储、预算、重试和未匹配 Action 恢复已经形成完整语义。再叠 ReproPatch 自有逐工具 operations、checkpoint 和会话数据库，会扩大而不是消除复杂度。

**采用方式：** Phase 1 作为外部补丁生产者。若未来需要它的完整 Workspace/Conversation，应整体接受并替换相应职责，再保留外层验证器；不长期维护双会话、双恢复权威。当前六函数工具需求与 Agents SDK 的公开函数工具更直接匹配，因此不新增第二默认引擎。

## 5. Codex 与 pi 的接入定位

**Codex。** 官方当前文档明确提供稳定 Python 分发 `openai-codex`，要求 Python 3.10+，通过本地 app-server JSON-RPC 控制 Codex；发布包包含固定 Codex CLI runtime 依赖。不能再用“Codex 只有 TypeScript SDK”排除它。官方仓库为 Apache-2.0。[S2](#s2)

但本轮没有建立“所有 Codex 内置 Shell/编辑都可完全替换成项目六个函数工具，并遵循只读 source snapshot”的实测证据。它的 sandbox preset 或 external sandbox 选项也不能被解释为自动将每个命令路由到 ReproPatch Docker。成熟 Codex 可直接用于生成补丁；Phase 1 的复用接口是 `verify-patch`，不是在宿主启动它后给整个生成过程附加未经验证的隔离保证。未来若接入 exec-server/app-server，必须由固定版本试点证明需要的路由和权限，不能只凭存在 RPC 就作承诺。

**pi。** 当日官方仓库为 `earendil-works/pi`，包名为 `@earendil-works/pi-coding-agent`，MIT。源码 `createAgentSession` 支持 `noTools`、`customTools` 和 `ResourceLoader`，具有可定制工具与会话能力。[S5](#s5) 这是一个可评估的现成运行时；在 Python 项目中嵌入则增加 Node 分发与进程桥接。本轮不为此建立 Node 侧车；先将其 patch 纳入同一验收路径。这里使用当日文档/源码快照，没有将 main 的 package version 当成“当日最新正式 release”。

<a id="benchmark-reuse"></a>
## 6. SWE-bench / Harbor 的实际复用方案

SWE-bench 官方评测在 Docker 环境中处理候选补丁并运行测试；Multilingual 提供含 C++ 的任务并使用 F2P/P2P 约束。[S6](#s6) 可复用任务出处、测试定义及已有评测知识。每项导入任务仍需检查许可证、固定 Commit、依赖、镜像和预算；C++ 实例存在不代表它符合本项目 CMake/CTest MVP 子集。不复制整个数据集安装器或所有语言解析器。

Harbor 官方当前文档明确区分默认 shared verifier 与可选 `environment_mode = "separate"`；独立模式建立新环境，只转移声明的产物等允许内容，不继承 Agent 全部文件系统。其 custom `BaseVerifier.verify()` 可以在 Harbor 宿主进程执行，并返回 `VerifierResult`；外部 `BaseAgent` 可在控制平面运行模型循环。[S7](#s7) 这些能力足以支持有边界的复用，不必自建通用评测平台。

**进一步审查后，不采用 inline 宿主 BaseVerifier 下载补丁。** 官方 `BaseEnvironment.download_file(source_path, target_path)` 没有公开 `max_bytes` 或流式读取接口，`exec` 有 timeout 但没有公开输出字节上限。仅在下载结束后检查文件大小，不能声称传输过程有界；先 exec 查询大小再下载也不能证明文件在两步之间不变。[公开环境接口](https://github.com/harbor-framework/harbor/blob/main/src/harbor/environments/base.py) 为保持 inline 方案另建远程限流、下载 worker 或逐 provider 兼容层，会重新引入本次要删除的复杂度。

Phase 3 因此采用两段式交接，命令及数据契约以 [CLI](CLI.md) 和 [评测规范](TESTING_AND_EVALUATION.md) 为准：

1. **导出 producer job。** `export-harbor` 生成受支持任务的 Harbor 配置和 task-map；显式设置 `verifier.disable=true`、并发 1、重试 0。声明 artifact source 为 `/logs/artifacts/candidate.patch`、destination 为 `candidate.patch`，并把生成要求写进任务说明。不依赖即将移除的 `/logs/artifacts/` 自动收集行为。
2. **Harbor 原生执行与收集。** 操作者运行 Harbor 的原生 job；Harbor 拥有 producer 容器、作业、尝试清单和 artifact collection。候选落在 `<trial-dir>/artifacts/candidate.patch`。生产阶段的运行、网络、传输和收集费用与限制由 Harbor 及其执行环境负责，不冒称受 ReproPatch 导入上限约束。
3. **从已结束的本地产物验证。** 新 `verify-harbor --job DIR --task-map FILE` 读取已完成 job 的尝试与 collection manifest，按现有外部补丁入口的文件类型、路径和大小边界导入候选，再串行复用 `verify-patch`。不回连 producer、不下载远端文件、不重跑模型，也不重新实现基线和 CTest 判定。ReproPatch 只拥有自己的新 baseline/verify 容器；所有容器都不获得 Docker socket。
4. **只读统计。** `eval` 关联 Harbor 尝试清单与 ReproPatch 验证证据重算指标，不启动作业或验证。对照与端到端计费分开记录；Harbor job 结束不等于补丁通过。

官方配置提供 `verifier.disable`，显式 artifact 的 destination 相对于 trial 的 `artifacts/`；收集报告位于 `<trial-dir>/artifacts/manifest.json`，状态为 `ok`、`empty`、`failed`、`skipped`。**收集失败不会自动使 Harbor trial 失败。** 缺失、空、失败、跳过或本地导入拒绝都必须保留在尝试清单和相应指标分母中，不能只枚举成功收到的 patch。确切失败分类见评测规范。[作业配置](https://docs.harborframework.com/jobs/configs)、[Artifact collection](https://docs.harborframework.com/jobs/artifact-collection)

上游 separate verifier 与 custom BaseVerifier 是已确认的成熟能力，本次选定路径不启用它们，不额外建立 verifier 容器或宿主 inline downloader。两段式只是把已有产物作为稳定交接点，仍直接复用 Harbor 的作业与收集能力。

这是待实施的窄集成方案，不是已经可用的 Adapter。P3-02 先固定 Harbor release/Commit，在一个 fixture 上验证导出、禁用原生 verifier、原生收集、本地有界导入与验证映射，并检查缺失/失败收集仍入统计；只有通过才扩展任务支持矩阵。无法保持任务与证据语义时明确拒绝。项目不引入 ContainerBackend、下载进程监管器、调度队列、worker 池或另一种通用轨迹协议。

## 7. 本次删除和保留了什么

| 上一版设计或容易延伸的设计 | 本次处理 | 保留的可验证项目价值 |
|---|---|---|
| 自写 Agent Loop / Model Adapter / 四角色消息协议 | 由 SDK 原生替代 | 六个工具的安全实现、预算钩子和独立验收 |
| 模型子进程、JSON RPC、DeadlineModel | 删除；直接使用公开 timeout 与 async I/O | 总任务期限及 Docker 超时清理 |
| 自建 Mock/Fake/Replay 模型接口 | 用 ScriptedModel 和原生 Items；只留 fixture loader | 复现预算、拒绝错误补丁和清理回归 |
| 自动删除旧工具轮组以压缩上下文 | 删除；原生输入超限就停止 | 可解释的上下文终止原因，不破坏协议 |
| 逐工具 operations 表、未知编辑核对和重做一个工具组 | 删除；只保留外层三表和安全片段 | 可恢复资格、预算不重置、未知副作用明确失败 |
| 只允许内置 Agent 产生结果 | Phase 1 新增一等 verify-patch 路径 | 对任意补丁来源采用相同基线与验证标准 |
| 自建通用评测平台或 inline 远程下载器 | Phase 3 复用 Harbor 原生生产/收集，再本地导入 | 小型任务选择、公平对照、收集失败入分母与成本证据 |
| 将 Docker、独立 verifier、线性历史宣传为原创 | 删除该表述 | 把成熟能力组合成真实可运行的 C++ 工程工具 |

没有删除的安全检查包括路径/模式许可、只读快照、宿主密钥隔离、容器权限与清理、固定测试集合、资源上限和持久化完整性。它们对应具体故障，不属于因为引入 SDK 就应一起移除的“多余代码”。详细验收分别见 [执行与安全](EXECUTION_AND_SECURITY.md)、[验证](VERIFICATION.md)、[测试与评测](TESTING_AND_EVALUATION.md)。

## 8. 实施门槛与资料边界

本轮确认的是公开能力与可行集成方向。下一步仍须先完成第一条 Docker 端到端路径及 `verify-patch`，再运行 P1-05 的小型 SDK 契约测试；没有 Docker 的环境不能以宿主执行绕过门槛。模型依赖增加、公开接口变动、任务适配不完整和无网络镜像准备是具体风险，不能用文档宣称它们已经解决。

Agents SDK、mini-SWE-agent 与 OpenHands 的上述结论绑定已核对的 release/Commit。Codex、pi、Harbor 使用本日官方文档或 main 源码快照，本轮未固定它们的最新 release；实际集成时必须补 pin。此处没有排行榜对比、原创性优越宣称或未经实验的效率百分比。

## 9. 主要官方来源索引

以下每组只支持其具体能力与版本，不自动支持“ReproPatch 已实现”或“比其他系统更好”。

<a id="s1"></a>
### S1. OpenAI Agents SDK

[官方 Python 文档](https://openai.github.io/openai-agents-python/)、[v0.24.0 release](https://github.com/openai/openai-agents-python/releases/tag/v0.24.0)、[固定源码树](https://github.com/openai/openai-agents-python/tree/17d994bd3045dae71acda676a4ef4762ed8ecd94)。逐项 API 与 pyproject/许可链接列在第 3 节。用途：确认可直接替代的运行时能力、公开测试接口、取消/重试边界与实际依赖。

<a id="s2"></a>
### S2. Codex

[官方 SDK 文档](https://learn.chatgpt.com/docs/codex-sdk)、[Python API reference](https://github.com/openai/codex/blob/main/sdk/python/docs/api-reference.md)、[non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)、[exec-server README](https://github.com/openai/codex/blob/main/codex-rs/exec-server/README.md)、[LICENSE](https://github.com/openai/codex/blob/main/LICENSE)。用途：确认 Python SDK、固定 runtime、非交互接入和执行集成入口；不能单独证明 ReproPatch 的全部命令重路由已实现。

<a id="s3"></a>
### S3. mini-SWE-agent

[v2.4.6 release](https://github.com/SWE-agent/mini-swe-agent/releases/tag/v2.4.6)、[pyproject](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/pyproject.toml)、[DefaultAgent](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/agents/default.py)、[工具解析](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/models/utils/actions_toolcall.py)、[Responses 模型](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/models/litellm_response_model.py)、[retry](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/models/utils/retry.py)、[Docker 环境](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/environments/docker.py)、[LICENSE](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/LICENSE.md)。用途：固定 Baseline 候选、核对 Bash 路径和直接嵌入成本。

<a id="s4"></a>
### S4. OpenHands Software Agent SDK

[v1.55.1 release](https://github.com/OpenHands/software-agent-sdk/releases/tag/v1.55.1)、[core pyproject](https://github.com/OpenHands/software-agent-sdk/blob/5fa4dea24c52fe3ac53fa4e3e67a1376b72189e2/openhands-sdk/pyproject.toml)、[自定义工具示例](https://github.com/OpenHands/software-agent-sdk/blob/5fa4dea24c52fe3ac53fa4e3e67a1376b72189e2/examples/01_standalone_sdk/02_custom_tools.py)、[Agent](https://github.com/OpenHands/software-agent-sdk/blob/5fa4dea24c52fe3ac53fa4e3e67a1376b72189e2/openhands-sdk/openhands/sdk/agent/agent.py)、[LocalConversation](https://github.com/OpenHands/software-agent-sdk/blob/5fa4dea24c52fe3ac53fa4e3e67a1376b72189e2/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py)、[EventStore](https://github.com/OpenHands/software-agent-sdk/blob/5fa4dea24c52fe3ac53fa4e3e67a1376b72189e2/openhands-sdk/openhands/sdk/conversation/event_store.py)、[LICENSE](https://github.com/OpenHands/software-agent-sdk/blob/5fa4dea24c52fe3ac53fa4e3e67a1376b72189e2/LICENSE)。用途：确认它已具备完整可编程会话，而不是为了拒绝复用只看平台宣传页。

<a id="s5"></a>
### S5. pi

[SDK 源码](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/src/core/sdk.ts)、[包元数据](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/package.json)、[LICENSE](https://github.com/earendil-works/pi/blob/main/LICENSE)。用途：核对现名、定制工具入口和 Node 接入成本；不宣称固定了该项目当日最新 release。

<a id="s6"></a>
### S6. SWE-bench / Multilingual

[Evaluation Guide](https://www.swebench.com/SWE-bench/guides/evaluation/)、[Multilingual](https://www.swebench.com/multilingual.html)、[官方源码](https://github.com/SWE-bench/SWE-bench)。用途：复用补丁评测和 F2P/P2P 实践，按任务核对 C++ 数据与既有测试逻辑；不把上游成绩引用为项目成绩。

<a id="s7"></a>
### S7. Harbor

[Separate verifier](https://docs.harborframework.com/tasks/separate-verifier)、[Custom verifiers](https://docs.harborframework.com/jobs/custom-verifiers)、[Custom agents](https://docs.harborframework.com/agents/custom-agents)、[作业配置](https://docs.harborframework.com/jobs/configs)、[Artifact collection](https://docs.harborframework.com/jobs/artifact-collection)、[BaseEnvironment 源码](https://github.com/harbor-framework/harbor/blob/main/src/harbor/environments/base.py)、[任务配置](https://docs.harborframework.com/tasks/configuration)、[官方仓库](https://github.com/harbor-framework/harbor)、[LICENSE](https://github.com/harbor-framework/harbor/blob/main/LICENSE)。用途：确认已有 verifier 能力、原生产物收集与其失败语义、公开下载接口限制，以及 Apache-2.0 许可；支持 Phase 3 两段式复用，不能替代实际版本 pin 与任务交接试点。
