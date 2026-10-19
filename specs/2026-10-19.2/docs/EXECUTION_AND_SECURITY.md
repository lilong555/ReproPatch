# 执行与安全边界

状态：**planned，规格修订 2026-10-19.2；Phase 1 的 `run` 与 `verify-patch` 共用本文边界，Phase 2 才增加中断后的状态核对。** 本文是宿主／容器权限、工作区、快照、进程生命周期和输出限制的权威定义。任务字段见 [Task 格式](TASK_FORMAT.md)，工具参数和 `CommandResult` 见 [Agent Runtime](AGENT_RUNTIME.md)，验收结论见 [验证](VERIFICATION.md)。

已有 `workspace.py`、`sandbox.py`、`process.py` 和 `tools.py` 是迁移基础，不能据此声称本文已实现。保留、收敛和待替换内容统一以 [现状与迁移](CURRENT_STATE.md) 为准；旧本地执行结果不能作为 Docker 安全边界的验收证据。

## 1. 固定信任模型

ReproPatch 面向单个可信操作者，在其 Linux 主机上处理可能有缺陷、可能包含恶意行为的源码。操作者信任 Harness 程序、系统 Git／Docker、所选镜像中的工具链，以及自己审核的 Task 和测试规则。模型输出、仓库源码、构建脚本、测试程序和它们的输出均不获得宿主执行权限。

| 对象 | 权限与责任 |
|---|---|
| 操作者 | 选择本地仓库、固定 commit、镜像、测试名单、可编辑文件和模型服务；保证有权向所选服务提交任务涉及的数据 |
| 宿主 Harness | 调用受控 Git／Docker CLI、读取和编辑明确授权的文件、调用模型、记录事件、生成最终报告 |
| Agent | 提议工具调用和结束；不能更改 Task、镜像、Docker 参数、验收规则或预算 |
| 外部补丁生产者 | 可提供 patch 和可选 trace；其代码执行、凭证、网络及生成预算不在 ReproPatch 保证范围，提供的记录不获得可信执行证据身份 |
| 源码容器 | 读取无 Git 元数据的 `/src` 快照；仅在临时构建区和临时目录写入；不能写宿主活跃 worktree |
| 独立验证器 | 使用冻结规则及候选 patch 创建干净源码，重新构建、检查测试身份、产生证据；不接受模型的自评作为结论 |

Phase 1 **不接受任意不可信的本地 `.git` 管理目录**。本地 Git 配置、对象库和元数据来自操作者信任的 checkout；这与“源码可在容器中运行”是两条不同的信任边界。下载的未知仓库应由操作者先在干净 Git 配置下正常 clone，再选择本地路径。Harness 不自动修复、重写或替操作者信任可疑 Git 元数据；公开 HTTPS 的受控获取留到 Phase 3。

Docker 依赖宿主内核、daemon、运行参数和权限配置。本文防范的是源码直接写宿主、误删除工作区、凭证注入、资源失控及普通工具故障；不承诺抵抗所有内核／容器逃逸，不把有限测试等同于恶意代码正确性证明。相关限制与 [Docker 官方安全说明](https://docs.docker.com/engine/security/) 一致。

### 1.1 复用 SDK，不转移执行边界

自动修复由宿主的 OpenAI Agents SDK `Runner` 驱动。ReproPatch 静态注册恰好六个 `FunctionTool`：`list_directory`、`read_file`、`search_code`、`edit_file`、`run_command`、`run_shell`。前四个只做受控文件数据操作；后两个只经本文 Docker 执行器运行源码。SDK 负责原生 Responses Items、模型调用和工具分发，不能根据模型返回的名字任意 import、反射调用宿主函数，或执行模型生成的 Python。

不注册 SDK 的默认 shell／apply-patch／computer／hosted tools、MCP、skills、handoff 或 `SandboxAgent`，也不从仓库加载扩展。工具输入和任务预算仍在 ReproPatch 边界校验。`ToolExecutionConfig.max_function_tool_concurrency=1` 与 `parallel_tool_calls=False` 都明确设置；前者限制实际本地工具并发，后者约束提供商的工具生成行为，两者不能互相替代。SDK 的工具执行及权限职责见 [官方工具说明](https://openai.github.io/openai-agents-python/tools/) 和 [运行配置](https://openai.github.io/openai-agents-python/running_agents/#tool_execution)。具体批次准入、参数错误和终止规则以 [Runtime](AGENT_RUNTIME.md) 为准。

API key 只交给宿主模型客户端，不写入 Task、argv、工具返回、容器环境或证据文件。首次模型调用前关闭 SDK 远程 tracing：设置 `set_tracing_disabled(True)`，RunConfig 同时明确 `tracing_disabled=True`；不安装外部 trace exporter。Responses 请求使用 `store=False`。这些选项不能替代服务提供者自身的数据保留政策；真实调用意味着操作者授权将选定任务内容提交给该端点。SDK 默认开启 tracing，因此不能依赖默认值，见 [官方 tracing 说明](https://openai.github.io/openai-agents-python/tracing/)。

模型端点、SDK 和固定工具实现属于受信任控制面。SDK 版本记录在报告中并由开发锁文件固定；升级必须重新验证六工具注册和串行预算 gate。不得把宿主 `codex exec` 或另一完整 Agent 的 subprocess 直接当成此 profile 的实现：外部程序可能拥有自己的 shell、文件工具、网络和凭证使用路径，一层调用包装无法证明这些路径都进入 Docker。

### 1.2 外部输入只走补丁验收入口

`verify-patch` 只接收操作者指定的本地 patch 和可选 producer trace，不启动或自动安装生产补丁的 Agent。它不加载模型 SDK，不读取模型密钥，也不把外部 trace 恢复成 SDK 历史。输入按普通文件原始 bytes 复制到独占证据目录；拒绝 symlink、目录、设备、归档展开和并发变化，记录实际大小及 SHA-256。原始 patch、导入后规范 patch 和最终验证产物的关系见 [候选补丁交接](VERIFICATION.md#6-候选补丁交接)。

外部 trace 只能证明“本次保存了这些输入 bytes”。无论其中声明何种容器限制、成功率、成本或测试结果，都不能据此构造 `CommandResult`、baseline 或 independent 证据。`--producer` 只是报告标签，不是可信身份认证。运行时既不解析外部 trace 的命令并执行，也不因内容要求改变测试规则。

## 2. Phase 1 最小运行前提

- Linux amd64，Python 3.12，受维护的 Git、Docker Engine 和 Docker CLI；实际版本写入最终报告的 provenance。
- `verify-patch` 仅需核心依赖；自动修复引擎的可选 `agent` extra 和版本要求见 [Runtime](AGENT_RUNTIME.md)。不能让补丁验收命令因未安装模型 SDK 或没有 API key 而无法启动。
- 本地已有固定 image ID 或 repo digest 对应的镜像；禁止运行时自动 pull、build 或安装依赖。
- 镜像提供 `/bin/sh`、GNU coreutils（包括固定路径 `/usr/bin/sleep`，支持 `infinity`）、基本文件读取工具、C++ 编译器、CMake／CTest **3.26 或以上**。preflight 必须核对这些依赖；固定版本下的命令发现结果也要记录。
- 使用本地 Docker daemon；Phase 1 不支持远程 `DOCKER_HOST` 或远程 context，因为它们不能证明绑定的是本机已校验快照。
- daemon 必须实际支持本任务需要的 CPU、内存、PID、只读 bind 和 tmpfs 限制。不支持就报错，不静默省略参数。
- 基线构建必须支持 `/src` 只读、`/build` 独立构建、无外网、无 Git 元数据。依赖源码内写入、在线下载或 `git describe` 的项目由操作者事先准备支持的 Task／镜像，不能靠放开宿主挂载解决。

本项目选择 CMake／CTest 3.26 作为最低工程验证基线；这不表示 `--no-tests=error` 首次出现在 3.26。3.26 release notes 中新增的是 `CTEST_NO_TESTS_ACTION` 环境变量，见 [CMake 3.26 release notes](https://cmake.org/cmake/help/v3.26/release/3.26.html)。测试发现和结果格式采用官方 `--show-only=json-v1`、`--output-junit` 能力，见 [CTest 3.30 手册](https://cmake.org/cmake/help/v3.30/manual/ctest.1.html)。以上是目标运行前提，不是本轮已经完成的 Docker 检测。

## 3. Git 与宿主工作区

### 3.1 只创建独占 worktree

PREPARING 按以下顺序执行：

1. 解析本地仓库和完整 commit，确认对象直接是 commit；不读取用户工作区的未提交文件作为任务输入。
2. 按下一节检查 Git 配置，在受控环境中读取固定 commit 的文件清单、模式和大小。
3. 为 Run 创建新的独占目录，保存 Run ID、源仓库 canonical path、commit、所属根目录和后续资源记录。目录已存在时拒绝占用。
4. 通过 `git worktree add --detach <owned-path> <full-commit>` 创建工作树；从 Git 查询并保存真实管理目录，不自行推测 `.git/worktrees/<name>`。
5. 校验检出的文件布局，展开 readable／editable／protected 集合，保存原始字节清单。`run` 随后进入基线复现；`verify-patch` 先在另一棵本 Run 独占的干净 worktree 导入并核定候选，基线仍只使用未打补丁的原始树。

不修改原仓库的源码、index 或分支。Git 注册和移除 worktree 所需的管理元数据写入是本功能的明确副作用。源仓库由操作者保持可用；不得在 Run 期间移动、删改其 Git 管理目录。普通其它分支开发不影响已固定的 detached commit。

Git Worktree 共享对象和部分引用，工作树中的 `.git` 通常是指向管理目录的文件；它本身不是隔离设施。容器完全不挂载 worktree，因此无需在容器内“修好”该指针，也绝不能为方便构建把原仓库管理目录一起挂进去。参见 [Git worktree](https://git-scm.com/docs/git-worktree)。

### 3.2 受控 Git 配置，不伪装成恶意仓库导入器

宿主 Git 包装只负责统一 argv、环境和必要固定参数，不新增插件或 Git 实现。每次调用使用受信任的 Git 可执行路径、明确 cwd／管理目录，移除继承的 `GIT_*` 控制变量；设置 `GIT_CONFIG_NOSYSTEM=1`、`GIT_CONFIG_GLOBAL=/dev/null`，不自动加载用户环境文件。

读取仓库本地配置时先禁止 include 展开。Phase 1 对本地 `include/includeIf`、额外 worktree 配置、活动 filter clean／smudge／process、非关闭的 fsmonitor、仓库自定义 hooksPath，以及外部 diff/textconv 程序配置返回 `UNSAFE_GIT_CONFIG`。对当前树中要求未提供的 Git LFS／自定义 filter 的属性返回 `UNSUPPORTED_GIT_FILTER`。这里采用固定有限的拒绝集合，不执行这些程序来探测是否安全，也不自动修改用户配置。标准 Git 自身的文本／换行属性可以保留，由补丁字节往返校验兜住一致性。

实际 Git 操作额外固定 `core.hooksPath=/dev/null`、`core.fsmonitor=false`、`core.autocrlf=false`；diff 禁止 external diff 和 textconv，禁用颜色及 rename 推断。宿主不执行 submodule update、LFS 下载、仓库安装脚本或自动合并。配置检查和 flags 是本地可信元数据边界内的防误执行措施，**不是对任意恶意 `.git`、Git 漏洞或对象库攻击的完整防御**。

Git 的外部 diff 和 textconv 确实可能运行外部程序，且 textconv 结果可能不能重新应用；补丁必须采用普通可应用 diff，见 [Git diff](https://git-scm.com/docs/git-diff)。

### 3.3 所有权和路径规则

根目录约束由 [Task 格式](TASK_FORMAT.md) 定义；执行层进一步要求 run 子目录是本次新建且由当前用户控制的真实目录，不能是 symlink。控制目录使用 `0700`，其中任务、事件、原生模型附件和外部 trace 文件使用 `0600`；源码快照的容器可读权限另见第 4 节。一个 Run 持有一个独占文件锁；锁在整个运行期间由打开的文件描述符维持，不依赖易遗留的“存在即锁定”标记。Phase 1 不支持多进程同时操作同一个 Run。

源码清单只接受 Git mode `100644/100755` 的普通文件。symlink、gitlink／submodule、冲突 index、非法路径或特殊文件布局直接拒绝；普通不可编辑二进制资源可以按原字节参与构建。不可编辑文件不能因“不是 C++ 源码”被自动删除。

文件工具只接受已展开的规范仓库相对路径。边界检查包括集合成员关系、路径父级不是链接、最终对象仍是预期普通文件。无不可信代码拥有活跃 worktree 的写权限，因而无需为每一次内部属性访问重复做路径校验。若操作者或其它宿主程序并发篡改独占目录，使文件类型、模式或非编辑文件哈希变化，终止为 `ERROR/SOURCE_CHANGED`，不继续猜测正确内容。

## 4. Host-only 文件工具与只读快照

### 4.1 受控源码修改入口

`list_directory/read_file/search_code` 在宿主读取已授权的跟踪文本；不启动源码中的程序。搜索可以使用现有 ripgrep，但须由 Harness 给出明确文件集合和 argv，不能继承模型提供的宿主选项。没有 ripgrep 时使用标准库的固定字面搜索即可，不添加搜索框架。

`edit_file` 是自动修复时唯一由模型触发的源码修改入口；操作者提供的外部 patch 由第 1.2 节的独立导入路径处理，不能通过工具参数混入。参数按 [Runtime](AGENT_RUNTIME.md) 校验；目标必须是 editable 中的已有普通 UTF-8 C/C++ 文件，替换匹配不成立时明确报工具错误。读写使用 bytes 与严格 UTF-8 转换，不通过会自动转换换行的文本读写路径；保留 UTF-8 BOM、CRLF 和末尾是否有换行，除非替换内容显式改变这些字节。临时文件写完后恢复原权限、flush／fsync，再在同一目录原子替换原文件。不得改变路径、Git mode、owner 或加入额外文件。

文件工具对不可编辑路径的请求返回可见错误并计入工具尝试；不请求模型再次批准、不偷偷扩大 allowlist。函数内部不捕获所有异常伪装成“修改成功”。宿主 I/O 或状态故障由 Run 边界统一转为 `ERROR`。

### 4.2 SourceManifest

每个基线、诊断和最终验证快照都来自当前静止的宿主树。`SourceManifest` 的 JSON 根固定为 `{ "schema_version": 1, "files": [...] }`；`files` 是按仓库相对 POSIX 规范路径的 **Unicode 码点顺序** 排序的数组，不使用 locale 排序，也不额外改变路径的 Unicode 归一化形式。每项只记录：

| 字段 | 内容 |
|---|---|
| `path` | 仓库相对 POSIX 路径字符串 |
| `sha256` | 原始文件 bytes 的 SHA-256，小写十六进制字符串 |
| `size_bytes` | 文件真实字节数，非负整数 |
| `git_mode` | 字符串 `"100644"` 或 `"100755"`；不是十进制数字 |

以下为格式示例，其中的文件是零字节文件，不表示已有项目产物：

```json
{
  "schema_version": 1,
  "files": [
    {
      "path": "src/empty.cpp",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "size_bytes": 0,
      "git_mode": "100644"
    }
  ]
}
```

`source_tree_sha256` 的输入是上述完整根对象的规范 JSON bytes：采用 `json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`，再以 UTF-8 编码，**不加末尾换行**。对这些 bytes 计算 SHA-256，保存小写十六进制结果；`source_tree_sha256` 本身不放入被哈希的对象。这里 `sort_keys=True` 只对对象键排序，`files` 仍须预先按路径排序。不纳入 inode、mtime、宿主绝对路径或随机临时目录。

`candidate.manifest.json` 等产物可以保存为便于阅读的 JSON。其 [EvidenceRef](ARCHITECTURE.md) 中的 `sha256` 是**产物文件实际 bytes** 的哈希，`size_bytes` 也是实际文件大小；空白、键顺序或末尾换行可以使该值不同于 `source_tree_sha256`。比较源码树使用规范数据摘要，核查产物完整性使用 `EvidenceRef`，二者不得互换。这些哈希证明已保存字节之间的一致性，不是代码正确性或来源真实性签名。

快照创建使用明确的已跟踪文件清单，逐文件检查普通文件类型并复制 bytes，复制后核对清单。禁止递归跟随链接、硬链接回活跃 worktree、直接复用可被后续 edit 改变的文件，或把用户提供的 tar 解压到宿主。`.git`、数据库、Task 快照、模型消息和 API 凭证均不进入源码快照。

### 4.3 快照的生命周期

同一 Run 串行执行，创建／复制快照期间不执行 edit。快照目录统一为 `0755`；普通文件按原始逻辑 Git mode 设置为 `0644` 或 `0755`，使固定容器用户能够读取源码并执行原本可执行的文件。逻辑 `git_mode` 仍按原始树记录，不能把快照权限规范化当作源码模式变更。完整快照冻结后才交给 Docker，挂载位置固定为 `/src:ro`，只读 bind 阻止容器写入。下一次编辑不会改变已运行容器看到的内容；一次诊断结果始终关联一个 source_tree_sha256。

普通诊断结束即删除其快照；不为每一次工具调用永久留一棵源码树。保留策略最多保存活跃 repair worktree 和最近一次需要诊断的 evaluation 快照，见第 9 节。快照和原仓库都不承载模型恢复状态；Phase 2 的 checkpoint 由 [状态与恢复](STATE_AND_RECOVERY.md) 定义。

`files.readable` 只约束结构化文件工具和自动加入消息的内容。**run_shell 可以读取完整 /src 快照并把内容输出给模型，所以 readable 不是源码保密或信息流控制系统。** 真实模型运行前，操作者必须排除源码中的凭证及无权提交的数据。protected 测试防修改，不保证对模型保密。

## 5. Docker 固定执行 profile

模型和 Task 均不能自定义这个 profile。下表是实现应实际设置并在 Docker 集成测试中核查的约束。

| 资源或权限 | Phase 1 固定行为 |
|---|---|
| 镜像 | 使用 PREPARING 解析出的实际本地 image ID；无自动 pull、build |
| 身份 | 固定 `--user 65534:65534`，不映射宿主操作者 UID/GID；宿主操作者可信，不因其以 root 运行 CLI 而额外拒绝 |
| 网络 | `--network none`，不发布端口；无 host network |
| Linux 权限 | `--cap-drop ALL`、`--security-opt no-new-privileges`；保留默认 seccomp，不传 privileged／设备／host PID/IPC |
| 根文件系统及入口 | `--read-only --init --entrypoint /usr/bin/sleep --no-healthcheck --restart no`，镜像后的固定参数为 `infinity`；不执行镜像自带入口或健康检查，不自动重启 |
| 源码 | 仅无 Git 元数据的 snapshot 只读 bind 到 `/src` |
| 构建 | `/build` 为 Task 限定大小的 tmpfs，rw、nosuid、nodev、uid=65534、gid=65534、mode=0700；允许执行编译后的程序 |
| 临时文件 | `/tmp` 为固定 64 MiB tmpfs，rw、nosuid、nodev；HOME、TMPDIR 指向容器临时区域 |
| CPU／内存／PID | 使用 Task 数值；memory-swap 与 memory 相同；tmpfs 和进程共同消耗 cgroup 内存 |
| 环境 | 不继承宿主环境；固定 locale、工作路径和串行 CTest 条件；绝不注入 API key、SSH agent、cloud 凭证或代理凭证 |
| 日志 | 固定 `--log-driver none`，不分配 TTY；宿主有界捕获 exec 输出，避免 Docker 再保存一份无界容器日志 |
| 挂载检查 | 不允许 Docker socket、用户 HOME、输出根、Git 管理目录或额外镜像 VOLUME 破坏上述挂载集合 |

固定入口、init、健康检查禁用、用户和重启策略使用 Docker 已有参数，见 [Docker 容器运行参数](https://docs.docker.com/reference/cli/docker/container/run/)。必要的用户态依赖都预装在镜像内。命令不能通过失败后的“自动联网重试”改变实验条件。Docker 没有对应限制能力时运行失败；即使 Fake Model 可以生成正确 patch，也不能用本地执行 fallback 填补 Docker gate。

CPU／内存限制不能证明所有宿主资源都隔离。tmpfs 解决本项目构建文件的容量上界，但宿主 Git 对象、源码副本、事件和日志仍需要文件大小限制与剩余磁盘检查；不宣称 Docker 为任意 bind mount 提供了硬磁盘配额。参见 [Docker 资源约束](https://docs.docker.com/engine/containers/resource_constraints/)。

## 6. 两种容器生命周期

### 6.1 一次 evaluation，一个容器

基线复现、Agent 的命名自检以及最终验收各自创建新容器。容器按第 5 节的固定参数启动，由 `--init` 管理的 `/usr/bin/sleep infinity` 维持生命，宿主使用 `docker exec` 按序执行 configure → build → inventory → 单个测试的 CTest 调用；这些命令共用该容器的 `/build` tmpfs。不能为 configure/build/test 各开新容器，否则临时构建结果会丢失。

每个命令由宿主以 argv 调用 Docker，命令工作目录固定为 `/src` 或 `/build`。测试选择、结果路径和超时参数只由 Harness 生成。CMake/CTest 发现出的镜像工具路径固定用于同一次 evaluation，不能把 /src 或 /build 追加到宿主 PATH。

正常的基线预期测试失败可以继续收集其余固定测试；任意 timeout、output_limit、容器 OOM、取消或无法确认的执行状态使整个 evaluation 立即结束，容器整体销毁，不复用受污染状态。

### 6.2 一次 run_shell，一个一次性容器

`run_shell(command, cwd, timeout_seconds)` 也使用第 5 节的固定 idle 容器；shell 文本只作为容器内一次 `docker exec` 的 `/bin/sh -lc` 输入。宿主仍使用参数数组启动 Docker，不把文本插入宿主 shell。cwd 仅允许 `/src` 或 `/build`；源码只读，命令无法绕开 edit_file 修改候选。

多条诊断可以由模型在同一次 shell 中组合，例如在 /build 中配置、编译并运行一个程序。调用结束后销毁整个容器，包含后台子进程和临时构建文件。下一次 shell 不继承 cwd、export、安装结果、daemon 或 /build 内容。这是明确的成本取舍，避免 MVP 维护可恢复的交互 shell。

## 7. 超时、退出与进程清理

每个容器有不可混淆的名称和 Run／操作标签；资源记录保存实际 ID、用途及所属 Run。创建后先记录身份，再启动；不使用会抢先销毁诊断状态的无条件 `--rm`。Phase 1 的记录供诊断和正常 finally 清理，尚不承诺崩溃恢复。

有效命令 deadline 为请求上限、Task command 上限、当前阶段剩余时间三者最小值。最后 10 秒清理预算不可给模型或正常命令消费。进程内持续时间用 monotonic clock；跨恢复 deadline 语义由 [Runtime](AGENT_RUNTIME.md) 与 [状态与恢复](STATE_AND_RECOVERY.md) 统一定义。

停止流程必须是：

1. 记录触发原因，停止安排后续命令。
2. 对记录中的容器 ID 发出整体停止／强制移除；允许短暂退出宽限，但总清理时间不得越过剩余清理预算。
3. inspect/wait 核对该容器已经停止或移除。仅在收到明确不存在的结果时才能视为已清理；daemon 不可达不是“不存在”。
4. 终止并回收宿主 Docker 客户端进程，记录退出和清理证据。
5. 仍无法确认时记录 cleanup_error，禁止继续同一 evaluation，也禁止给出 ACCEPTED。

只杀宿主 `docker exec` 进程不满足超时处理要求。Docker 文档说明 exec 命令依附于容器主进程生命周期，因此本项目把容器作为清理单位，参见 [Docker exec](https://docs.docker.com/reference/cli/docker/container/exec/)。

底层只产生 [Runtime](AGENT_RUNTIME.md) 中的 `exited/timed_out/oom_killed/cancelled/infra_error/output_limit`。正常非零退出仍是 exited，由验证器解释；取消或强制终止后的客户端返回值不能覆盖已经观察到的 timeout。仅凭 137 不推断 OOM；须有 Docker 状态／事件证据。Docker 连接断开、启动拒绝或执行证据矛盾均不得伪装成普通测试失败。证据不足时返回 infra_error，exit_code 可以为空。

模型工具超时在容器清理确认后可作为工具错误反馈给 SDK；运行总预算耗尽、用户取消或最终验证超时不再安排下一次模型调用。SDK 任务取消必须进入工具的资源清理路径，不能只取消等待 `docker exec` 的 coroutine 后遗留容器。整个调用是否停止、是否可交接候选，以 [Runtime](AGENT_RUNTIME.md) 和 [验证](VERIFICATION.md) 的终止规则为准。

模型请求使用 SDK 的异步客户端及有界取消，沿用公开 API。取消本地请求不能证明远端停止生成或不计费；请求结果未知时不自动重发。Phase 2 只从已关闭 Agent segment 的安全 checkpoint 恢复；开放 segment、中断的验证或无法核对的副作用按 [状态与恢复](STATE_AND_RECOVERY.md) 进入明确失败，不重新执行未知副作用。

## 8. 有界输出与证据导出

以下均为 Phase 1 代码常量，先不扩展成 Task 配置面：

| 对象 | 上限与行为 |
|---|---|
| 一棵源码快照 | 256 MiB；准备阶段预查 Git 文件大小，复制后以实际 bytes 再核对 |
| 单个源文件 | 16 MiB；超限任务拒绝 |
| 单个被编辑文件 | 1 MiB；替换前后均检查 |
| 候选 patch | 8 MiB；超限候选拒绝，不截断后验收 |
| 外部 producer trace | 16 MiB；普通文件整体复制并哈希；超限拒绝，不截断后冒充原始输入 |
| 文件读取／模型可见命令输出 | 每次最多 64 KiB；明确附 truncated 标志，不称作完整日志 |
| 每命令原始 stdout+stderr | 合计 4 MiB；累计观察字节数 `>= 4 * 1024 * 1024` 时立即停止命令并销毁容器，status=output_limit；恰好达到上限也按证据不完整处理 |
| 一个 Run 的非源码审计产物 | 256 MiB；写入受限，给最终状态／错误诊断预留空间；不能通过删除早期证据继续伪装完整运行 |

stdout/stderr 必须持续读取，不能因只等进程结束而堵塞管道。每条命令在独立证据子目录保存 `stdout.bin` 和 `stderr.bin` 两个原始 bytes 文件，通过 `CommandResult.stdout_log`、`stderr_log` 的 EvidenceRef 引用；不编码为 Base64 JSONL，也不再创建第三份合并日志。正常无输出也保存零字节文件；启动前文件创建失败时相应引用为 null，并保留 I/O 错误，不能用缺失文件表示已观察到空输出。

每个流内部保留观察到的字节顺序；不承诺 stdout 与 stderr 的跨流相对次序。展示用 UTF-8 replacement 解码，64 KiB 总 preview 确定性保留首尾片段并标记省略；不得修改原始证据。终端控制字符转义后显示。字面失败签名分别在完整 stdout 或完整 stderr 中查找，任一流命中即可；不能拼接两个流制造签名，也不能在模型摘要中猜测结果。即使已命中签名，只要原始输出触及硬上限，本次证据仍不完整。

JUnit 在 /build 内生成。**tmpfs 内容在容器停止后不可依赖，必须在正常 evaluation 结束、销毁之前通过有界 stdout 读取到宿主证据目录。** 只读取 Harness 生成的固定结果路径，不将源码提供的归档或 docker cp 结果直接解压到宿主。读取失败、超限或内容损坏保留已有记录并交给验证器判为无法确定，不能按“没有失败条目”处理为通过。

容器产生的 XML／日志是非可信数据；宿主使用有界标准库解析器，拒绝 DTD／实体声明、异常深度和不符合预期结构的数据。最终报告、摘要状态和事件由宿主编写，不能由容器文件覆盖。允许记录的原生 SDK 输入／输出附件不含 Authorization header、API key 或完整 SDK 调试转储；不透明的加密 continuation 只在私有本地产物中保存，不解码成隐藏推理，也不输出到人类报告。确有敏感数据进入源码时，日志脱敏不是自动补救权限的承诺。

## 9. 清理、保留与失败边界

清理的对象是已记录且属于本 Run 的资源。容器 ID、标签与本地资源记录应一致；worktree 必须位于已确认的 workspace 根内且仍登记在对应可信仓库。路径不符合预期时停止清理并报告，不追踪链接、不对任意父目录递归删除。

| retain | 正常结束后的宿主工作区 |
|---|---|
| none | 在容器停止确认、patch 与报告落盘后移除本 Run worktree／源码快照 |
| on_failure | ACCEPTED 后移除；其它结果保留 repair worktree 及最近的诊断快照 |
| always | 保留上述工作区，不保留运行中的容器 |

所有模式都保留有界审计产物。移除 worktree 使用 Git 命令；只对本 Run 专属且已核对的脏工作树使用必要的 force。移除普通快照不跟随 symlink。不得运行全局 docker prune、git worktree prune 或清理其它 Run。

容器清理未确认时保留主因和 cleanup_error；若原本可以 ACCEPTED，则降为 INCONCLUSIVE。工作区文件保留／删除失败但已确认无活跃代码时，记录具体清理错误，不伪造删除成功。Phase 2 的 INTERRUPTED Run 必须先完成恢复判断，不能因默认 on_failure 策略提前删掉 checkpoint 依赖。

## 10. 人工授权与残余风险

正常 `run` 已授权在本 Run 资源内编辑源码、运行已审核命令和清理临时容器；`verify-patch` 已授权复制所选输入、在独占工作树应用补丁及进行同等隔离的复现／验收。两者不需要对每个内部步骤再次询问。调用真实付费模型须满足 CLI 的显式授权条件。上传 patch、推送 commit、创建对外 PR、变更宿主配置或放宽隔离不属于这两条命令的授权范围；Phase 1 不实现这些动作。

残余风险必须出现在公开安全说明中：Docker 共享内核；操作者提供的 Git 元数据和镜像仍在信任边界内；镜像 digest 不冻结宿主内核与硬件；运行代码可以消耗已授权的全部资源；readable 不构成 run_shell 的保密边界；只读 tests 和新容器不能使任意测试 oracle 完全抵抗恶意生产代码。遇到必须放宽这些边界的任务应显式不支持，不能无提示 fallback。

Phase 3 的 Harbor 集成采用两个顺序完成的阶段。`export-harbor` 只生成可审核的生产者配置：关闭 Harbor 验证，显式收集 `/logs/artifacts/candidate.patch` 到 trial 的本地 `artifacts/candidate.patch`，首次试点并发 1、重试 0。Harbor 自己运行 Agent、管理环境、处理凭证及收集远程产物。ReproPatch 不接管该阶段的传输安全、预算或清理，也不把自己的源码只读 profile 宣称为外部生产者的权限。

操作者提供已经结束的本地 job 目录及受信任 Task map 后，`verify-harbor` 只从已记录 trial 的固定 artifact 位置有界读取普通文件，复用本项目的路径检查、8 MiB 输入限制及 `verify-patch`。不依据 Agent 或 artifact 文本选择宿主路径、Task、命令或 Docker 参数；不跟随 symlink、不解包归档，不修改 Harbor 原结果。collection manifest 的 ok/empty/failed/skipped 及缺失记录都保留；其中的 ok 只说明 Harbor 报告收集成功，仍需核查本地 bytes。

两个系统各自拥有各自阶段的容器；没有实时 verifier 插件、远程读取 fallback、嵌套 Docker 或容器内 socket 挂载。ReproPatch 的保证从本地导入边界开始，不能追溯覆盖 Harbor 已经执行的下载。固定版本试点核对产物收集、映射、失败分类与本项目资源清理，不能把 job 结束或外部 reward 当作独立验收通过。具体流程见 [验证](VERIFICATION.md#21-两个入口共用一个验证器) 和 [测试与评测](TESTING_AND_EVALUATION.md)，已核对官方能力见 [生态调研](ECOSYSTEM_REVIEW.md)。

## 11. 必要验证与迁移完成条件

测试安排和标识以 [测试与评测](TESTING_AND_EVALUATION.md) 为准。执行模块至少需要实际证明以下行为：容器不能写 /src 或访问宿主控制目录／凭证；模型只能触发六个受控工具，不能启用宿主 shell；外部补丁越界、特殊文件及不支持的修改在执行前拒绝；超时或 SDK 取消后容器及后台子进程停止；输出达到上限后停止且两份原始日志准确；构建 tmpfs 在同次 evaluation 内保留并在下一次 evaluation 重新创建。

这些是少量行为场景，不需要为每个 Docker flag 建一个独立 Mock 测试。单元测试可验证 argv 构造和边界逻辑，**只有真实 Docker 集成运行才能验收隔离和清理**。没有 daemon 的环境可以运行不依赖 Docker 的检查，但报告必须把 Docker gate 标为未执行，不能据此发布达到本规格的 MVP。
