# Agent Runtime 与工具数据契约

状态：**目标 Phase 1；恢复扩展属于 Phase 2。** 本文是模型消息、工具接口、CommandResult、上下文和预算执行语义的权威定义。Task 默认值见[TASK_FORMAT](TASK_FORMAT.md)，Run 状态／事件身份见[STATE_AND_RECOVERY](STATE_AND_RECOVERY.md)，验收结果见[VERIFICATION](VERIFICATION.md)。以下 Python 片段用于接口说明，不代表本轮交付了运行时代码。

## 1. 责任与最小接口

模型提出下一步行动；Agent Loop 管理对话；Harness 掌握权限、时间、持久化和验收。模型不能自行改变预算、调用验收器内部接口、选择容器挂载或声明 `ACCEPTED`。模型的最终文字只是 `MODEL_FINISHED`。

保留现有 `models.py` 中的一层 `Model` Protocol。一个真实适配器和一个确定性 `MockModel` 足够，不建立 provider registry、通用路由器、基类树或插件发现机制。

```python
@dataclass(frozen=True)
class ToolCall:
    provider_call_id: str          # 仅用于模型协议关联，不作为路径或权限
    name: str
    arguments: dict[str, object]   # 由适配器解析 JSON；由工具入口校验具体 schema

@dataclass(frozen=True)
class Usage:
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None

@dataclass(frozen=True)
class Turn:
    text: str | None
    calls: tuple[ToolCall, ...]
    usage: Usage
    provider_response_id: str | None
    finish_reason: str | None

class Model(Protocol):
    def complete(
        self, messages: list[dict], tools: list[dict], *,
        timeout_seconds: float, max_output_tokens: int
    ) -> Turn: ...
```

使用 JSON-compatible dict 承载 wire messages 即可，避免自研第二套消息继承体系。以下四种 role 是唯一持久化形式：

```jsonl
{"role":"system","content":"冻结的 Harness 指令"}
{"role":"user","content":"缺陷描述、允许编辑文件和原始失败证据"}
{"role":"assistant","content":null,"tool_calls":[{"id":"call_7","type":"function","function":{"name":"read_file","arguments":"{\"path\":\"src/stats.cpp\"}"}}]}
{"role":"tool","tool_call_id":"call_7","content":"{\"ok\":true,\"data\":{\"path\":\"src/stats.cpp\",\"text\":\"...\"}}"}
```

每个 assistant 的 calls 和对应 tool results 组成不可拆开的“工具组”。单响应最多 8 个调用，严格顺序执行；没有并发修改。每个组内 provider_call_id 必须非空且唯一；Harness 另外生成 `step_id`、`tool_call_id`，见状态文档，不能把模型给出的 ID 拼入文件路径。一个请求同时含 text 与 calls 时先处理 calls，text 只作为轨迹，不算完成。空 text 且无 calls、不可解析参数 JSON、重复 ID、超量 calls 为 `PROTOCOL_ERROR`。

### 1.1 真实适配器

`OpenAICompatibleModel` 使用官方 `openai` Python SDK 的同步 Chat Completions 工具调用接口，复用连接、JSON/HTTP 处理和错误类型。SDK 设置 `max_retries=0`、明确 timeout；不要在外面再包一层重试。官方 SDK 的默认重试可配置，因此必须显式关闭，见[官方 SDK](https://github.com/openai/openai-python#retries)。

MVP 只认证一个实际端点＋模型组合的兼容性，要求支持 `messages/tools`、工具响应 ID、非流式返回及输出上限参数。默认使用 `max_completion_tokens`；若选定兼容服务只接受其它参数，先在单适配器中作有文档的选择，不写自动探测／多级 fallback。模型名称由操作者选择，不把会过时的模型名写入 Task 或代码常量。

模型连接选项：model_name、api_base、key_env。API key 由宿主读取一次并只交给 SDK；不进 Task、事件、Docker、异常 repr。URL 限 HTTPS、无 userinfo、fragment 和 query；报告记录去敏的 origin/path。返回 401/403/429/5xx、网络 timeout 与 schema 错误分别记 reason，按 `MODEL_ERROR` 终止；没有假造成功回复，也不在本 Run 自动重试收费请求。

不保存模型隐藏推理。保存 API 提供的可见消息、工具调用和 usage；usage 缺失时写 null，不能写零冒充未消耗。真实模型试跑必须由用户显式选择并同意费用／源码出境；Mock 不具备模型修复能力证明。

### 1.2 MockModel

继续复用已有脚本方式，目标脚本顶层 `{"version":1,"turns":[...]}`，每项与 Turn 的可见字段对应；`arguments` 为 JSON object。脚本严格按调用次数返回，耗尽时抛 `MockScriptExhausted`，不得偷偷返回“完成”。测试也可直接构造 `MockModel(turns)`。

只提供少量行为脚本：读文件→精确替换→自查→完成、错误补丁→完成、无补丁完成。timeout 和崩溃应在实际执行边界注入，不模拟第三方库的每个内部方法。Mock usage 写零并标记 synthetic，报告显示 `model.kind=mock`。

## 2. 最小运行循环

进入 REPAIRING 前已有固定 Task、工作树、基线 F2P 失败和 P2P 通过的证据。初始消息包括：角色与工具规则、问题描述、允许改动文件、目录摘要、实际 commit/image 标识、原始失败的有界输出、剩余预算。run_shell 可直接读取当前快照的全部测试与源码；MVP 不提供隐藏测试或仓库内机密性边界。

```text
构造固定前缀与初始上下文
while 尚有 Agent 时间、step 和 tool 预算:
    裁剪旧的完整工具组，使请求不超过上下文上限
    先计入模型尝试，再调用 Model.complete
    保存完整可见响应；Phase 2 必须 durable 后才执行其工具
    若没有 calls 且有最终文字：stop = MODEL_FINISHED，退出循环
    按响应顺序处理每个 call:
        分配 Harness ID；先扣一次 tool attempt
        入口校验参数和权限；执行并记录结构化结果
        将一个 tool result 追加到对话
        若工具预算或Agent时间耗尽：剩余 call 记 NOT_EXECUTED，不执行
    完成组边界；Phase 2 才提交 checkpoint
根据 stop reason 冻结候选 diff
由 Harness 决定是否进入独立 VERIFYING
```

`NOT_EXECUTED` 结果用于补全最后一个 assistant 组，记录 reason 为 budget/cancelled；未实际尝试的不扣工具预算。max_steps 只阻止下一次模型请求，不阻止最后一次已取得响应中的工具；这些工具仍只检查工具数与Agent时间。组完成后才判断STEP_BUDGET。若硬错误使事务不能继续写入，则不用伪造完整对话，交由恢复规则处理。没有每轮“先问模型是否完成”的额外请求。

认证的Chat Completions端点对finish_reason采用下列映射：`stop`＋非空text＋无calls才是MODEL_FINISHED；`tool_calls`必须具有完整合法calls；`length`为MODEL_ERROR/MODEL_OUTPUT_LIMIT，`content_filter`为MODEL_ERROR/MODEL_CONTENT_FILTER，其它未知或与内容不一致的值为PROTOCOL_ERROR。不能将被截断的回复记为正常结束。Mock脚本也给出正常的`stop`或`tool_calls`，不依赖缺省值猜测。

## 3. 工具接口

工具名、参数和返回 schema 由 `tools.py` 一个静态列表定义；Model Adapter 仅序列化这份定义，pytest 用同一入口执行。未声明参数拒绝，不给模型额外的 kwargs 通道。路径规则见[执行文档](EXECUTION_AND_SECURITY.md)。

| 工具 | 参数 | 返回主体 | 行为 |
|---|---|---|---|
| `list_directory` | `path: str="."` | 直接子项 `{name,type}`，最多 200 项，`truncated` | 展示结构化可读集合，不遍历宿主；唯一允许 `.` 表示源码根 |
| `read_file` | `path`, `start_line:int=1`, `max_lines:int=200` | path、1-based 起止行、text、total_lines、truncated | 最多 400 行且最多 64 KiB；只读 files.readable 内 UTF-8 文本 |
| `search_code` | `query`, `path:str="."` | `{path,line,text}` 列表与 truncated | 字面量、区分大小写，最多 100 匹配／64 KiB；query 最多 1 KiB；路径按可读集合过滤 |
| `edit_file` | `path`, `old`, `new` | path、before_sha256、after_sha256 | old 非空且恰好匹配一次；UTF-8 文件；new 可为空但不能删除整个文件对象；只允许 files.editable |
| `run_command` | `name: "reproduce"\|"verify"` | check 报告、CommandResult 列表 | 当前源码的干净快照自查；configure/build 后运行对应固定集合；不改变最终验收结论 |
| `run_shell` | `command`, `cwd: "/src"\|"/build"="/src"`, `timeout_seconds:int?` | CommandResult | 命令作为单参数传入容器 `/bin/sh -lc`；最多 16 KiB；自带只读源码和独立临时构建空间 |

`run_command("reproduce")` 在修复过程中用 F2P 检查当前是否已经通过，不再要求看到原始失败签名；`run_command("verify")` 自查 F2P+P2P。二者都不是独立验收器，产物标 `evaluation_role=agent_check`。预算按内部每条 command 和整个 Agent 剩余时间执行，不能借一次工具调用获得无限命令时间。

`run_shell` 的“受限”来自容器权限、无网络、只读快照、资源和生命周期，不来自可绕过的命令名黑名单。它不能修改 repair 工作树；源码修改统一经 edit_file。`cd/export` 和 `/build` 内容不跨工具调用保留；需要编译后调试时在同一次 shell 中写 `cmake ... && cmake --build ... && ...`。没有持久终端、交互输入、PTY 或后台服务接口。

list/read/search/edit 是宿主受控数据操作，不执行仓库内容。没有恶意执行进程能写宿主工作树，容器只看独立只读快照，因此无需在每个内部函数堆叠相同路径防护。`edit_file` 从 bytes 解码为 UTF-8、精确替换并以 UTF-8 写回，不进行 universal-newline 归一化；必须保持未改字节、mode。文件最大 1 MiB；old/new 各不得超过该限制；0 次／多次匹配分别给出明确错误，不猜测目标段落。

### 3.1 工具响应

成功的数据读取与可观察执行结果：

```json
{"ok":true,"data":{"path":"src/stats.cpp","before_sha256":"...","after_sha256":"..."}}
```

模型可自行修正的工具错误：

```json
{"ok":false,"error":{"code":"EDIT_MATCH_NOT_UNIQUE","message":"old matched 2 locations; provide a longer exact context"}}
```

允许反馈的错误包括 `INVALID_ARGUMENT`、`PATH_NOT_READABLE`、`PATH_NOT_EDITABLE`、`FILE_TOO_LARGE`、`NOT_UTF8`、`EDIT_MATCH_NOT_FOUND`、`EDIT_MATCH_NOT_UNIQUE`、`UNKNOWN_TOOL`。这些也是失败的已计数工具尝试，不能无限重试。

Git 损坏、磁盘满、Docker daemon 不可达、事件写入失败是 Harness 基础设施错误，向任务边界传播；不能把它们包装成 `search found 0` 或让模型反复尝试。最外层允许一次捕获未预期异常，保留 traceback 和原始 cause 后产生 `ERROR`，而不是全链路重复包装。

## 4. CommandResult

以下对象是执行观察，不能直接当“修复成功”布尔值：

```python
@dataclass(frozen=True)
class CommandResult:
    command_id: str                 # 该条命令的 operation_id
    argv: tuple[str, ...]           # 容器内实际 argv；无宿主密钥
    cwd: str
    status: Literal["exited", "timed_out", "oom_killed", "cancelled",
                    "infra_error", "output_limit"]
    exit_code: int | None           # 只有观察到正常退出才具有退出码语义
    started_at: str                # UTC RFC 3339；包含启动尝试
    finished_at: str               # 本地观察结束，不等于远端已停止
    duration_ms: int
    stdout: str                     # 模型可见 preview，UTF-8 replacement 解码
    stderr: str
    stdout_bytes: int               # 实际捕获／已观测字节数
    stderr_bytes: int
    truncated: bool
    log: EvidenceRef | None         # ARCHITECTURE 定义；未能创建日志时为 null
    container_id: str | None
    cleanup_confirmed: bool
    error_code: str | None
```

`run_command` 的多个内部 command 分配不同 operation_id；其 Tool Call ID 相同，通过事件关联。`exit_code=8,status=exited` 是一次正常执行的失败测试；`status=timed_out` 不是普通非零退出，即使底层清理也得到 137。没有足够 Docker 证据时不得仅从 137 宣称 OOM。`infra_error` 记录启动或观察失败；Runtime 应终止而非假定进程没启动。

每条命令累计观察到 stdout+stderr 字节数 `>= 4 * 1024 * 1024` 即终止所属容器并返回 `output_limit`，原始数据最多保留 4 MiB；恰好达到也不算完整证据。模型 preview 总共最多 64 KiB，首尾各取一半并标记省略；preview 截断不意味着原始证据丢失。原始日志达到硬上限则证据不完整，不能用于 ACCEPTED 或原始失败签名匹配。不能等子进程退出后才检查大小；现有 process.py 通过流式读取实现。

原始日志为 UTF-8 JSONL，每行严格为 `{"seq":1,"stream":"stdout","data_b64":"..."}`：seq 从 1 递增，stream 只能 stdout/stderr，data_b64 是标准 Base64 编码的非空原始块。这是宿主观察顺序，不承诺两个文件描述符在程序内部的真实写入顺序。失败签名分别还原两个流后匹配；4 MiB 限制针对解码后的输出 bytes，Base64／JSON 开销计入 Run 产物总限额。正常命令即使无输出也保存空日志文件；启动前已发生 I/O 故障时 log 可为 null，不能凭缺失日志宣称验证完成。

`cleanup_confirmed` 表示生成该 CommandResult 时的观察：同一次 evaluation 中间的 configure/build 结束时容器仍在运行，该值为 false 是正常情况。容器最终停止结果由 evaluation 的 cleanup 与 `cleanup_finished` 事件记录；最终验收检查该最终清理证据，不要求每条中间 CommandResult 都为 true，不改写已经持久化的历史结果。

## 5. 时间、步数与终止

在 Run 创建时设总 deadline。正常运行用 `time.monotonic()` 控制剩余时长，UTC deadline 用于报告／P2 恢复。固定清理余量 10 秒；Agent 最晚停止时刻是总 deadline 减 verification reserve 再减清理余量。PREPARING／基线也不能挤占最终验证和清理预留；若它们用尽前段时间，停止并产生对应的无法确定／环境结果，而非硬启动模型。

每次开始命令前，timeout 取：Task 单命令上限、工具请求上限（存在时）、阶段剩余时长的最小值。每次模型请求同理。执行器必须限制总请求耗时，而非仅单次 socket read。真实适配器固定采用**一次请求一个可终止的宿主子进程**：用当前Python解释器的私有`models` worker入口调用同步SDK，经stdin/stdout交换有界JSON，父进程复用process.py的流式I/O和总deadline；模型key只作为该子进程的最小环境变量，不放argv或输入日志。stdout只容许一个Turn响应，最多1MiB；stderr脱敏保存。超时先terminate进程组、最多等待2秒，再kill并限时回收，计入固定清理余量。回收无法确认则ERROR并停止。worker 启动即按请求剩余时长设置 Linux `signal.setitimer` 硬计时器，使用 SIGALRM 默认终止动作，防止父进程被 SIGKILL 后留下无限等待的本地请求；该计时器同样不能取消服务端计费。子进程串行且只有一个，不建worker池、通用RPC或调度器。Mock在主进程返回确定性Turn，无需启动子进程。

这个边界可以终止本地请求进程，不能证明服务端已取消或未收费；失败后不在本Run重发。SDK自己的网络timeout仍设置为剩余时间，作为内部连接诊断。采用子进程而不只取消future的依据是[HTTPX超时语义](https://www.python-httpx.org/advanced/timeouts/)与[Python线程任务取消限制](https://docs.python.org/3.12/library/concurrent.futures.html)。

上面 10 秒是清理尝试预算，不是“Docker 失联也能保证十秒删除”。用尽且无法确认进程消失时，记录 cleanup 未确认并停止，禁止继续验收成功。

`max_steps` 与 API 尝试数一一对应，不另设一个意义相同的 max_model_calls。单响应内按顺序消费 `max_tool_calls`，余额不足时不执行剩余工具。Phase 2 恢复不退款；重做工具产生新 attempt 并继续消费；请求结果未知不能计零。

| 停止原因 | 候选处理 |
|---|---|
| `MODEL_FINISHED` | 有有效非空 diff → 独立验证；没有 diff → REJECTED/NO_PATCH |
| `STEP_BUDGET`、`TOOL_BUDGET`、`AGENT_DEADLINE` | 有有效 diff 且有预留时间 → 验证；无 diff → BUDGET_EXHAUSTED |
| `CONTEXT_LIMIT` | 有有效 diff → 验证；无 diff → BUDGET_EXHAUSTED/CONTEXT_LIMIT |
| `MODEL_ERROR`、`PROTOCOL_ERROR` | ERROR，保留未验候选，不自称成功 |
| `USER_CANCELLED` | 清理并 CANCELLED；不在用户取消后继续模型或验证 |

最终 outcome 和 agent_stop_reason 分开：例如预算已耗尽但已有补丁通过独立验证，可以 `outcome=ACCEPTED, agent_stop_reason=STEP_BUDGET`。验证自身超时、证据不全按验证文档处理，不能为了输出一种失败状态而丢失真实原因。

## 6. 上下文策略

MVP 的硬请求上限是规范序列化消息 256 KiB；单回复协议体上限 1 MiB。它们是字节上限，不是模型 token window 的证明。固定前缀包括系统规则、原始 Task 概要、允许文件和复现证据；保留最新完整工具组。超出时按时间删除最旧的完整 assistant+tools 组，插入程序生成的“已省略 N 个旧组，请重新读取文件”标识。不能留下孤立 tool message，不用第二个模型做摘要。

模型正文在 SDK 返回之前可能已经被客户端解析；服务端必须是所配置的可信 API，不能据事后大小检查声称抵御恶意 HTTP 服务的无限响应。超限返回 protocol error 并停止。固定前缀＋最新组仍超限时 `CONTEXT_LIMIT`，不截掉安全规则和任务定义。不自动换模型、不模糊压缩代码、不开向量数据库；先用实际任务评估这种简单策略，再决定 Phase 4 是否需要 token-aware 管理。

## 7. 持久化边界

Phase 1：记录模型请求／响应、工具输入／结果、每条命令、预算、候选与验收事件；SQLite 是审计事件来源，JSONL 是导出，尚不能恢复。秘密值过滤在进入日志处执行，不靠发布前搜索补救。

Phase 2：请求／工具 intent 在副作用前 durable，模型响应 durable 后才执行工具；最后工具结果与完整组、post manifest／patch／transcript 引用和 next_action 同事务提交，之后才建立 checkpoint。完整组已提交而 checkpoint 未提交时，核对后补交，不重做工具。只有真正未完成的一组才按恢复文档在预算允许时回滚重做；不再次请求模型。最终文字与停止决定同事务保存，恢复后直接冻结候选；任何未知模型响应均不得盲重试。这些规则只在 Phase 2 实现，不给 Phase 1 加未使用的操作调度框架。
