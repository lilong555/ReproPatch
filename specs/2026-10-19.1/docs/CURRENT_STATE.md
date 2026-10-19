# 既有实现、历史证据与迁移基线

> 本文只记录 2026-10-19 在本轮任务中只读检查到的已有内容。读取了目录、Git 元数据、源码、文档和已保存测试产物；没有复跑旧测试、构建容器、调用模型或改动旧项目。后续目标行为见 [SPEC.md](../SPEC.md)，不要把目标规格倒写为已实现事实。

## 1. 检查范围与仓库身份

本轮开始时，任务工作目录 `/workspace/scratch/baceb7d71452` 没有可见项目代码，也不是 Git 仓库。随后在已有工作区中找到并只读检查了：

```text
/workspace/scratch/e6a8be3c34cc/repropatch
```

该来源路径属于本次环境记录，不是开源项目运行时依赖，文档不通过相对链接假装它会随 Spec 一起发布。

| 项目 | 观察结果 |
|---|---|
| 分支 | `main` |
| HEAD | `611e43edd1fc9c7ba07e28ebfd33415cfbb0b65a` |
| 提交主题 | `Implement reproducible C++ repair harness MVP with verified fixture evidence` |
| Git remote | `git remote -v` 无输出 |
| 包版本 | `0.1.0` |
| 未提交文件 | `src/repropatch/harness.py`、`src/repropatch/sandbox.py`、`tests/test_process_sandbox.py` |

未提交修改的内容是保留容器操作的原始异常，并在清理也失败时附加异常说明；测试文件增加对应回归检查。本轮没有改写、撤销、提交这些修改，也没有用历史测试输出证明这些修改已通过。

本轮新建的 `repropatch/` 交付目录是一套规格和示例文档，**没有把旧源码复制进来，也没有实施目标 Runtime**。目标版本安排为 Phase 1 `0.2.0`、Phase 2 `0.3.0`、Phase 3 `0.4.0`；只有通过公开稳定版门槛才考虑 `1.0.0`。这些是规划版本，不是发布声明。

## 2. 观察到的已有工程

以下文件名均相对上面的旧项目根目录；它们是审计来源，不是本 Spec 包内的链接。

| 文件或目录 | 实际职责 |
|---|---|
| `pyproject.toml` | setuptools 打包，Python `>=3.12`，CLI 入口，依赖和 Ruff/pytest 配置 |
| `src/repropatch/cli.py` | argparse CLI：`run`、`doctor`、`validate-task` |
| `src/repropatch/task.py` | dataclass Task、YAML v1 解析、外部输入校验 |
| `src/repropatch/models.py` | `Model` Protocol、预写动作的 `MockModel`、手写 urllib 的 OpenAI-compatible 适配 |
| `src/repropatch/harness.py` | 复现、串行 Agent Loop、独立验证、报告生成 |
| `src/repropatch/tools.py` | 读取、字面量搜索、精确替换、固定命令自查四个工具 |
| `src/repropatch/workspace.py` | detached Worktree、导出快照、允许文件补丁复制和 diff 核对 |
| `src/repropatch/sandbox.py` | Docker CLI 生命周期和限制参数 |
| `src/repropatch/process.py` | 宿主工具的输出限制、超时、进程组清理、最小环境变量 |
| `src/repropatch/events.py` | 单表 SQLite 审计日志和 JSONL 顺序双写 |
| `examples/cpp-bugs/` | 自有 `negative-maximum` C++20 缺陷 fixture |
| `tests/` | Python 测试、受信任 fixture 的宿主编译测试、显式启用的 Docker 测试 |
| `.github/workflows/ci.yml` | Python/C++ job 和 Docker job 的配置文件 |
| `docs/evidence/` | 历史 XML/日志、fixture 报告、补丁、源码快照、Git bundle |

运行依赖只有 `PyYAML>=6.0.2,<7`。CLI、模型协议数据结构、SQLite、文件和进程操作使用标准库。开发依赖为 pytest、pytest-cov、Ruff、build。不存在 Typer、Pydantic、uv、服务框架或 C++ 独立执行器。

已有 C++20 代码是用于验证流程的目标 fixture，不是 Harness 的底层执行器。新计划保留 Python 控制面，只有真实需求满足 Phase 4 门槛时才考虑 C++ 执行组件。

## 3. 已有对外契约

### 3.1 CLI 与 YAML v1

已存在的命令为：

```text
repropatch --version
repropatch doctor [--image IMAGE]
repropatch validate-task TASK
repropatch run TASK [--output DIR] [--image IMAGE]
    [--model mock|openai-compatible] [--script FILE]
    [--model-name NAME] [--api-base URL] [--key-env NAME]
    [--allow-paid-model]
```

旧退出码为通过 `0`、运行未通过/运行错误 `1`、输入或前置依赖错误 `2`。没有 `inspect`、`report`、`resume`、`replay`、`eval`。目标 CLI 是 [CLI.md](CLI.md) 定义的后续契约，不应拿目标命令要求旧包现在就支持。

YAML v1 要求 `version/id/repository/prompt/editable_paths/commands`，可选 `revision/failure_exit_code/failure_contains/timeout_seconds/max_steps`。仓库仅支持本地路径；`revision` 默认 `HEAD`，运行时解析完整 commit；镜像由 CLI 参数传入，默认 `repropatch-cpp:0.1`。

`commands` 固定为 configure/build/reproduce/verify 四组 argv，可执行程序只允许 `cmake` 和 `ctest`。`editable_paths` 是精确 C/C++ 文件列表，没有通配符；只支持已有被跟踪文件，不支持增加、删除、改名和修改权限。

新 [TASK_FORMAT.md](TASK_FORMAT.md) 使用 YAML v2，不重复使用 v1 版本号重新解释字段。后续以显式转换示例/任务生成器帮助迁移，不建立任意旧格式兼容层。

### 3.2 Agent 能力

已有 `Model.complete(messages, tools) -> Turn`，`Turn` 带文本及工具请求。每轮最多 8 个工具调用，默认最多 24 轮，单请求上限 2048 completion tokens 和 60 秒。完整消息历史一直累积，到约 1 MB 请求体上限时失败；没有目标规格中的确定性上下文裁剪。

工具只有 `read_file`、`search_code`、`edit_file`、`run_command`。`run_command` 仅选择已审核的 reproduce/verify，并重新配置、构建和测试；没有目录查看和任意容器 shell 工具。工具参数策略错误反馈给模型，模型或基础设施错误终止 Run。

模型产生非空的无工具文本时，Harness 进入候选处理，而不是直接宣布修复成功。Fake/Mock 行动脚本是固定序列，不能用其完成修复推算真实模型能力。

### 3.3 执行与验证

已有独立 detached Worktree、仅被跟踪普通文件的源码快照，以及干净 validation Worktree。模型不能直接调用宿主 shell/Git/Docker；编译与测试的生产路径只使用 Docker，不自动回退宿主执行。

Docker 设计包含只读 `/src`、只读根文件系统、非 root 用户、断网、清空 capabilities、no-new-privileges、CPU/内存/PID 限制与 `/build` tmpfs。首次解析镜像 image ID，后续评估要求相同 ID。API key 不传入容器。

原始基线必须 configure/build 成功、目标 reproduce 返回声明的非零退出码并包含输出标记；超时和截断不算复现。Agent 结束后将允许文件复制到原 commit 的新 Worktree，核对完整 diff 一致，重新 configure/build/reproduce/verify，全成功才记录 `passed`。

这是一条已存在代码路径，但 Docker 层实际成功运行尚无证据。它还缺少目标规格的 P2P 基线、固定测试身份/非空集合/跳过判定、明确预算保留及统一结局分类。

### 3.4 状态与审计

旧状态字符串包括 `running`、`baseline_setup_failed`、`not_reproduced`、`budget_exhausted`、`no_patch`、`passed`、`failed`、`interrupted`、`error`、`internal_error`。这些是分散赋值的结果字段，不是带转移校验和事务的 Task State Machine。

已有 SQLite `events(seq,timestamp,run_id,kind,payload)`。每条事件先 commit SQLite，再 append/flush JSONL，正常结束时可以一致，但崩溃时不保证尾部一致。没有操作 intent/result、Checkpoint、Resume、Trace Replay 或 Execution Replay；不能因为已经有数据库文件而声称具备可靠恢复。

## 4. 历史测试证据与未验证边界

主要审计来源是旧项目的 `docs/TEST_REPORT.md`、`docs/evidence/final-tests.log`、`docs/evidence/final-tests.xml`、`docs/evidence/docker-gate.log`、`docs/evidence/doctor.json` 和 `docs/evidence/trusted-fixture/report.json`。

| 事项 | 观察到的历史产物 | 可以得出的结论 |
|---|---|---|
| Python/fixture 测试 | 日志记录 `74 passed, 3 skipped` | 该份历史测试运行的结果；不是本轮重新运行结果 |
| 真实 Docker 测试 | 默认有 3 项 skipped；显式 gate 记录 1 项 failed | Docker 不可用，隔离验收尚未完成 |
| Docker 前置检查 | `docker:null, daemon:false, image:false` | 该次记录环境没有可用 Docker |
| 自有 fixture 修复 | `isolated:false`、`TrustedLocalSandbox`、`MockModel` | 已保存宿主受信任编译/独立 Worktree 的运行证据 |
| 真实模型服务 | 文档明确未调用，测试以模拟 HTTP/Fake 完成 | 没有真实 API 兼容性或修复能力验收证据 |
| 远程 CI | 仅有 workflow 配置，无 remote、无成功运行链接 | 不能宣称 GitHub Actions 已通过 |
| 当前未提交补强 | 源码及新增测试可读 | 旧证据不足以证明它们已测试通过 |

自有 fixture 的历史 Run ID 是 `negative-maximum-ead30b400a42`，基线 commit 为 `bdbeddbe6e9bf18cdd161d9698f2cb5dc66e6ad6`。报告记录原始目标测试返回 8，含 `expected -3, got 0`；正确补丁将初值 `0` 改为 `samples.front()` 后，独立 Worktree 的复现测试及 4 个 CTest 用例通过。测试目录还存在将初值改为 `-1`、要求独立验证拒绝的真实编译用例。

上述是真实保存的历史产物及其内容核查，不代表本轮证明了完整执行链的真实性，更不构成模型修复成功率、容器安全审计或性能基准。历史覆盖率不作为新阶段的质量目标；新版应以关键行为和隔离门槛实际通过为准。

## 5. 保留与迁移表

| 领域 | 保留的基础 | 目标改变 | 阶段与权威规格 |
|---|---|---|---|
| CLI/数据结构 | argparse、dataclass、小型 Model Protocol | 扩展必要命令与稳定错误/结局，不引入框架 | Phase 1，[ARCHITECTURE.md](ARCHITECTURE.md)、[CLI.md](CLI.md) |
| 任务输入 | YAML 单次边界校验、精确允许文件 | v2 完整 commit/image、显式资源/测试/路径契约 | Phase 1，[TASK_FORMAT.md](TASK_FORMAT.md) |
| 模型适配 | 一个协议、一个 Fake、一个真实提供商路径 | 官方成熟 SDK、显式关闭自动重试、准确预算/响应错误 | Phase 1，[AGENT_RUNTIME.md](AGENT_RUNTIME.md) |
| 工具 | 精确编辑、受控文件读取、固定自查 | 目录查看、受限容器 shell、稳定结果和截断契约 | Phase 1，[AGENT_RUNTIME.md](AGENT_RUNTIME.md) |
| 工作区 | detached Worktree、隔离源码快照 | 显式所有权、允许/保护集合、可验证清理 | Phase 1，[EXECUTION_AND_SECURITY.md](EXECUTION_AND_SECURITY.md) |
| 验收 | 原 commit 新 Worktree、无 Agent 构建缓存 | P2P 基线、每测试身份/结果证据、标准 Outcome | Phase 1，[VERIFICATION.md](VERIFICATION.md) |
| 审计存储 | SQLite 和保留失败产物 | SQLite 单一事件权威、JSONL 派生导出 | Phase 1，[STATE_AND_RECOVERY.md](STATE_AND_RECOVERY.md) |
| 状态恢复 | 不把旧日志冒充 Checkpoint | 事务状态、操作核对、边界 Checkpoint 和 Resume | Phase 2，[STATE_AND_RECOVERY.md](STATE_AND_RECOVERY.md) |
| 测试 | 自有 fixture、确定性 Fake、Docker 显式 gate | 对真实边界和关键故障窗口补最少必要测试 | 分阶段，[TESTING_AND_EVALUATION.md](TESTING_AND_EVALUATION.md) |
| 评测 | 手写 fixture 只检验流程 | 固定真实 C++ 任务、同模型/预算、Baseline 对照 | Phase 3，[TESTING_AND_EVALUATION.md](TESTING_AND_EVALUATION.md) |
| C++ 执行器 | 当前不存在 | 只有性能/进程语义需求有证据时开展 | Phase 4，[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) |

不存在“先全量重写，再迁回已有能力”的要求。编码时先确认旧工作树仍是这份基线，保留未提交修复，围绕目标行为分段修改；不可因为生成了新 Spec 就覆盖用户的代码或清空 Git 状态。

## 6. 实现者必须处理的已知差距

### 6.1 真实隔离与可复现性

旧 Docker 安全参数有源码和模拟测试，但尚未在真实 daemon 验收。应在受支持 Linux 主机运行真实 Docker gate，记录镜像 ID、权限、断网、只读、超时清理和端到端结果；缺失时明确阻塞目标 MVP 完成，而不是把宿主 fixture 结果替代进去。

旧 Dockerfile 以 `ubuntu:24.04` 和未锁版本的 apt 包构建。固定一次运行内 image ID 不等于他人在未来重建相同镜像；目标任务要锁定并说明镜像可获取条件。

本地 Git 配置是旧系统的受信任边界。关闭 hooks/fsmonitor 不会自动禁用所有 clean/smudge filters；不能直接声称接受任意敌对 `.git` 目录是安全的。目标边界和不支持情形以执行安全文档为准。

### 6.2 验证语义

旧系统只在基线运行目标失败测试，没有独立执行 P2P 集合。旧验证主要看命令退出码，`--no-tests=error` 是示例习惯而非强制契约；没有完整的 skip/缺失/额外测试处理。新版必须补齐，才能对“回归保持通过”给出可检查证据。

旧 allowlist 只检查被允许文件是 C/C++ 扩展名。操作者若把 `tests/foo.cpp` 列为 editable，解析器不会额外拒绝。因此旧文档中的“不能修改测试”需要限定为正确填写允许列表时的行为。新版要求测试/构建保护集合和编辑集合明确互斥。

### 6.3 预算、诊断和持久化

旧预算主要是模型轮数、每条命令超时和请求大小，没有完整 wall deadline、独立验证保留时间与工具总调用数。改造时避免同时保留两套相互冲突的配置来源。

旧 `search_code` 跳过所有 `ReproPatchError`，可能把基础设施问题掩盖为无搜索结果；应只跳过明确允许的非文本/超限文件，其他错误传播。旧 `safe_path` 的宽泛异常捕获也应收窄到边界预期异常。

旧 `Harness.run` 对未预期异常只给简略类型信息，缺少可核查的本地 traceback。新版应在 Run 边界保留受控诊断，避免泄露密钥，同时不隐藏开发缺陷。现有未提交的“清理失败不遮蔽原异常”修改应保留并验证。

SQLite 和 JSONL 双写问题在 Phase 1 就可通过“仅 SQLite 写入、按需导出”小幅修正，不必等到整个恢复系统完成。状态事务、未知付费请求处理和 Checkpoint 则按 Phase 2 单独实现。

## 7. 使用本审计的规则

开始每项开发任务前，以 [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) 确定目标、前置依赖和验收方式，再核对相关旧源码；不要从本文件推断尚未实现的新接口已经存在。

以后新增真实测试证据，记录测试时间、完整版本/commit、工作树修改、命令和原始产物位置。更新实现状态时应写清“哪个版本、哪个环境实际通过了什么”，不能把 0.1.0 的历史 fixture 结果继承成 0.2.0 或稳定版验收结果。
