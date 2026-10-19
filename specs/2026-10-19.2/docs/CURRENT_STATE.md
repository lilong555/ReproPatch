# 既有实现、历史证据与迁移基线

> 本文记录 2026-10-19 的两次审计：首次规格编写时的历史快照，以及本次生态复用审计时的最新复核。当前状态以本次复核为准。两次审计均读取目录、Git 元数据、源码、文档和已保存测试产物；本次没有复跑产品测试、构建容器、调用模型或改动原项目。后续目标行为见 [SPEC.md](../SPEC.md)，不要把目标规格倒写为已实现事实。

## 1. 检查范围与仓库身份

首次规格任务开始时，任务工作目录 `/workspace/scratch/baceb7d71452` 没有可见项目代码，也不是 Git 仓库。随后在已有工作区中找到并只读检查了：

```text
/workspace/scratch/e6a8be3c34cc/repropatch
```

该来源路径属于本次环境记录，不是开源项目运行时依赖，文档不通过相对链接假装它会随 Spec 一起发布。

| 项目 | 首次规格审计的历史快照 | 本次复核的当前状态 |
|---|---|---|
| 分支 | `main` | `work/spec-p1-01` |
| HEAD | `611e43edd1fc9c7ba07e28ebfd33415cfbb0b65a` | `ab6e4c4bbc7fea4778a993257fef1245e26543ed` |
| 提交主题 | `Implement reproducible C++ repair harness MVP with verified fixture evidence` | `Preserve cleanup failure causes and stage Spec P1-01 with blocked Docker evidence` |
| Git remote | `git remote -v` 无输出 | 仍无输出 |
| 包版本 / Task | `0.1.0` / v1 | 仍为 `0.1.0` / v1 |
| 工作树 | 三个未提交修改文件 | `git status --short` 无输出，工作树干净 |

首次审计看到的三个修改文件是 `src/repropatch/harness.py`、`src/repropatch/sandbox.py`、`tests/test_process_sandbox.py`，内容为保留容器操作原始异常、清理失败附加说明及两项对应回归检查。它们已被当前 HEAD 收录，不能继续把这些修改写成待保留的 dirty 工作。接入前的精确 diff 和来源仍保存在原项目 `docs/evidence/p1-01/preexisting-cleanup.diff` 与 `intake.json`。

当前提交还加入 `SPEC.md` 入口、原字节归档的 `specs/2026-10-19.1/`、`docs/P1-01.md`、更新后的 README/测试说明与 P1-01 证据，并增加真实 Docker 错误补丁拒绝测试。原归档中的 CURRENT_STATE 是历史快照，本次修订不改写该归档。P1-01 的本地核验已有记录，但真实 Docker gate 仍阻塞；P1-02 尚未开始，模型 SDK、Task v2、事件单写与恢复协议尚未实现。

本次交付的 `repropatch/` 目录仍是一套规格和示例文档，**没有把旧源码复制进来，也没有实施目标 Runtime**。后续阶段和目标版本以 [SPEC.md](../SPEC.md) 与 [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) 为准，规划版本不是发布声明。

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
| `SPEC.md`、`specs/2026-10-19.1/` | 当前规格入口与上轮完整规格的只读历史归档，不代表目标功能已实现 |
| `docs/P1-01.md`、`docs/evidence/p1-01/` | 规格接入、清理修复核验与 Docker gate 阻塞记录 |

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

旧退出码为通过 `0`、运行未通过/运行错误 `1`、输入或前置依赖错误 `2`。没有 `verify-patch`、`inspect`、`report`、`resume`、`replay`、`export-harbor`、`verify-harbor`、`eval`。目标 CLI 是 [CLI.md](CLI.md) 定义的后续契约，不应拿目标命令要求旧包现在就支持。

YAML v1 要求 `version/id/repository/prompt/editable_paths/commands`，可选 `revision/failure_exit_code/failure_contains/timeout_seconds/max_steps`。仓库仅支持本地路径；`revision` 默认 `HEAD`，运行时解析完整 commit；镜像由 CLI 参数传入，默认 `repropatch-cpp:0.1`。

`commands` 固定为 configure/build/reproduce/verify 四组 argv，可执行程序只允许 `cmake` 和 `ctest`。`editable_paths` 是精确 C/C++ 文件列表，没有通配符；只支持已有被跟踪文件，不支持增加、删除、改名和修改权限。

新 [TASK_FORMAT.md](TASK_FORMAT.md) 使用 YAML v2，不重复使用 v1 版本号重新解释字段。后续以显式转换示例/任务生成器帮助迁移，不建立任意旧格式兼容层。

### 3.2 Agent 能力

已有 `Model.complete(messages, tools) -> Turn`，`Turn` 带文本及工具请求。每轮最多 8 个工具调用，默认最多 24 轮，单请求上限 2048 completion tokens 和 60 秒。完整消息历史一直累积，到约 1 MB 请求体上限时失败。本次目标改为 SDK 原生输入及明确体积上限，同样不自动裁剪历史；不能把上轮提出的裁剪策略写成已有能力或本轮必需组件。

工具只有 `read_file`、`search_code`、`edit_file`、`run_command`。`run_command` 仅选择已审核的 reproduce/verify，并重新配置、构建和测试；没有目录查看和任意容器 shell 工具。工具参数策略错误反馈给模型，模型或基础设施错误终止 Run。

模型产生非空的无工具文本时，Harness 进入候选处理，而不是直接宣布修复成功。Fake/Mock 行动脚本是固定序列，不能用其完成修复推算真实模型能力。

### 3.3 执行与验证

已有独立 detached Worktree、仅被跟踪普通文件的源码快照，以及干净 validation Worktree。模型不能直接调用宿主 shell/Git/Docker；编译与测试的生产路径只使用 Docker，不自动回退宿主执行。

Docker 设计包含只读 `/src`、只读根文件系统、非 root 用户、断网、清空 capabilities、no-new-privileges、CPU/内存/PID 限制与 `/build` tmpfs。首次解析镜像 image ID，后续评估要求相同 ID。API key 不传入容器。

原始基线必须 configure/build 成功、目标 reproduce 返回声明的非零退出码并包含输出标记；超时和截断不算复现。Agent 结束后将允许文件复制到原 commit 的新 Worktree，核对完整 diff 一致，重新 configure/build/reproduce/verify，全成功才记录 `passed`。

这是一条已存在代码路径，但 Docker 层实际成功运行尚无证据。它还缺少目标规格的 P2P 基线、固定测试身份/非空集合/跳过判定、明确预算保留及统一结局分类。

### 3.4 状态与审计

旧状态字符串包括 `running`、`baseline_setup_failed`、`not_reproduced`、`budget_exhausted`、`no_patch`、`passed`、`failed`、`interrupted`、`error`、`internal_error`。这些是分散赋值的结果字段，不是带转移校验和事务的 Task State Machine。

已有 SQLite `events(seq,timestamp,run_id,kind,payload)`。每条事件先 commit SQLite，再 append/flush JSONL，正常结束时可以一致，但崩溃时不保证尾部一致。没有事务性 Run 状态、Checkpoint、Resume、Trace Replay 或 Execution Replay；不能因为已经有数据库文件而声称具备可靠恢复。本次目标也不实现上轮提出的工具 operation 调度／半组重做协议。

## 4. 历史证据、本次复核与未验证边界

主要审计来源是原项目的 `docs/TEST_REPORT.md`、`docs/P1-01.md`、`docs/evidence/final-tests.log`、`docs/evidence/final-tests.xml`、`docs/evidence/p1-01/docker-tests.log`、`docs/evidence/p1-01/docker-tests.xml`、早期 `docker-gate.log`、`doctor.json` 和 `trusted-fixture/report.json`。本次实际读取了日志与 XML 的计数，不仅转述 README。

| 事项 | 本次观察到的产物及历史对照 | 可以得出的结论 |
|---|---|---|
| Python/fixture 测试 | 最新日志 `76 passed, 4 skipped`；XML 共 80 项、0 failure/error、4 skipped；上轮为 `74 passed, 3 skipped` | 新增两项清理主因回归已进入所存通过记录；新增 Docker 错误补丁测试进入跳过集合。不是本次重新运行结果 |
| 完整真实 Docker gate | 最新 P1-01 日志 `4 failed, 76 deselected`；XML 共 4 项、4 failures、0 skipped；早期单项 gate 为 1 failed | 测试命令已实际尝试，容器执行因 Docker 缺失未发生；隔离、正确/错误补丁与超时清理均未获真实 Docker 验收 |
| Docker 前置检查 | `docker:null, daemon:false, image:false` | 该次记录环境没有可用 Docker |
| 自有 fixture 修复 | `isolated:false`、`TrustedLocalSandbox`、`MockModel` | 已保存宿主受信任编译/独立 Worktree 的运行证据 |
| 真实模型服务 | 文档明确未调用，测试以模拟 HTTP/Fake 完成 | 没有真实 API 兼容性或修复能力验收证据 |
| 远程 CI | 仅有 workflow 配置，无 remote、无成功运行链接 | 不能宣称 GitHub Actions 已通过 |
| 清理修复与规格接入 | 当前 HEAD 已提交，工作树干净；P1-01 保存 intake/diff 和新增测试产物 | 接入与本地修复核验已有依据，不能重新要求保留一份已不存在的 dirty diff；P1-01 仍未达到全部 DoD |

最新普通测试 XML 时间戳为 `2026-10-19T10:41:07.887861+05:00`，Docker XML 为 `2026-10-19T10:41:52.818466+05:00`；保留原时区，不误标为本次审计时刻。当前提交收录这批源码及证据，日志没有独立声明“在提交后重测该 HEAD”，因此这里只确认提交内保存的运行记录。P1-01 文档记录执行过 Ruff 与格式检查；没有单独保留这两条命令的原始日志，本次也未复跑。

自有 fixture 的历史 Run ID 是 `negative-maximum-ead30b400a42`，基线 commit 为 `bdbeddbe6e9bf18cdd161d9698f2cb5dc66e6ad6`。报告记录原始目标测试返回 8，含 `expected -3, got 0`；正确补丁将初值 `0` 改为 `samples.front()` 后，独立 Worktree 的复现测试及 4 个 CTest 用例通过。测试目录还存在将初值改为 `-1`、要求独立验证拒绝的真实编译用例。

上述是真实保存的历史产物及其内容核查，不代表本轮证明了完整执行链的真实性，更不构成模型修复成功率、容器安全审计或性能基准。历史覆盖率不作为新阶段的质量目标；新版应以关键行为和隔离门槛实际通过为准。

## 5. 保留与迁移表

| 领域 | 保留的基础 | 目标改变 | 阶段与权威规格 |
|---|---|---|---|
| CLI/数据结构 | argparse、dataclass 与直接函数组合 | 扩展必要命令与稳定错误/结局，不引入 CLI／注入框架 | Phase 1，[ARCHITECTURE.md](ARCHITECTURE.md)、[CLI.md](CLI.md) |
| 任务输入 | YAML 单次边界校验、精确允许文件 | v2 完整 commit/image、显式资源/测试/路径契约 | Phase 1，[TASK_FORMAT.md](TASK_FORMAT.md) |
| 模型运行 | 自动修复与验证解耦、静态工具及单模型认证范围 | 用 OpenAI Agents SDK Runner、Responses 原生 Items 与 ScriptedModel 替换手写 Loop／HTTP／Model/Turn 协议；无模型子进程 wire | Phase 1，[AGENT_RUNTIME.md](AGENT_RUNTIME.md) |
| 外部补丁 | 原始基线与独立验证已有可提取逻辑 | 新增无模型依赖的 verify-patch；复用现成 Agent 的产物，不把外部轨迹当可信执行证据 | Phase 1，[CLI.md](CLI.md)、[VERIFICATION.md](VERIFICATION.md) |
| 工具 | 精确编辑、受控文件读取、固定自查 | 目录查看、受限容器 shell、稳定结果和截断契约 | Phase 1，[AGENT_RUNTIME.md](AGENT_RUNTIME.md) |
| 工作区 | detached Worktree、隔离源码快照 | 显式所有权、允许/保护集合、可验证清理 | Phase 1，[EXECUTION_AND_SECURITY.md](EXECUTION_AND_SECURITY.md) |
| 验收 | 原 commit 新 Worktree、无 Agent 构建缓存 | P2P 基线、每测试身份/结果证据、标准 Outcome | Phase 1，[VERIFICATION.md](VERIFICATION.md) |
| 审计存储 | SQLite 和保留失败产物 | SQLite 单一事件权威、JSONL 派生导出 | Phase 1，[STATE_AND_RECOVERY.md](STATE_AND_RECOVERY.md) |
| 状态恢复 | 不把旧日志冒充 Checkpoint | 只增加 runs/events/checkpoints 三表；SDK 完整输入边界与源码 Checkpoint；开放 segment 明确 RECOVERY_FAILED | Phase 2，[STATE_AND_RECOVERY.md](STATE_AND_RECOVERY.md) |
| 测试 | 自有 fixture、确定性脚本、Docker 显式 gate | 使用上游 ScriptedModel，按真实边界和关键故障窗口补最少必要测试 | 分阶段，[TESTING_AND_EVALUATION.md](TESTING_AND_EVALUATION.md) |
| 评测 | 自有 fixture 只检验流程 | 固定真实 C++ 任务、同模型/预算；复用 Harbor，ReproPatch 做领域结果聚合 | Phase 3，[TESTING_AND_EVALUATION.md](TESTING_AND_EVALUATION.md) |
| C++ 执行器 | 当前不存在 | 只有性能/进程语义需求有证据时开展 | Phase 4，[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) |

不存在“先全量重写，再迁回已有能力”的要求。编码时先确认 HEAD 与工作树是否仍为本次记录的状态，再围绕目标行为分段修改；不可因为生成了新 Spec 就覆盖用户代码或清空 Git 状态。

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

旧 `Harness.run` 对未预期异常只给简略类型信息，缺少可核查的本地 traceback。新版应在 Run 边界保留受控诊断，避免泄露密钥，同时不隐藏开发缺陷。“清理失败不遮蔽原异常”的补强已提交并有本地测试记录，不必重写；真实 Docker 清理行为仍需完成 P1-01 验收。

SQLite 和 JSONL 双写问题在 Phase 1 就可通过“仅 SQLite 写入、按需导出”小幅修正，不必等到整个恢复系统完成。状态事务、未知付费请求处理和 Checkpoint 则按 Phase 2 单独实现。新版模型接入直接使用 SDK Runner；不先实现上轮的手写消息兼容层，再套上 SDK，也不将旧恢复设计当作迁移前置条件。

## 7. 使用本审计的规则

第一项实施应继续处理 **P1-01 的 Docker 环境阻塞，并将本次修订 Spec 与现有规格入口对齐**。不要重做已提交的三项清理修复，不把原字节归档覆盖为新版，也不要把本地检查通过解释为 P1-01 全部完成。新 Spec 的具体依赖与任务拆分以实施计划为准。

开始每项开发任务前，以 [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) 确定目标、前置依赖和验收方式，再核对相关旧源码；不要从本文件推断尚未实现的新接口已经存在。

以后新增真实测试证据，记录测试时间、完整版本/commit、工作树修改、命令和原始产物位置。更新实现状态时应写清“哪个版本、哪个环境实际通过了什么”，不能把 0.1.0 的历史 fixture 结果继承成 0.2.0 或稳定版验收结果。
