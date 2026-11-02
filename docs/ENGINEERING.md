# 工程指南

ReproPatch 将 C++ 修复与验证组织为可追踪的 Run：固定任务和环境，接收外部补丁或运行可选 Agent，冻结候选，在独立环境验收，并保存状态、预算和原始证据。日常使用从[零密钥演示](DEMO.md)开始；模块与 SDK 职责见[架构](ARCHITECTURE.md)。

## 运行契约与配置

### 准备环境

Python 3.12+ 与 Git 在宿主运行，CMake、编译器、CTest 和第三方代码在 Docker 内运行。目标环境为 Linux amd64；WSL2 使用 Linux Docker 引擎，源码和 Run 目录放在发行版文件系统中。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements/agent.txt '.[agent,semantic]'
docker build -t repropatch-cpp:0.1 -f docker/Dockerfile docker
repropatch doctor --image repropatch-cpp:0.1 --json
```

核心安装支持 Task 检查、补丁验收和既有证据查询。`agent` extra 安装公开 SDK，离线 `fake` 引擎同样使用该依赖；`semantic` extra 安装 Tree-sitter C++。SDK 依赖固定在 [pyproject.toml](../pyproject.toml) 与 [requirements/agent.txt](../requirements/agent.txt)。

实现：[cli.py](../src/repropatch/cli.py)、[models.py](../src/repropatch/models.py)、[docker/Dockerfile](../docker/Dockerfile)。验证：[可选 SDK 导入](../tests/test_sdk_optional.py)、[CLI 环境检查](../tests/test_engineering_cli.py)。

### Task

Task v2 描述本地仓库、完整 commit OID、镜像 ID/digest、可读和可编辑文件、受保护输入、固定命令、F2P/P2P 与预算。准备仓库和镜像后，示例 Task 可由实际身份生成：

```bash
python scripts/init_example.py --write-task .repropatch/tasks/negative-maximum.yaml --image repropatch-cpp:0.1
repropatch validate-task .repropatch/tasks/negative-maximum.yaml
```

真实仓库由操作者准备本地 checkout 和构建镜像，再按 [Task 契约](../specs/2026-10-19.2/docs/TASK_FORMAT.md)声明文件与测试。F2P 标识预期从失败变为通过的测试，P2P 标识应持续通过的回归测试；二者共同构成 Task 声明的验收集合。构建文件与测试受保护，修复对象为显式授权的已有 C/C++ 源码。

实现：[task.py](../src/repropatch/task.py)、[初始化脚本](../scripts/init_example.py)、[workspace.py](../src/repropatch/workspace.py)。验证：[Task 解析](../tests/test_task.py)、[文件与补丁策略](../tests/test_source_integrity.py)。

### CLI 选项

| 选项 | 配置作用 | 实现与验证 |
| --- | --- | --- |
| `--engine fake --mock-script FILE` | 以公开 SDK ScriptedModel 执行原生 JSON 脚本，模型请求为本地合成记录 | [models.py](../src/repropatch/models.py) · [SDK 脚本测试](../tests/test_sdk_contract.py) |
| `--engine agents-sdk` 或 `sdk` | 使用显式构造的公开 Responses 模型 | [models.py](../src/repropatch/models.py) · [模型 CLI](../tests/test_models_cli.py) |
| `--model NAME --allow-paid-model` | 固定模型并显式授权真实模型请求 | [cli.py](../src/repropatch/cli.py) · [模型 CLI](../tests/test_models_cli.py) |
| `--api-base URL --key-env NAME` | 指定服务地址和凭据环境变量；默认 OpenAI API 与 `OPENAI_API_KEY` | [models.py](../src/repropatch/models.py) · [模型 CLI](../tests/test_models_cli.py) |
| `--use-env-proxy` | 显式使用宿主代理与 TLS 环境配置；默认客户端独立配置 | [models.py](../src/repropatch/models.py) · [传输测试](../tests/test_sdk_contract.py) |
| `--tool-mode legacy` | 默认六工具，受控文件操作和新环境自检 | [tools.py](../src/repropatch/tools.py) · [工具测试](../tests/test_agent_runtime.py) |
| `--tool-mode shell-only` | 单一 Bash，持久修复容器与跨命令构建目录 | [repair_sandbox.py](../src/repropatch/repair_sandbox.py) · [Shell 测试](../tests/test_shell_runtime.py) |
| `--semantic-state` | 为 legacy 增加结构查询与证据状态，并选用支持压缩的上下文策略 | [semantic_state.py](../src/repropatch/semantic_state.py)、[harness.py](../src/repropatch/harness.py) · [结构状态测试](../tests/test_semantic_state.py) |
| `--compiler-cache` | 为修复自检启用本 Run 的独占 ccache；独立验收保持冷构建 | [verification.py](../src/repropatch/verification.py) · [真实缓存隔离测试](../tests/test_docker_integration.py) |
| `--pause-after-step N` | 在累计第 N 个模型步骤之后的完整输入边界暂停 | [agent_runtime.py](../src/repropatch/agent_runtime.py) · [Checkpoint 测试](../tests/test_checkpoints.py) |
| `--candidate-only` | 冻结并核验候选往返后交付外部 Oracle，结局为 `INCONCLUSIVE / EXTERNAL_ORACLE_REQUIRED` | [harness.py](../src/repropatch/harness.py) · [候选资格测试](../tests/test_candidate_eligibility.py) |
| `--output-root PATH` | 指定 run/verify-patch 的证据根目录；查询与恢复使用该路径作为 `--root` | [harness.py](../src/repropatch/harness.py)、[task.py](../src/repropatch/task.py) · [路径测试](../tests/test_harness.py) |

Task 的 `budget` 配置累计模型步骤、工具调用、单请求与命令超时、总 wall 期限、验证预留和输出 Token 上限。`max_steps: null`、`max_tool_calls: null` 开放累计次数；期限、单次限额和持续计量继续生效。预算通过 Task 冻结，恢复沿用原值。

`ContextPolicy`、`context_meter` 和 `intermediate_checks` 是 Harness 的程序化配置，实验脚本据此固定协议；公共 `run` CLI 的直接配置以表中选项为准。

实现：[task.py](../src/repropatch/task.py)、[harness.py](../src/repropatch/harness.py)、[context.py](../src/repropatch/context.py)。验证：[开放预算](../tests/test_unlimited_harness_budget.py)、[结构状态累计计量](../tests/test_semantic_state.py)、[预算预留](../tests/test_agent_runtime.py)。

## 工具、权限与沙箱

### 工具模式

Legacy 文件工具按冻结的 readable 集合读取和搜索，返回 `editable` 提示；编辑仅在 editable 集合中精确替换唯一文本。`run_command reproduce` 在全新容器配置、构建并运行 F2P，`verify` 运行 F2P/P2P。`run_shell` 提供一次性只读源码 Shell，`/build` 随容器释放。

Shell-only 在 `/src` 展示完整 prepared 源码快照，通过逐文件可写挂载支持授权文件原位编辑。修复容器和 `/build` 在同一修复阶段跨命令保留；每条命令结束后冻结容器、检查派生进程、核验源码与 Git mode。恢复重建容器时，构建目录与缓存从空环境开始。

实现：[tools.py](../src/repropatch/tools.py)、[harness.py](../src/repropatch/harness.py)、[repair_sandbox.py](../src/repropatch/repair_sandbox.py)。验证：[授权文件工具](../tests/test_workspace_tools.py)、[Shell 运行](../tests/test_shell_runtime.py)、[持久沙箱](../tests/test_repair_sandbox.py)、[Shell 恢复](../tests/test_shell_docker.py)。

每个模型响应先核对原生调用身份与注册工具，再整批扣减预算，最多八次调用、串行执行。工具反馈携带剩余请求、工具和时间额度；普通权限或参数错误作为可见反馈返回，基础设施异常进入运行失败处理。

实现：[agent_runtime.py](../src/repropatch/agent_runtime.py)。验证：[批次准入与串行执行](../tests/test_sdk_contract.py)、[错误与预算反馈](../tests/test_agent_runtime.py)。

### 执行约束

| 资源 | Task 默认值或固定约束 | 实现与验证 |
| --- | --- | --- |
| CPU、内存、PID | 默认 2 CPU、2048 MiB、128 PID，可由 Task 配置 | [task.py](../src/repropatch/task.py)、[sandbox.py](../src/repropatch/sandbox.py) · [沙箱测试](../tests/test_process_sandbox.py) |
| 构建与临时空间 | `/build` 默认 1024 MiB tmpfs；`/tmp` 64 MiB，执行权限由 `tmp_executable` 配置，默认关闭 | [sandbox.py](../src/repropatch/sandbox.py) · [真实 Shell](../tests/test_shell_docker.py) |
| 运行权限 | UID/GID 65534、断网、只读根文件系统、无 capabilities、no-new-privileges | [sandbox.py](../src/repropatch/sandbox.py) · [Docker 集成](../tests/test_docker_integration.py) |
| 源码与候选 | 单源文件 16 MiB、整树 256 MiB、可编辑文本 1 MiB、patch 8 MiB | [workspace.py](../src/repropatch/workspace.py) · [源码完整性](../tests/test_source_integrity.py) |
| 输出与审计 | 每命令双流原始输出合计 4 MiB、预览合计 64 KiB、Run 非源码审计 256 MiB | [process.py](../src/repropatch/process.py)、[artifacts.py](../src/repropatch/artifacts.py) · [进程与输出](../tests/test_process_sandbox.py) |

镜像在运行前准备；Task 固定 image ID/digest，准备阶段核验实际身份，后续阶段使用同一 ID。容器 profile 在创建后再次核查。超时、取消、输出达限与阶段结束都执行整容器删除和 inspect 确认；资源归属由 Run 目录、容器 ID/标签、Git 管理身份和文件锁共同记录。

`retain` 配置 `none/on_failure/always` 管理可释放的修复工作区与诊断快照；暂停保留恢复必需的源码和证据。最终结局同时反映资源清理是否确认。

实现：[sandbox.py](../src/repropatch/sandbox.py)、[resources.py](../src/repropatch/resources.py)、[harness.py](../src/repropatch/harness.py)。验证：[生命周期与清理](../tests/test_runtime_lifecycle.py)、[执行身份](../tests/test_exec_identity.py)、[真实 Docker](../tests/test_docker_integration.py)。信任关系见[安全模型](../SECURITY.md)。

## 运行状态与恢复

正常修复经历准备、基线复现、修复、独立验收与收尾，`state` 记录阶段，`outcome/reason_code` 记录终态判断。SQLite 事务同时提交状态、累计预算与事件；Checkpoint 引用提交后成为恢复输入。

实现：[events.py](../src/repropatch/events.py)、[recovery.py](../src/repropatch/recovery.py)。验证：[状态事务](../tests/test_recovery.py)、[Checkpoint](../tests/test_checkpoints.py)。

### 暂停与续跑

对已生成的示例 Task，可用本地 SDK 脚本展示可检查的暂停点：

```bash
repropatch run .repropatch/tasks/negative-maximum.yaml --engine fake --mock-script examples/models/fix-negative-maximum.json --output-root .repropatch/runs --pause-after-step 3 --json
```

该脚本先读取、搜索和编辑源码，随后在下一完整输入边界提交 Checkpoint 并暂停。使用 JSON 中的 Run ID 查询和恢复：

```bash
repropatch inspect RUN_ID --root .repropatch/runs --json
repropatch diagnose RUN_ID --root .repropatch/runs --json
repropatch resume RUN_ID --root .repropatch/runs --json
```

`resume --pause-after-step N` 使用累计的绝对步骤数；N 大于已用步骤，并在有限 `max_steps` 之前。恢复核验实现、Python/SDK、Task、镜像、指令、工具 schema 与完整证据，从 base + patch 重建源码，沿用已核验基线、原 wall 期限和剩余额度。暂停等待计入原期限。

实现：[recovery.py](../src/repropatch/recovery.py)、[示例脚本](../examples/models/fix-negative-maximum.json)。验证：[原生输入与剩余脚本](../tests/test_resume.py)、[真实容器暂停和恢复](../tests/test_docker_integration.py)。

### 故障判断

| 诊断原因 | 运行事实与处理依据 | 对应验证 |
| --- | --- | --- |
| `MODEL_RESULT_UNKNOWN` | 请求已开始，结果事实未闭合；保存诊断和已有候选 | [进程故障恢复](../tests/test_resume.py) |
| `OPEN_AGENT_SEGMENT` | 工具轮次或输入边界尚未完整提交；保存明确失败身份 | [进程故障恢复](../tests/test_resume.py) |
| `CHECKPOINT_CORRUPT` | 已提交引用、哈希或源码重建核验失败；保留原始证据供调查 | [Checkpoint 与源码分歧](../tests/test_resume.py) |
| `WORKSPACE_DIVERGED` | 已有修复树与 Checkpoint 源码分歧；现有文件保留为诊断 | [源码分歧](../tests/test_resume.py) |
| `INPUT_CHANGED` | 实现、运行依赖、Task、镜像或工具身份发生变化；按冻结配置核对环境 | [SDK 身份变化](../tests/test_resume.py) |
| `OWNED_RESOURCE_UNCONFIRMED` | 自有容器归属或清理结果仍有未确认项；先检查 Docker 和资源记录 | [清理故障](../tests/test_resume.py)、[真实容器故障](../tests/test_docker_integration.py) |

实现：[recovery.py](../src/repropatch/recovery.py)。故障门禁见[check_recovery_gate.py](../scripts/check_recovery_gate.py)，按安全恢复、明确失败和控制器拒绝分组输出。恢复以最新已提交的闭合 Checkpoint 为依据，原始诊断、候选和事件前缀可用于故障定位。

## 上下文与结构证据

默认 CLI 使用 legacy 上下文策略，原生输入有 256 KiB 传输限额。`--semantic-state` 选择带完整轮次压缩的策略：当前默认上下文窗口为 128000 Token、触发阈值 80000、目标 32000，传输限额 2 MiB。Token 估算以实际 Usage 为锚点，并对明文增量及不透明状态分别归因；估计值与供应商原始用量各自保存。

上下文策略的窗口、阈值和输出预留通过 `ContextPolicy` 配置，Task 的单次输出 Token 限额通过 `budget.max_output_tokens` 配置。压缩在完整工具轮次边界进行，摘要请求计入总步骤，保留固定任务合同、近期轮次和证据索引。压缩耗时和后续工具执行均写入记录。

实现：[context.py](../src/repropatch/context.py)、[agent_runtime.py](../src/repropatch/agent_runtime.py)、[harness.py](../src/repropatch/harness.py)。验证：[Usage 归因](../tests/test_context_results.py)、[压缩边界](../tests/test_context_compaction.py)、[结构状态下的压缩与续跑](../tests/test_semantic_state.py)。

Legacy 配合 `--semantic-state` 提供第七个工具 `query_code`：

| 查询 | 返回内容 |
| --- | --- |
| `definitions` | 授权 C++ 源码中的定义与声明，附位置、符号、作用域和源码 SHA |
| `references` | 标记为 `syntactic` 的语法引用与调用关系 |
| `includes` | 包含关系与对应源码位置 |
| `state` | 已有修改、可见检查、近期观察与累计结构检索指标 |
| `evidence` | 按已登记 tool ID 或 `baseline` 读取先前可见记录，并核对证据 SHA |

查询按 `path` 收窄范围，使用 `next_offset` 分页，同时报告解析错误与截断。源码变化使相关索引失效。Checkpoint 保存可序列化证据状态；解析器和 AST 缓存恢复后按需重建。语法关系帮助定位实现，实际编译与测试为候选验收提供依据。

实现：[semantic_state.py](../src/repropatch/semantic_state.py)、[tools.py](../src/repropatch/tools.py)。验证：[授权结构查询与缓存失效](../tests/test_semantic_state.py)。补充说明见[结构证据状态](SEMANTIC_STATE.md)。

## 观测与优化

### 查询与产物

将 `RUN_ID` 替换为输出中的运行身份，`PATH` 替换为包含各 Run 目录的根路径：

```bash
repropatch inspect RUN_ID --root PATH --json
repropatch diagnose RUN_ID --root PATH --json
repropatch replay RUN_ID --root PATH --mode trace --json
mkdir -p exports
repropatch export-trace RUN_ID --root PATH --output exports/trace.jsonl
repropatch report RUN_ID --root PATH --format json
```

| 入口 | 作用与运行影响 | 实现与验证 |
| --- | --- | --- |
| `inspect` | 只读查询阶段、结局、事件前缀、证据与派生产物完整性 | [reports.py](../src/repropatch/reports.py) · [报告查询](../tests/test_events_reports.py) |
| `diagnose` | 只读分析阶段、证据、用量和恢复条件；退出码反映证据完整性 | [diagnostics.py](../src/repropatch/diagnostics.py)、[cli.py](../src/repropatch/cli.py) · [诊断 CLI](../tests/test_engineering_cli.py) |
| `replay --mode trace` | 只读生成按事件序号排序的轨迹和证据引用 | [trace.py](../src/repropatch/trace.py) · [只读轨迹](../tests/test_trace.py) |
| `export-trace` | 从一致性快照输出 JSONL，发布到 stdout 或 Run 外的新文件 | [trace.py](../src/repropatch/trace.py) · [轨迹导出](../tests/test_trace.py) |
| `report` | 持锁从已提交事实重建 report、JSONL 与导出索引 | [reports.py](../src/repropatch/reports.py) · [重建与导出故障](../tests/test_events_reports.py) |
| `resume` | 持锁核验 Checkpoint 和资源后继续同一 Run，产生后续事件 | [recovery.py](../src/repropatch/recovery.py) · [恢复](../tests/test_resume.py) |

`diagnose` 返回 0 表示证据完整，3 表示证据核验或读取问题，参数错误返回 2。修复结局通过 JSON 的 `outcome/reason_code` 阅读。`inspect` 的 `errors/evidence_errors` 展示查询发现的问题。`export-trace` 的目标使用新文件，父目录提前准备。

Run 保存 `task.resolved.json`、`events.sqlite3`、候选补丁与源码清单、原始 stdout/stderr、JUnit、SDK 原生附件和 Checkpoint。`report.json`、`report.md`、`events.jsonl` 与 `run.json` 是派生产物。EvidenceRef 以路径、大小和 SHA-256 关联证据；终态与导出错误分别保存，报告重建使用已提交事实。

实现：[artifacts.py](../src/repropatch/artifacts.py)、[reports.py](../src/repropatch/reports.py)、[events.py](../src/repropatch/events.py)。验证：[派生产物重建](../tests/test_events_reports.py)、[证据引用](../tests/test_trace.py)。

### 可验证指标

| 指标 | 测量依据 | 实现与验证 |
| --- | --- | --- |
| 修复质量 | 独立验收的 outcome/reason_code、声明的 F2P/P2P 实际执行结果、测试身份和候选 SHA | [verification.py](../src/repropatch/verification.py) · [判定测试](../tests/test_verification.py) |
| 请求与用量 | 累计模型步骤、准入工具数、HTTP 尝试、原始 Usage、known_tokens 与 unknown_turns；ScriptedModel 标记 synthetic | [agent_runtime.py](../src/repropatch/agent_runtime.py) · [原始用量](../tests/test_sdk_contract.py) |
| 执行耗时 | 各 configure/build/CTest 命令的 monotonic 耗时、自检次数、首个编辑事件与验收时间 | [process.py](../src/repropatch/process.py)、[events.py](../src/repropatch/events.py) · [命令事件](../tests/test_events_reports.py) |
| 构建复用 | 修复自检 ccache 统计，与独立验收的冷构建结果分别记录 | [verification.py](../src/repropatch/verification.py) · [Docker 缓存隔离](../tests/test_docker_integration.py) |
| 上下文 | 请求字节、估算与实际 input Token、压缩前后规模、摘要耗时、压缩后工具执行 | [context.py](../src/repropatch/context.py) · [上下文结果](../tests/test_context_results.py)、[压缩](../tests/test_context_compaction.py) |
| 结构检索 | queries_total、parse_count、cache_hits、indexed_bytes_total、index_seconds_total、parse_seconds_total | [semantic_state.py](../src/repropatch/semantic_state.py) · [跨恢复累计计量](../tests/test_semantic_state.py) |
| 恢复与资源 | 恢复尝试、故障边界、预算连续性、源码一致性、容器清理确认 | [recovery.py](../src/repropatch/recovery.py)、[resources.py](../src/repropatch/resources.py) · [恢复](../tests/test_resume.py)、[生命周期](../tests/test_runtime_lifecycle.py) |

优化先按事件和命令耗时定位主要成本，再固定 Task、prepared commit、镜像、模型配置和预算做配对验证。构建占比高时比较 `--compiler-cache` 或持久 Shell，记录冷/热条件、自检次数与独立验收；上下文增长快时检查工具输出、压缩规模与 Usage 归因；检索重复时检查缓存命中和解析耗时。

每次比较保留首次尝试、失败与未知用量，按多个仓库和重复样本报告验收通过、耗时及请求差异。工程演示用于验证控制面流程；真实缺陷实验为质量和效率判断提供样本，协议与原始数据见[评测索引](../benchmarks/README.md)。

## 验证入口

本地测试环境在宿主执行受信任 C++ fixture，使用 `cmake==4.4.4` 与 C++ 工具链，和 CI 的 `sdk-contract` 保持一致。日常修复与演示的 CMake、编译器和 CTest 由 Docker 镜像提供。

```bash
python -m pip install -c requirements/agent.txt -e '.[agent,semantic,dev]' cmake==4.4.4
ruff check src tests scripts
ruff format --check src tests scripts
python -m pytest -m 'not docker and not sdk' -q
python -m pytest -m 'sdk and not docker' -q
python scripts/check_recovery_gate.py --output .repropatch/recovery-evidence
python scripts/check_docker_gate.py --image repropatch-cpp:0.1
python scripts/check_engineering_gate.py --image repropatch-cpp:0.1 --output .repropatch/engineering-evidence
```

门禁输出使用新目录，保存安装身份、命令摘要、原始记录与运行产物。工程门禁默认使用当前安装环境，支持 editable 安装；真实 Docker 门禁使用已准备的编译镜像。

### 交付包验收

安装上述测试依赖并准备 Docker 镜像后，构建和安装 wheel，再执行强制安装包来源核验：

```bash
python -m build
python -m pip install --force-reinstall --no-deps dist/repropatch-0.4.0-py3-none-any.whl
python scripts/check_engineering_gate.py --image repropatch-cpp:0.1 --output .repropatch/engineering-wheel-evidence --require-installed-wheel

python -m venv .repropatch/core-env
.repropatch/core-env/bin/python -m pip install dist/repropatch-0.4.0-py3-none-any.whl
.repropatch/core-env/bin/python scripts/check_core_distribution.py \
  --wheel dist/repropatch-0.4.0-py3-none-any.whl \
  --image repropatch-cpp:0.1 --output .repropatch/core-wheel-evidence
```

`python -m build` 生成 sdist 和 wheel，`pip install` 将 wheel 安装到当前 Python 环境，`--require-installed-wheel` 检查安装元数据中的 wheel 来源。门禁通过 `python -I -m repropatch` 调用已安装的 CLI，执行三个场景并保存证据。

| 验证层 | 检查对象 | 入口 |
| --- | --- | --- |
| Core | Task、源码、事件、报告、进程与证据 | [tests](../tests)、[CI](../.github/workflows/ci.yml) |
| SDK | ScriptedModel、原生 Items、hooks、串行工具、预算与暂停恢复 | [SDK 契约](../tests/test_sdk_contract.py)、[恢复](../tests/test_resume.py) |
| 恢复故障门禁 | 真实控制进程故障后的事务前缀、安全边界与明确失败 | [check_recovery_gate.py](../scripts/check_recovery_gate.py) |
| Docker 门禁 | 实际容器约束、C++ 构建、CTest、补丁往返与清理 | [check_docker_gate.py](../scripts/check_docker_gate.py)、[Docker 集成](../tests/test_docker_integration.py) |
| 工程门禁 | 核验当前安装环境，在真实 Docker 执行三场景，核对 inspect/diagnose/replay/export-trace 对原 Run 的只读性；`--require-installed-wheel` 强制核验 wheel 来源 | [check_engineering_gate.py](../scripts/check_engineering_gate.py)、[CLI 合同](../tests/test_engineering_cli.py) |
| 核心分发门禁 | 同一 wheel 的 core-only 安装，源码目录外调用正确与错误补丁；核对基线、独立冷验收、清理和只读查询 | [check_core_distribution.py](../scripts/check_core_distribution.py) |

CI 的 `docker-integration` 先执行 Docker 门禁，再构建和安装 wheel，随后验收三场景与独立 core-only 正反例，并上传 `engineering-evidence` 与 `dist/`。日常 CI 保持 Core、SDK 和 Docker 三个作业；历史 mini/Codex 原生上下文由手动参数 `native_context=true` 启用。完整测试结果、耗时与场景结局见[测试报告](TEST_REPORT.md)，交付标准见[工程验收](ACCEPTANCE.md)。
