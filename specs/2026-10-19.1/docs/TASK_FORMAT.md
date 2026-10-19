# Task 格式与配置契约

状态：**设计冻结，目标 Phase 1；尚未按本格式完成实现验收。** 本文是 `version: 2` Task、默认值、输入规范化的唯一权威定义。旧实现使用不同的 `version: 1`，见[现状与迁移](CURRENT_STATE.md)。执行权限见[执行与安全](EXECUTION_AND_SECURITY.md)，判定语义见[验证](VERIFICATION.md)。

## 1. 格式的责任

一个 Task 只描述“对一个固定源码版本，在一种固定环境和有限预算内修复一个已知失败”。它不是流水线语言：没有条件、循环、变量展开、模板、步骤依赖、动态工具声明、任意宿主脚本或多仓库编排。一次 `run` 只读取并冻结一次 Task，之后不重新读取原 YAML。

配置只有三处：Task 保存可复现的任务条件；CLI 保存本次模型选择及产物位置覆盖；宿主环境变量提供 API key。没有全局 YAML、配置继承和 `.env` 自动加载。CLI 只允许覆盖模型连接、输出根目录，不允许静默改 commit、镜像、测试名单和预算。改变这些实验条件必须修改 Task 并生成新 Run。

## 2. 完整示例

机器可读文件：[task.example.yaml](../examples/task.example.yaml)。它与下表共同定义协议，正文不复制第二份 YAML。

示例关联已有 `negative-maximum` fixture：`negative_values` 是 F2P；`positive_values`、`empty_values`、`mixed_values` 是 P2P。示例 commit 来自已存历史证据；镜像使用明确标注的全零 SHA 占位。**这份 Spec 交付包不包含可运行镜像，也没有重新打包旧实现。** 将文档合入代码仓库后，由计划中的 `scripts/init_example.py --write-task ... --image ...` 读取实际 fixture commit 和本地 image ID，生成可运行 Task。不得把占位镜像当作已发布资源。

### 2.1 顶层字段

| 字段 | 必需 | 类型／默认 | 精确语义 |
|---|---|---|---|
| `version` | 是 | 整数 `2` | 其它版本明确拒绝；bool 不视为整数 |
| `id` | 是 | string | `^[a-z0-9][a-z0-9._-]{0,63}$`；是 Task 标签，不是 Run 主键 |
| `repository` | 是 | object | 源仓库及不可变 commit |
| `environment` | 是 | object | 固定镜像和执行资源 |
| `bug.description` | 是 | 非空 string | 原始症状、期望行为、可选日志；最多 32 KiB UTF-8 |
| `commands` | 是 | object | 配置、编译、复现、验收的命令模板 |
| `tests` | 是 | object | 固定测试身份及原始失败签名 |
| `files` | 是 | object | 模型可读集合与可编辑集合 |
| `budget` | 否 | object，见后表 | 运行和 Agent 预算 |
| `workspace` | 否 | object，见后表 | 工作区位置及保留条件 |
| `outputs` | 否 | object，见后表 | 产物位置 |

### 2.2 仓库与环境

| 字段 | 必需／默认 | 约束 |
|---|---|---|
| `repository.path` | Phase 1 必需 | 本地 Git 仓库；相对路径以 YAML 所在目录为根；原仓库未提交文件不进入任务 |
| `repository.url` | Phase 3 才支持 | 与 `path` 恰有一个；只接受公开 `https://` URL，无 userinfo、凭证、helper 协议或 SSH；Phase 1 遇到即报不支持 |
| `repository.commit` | 必需 | 40 或 64 位小写十六进制完整 OID；必须存在且直接指向 commit，长度与仓库 object format 一致；不接受 HEAD、branch、tag、缩写 |
| `environment.image` | 必需 | `sha256:<64hex>` 本地 image ID，或 `name@sha256:<64hex>`；不接受仅 tag；禁止自动 build/pull |
| `environment.platform` | `linux/amd64` | Phase 1 唯一验收平台；镜像和主机须匹配，不隐式模拟另一架构 |
| `environment.cpu_limit` | `2.0` | 有限正数，传给 Docker CPU quota |
| `environment.memory_mib` | `2048` | 正整数；memory-swap 同值，不额外放开 swap |
| `environment.pids_limit` | `128` | 正整数；覆盖编译／测试派生进程 |
| `environment.build_tmpfs_mib` | `1024` | 正整数且小于 memory_mib；构建 tmpfs 与进程共用内存预算 |

Digest 和 image ID 含义不同：前者锁定仓库内容引用，后者锁定本地镜像对象。PREPARING 时 Docker inspect 解析出实际 image ID、RepoDigests、OS/architecture、工具链版本；后续所有容器均使用该实际 ID。只有本地 ID 的任务跨机器执行前需要操作者导入同一镜像；不能把该 ID 当成可拉取地址。镜像 Dockerfile 固定基础镜像 digest 仍不保证未锁定的 apt 包可重建成同一结果。

### 2.3 命令与测试

命令都是非空 `list[str]`，单参数不含 NUL。宿主不经 Shell 展开。`configure` 和 `build` 只在 Docker 内运行；前者第一项必须为 `cmake`，使用 `/src` 与 `/build`，后者形如 `cmake --build /build ...`。操作者可以提供必要 CMake `-D` 选项；不能通过 Task 增加宿主挂载、Docker 参数或密钥环境。

Phase 1 的 `commands.reproduce` 与 `commands.verify` 必须是：

```json
["ctest", "--test-dir", "/build", "--output-on-failure", "--no-tests=error"]
```

仅允许额外一个 `--verbose`。这两处显式模板保留复现／验收入口，但不引入任意命令协议：需要支持非 CTest 项目时先重新评估范围。模型的临时诊断使用 `run_shell`，不能改验收模板。最低 CMake/CTest **3.26**；版本来源与执行细节见[执行文档](EXECUTION_AND_SECURITY.md)。

测试选择由 Harness 按固定名字生成，不接受 Task 自定义 `-R`、`--repeat`、`--rerun-failed`、dashboard 模式或测试选择脚本。每次执行一个命名测试，Harness 追加精确锚定并转义的选择表达式、结构化结果文件路径和剩余超时。命令中的测试选择与 YAML 名单不会成为两个竞争的事实来源。

| 字段 | 必需 | 约束 |
|---|---|---|
| `tests.fail_to_pass` | 是 | 至少 1 项对象，不重复；目标原始失败集合 |
| `tests.fail_to_pass[].name` | 是 | 非空 CTest 精确名字；禁止控制字符；必须实际发现且仅匹配一个测试 |
| `tests.fail_to_pass[].expected_exit_code` | 是 | `1..255` 整数，是 ctest 进程退出码；常用 `8`，不代替 JUnit 中测试状态检查 |
| `tests.fail_to_pass[].output_contains` | 是 | 非空字面子串，最多 4 KiB；不使用正则；原始失败时在有界合并输出内必须出现 |
| `tests.pass_to_pass` | 是 | 至少 1 个精确测试名；与 F2P 不相交、不重复；基线必须全过 |
| `tests.protected_paths` | 是 | 验收源码、输入、注册及脚本的文件／目录列表；与 editable 展开后的集合不相交 |

测试名不意味着一个 C++ 断言；一个 CTest 用例内部可以有多个断言。指标只按 Task 和 CTest 身份计数，禁止从模糊日志推断内部断言数。Phase 1 只支持“构建成功后，正常结束的断言／退出失败”任务；构建失败型、挂起型、需外网／交互服务、自动附加 CTest fixture 测试的任务先明确拒绝，不以非零退出泛化支持。

### 2.4 文件集合

`files.readable` 是 list_directory/read_file/search_code 三个结构化工具可读取的 Git 跟踪文本集合；`files.editable` 是其子集，只包含明确列举的已有普通 C/C++ 源码文件，例如 `.cpp/.cc/.cxx/.c/.h/.hpp/.hxx`。不允许用目录、glob 或 `*` 表示全部可编辑。MVP 不支持新增、删除、重命名、二进制和 mode 变更。

readable 与 protected 的目录写法以 `/` 结尾，例如 `src/`；含义为该目录下递归的跟踪文件。普通路径精确匹配一个文件。两个列表在 PREPARING 按固定 commit 展开为文件集合，保存展开结果；不存在的显式路径报 `TASK_PATH_NOT_FOUND`。只对最终集合校验一次交集，不反复在内部函数重算。

所有相对仓库路径必须是规范 POSIX 路径：不含绝对根、空段、`.`、`..`、反斜杠、NUL／换行；不允许 `.git` 元数据及控制产物。源码树中的 symlink、gitlink、设备／FIFO 等特殊布局按执行文档拒绝。所有 `CMakeLists.txt`、`.cmake` 文件及声明的 protected 集合都不可编辑。Task 维护者仍须审核间接 test 输入／脚本是否完整列入 protected；Harness 不静态分析任意 CMake 程序来证明测试依赖闭包。

结构化可读集合之外的文件也参与容器构建；run_shell 可以直接读取当前只读快照内的全部文件并将内容返回模型。Phase 1 不提供隐藏测试或仓库内文件保密能力，readable 不是机密性边界。使用真实模型意味着操作者批准任务快照及命令输出发往所选服务。仓库应在运行前排除密钥与无权上传的数据。

### 2.5 预算与位置

| 字段 | 默认 | 语义 |
|---|---:|---|
| `budget.max_steps` | 24 | 最多发起的模型请求次数，失败及未知请求也计入；无隐式 SDK 重试 |
| `budget.max_tool_calls` | 80 | 最多工具尝试数；参数不合法的已请求工具也计数 |
| `budget.wall_seconds` | 900 | Run 创建起总时间预算，包括准备、基线、修复、最终验证；恢复时离线时间也计入 |
| `budget.verification_reserve_seconds` | 240 | 为最终独立验证预留，模型不得消费 |
| `budget.model_timeout_seconds` | 60 | 单模型请求上限，另受 Agent 剩余时间限制 |
| `budget.command_timeout_seconds` | 120 | 单命令上限，另受所属阶段剩余时间限制 |
| `budget.max_output_tokens` | 2048 | 单次模型输出上限，按实际 SDK 参数映射 |
| `workspace.root` | `.repropatch/workspaces` | YAML 相对的工作区根；每 Run 创建独占子目录 |
| `workspace.retain` | `on_failure` | `none/on_failure/always`；只控制工作树，不删除审计产物；P2 可恢复中断不得提前清理 |
| `outputs.root` | `.repropatch/runs` | YAML 相对的产物根；每 Run 子目录名为 Run ID |

预算数值必须为正整数（cpu_limit 除外）；`wall_seconds > verification_reserve_seconds + 10`，其中最后 10 秒固定给清理。计时、消耗与终止优先级由[Runtime](AGENT_RUNTIME.md)定义。Token 总量和价格是可缺失的观测指标；模型请求数、最大输出和时间有执行上限，不把它们宣传为提供商账单的严格上限。

根目录创建后转换为绝对 canonical path，不能互相包含、不能位于目标源码仓库中、不能指向目标仓库／任意系统目录；允许不同 Run 共用这两个专用根，不共享子目录。控制元数据／输出永不挂载到容器。给原源码仓库指定 `retain: none` 不会删除该仓库。更多所有权检查由执行文档定义。

## 3. 解析和冻结

使用 PyYAML 的安全加载能力，外层只添加必要限制：原文件最多 128 KiB；拒绝自定义 tag、锚点／alias、重复 key 和未知字段；限制结构深度 12；按各字段的明确类型解析，禁止把字符串数字和 bool 悄悄转换成预算。标准 `safe_load` 不自动检查重复 key，须在边界的 mapping constructor 中处理一次；无需手写 YAML parser。

语法／类型错误为 `validate-task` 退出码 2，给出字段路径、行列（解析器可提供时）及期望类型；不创建 Run。`validate-task` 不调用网络、模型或编译器。路径存在、commit、image、Docker 特性、测试发现属于 PREPARING／基线阶段的动态检查；静态通过不表示可复现。

经过动态解析形成不可变 `ResolvedTask`。以下是接口结构说明，不是本轮已经实现的代码：

```python
@dataclass(frozen=True)
class ResolvedTask:
    task: TaskSpec                 # version=2 的已校验 dataclass
    task_source_sha256: str        # 原始 YAML bytes
    task_sha256: str               # 下述规范化执行契约
    repository_path: Path         # canonical source repository
    base_commit: str
    image_id: str
    image_repo_digests: tuple[str, ...]
    readable_files: frozenset[str]
    editable_files: frozenset[str]
    protected_files: frozenset[str]
    workspace_root: Path
    output_root: Path
```

`task.resolved.json` 保存完整有效 Task、展开路径、实际 image 身份、工具版本和位置；不保存 API key。规范 JSON 使用 UTF-8、sorted keys、紧凑 separators、禁止 NaN；命令和测试等有语义顺序的列表保留原顺序。展开后的 frozenset 文件集合按规范 POSIX 路径的 Unicode code point 顺序排序后编码为数组，禁止直接 list(set)；不同进程 hash seed 不得改变 task hash。

`task_sha256` 对规范执行契约计算：包含 version/id、base commit、image ID/platform、bug、命令、测试、文件集合、执行资源和预算；**不包含**本地仓库绝对路径、工作区／产物位置、保留策略、Run ID 和时间。这样跨目录可比较。原 YAML hash 负责精确来源；模型／工具实现／prompt 另记 fingerprint，由评测组成 experiment key，不能只靠 task hash 声称实验相同。

冻结顺序：静态校验 → 创建带所有权记录的 Run → 解析 source/commit/image → 扩展文件集合 → 持久化 resolved JSON/hash → 后续统一读内存不可变对象。冻结失败属于 `ERROR` 并保留已有诊断；不重新加载用户更改后的文件继续同一个 Run。

## 4. v1 迁移

不维护两套运行器。目标 0.2.0 默认只接受 v2；拒绝 v1 时指向本节。先更新已有 fixture、测试和 README，再删除仅服务 v1 的解析分支。无需自动把任意旧清单“猜测转换”。

| v1 | v2 迁移动作 |
|---|---|
| `repository: PATH`、`revision: HEAD` | 改 object；显式写入实际完整 commit |
| CLI `--image TAG` | 任务内固定 image ID/digest；doctor 的 `--image` 仅做诊断 |
| `prompt` | `bug.description` |
| `editable_paths` | `files.editable`，补 readable 和 protected 集合 |
| reproduce 的 `-R` | 移除自定义 selector；在 F2P 中给出精确名字及失败签名 |
| `verify` 全量 ctest | 明确列出 P2P 名单；基线也运行这些用例 |
| `failure_exit_code/failure_contains` | 移至每个 F2P 的 expected 字段 |
| `max_steps/timeout_seconds` | 移入 budget，添加总时间、工具预算及验证预留 |
| 隐含工作区／输出位置 | 写明新根目录默认值或显式配置 |

实际迁移由[实施计划](IMPLEMENTATION_PLAN.md)的 P1-02 完成。Task v2、数据库 schema_version、event schema_version、软件版本分别管理，禁止把它们混成同一个版本号。
