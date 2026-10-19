# Agent Runtime：复用 SDK 的受控自动修复路径

状态：**目标 Phase 1；安全 Checkpoint 属于 Phase 2。** 本文定义 SDK 接入、工具、CommandResult、上下文与预算语义。Task 字段见[TASK_FORMAT](TASK_FORMAT.md)，状态与恢复见[STATE_AND_RECOVERY](STATE_AND_RECOVERY.md)，独立判定见[VERIFICATION](VERIFICATION.md)。这里的接口示例是实施契约，不是已经运行的产品代码。

## 1. 责任与复用边界

默认自动路径直接使用 **OpenAI Agents Python SDK v0.24.0**，本次核查 Commit 为 `17d994bd3045dae71acda676a4ef4762ed8ecd94`。运行时、数据类型和工具分派交给上游；ReproPatch 只负责冻结任务、预算准入、受控工具、领域事件和候选交接。[官方 Runner](https://openai.github.io/openai-agents-python/running_agents/)、[固定版本源码](https://github.com/openai/openai-agents-python/tree/17d994bd3045dae71acda676a4ef4762ed8ecd94)。

| 责任 | 所有者 | 本项目不另行实现 |
|---|---|---|
| 对话循环、模型输出 Items 与 function call 关联 | `Runner` 与 SDK 模型实现 | 自有 while-loop、四 role 归一化、响应协议解析器 |
| 一个真实模型接口 | `OpenAIResponsesModel`＋`AsyncOpenAI` | 自制 HTTP、自动 endpoint 探测、多供应商框架 |
| 确定性测试模型 | `agents.testing.ScriptedModel` | Fake 服务、第二套模型行为框架 |
| 工具 schema／参数结构校验和分派 | SDK function tools | 通用工具注册／插件系统 |
| 路径、修改范围、容器、时间、资源与证据 | ReproPatch 的已有模块 | 不把 SDK 默认工具的权限当成本项目权限 |
| 最终接受／拒绝 | ReproPatch 独立验证器 | 不使用模型 final_output 作验收 |

`verify-patch` 完全不进入此运行时，不导入 agent extra，不读取模型密钥。任何外部 Agent 都可以作为补丁生产者，但其对话、工具和费用只是外部来源，不能冒充经过本运行时管理。

## 2. 最小接入与数据结构

保留 `models.py` 作为 **SDK 对象构造与测试脚本加载的局部模块**，删除旧自定义 HTTP 和 Model/Turn 对话协议。无需本项目的 Model 基类；真正需要新增模型时使用 SDK 的公开 `Model` 接口或上游适配器，再认证一个实际端点。[SDK Model 接口](https://openai.github.io/openai-agents-python/ref/models/interface/)。

`harness.py` 编排基线→Agent→候选→验证。将 Agent 调用集中为一个函数即可：

```python
@dataclass(frozen=True)
class AgentResult:
    stop_reason: str
    final_text: str | None
    steps_used: int
    tool_calls_admitted: int
    http_attempts: int | None
    usage: dict[str, int | None]
    native_trace: tuple[EvidenceRef, ...]

async def run_agent(context: RunContext) -> AgentResult:
    ...  # 构造 SDK Agent，调用一次 Runner；不实现另一层对话循环
```

`EvidenceRef` 由[架构](ARCHITECTURE.md)定义。RunContext 仅包含已冻结 Task、工作区／执行器句柄、剩余预算和事件 sink；不能把 API key 或 SDK client 放入可序列化 context。用于报告的 `engine` 与 `producer` 字段由[验证报告](VERIFICATION.md)统一定义。

### 2.1 配置必须显式

下面只展示上游公开入口，`registered_tools`、`boundary_filter` 与 `audit_hooks` 是本项目的静态配置／领域回调；它们的义务见后文：

```python
from agents import Agent, ModelSettings, ModelRetrySettings, RunConfig, Runner
from agents import OpenAIResponsesModel, ToolExecutionConfig, retry_policies
from openai import AsyncOpenAI

async def invoke_sdk(model_name, api_key, api_base, initial_items,
                     registered_tools, boundary_filter, audit_hooks,
                     instructions, task, context):
    async with AsyncOpenAI(
        api_key=api_key, base_url=api_base, max_retries=0,
        timeout=task.budget.model_timeout_seconds,
    ) as client:
        agent = Agent(
            name="ReproPatch repair",
            instructions=instructions,
            model=OpenAIResponsesModel(model=model_name, openai_client=client),
            tools=registered_tools,
            model_settings=ModelSettings(
                store=False,
                preserve_raw_usage=True,
                response_include=["reasoning.encrypted_content"],
                parallel_tool_calls=False,
                max_tokens=task.budget.max_output_tokens,
                timeout=task.budget.model_timeout_seconds,
                retry=ModelRetrySettings(
                    max_retries=0, policy=retry_policies.never()
                ),
            ),
        )
        return await Runner.run(
            agent, input=initial_items, context=context,
            max_turns=context.remaining_steps,
            hooks=audit_hooks,
            run_config=RunConfig(
                tracing_disabled=True,
                call_model_input_filter=boundary_filter,
                tool_execution=ToolExecutionConfig(
                    max_function_tool_concurrency=1
                ),
                tool_not_found_behavior="raise_error",
            ),
        )
```

实际调用外面还有 `asyncio.timeout(agent_remaining_seconds)` 与任务边界的 `finally` 清理；片段没有省略这些义务的含义。SDK `ModelSettings.timeout` 覆盖完整单次 attempt，并等待协作式取消清理；不覆盖工具、重试 backoff 或整个 Run。外层 deadline 和容器清理仍必须由 Harness 完成。[模型超时与重试](https://openai.github.io/openai-agents-python/models/#model-call-timeouts)。

只注册 §4 的六个本地 function tools；不配置 handoffs、MCP servers、hosted tools、web search、skills、memory、ShellTool、SandboxAgent、服务端 conversation 或 `previous_response_id`。不因上游发行包内包含这些功能就自动启用。使用非流式 HTTP，避免为 MVP 再维护流式 UI 或 WebSocket 生命周期。

SDK 远程 tracing 默认开启，本项目明确关闭；只做本地受控审计。不从仓库自动发现 prompt／配置／扩展。模型配置必须显式给 model_name，不能沿用 SDK 会变化的默认模型。[Tracing 默认行为](https://openai.github.io/openai-agents-python/tracing/)。

### 2.2 模型与配置错误

P1 只认证官方 Responses 的一个实际 model 配置。保留显式 `--api-base`，但第三方仅声称“OpenAI-compatible”不构成 Responses 兼容证据；未经 V-LIVE 的组合标为未认证，不自动退回 Chat Completions。真实调用必须有 `--allow-paid-model` 和模型名。

API URL 必须 HTTPS、无 userinfo/query/fragment；key_env 只保存环境变量名称。宿主读取 key 后仅交给 SDK，不能放 argv、容器环境、Task、事件、客户端 repr 或 checkpoint。源码及工具输出可进入模型上下文；操作者通过一次运行授权批准这一数据流。

HTTP 401/403/429/5xx、连接／请求超时和 SDK 协议异常区分 reason_code，归入 `MODEL_ERROR` 或 `PROTOCOL_ERROR` 并终止；不假造回复，不在原 Run 重发未知收费请求。已获得补丁保存为未验候选。SDK 一次 turn 与底层请求数分别记录；没有观测底层次数就写 null，不根据 hooks 数量编造 HTTP 计数。

### 2.3 确定性测试，直接用上游能力

```python
from agents.testing import ScriptedModel, ModelStep, assistant_message, function_call

model = ScriptedModel([
    ModelStep(output=[function_call(
        "edit_file",
        {"path": "src/stats.cpp", "old": "int best = 0;", "new": "int best = values[0];"},
        call_id="fixture_call_1",
    )]),
    ModelStep(output=[assistant_message("Candidate ready for independent verification.")]),
])
# 测试将 model 传入同一个 Agent / Runner；结束后 model.assert_complete()。
```

字符串替换仅为接口示意，实际 fixture 脚本必须匹配源码并覆盖空输入条件，不能将示意替换当作已验证修复。官方测试 API 位于[agents.testing](https://openai.github.io/openai-agents-python/testing/)。

CLI 的 `--engine fake --mock-script FILE` 用一个薄加载器构造 ScriptedModel。文件顶层为 `{"version":1,"steps":[...]}`；每步对应公开 `ModelStep` 的 `output`，元素采用 SDK 原生 Responses output item JSON（message/function_call 等），用 SDK 的公开类型完成校验。只允许 output 与可选合成 usage，不支持从文件加载 Python callback、模块名或表达式。加载器必须把message/function_call分别通过公开`ResponseOutputMessage.model_validate`／`ResponseFunctionToolCall.model_validate`转成SDK对象，usage构造公开`agents.Usage`；不能直接把原始dict传给ModelStep。测试需要reasoning项时同样使用该锁定SDK的公开类型。需要异常／延迟时在 pytest 中直接用 `ModelStep.error`／`responder`，不把故障 DSL 暴露给用户。没有自有 Turn 转译协议。

耗尽脚本且 Runner 仍要请求时必须报错；不能自动返回“完成”。测试结束 `assert_complete()` 防止预期步骤根本没走到。fake usage 为合成值，标 synthetic；它只证明 Harness 路径，不证明模型会修复。

## 3. 执行语义与公开回调

以下是所有权与时序说明，**不是让开发者照写新的循环**：

1. Harness 已完成基线 F2P 失败、P2P 通过。构造冻结 instructions、缺陷说明、文件范围、目录摘要、commit/image 标识、失败证据 preview 和预算。
2. 调用 `Runner.run`。`call_model_input_filter` 在模型请求前检查上下文大小、deadline 和剩余额度；返回未被手裁的原生 `ModelInputData`。P2 在这个完整边界提交 checkpoint。
3. `on_llm_start` 在任何模型调用前持久化 turn 开始、累积预算；P2 先提交 `segment_open=true`。步骤计数不能在失败后退还。
4. SDK 获得原生 `ModelResponse`，`on_llm_end` 记录原生 output／usage。只检查需要的领域不变量：function call ID 非空且在本响应唯一、单响应≤8个调用、实际工具名存在、未出现明确 incomplete 的执行项。
5. **整批准入**该响应的 function calls：剩余额度不足时不准入任何一项，产生 `TOOL_BUDGET` 并退出 Runner；已有候选仍可验证。准入后一次性扣额度，SDK 再校验参数并串行分派；参数错误或中途失败不退款。不伪造 NOT_EXECUTED 结果来补齐截断对话。
6. 工具入口实施路径／资源规则，记录自己的结果；SDK 负责把结果关联回 function_call_output。工具日志／事件必须先保存，再让后续阶段使用其结论。
7. SDK 下一轮进入 input filter 时，前轮工具已结束且容器清理已确认。P2 可提交新的安全 checkpoint并关闭 segment。Runner 正常返回 final_output 时记 `MODEL_FINISHED`，由 Harness 冻结候选并独立验证。

`on_llm_end` 中存在 text 与 calls 时不提前结束；最终结束由 SDK Loop 决定。明确标为 incomplete 的消息／function call 不能当正常结束。未知可执行类型直接协议错误，不用未来工具扩展作默认 fallback；纯 continuation data 保持原样但不解释成权限。

SDK可能在公开on_llm_end之前拒绝不合法call ID等响应；此时记录公开可取得的错误与模型turn消耗，不承诺一定获取完整原生output，更不能伪造一个完整响应。

静态注册的回调只负责上述领域逻辑，不读写 SDK 私有 `_state`、不覆盖 SDK 的核心 step、action parser 或工具分派器。P1-04 的集成门槛须实际证明公开 hooks 的执行次序符合“先准入再副作用”。不符合时先修订边界，不维护 fork。

## 4. 六个受控工具

六个注册回调必须是`async def`，即使内部复用短小有界的同步helper也明确包在该async回调中。固定SDK对普通同步`def`工具会使用`asyncio.to_thread`；不能直接装饰同步写文件／启动进程函数，再误以为取消await会终止后台线程。不得依赖线程取消来保证工具已停止。

工具函数的类型注解和 SDK `function_tool` 产生 schema，复用现有工具数据逻辑；不分别维护另一份模型 JSON schema。参数上限／文件集合是领域校验。使用 `failure_error_function=None`，wrapper 仅捕获明确的 PolicyError／可纠正输入错误返回 JSON；磁盘、Git、Docker、事件存储等基础设施异常必须传播。[官方工具错误处理](https://openai.github.io/openai-agents-python/tools/)。

| 工具 | 参数 | 返回主体 | 行为 |
|---|---|---|---|
| `list_directory` | `path: str="."` | 子项 `{name,type}`、truncated，最多200项 | 只展示结构化可读集合；`.`仅在这里与search表示源码根 |
| `read_file` | `path`, `start_line:int=1`, `max_lines:int=200` | path、行范围、text、total_lines、truncated | 最多400行／64KiB；readable内UTF-8文本 |
| `search_code` | `query`, `path:str="."` | `{path,line,text}`列表、truncated | 字面量区分大小写；query≤1KiB，最多100匹配／64KiB；无自建搜索索引 |
| `edit_file` | `path`, `old`, `new` | path、before_sha256、after_sha256 | old非空且只匹配一次；只修改editable已有文件 |
| `run_command` | `name: "reproduce" 或 "verify"` | check报告与CommandResult列表 | 当前源码干净快照自查；配置编译后跑固定F2P或F2P+P2P |
| `run_shell` | `command`, `cwd: "/src" 或 "/build"="/src"`, `timeout_seconds:int或null` | CommandResult | Docker内`/bin/sh -lc`，command≤16KiB；源码只读，无持久终端 |

`run_command("reproduce")` 在修复期间检查目标是否通过，不要求再次匹配旧失败签名；两种自查均标 `evaluation_role=agent_check`，不改变最终验收。一次工具内每个 configure/build/test 命令都有各自 timeout，并共享 Agent 剩余时间，不获得无限内部执行。

run_shell 的限制来自容器、只读快照、无网络、资源及生命周期；不维护可绕过的命令名黑名单。`cd/export`、临时 build 不跨调用保留，命令中需要连贯的配置／编译／调试就放在同次 Shell 中。Shell 不能修改 repair 工作树；源码变更经受控 edit_file。没有 PTY、后台服务 API 或宿主 Shell 求值。

list/read/search/edit 不执行仓库代码。只读容器快照不与 host 工作树共享写入者。edit_file 用 bytes→UTF-8→精确替换→bytes，保持未改字节、CRLF、尾换行和 mode；文件最大1MiB，old/new各≤1MiB。不能用宽泛正则或猜测匹配自动修复工具错误。

成功返回例如：

```json
{"ok":true,"data":{"path":"src/stats.cpp","before_sha256":"...","after_sha256":"..."}}
```

可纠正领域错误例如：

```json
{"ok":false,"error":{"code":"EDIT_MATCH_NOT_UNIQUE","message":"old matched 2 locations; provide a longer exact context"}}
```

稳定代码包括 INVALID_ARGUMENT、PATH_NOT_READABLE、PATH_NOT_EDITABLE、FILE_TOO_LARGE、NOT_UTF8、EDIT_MATCH_NOT_FOUND、EDIT_MATCH_NOT_UNIQUE。SDK schema 解析失败或未知工具按 PROTOCOL_ERROR 终止；只有已准入批次不退款，准入前拒绝不扣工具额度，已开始的模型turn仍消耗；不把每个 SDK 异常硬改成工具反馈。执行器返回非零退出是 CommandResult，不自动作为 Python 异常。磁盘满／daemon失联／事件写入失败是 ERROR，不能返回空搜索结果。

## 5. CommandResult 与原始证据

```python
@dataclass(frozen=True)
class CommandResult:
    command_id: str
    argv: tuple[str, ...]
    cwd: str
    status: Literal["exited", "timed_out", "oom_killed", "cancelled",
                    "infra_error", "output_limit"]
    exit_code: int | None
    started_at: str
    finished_at: str
    duration_ms: int
    stdout: str
    stderr: str
    stdout_bytes: int
    stderr_bytes: int
    truncated: bool
    stdout_log: EvidenceRef | None
    stderr_log: EvidenceRef | None
    container_id: str | None
    cleanup_confirmed: bool
    error_code: str | None
```

command_id 是[状态文档](STATE_AND_RECOVERY.md)定义的 operation_id，只关联命令日志和事件，不存在单独的 operation 调度表。工具内部多条命令有不同 command_id，与同一个 tool_call_id 关联。时间为UTC RFC3339，duration使用monotonic；finished_at表示本地观察结束，不证明外部进程消失。

`status=exited,exit_code=8` 是正常结束的测试失败，不能混同 timed_out 的清理退出码137。只有 Docker 明确 OOM 证据才标 oom_killed；启动或观察失联标 infra_error，exit_code可为null。

原始 stdout/stderr 直接写到 `logs/<command_id>/stdout.bin` 和 `stderr.bin`，保持 bytes。保存上限为两流合计4MiB，达到上限即终止所属容器并标 output_limit；不能等进程退出后才截断。两个 EvidenceRef 指向完整保存部分；即使无输出也创建空文件，创建失败时才为null。**删除旧版 Base64分块JSONL协议**；不宣称可还原两文件描述符的全局写入顺序。

模型 preview 合计最多64KiB，首尾取样并显式说明省略，UTF-8 replacement解码；preview截断不等于原始证据不全。实际达到原始上限、日志缺失或清理不确认时，不能用于 ACCEPTED 或原始失败签名证明。签名分别在原始 stdout/stderr 匹配，任一完整流命中即可，不跨流拼接。已知密钥的过滤与证据保留要求见[安全文档](EXECUTION_AND_SECURITY.md)。

同次evaluation的configure/build结束时容器仍可能运行，中间CommandResult.cleanup_confirmed=false是历史观察；最终evaluation清理事件负责最终证明。不回写历史CommandResult为true，也不要求每条中间命令都提前删除容器。

## 6. 预算、错误和结束

时间基准：Run创建时固定UTC deadline，正常运行用monotonic剩余时间。默认wall900秒，其中verification reserve240秒、清理余量10秒；准备／基线也不能消费最后的验证与清理预留。所有SDK调用受Agent阶段剩余时间限制，工具单命令取Task上限／请求上限／阶段剩余时间最小值。

SDK使用async网络接口与原生timeout；总Run的取消用标准`asyncio.timeout`。现有同步容器／Git helper可以在工具回调内串行调用，但每次自身必须有执行deadline和有界清理；不能把无限同步等待移到thread再误以为取消future就杀死线程。无worker池、无单请求子进程、无自制JSON RPC。

正常超时可停止本地等待，不能证明模型服务端取消或不会计费。SDK取消等待自身cleanup，若远端／daemon失联，固定10秒只限制本项目的清理尝试，不保证分布式资源在十秒内消失；结果需明确未知且禁止成功。SIGKILL只能在P2恢复时处理，不能由 finally 保证。

| 预算／观测 | 语义 |
|---|---|
| max_steps／steps_used | SDK model turns；开始即计入额度，不是TCP/HTTP次数；P2累计不重置 |
| max_tool_calls | 整批已准入function calls；一次超过余额整批拒绝，已准入后不退款 |
| max_output_tokens | 通过SDK max_tokens映射到选定Responses输出上限；不是全Run token总预算 |
| http_attempts | 真实可观测时记录，否则null；没有HTTP的fake/verify路径为0 |
| usage | 开启preserve_raw_usage，以raw_usage字段存在性记录input/output/total；缺失null，fake明确synthetic |

最后一个允许turn中的工具仍可以执行；max_steps只阻止下一模型turn。SDK原生MaxTurnsExceeded映射STEP_BUDGET；模型/工具准入在真实副作用前执行，这一点必须集成测试。所有模型重试设置明确关闭；不配置服务端conversation或自动previous_response_id，避免重试/会话锁语义进入MVP。若提供商或SDK未暴露内部请求，不能把steps_used伪装成实际HTTP数。

| agent_stop_reason | 候选处理／最终任务规则 |
|---|---|
| MODEL_FINISHED | 有有效非空补丁→独立验证；无补丁→REJECTED/NO_PATCH |
| STEP_BUDGET、TOOL_BUDGET、AGENT_DEADLINE、CONTEXT_LIMIT | 有有效补丁且还有验证预留→验证；无补丁→BUDGET_EXHAUSTED |
| MODEL_ERROR、PROTOCOL_ERROR | ERROR；保留未验候选与实际错误，不继续调用模型 |
| USER_CANCELLED | 清理并CANCELLED；不在用户取消后继续验收 |

通过验收时可以 outcome=ACCEPTED、agent_stop_reason=STEP_BUDGET；两个维度不得混用。验证自身的资源或证据问题按VERIFICATION产生INCONCLUSIVE／ERROR。

P2增加操作者参数 `--pause-after-step N`（run/resume），N为整个Run累计turn数且严格小于max_steps。在后续input_filter观察到已完成N轮、工具与清理完毕时，先提交安全checkpoint，设置INTERRUPTED/outcome=null，再抛本项目的HarnessPause离开Runner；不发送下一模型请求。正常最终回复不强行暂停而是进入验收。此受控暂停与SIGINT/CANCELLED不同；恢复不读任意pending RunState，详见状态文档。

## 7. 原生上下文、存储与长期演进

SDK可能将缺失usage归一化为0用于内部累积，本项目不能把这个默认值写成已知消耗。必须开启`preserve_raw_usage=True`；逐响应按raw_usage的实际字段提取，缺失保持null，已知部分可单独累计并记录未知turn数。

模型上下文采用 SDK 原生 Responses input/output Items，包括 message、function_call、function_call_output、reasoning 及 SDK 要求的不透明continuation。可见文本与opaque数据不能挤进固定四role消息表。以SDK公开JSON序列化保存私有原生附件，领域事件只记引用、身份和usage；不维护一份本项目对话表加一份SDK Session数据库。

`store=False`下仍须保留上游返回的continuation item，使用`response_include=["reasoning.encrypted_content"]`请求不透明续接内容；不解码、不推断、更不向报告展示隐藏推理。支持的SDK自动处理应直接复用，不能仅拼接文本丢失items。[Responses迁移](https://developers.openai.com/api/docs/guides/migrate-to-responses)、[推理上下文](https://developers.openai.com/api/docs/guides/reasoning)。

请求中instructions加native input的规范JSON总大小上限256KiB；单次完成的原生模型output序列化后最大1MiB。后者是在可信API客户端完成解析后的本地限制，不声称防御恶意API的无限HTTP响应。入口超限停止CONTEXT_LIMIT／PROTOCOL_ERROR，保留候选按规则处理。

**MVP不手动丢弃旧轮、不自制摘要器、不再询问模型总结、不自动换模型。** 字节上限并不保证一定小于具体模型token window，服务端context错误仍需明确记录。若真实任务频繁触发此门槛，再由P4-04测试上游compaction或上下文管理：额外模型调用要计预算，原始证据仍保留，续接项结构不能丢失。

恢复只使用本项目保存的安全下一次输入边界，不能把SDK通用RunState反序列化能力宣传为任意SIGKILL安全续跑。升级SDK或更改工具schema后，旧checkpoint默认不可继续；可以保留旧环境复核，或用新的verify-patch Run重新验收保存的候选。
