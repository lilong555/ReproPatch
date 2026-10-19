# 故障复现、候选补丁与独立验证

状态：**planned，规格修订 2026-10-19.2；Phase 1 的核心验收规格。** 本文是复现条件、测试身份、补丁交接、观察到结论的映射以及验证证据的权威定义。全局状态和终态名称见 [状态与恢复](STATE_AND_RECOVERY.md)，输入字段见 [Task 格式](TASK_FORMAT.md)，容器与字节清单见 [执行与安全](EXECUTION_AND_SECURITY.md)。

独立验证由计划新增的 `verification.py` 承担；既有 harness／sandbox 代码的可复用部分与差距见 [现状与迁移](CURRENT_STATE.md)。本文描述拟实现行为，未宣称现有代码已经通过这些门槛。

## 1. 验证承诺与支持范围

一个 Run 只有满足全部条件，才可得到 `ACCEPTED`：

1. 固定原始 commit 在固定环境中能够构建。
2. 声明的每个 F2P 测试真实执行并出现所声明的原始失败。
3. 声明的每个 P2P 测试在原始 commit 上通过。
4. 候选只有被允许的源码修改，patch 能精确还原候选字节。
5. 独立环境从原始 commit 应用该 patch，使用新的空构建目录重新构建。
6. 原始测试身份与候选测试身份一致；所有 F2P 和 P2P 都真实执行并通过，无 skip／disabled／缺失。
7. 执行证据完整、所用配置未变，所属容器已经停止或移除。

`ACCEPTED` 的含义是“通过本 Task 的冻结验收契约”。它不证明对所有输入正确，也不证明任意恶意补丁不能迎合有限测试。模型自称完成、Agent 自检通过、patch 非空或编译成功均不能替代上述条件。

Phase 1 聚焦构建成功后由命名 CTest 用例正常报告失败的缺陷。编译失败型、超时型、必须联网、交互服务、自动补充 fixture 测试的任务先明确不支持。Task 维护者负责选择正确 oracle，Harness 负责保证按固定条件执行并保留可核查证据。

## 2. 三种 evaluation 的关系

事件和报告统一使用 `evaluation_role: baseline | agent_check | independent`；independent 即最终独立验收，不再引入另一套 purpose 枚举。

| 用途 | 源码输入 | 结果的用途 |
|---|---|---|
| baseline | 固定原始 commit 的干净源码 | 建立 F2P 原始失败、P2P 原始通过和测试身份基准 |
| agent_check | 当前 repair worktree 的独立只读快照 | 反馈模型诊断；不覆盖 baseline，不直接修改最终 outcome |
| independent | 从原始 commit 重新创建的 worktree，加冻结 candidate patch | 唯一可以产生最终 ACCEPTED 的执行依据 |

每次 evaluation 都创建自己的新容器。configure、build、测试发现和逐个测试在该容器内串行执行，共用该次 /build tmpfs；另一次 evaluation 不复用它的二进制、CTest 文件、缓存或状态。

Agent 的命名 `run_command` 自检可以调用同一底层 evaluation 能力，不复制一套编译／测试实现。`reproduce` 用于观察当前源码的 F2P，`verify` 用于观察当前源码的 F2P 和 P2P；精确工具参数和返回壳由 [Runtime](AGENT_RUNTIME.md) 定义。自检结果必须带源码快照哈希及用途，禁止在 report 中冒充 independent。

### 2.1 两个入口共用一个验证器

| Phase 1 入口 | 候选来源与顺序 | 可声明的执行范围 |
|---|---|---|
| `run TASK --engine agents-sdk` 或 `--engine fake` | 准备原始树 → baseline → SDK 驱动六个受控工具 → 冻结 candidate → independent | ReproPatch 管理的准备、模型／工具调用、候选和验证；真实／Fake 引擎明确区分 |
| `verify-patch TASK --patch FILE` | 准备原始树 → 在另一干净工作树导入候选 → baseline → independent | 输入 patch 的效果及本次独立验证；不包括外部生成阶段 |

`verify-patch` 不需要模型 SDK 或 API key，不创建 Agent，也不读取外部 Agent 的工作树作为真相。候选静态检查不合格可在 PREPARING 直接拒绝，baseline 为 null；任何可能得到 ACCEPTED 的候选仍必须实际完成原始基线和新环境验收，不能拿生产者的“测试通过”记录跳过其中之一。CLI 参数以 [CLI](CLI.md) 为准，本文不是已经可运行的命令公告。

Phase 1 的最终验证只有一次交接：SDK 结束或外部候选导入后，进入 independent 便不再调用模型。最终失败不会隐式启动额外修复轮次；自动修复可在交接前、在其预算内自行诊断和修改。原生 SDK 终止与 Harness 验收是两件事，生产者的最终文本不决定 outcome。

Phase 3 采用两段式 Harbor 集成。`export-harbor` 生成生产者 job 配置：`verifier.disable=true`，显式声明 artifact 的 source 为 `/logs/artifacts/candidate.patch`、destination 为 `candidate.patch`，初次试点并发为 1、重试为 0。Harbor 负责运行现成 Agent 并收集产物；ReproPatch 不在 Harbor 的实时验证回调中执行，也不向 Harbor 写回自己的 reward。[Harbor job 配置](https://docs.harborframework.com/jobs/configs) 和 [产物收集](https://docs.harborframework.com/jobs/artifact-collection) 提供这些现成入口；不能依赖即将移除的 `/logs/artifacts` 隐式收集。

Harbor 结束后，`verify-harbor --job DIR --task-map FILE [--output-root DIR]` 只读取操作者指定的本地 trial 元数据、collection manifest 和固定位置的普通补丁文件；根据受信任 Task map，对可用 patch 串行复用 `verify-patch`，每次仍生成新的 Run、baseline 和 independent。子 Run 的 `input_mode` 保持 `verify-patch`，不增加第三套验收或报告协议。缺失／empty／failed／skipped 的产物保留关联和分类，不靠重复下载、重新启动 Agent 或伪造空补丁补齐。后续 `eval` 只聚合这些记录，不负责启动验证。

Harbor 生产、权限、凭证、网络和远程产物收集仍属于 Harbor 自身的执行范围；ReproPatch 的 8 MiB 输入限制从本地导入开始生效，不能追溯声称此前下载已受该限额控制。两个阶段各自拥有自己的容器，不嵌套 Docker、不共享 lifecycle，也不增加第二套下载或调度框架。首个固定版本 fixture 试点须核对关闭验证时的产物收集、Task 映射、缺失与失败分类及新 Run 证据；通过前不声称连接已验证。指标与重验的归属见 [测试与评测](TESTING_AND_EVALUATION.md)，现有生态能力及许可证见 [生态调研](ECOSYSTEM_REVIEW.md)。

## 3. 不可变验收契约

PREPARING 冻结 Task、完整 commit、实际 image ID、配置／构建／CTest 模板、F2P/P2P 名单、失败签名、可编辑文件、保护文件和预算。冻结结果与哈希保存在容器无法写入的宿主控制目录。后续不重新加载原 YAML，不采信 Agent 生成的“新测试清单”。

所有 `CMakeLists.txt`、`.cmake`、声明的 protected 路径，以及任何未列入 editable 的文件都不能被修改。测试文件虽然可被模型阅读，仍使用原始 commit 中的 bytes。因为 editable 仅为逐文件声明的已有生产源码，Agent 或外部 patch 都不能添加替代测试、删掉回归输入或修改构建命令来获得通过。

Harness 不静态推导任意 CMake 程序的完整依赖关系。Task 维护者须审核会影响测试解释的间接脚本、输入、代码生成模板和头文件；若某生产文件同时决定测试预期，应缩小 editable 或选择独立 oracle。隐瞒这条责任会造成“文件没改，但 oracle 的含义变了”的假保证。

## 4. 基线复现算法

### 4.1 构建与发现

baseline 由以下步骤组成，全部属于总时间预算：

1. 从已核定的原始 worktree 创建 source snapshot，保存初始 SourceManifest。
2. 创建新的受控 evaluation 容器和空 /build。
3. 执行冻结的 configure argv；仅 `status=exited, exit_code=0` 允许进入下一步。
4. 执行冻结的 build argv；成功条件相同。
5. 执行 `ctest --test-dir /build --show-only=json-v1`，保存原始 JSON，校验选定测试存在、身份唯一、没有不支持的 fixture／附加依赖执行。
6. 按 Task 中 F2P 的顺序逐个运行测试，再按 P2P 顺序逐个运行测试，收集第 5 节定义的结果。
7. 导出有界结果文件，销毁容器并确认停止。

原始 configure／build 失败不意味着 Bug 复现成功。普通构建错误、缺失依赖或需要源码写入的项目均记录 `ERROR` 和具体 setup reason；本阶段不尝试通过模型“修复环境”。Docker 故障、资源终止或证据丢失另外保留其底层状态，不能统一伪装成 exit code 1。

### 4.2 F2P 的严格条件

每个 F2P 必须同时满足：

- 选定的是声明的唯一 CTest 名字，实际结果也恰好对应这个名字。
- CTest 命令正常退出，退出码等于该项 `expected_exit_code`。
- 结构化结果表明该测试实际运行并普通失败，不是未运行、跳过、disabled、timeout、启动失败或无法识别的终止。
- 该测试的 `output_contains` 字面签名在完整的有界命令输出中出现。
- 没有 Docker OOM、宿主超时、输出超限或执行连接不确定。

Task 签名按 UTF-8 编码后，分别在 `stdout_log` 与 `stderr_log` 指向的完整原始 bytes 中执行字面查找，**任一流命中即满足签名条件**。不拼接两个流，不推断跨流顺序，也不接受只有拼接后才出现的签名。原始文件缺失、超限或 hash 不符时 `marker_seen=null`，保留证据故障；不是先从不完整片段找到签名便算复现成功。模型只看到的 64 KiB preview 不是匹配数据源。

F2P 测试通过，或者正常失败但退出码／字面签名不符，属于 `NOT_REPRODUCED`。这并不自动说明环境损坏，只说明观察不到所声明的原始故障。失败发生在别的用例、只有“总测试失败”文本、或只有非零命令退出都不满足条件。

### 4.3 P2P 的严格条件

原始 P2P 的每项都必须有唯一实际测试结果、正常 CTest 退出码 0、无 failure/error/skipped 且未 disabled／未运行。基线存在 P2P 失败时返回 `INCONCLUSIVE/BASELINE_REGRESSION_FAILED`，不进入 Agent 修复。

只有整个基线合格，`run` 才进入 REPAIRING，`verify-patch` 才将已冻结候选交给 VERIFYING。普通测试失败或签名不符仍可在预算内完成剩余已声明测试，避免仅因列表顺序改变故障分类；资源故障、取消或证据无法安全读取则立即结束 evaluation。基线综合判定优先考虑不完整／P2P 无法通过等不确定性，再考虑 F2P 不匹配，不把未完成的测试标成通过。

MVP 不“重复到失败为止”，不自动删除 flaky 用例。一次固定基线不能证明不存在 flakiness；Phase 3 的重复实验另行记录，见 [测试与评测](TESTING_AND_EVALUATION.md)。

## 5. CTest 身份和结果解析

### 5.1 发现数据

使用官方 JSON v1 发现协议，而非解析 `ctest -N` 的人类可读行。对每个选定名字保存：

| 信息 | 比较规则 |
|---|---|
| name | 与 Task 精确相等；同名多项拒绝 |
| command | 完整 argv；baseline 与 independent 必须相同 |
| properties | 按属性名规范化后比较；保留值的类型与列表顺序 |
| backtrace | 原始证据可保留；不纳入身份，因为它是文档／来源索引 |

selected identity 是上述 name／command／properties 的规范 JSON 哈希。稳定的 /src、/build 容器路径使大部分命令无需跨宿主路径改写；不使用任意正则“去掉变化部分”让身份勉强相等。环境变量、工作目录、WILL_FAIL、SKIP 条件、PASS/FAIL_REGULAR_EXPRESSION、DISABLED 等都是会改变测试解释的属性，不能从比较中省略。

选定测试有自动 fixture setup/cleanup/required，或需要自动附加其它用例时，Phase 1 返回不支持；不偷偷添加新的测试阶段。未列入 F2P/P2P 的其它普通测试可留在 inventory 中，但不计作已验收回归覆盖。

### 5.2 精确选择

Harness 为每个名字生成适合 CTest 的字面转义表达式，并添加首尾锚点。例如名字 `parse[value]+edge` 不可直接当正则使用。每个选择表达式在 inventory 上必须恰好命中该项一次；自动附加 fixture 造成实际结果多于一项时同样不满足契约。

单项命令由冻结的 reproduce 或 verify 模板追加以下参数，操作者和 Agent 都不能另设 selector：

```text
-R <anchored-literal-name>
--output-junit /build/.repropatch-results/<harness-generated-id>.xml
--timeout <remaining-test-seconds>
```

结果文件名来自 Harness 操作 ID，不把测试名直接拼成文件路径。串行执行，不使用 rerun-failed、repeat、随机排序或“失败后自动放宽 timeout”。`--no-tests=error` 必须保留；但它仅防止零测试的常见假通过，不替代完整身份检查。官方行为见 [CTest 手册](https://cmake.org/cmake/help/v3.30/manual/ctest.1.html)。

### 5.3 结构化结果

JUnit 以固定路径在新 evaluation 的 /build 中生成，并在销毁容器前读取进宿主证据。解析必须检查恰好一项 testcase、名字一致、计数与实际子节点不矛盾，以及实际运行／失败／跳过信息。不能把 XML 缺失、空文件、解析失败或未知状态解释成“没有失败”。

内部 `TestObservation` 至少保存以下信息；它描述证据，不直接保存最终 Run outcome：

| 字段 | 内容 |
|---|---|
| evaluation_role／group／name | baseline/agent_check/independent、F2P/P2P、精确用例名 |
| command_id | `str \| null`；指向该次 CTest 的 CommandResult；未启动时为 null |
| identity_sha256 | `str \| null`；所用 name／command／properties 身份；未取得有效发现证据时为 null |
| observed_status | passed、failed、skipped、not_run、timed_out、crashed 或 invalid |
| ctest_exit_code | 外层 CTest 退出码；不冒充被测二进制自身退出码 |
| marker_seen | baseline F2P 的字面匹配结果；不适用时为空 |
| result | `EvidenceRef \| null`；宿主保存的原始 JUnit，引用遵守 ARCHITECTURE；未取得时为 null |
| diagnostic | `str`；有界 CTest status／failure 信息及明确缺失项；无诊断时为空字符串 |

上述字段全部出现；group 只取 `F2P/P2P`，evaluation_role 取本文第 2 节枚举，name 为 Task 精确名字。ctest_exit_code 是 `int | null`，marker_seen 是 `bool | null`。每次计划执行的测试都应有一项观察：上游 configure/build 失败时尚未启动的用例显式为 not_run，command_id、exit_code、result 为 null；这不构成“实际跑过且失败”的证据。

parsed status 以实际固定镜像的 CTest 输出为契约：普通 failure 与 CTest 的 timeout／not-run／异常终止分别记录；无法识别的状态为 invalid，不建立宽松“任意 XML 都兼容”fallback。最低镜像的实际 JUnit 样本应在实现期由真实 Docker 测试保留并作为解析器的小型 fixture；本规格不伪造样本运行结果。

passed 要求：CommandResult 是正常 exited/0，唯一测试确已运行，无 failure/error/skipped/disabled，也没有资源终止或证据矛盾。failed 要求存在可信的普通失败结果；timeout 和信号终止不能仅凭失败标签混入基线普通失败。候选可靠的测试崩溃是拒绝候选的证据，无法区分资源终止时则为无法确定。

CTest 自己可以把某些返回码解释成 skip，参见 [SKIP_RETURN_CODE](https://cmake.org/cmake/help/v3.29/prop_test/SKIP_RETURN_CODE.html)。因此即使 CTest 整体返回 0，也必须拒绝将 skip 记成通过。

## 6. 候选补丁交接

### 6.1 统一的 CandidatePatch

两个入口使用以下相同结构，不从模型消息或外部 trace 反向解析；EvidenceRef 定义在 [架构](ARCHITECTURE.md)：

```python
@dataclass(frozen=True)
class CandidatePatch:
    base_commit: str
    patch: EvidenceRef
    manifest: EvidenceRef
    source_tree_sha256: str
    changed_files: tuple[str, ...]  # 规范 POSIX 路径，按码点排序
```

patch 和 manifest 的引用哈希对应产物文件的实际 bytes；source_tree_sha256 对应 EXECUTION_AND_SECURITY 定义的规范源码树。`candidate.patch` 总是第 6.2 节生成的规范 diff，不保证等于外部输入文件的排版或上下文行数。原始输入另以 `producer.patch` 保存；两者通过导入后源码字节一致性建立联系。只有通过范围检查且非空的候选才形成 CandidatePatch；违规／未验修改可以作为 diagnostics 产物保留，但不能假冒有效候选。

自动修复停止时，先等待 SDK 不再派发工具，结束所有本地工具并确认相关容器已停止，再进行候选冻结；此后模型不能修改该树。外部输入先完成第 6.3 节的受控导入，再进入同一检查。复用 [SourceManifest](EXECUTION_AND_SECURITY.md) 比较初始与当前文件集合：

- 文件集合完全相同；新增、删除、重命名、特殊文件均不在 Phase 1 范围。
- 所有 Git mode 未变；不把 chmod 当作普通源码修改忽略。
- 变化只发生在 expanded editable 集合中，且不碰 protected／构建规则。
- 变化文件仍为规定大小内的普通 UTF-8 C/C++ 文本。
- 未变化文件的原始 bytes 哈希保持不变。

同时使用 NUL 分隔的 Git status／差异清单确认没有新增或其它未纳入变化。普通 `git diff` 不包含 untracked 文件，因此不能只凭“diff 看起来合法”认定没有额外文件。P1 通过工具不提供创建／删除、外部 patch 导入前检查及导入后完整清单检查解决该问题，不为后续文件新增功能提前写补丁数据库。

候选策略违规返回 `REJECTED/FORBIDDEN_PATCH` 并保留诊断，不静默删除违规修改后验收另一份补丁。如果在工具执行期间发现宿主独占目录被外部并发篡改，则属于执行不变量破坏，按 `ERROR/SOURCE_CHANGED` 处理；两者不是同一事件。

### 6.2 使用 Git 导出，不重新实现 diff

宿主使用固定配置、原始 commit 和整个 worktree 生成 canonical diff，至少固定：

```text
git diff --no-ext-diff --no-textconv --no-renames --no-color --full-index <base-commit> --
```

真实调用还须遵守执行文档的可信 Git 路径和配置规则。不能只对 editable 路径执行 diff 而隐藏其它变化；不能从模型最终消息中提取“看起来像 diff”的内容作为权威 patch。

patch 按原 bytes 保存为 patch.diff 并计算 SHA-256；不得截断后继续使用，不自动整理空格、转码、去掉 CR 或补末尾换行。Git 可能按属性形成规范文本表示，因此另保存候选完整 SourceManifest，后面的原字节往返检查不可省略。

空 patch 加正常 MODEL_FINISHED 为 `REJECTED/NO_PATCH`；空 patch 加步骤／工具／时间／上下文预算停止为 `BUDGET_EXHAUSTED`。模型／协议错误保留当前 patch 但结束为 ERROR；用户取消为 CANCELLED。存在非空合法候选且验证预留仍可使用时，即使 SDK 运行因预算或上下文限制停止，也允许进行一次独立验证；AgentStopReason 单独保留。`verify-patch` 没有 AgentStopReason，空输入或导入后没有有效源码变化同样为 `REJECTED/NO_PATCH`。

### 6.3 外部 patch 的导入

入口只接受 Git 可应用的文本 diff 文件，不接受编辑工具 DSL、可执行脚本、归档或生产者提供的已构建二进制。按下列顺序导入，尚不执行任何候选代码：

1. 把所选普通文件在大小上限内整体复制到 Run 私有产物目录，保存原始 bytes 的 EvidenceRef。输入文件在读取期间变化或读取失败属于输入／宿主错误，不继续使用一份不完整复制。可选 producer trace 同样复制为 opaque 附件，大小限制见 [执行文档](EXECUTION_AND_SECURITY.md#8-有界输出与证据导出)。不解析它来补充可信字段。
2. 冻结 Task 和原始 SourceManifest，从完整 base commit 创建新的 candidate worktree。该树与 baseline 使用的原始树分开，初始完整清单必须相同。
3. 使用受控 Git 的 `git apply --numstat -z` 对保存的 patch 做非修改性预查。逐项校验输出中的路径是规范 POSIX 相对路径，属于原始树且在 expanded editable 中；二进制统计标记、不合法路径或未知输出格式直接拒绝。`git apply --summary` 若报告创建、删除、rename 或 mode 变化，也拒绝。不自己重写 diff 解析器，Git 预查失败不能靠宽松字符串提取继续。
4. 在 candidate worktree 根先运行 `git apply --check`，再运行普通 `git apply`，沿用第 6.4 节的禁止选项；尤其不启用 `--unsafe-paths`。原始树不允许 symlink，预查后的路径名单不能绕过 Git 自己的工作树外路径保护。受控 Git 进程不执行仓库 hook、filter 或模型提供的命令。
5. 对应用后的完整文件集合执行第 6.1 节全部规则。即使 Git 接受了输入，文件缺失、集合／mode 变化、非 UTF-8、超限或范围越界仍拒绝；在这一步通过前不创建候选执行容器。
6. 从此树生成规范 `patch.diff` 和 SourceManifest，形成 CandidatePatch。独立验证必须再从 base 应用这份规范 patch，检验往返后的完整 bytes 相同，不能因为外部工具宣称已应用或通过测试而跳过。

输入 diff 的元数据、上下文行数或空白排版可以与 Git 重新导出的规范 diff 不同；这不是修复源码的许可。规范化只转换 patch 的表示，不允许改变其应用后的源码效果。原始文件保存哈希用于审计导入来源，CandidatePatch 的哈希和完整清单用于后续复现。若 Git 属性使效果无法原样往返，明确拒绝，不偷偷修正内容。

静态范围／格式失败可以在 PREPARING 结束，使用 `FORBIDDEN_PATCH` 或 `PATCH_APPLY_FAILED`，无需先花时间运行 baseline。已通过导入的候选必须重跑第 4 节原始基线。外部 trace 中的命令、奖励、测试通过信息、成本、环境声明和作者名称均是生产者自述，不加入可信 observations；记录在报告的 producer 中供人工核对。

### 6.4 从原始 commit 应用候选

最终验收不能直接把 repair worktree 重新命名成 verifier。必须：

1. 从同一固定 commit 创建新的独占 detached worktree，使用同一受控 Git 配置。
2. 确认该树没有额外文件或未提交变更，初始清单与 baseline 源码一致。
3. 校验 patch.diff 的保存哈希和范围。
4. 在 worktree 根执行 `git apply --check`，通过后执行普通 `git apply`。
5. 不使用 reverse、三方合并、reject、`--unsafe-paths`、忽略 whitespace 或 whitespace fix；不能以修改后的 patch“修好应用失败”。
6. 对应用后的完整文件集合重新计算 SourceManifest，必须与冻结候选逐字节及 Git mode 相同。
7. 按同样 flags 重新生成 canonical diff，必须与保存 patch 的哈希一致。
8. 从该 verifier worktree 创建新的只读 snapshot，交给全新 independent 容器。

patch 无法应用、候选／应用结果不等价或保护文件不一致时停止，记录 REJECTED 和具体原因。若根因是宿主 I/O、Git 进程故障或持久化文件损坏，则保留 ERROR／INCONCLUSIVE 的基础设施分类，不将工具故障硬说成错误修复。

普通 Git apply 不创建 commit，且默认不会为了应用部分 hunk 而留下部分接受结果；本项目不打开会改变该语义的选项，见 [Git apply](https://git-scm.com/docs/git-apply)。无论应用阶段是否被中断，都不能把未完成的 verifier tree 当成成功快照复用。

CRLF、BOM、文件末尾换行和可执行位以真实 bytes／mode 清单为准。若某种 Git 属性布局导致 patch 无法原样往返，返回明确的不支持／不等价结果；不要为了扩大覆盖而悄悄把候选转换成另一份源码。二进制和文件新增支持留待有真实任务后单独设计。

## 7. 最终独立执行与判定

### 7.1 执行步骤

independent 按同一 configure → build → inventory → F2P → P2P 顺序运行，使用相同的实际 image ID、CPU／内存／PID限制和命令模板。与 baseline 的差别只应是合法 candidate patch；所有不同的 Git 源码身份都通过 patch／清单记录。

候选 inventory 的选定测试身份必须逐项等于 baseline。缺少、重复、新增附加测试、禁用或改变解释属性时拒绝验收，不能把剩下的测试重命名为新 P2P。执行后实际 JUnit 集合仍须恰好与每次选定名字对应，防止只通过发现阶段却没有真正运行。

所有候选 F2P 都要通过；它们不再要求出现原始失败签名。所有候选 P2P 也都要通过。P2P 是声明的回归集，不是对整个仓库全部行为的覆盖承诺。

资源／证据故障发生后立即结束；明确发现普通 build/test 回归时，可以在当前预算内收集剩余用例供诊断，但不会因此放宽通过条件，也不重复测试以寻找一次成功。

### 7.2 终态映射

下表是普通 Run 的判定规则；Read-only inspect/report 的退出行为见 [CLI](CLI.md)。状态名不在本文重新定义。

| 观察 | Outcome | 典型 reason_code |
|---|---|---|
| 基线普通 configure／build 失败，或已知任务布局不支持 | ERROR | BASELINE_CONFIGURE_FAILED、BASELINE_BUILD_FAILED、UNSUPPORTED_TEST_LAYOUT |
| 基线 F2P 通过，或正常失败但签名／退出码不符；其余基线完整合格 | NOT_REPRODUCED | F2P_PASSED、FAILURE_SIGNATURE_MISMATCH |
| 基线 P2P 失败、测试未运行／缺失、证据损坏、资源终止或基线未完成 | INCONCLUSIVE | BASELINE_REGRESSION_FAILED、BASELINE_INCOMPLETE、EVIDENCE_INVALID |
| 候选越界、改变文件集合／mode、外部 diff 不支持、无法应用或字节往返不等价 | REJECTED | FORBIDDEN_PATCH、PATCH_APPLY_FAILED、PATCH_ROUNDTRIP_MISMATCH |
| 外部候选无有效变化，或自动修复正常结束但无 patch | REJECTED | NO_PATCH |
| 候选正常构建失败、指定测试普通失败或有可靠证据的测试崩溃 | REJECTED | CANDIDATE_BUILD_FAILED、F2P_FAILED、REGRESSION_FAILED |
| 候选可靠发现测试身份改变、必需用例删除／disabled／skip | REJECTED | TEST_IDENTITY_CHANGED、REQUIRED_TEST_NOT_RUN |
| 候选 timeout、OOM、output_limit、Docker 断连、JUnit 缺失／畸形、执行结果无法确认 | INCONCLUSIVE | VERIFICATION_TIMEOUT、RESOURCE_TERMINATION、EVIDENCE_INVALID |
| Agent 预算停止且没有可交接候选 | BUDGET_EXHAUSTED | 保留具体 AgentStopReason |
| 模型／协议或宿主控制面错误 | ERROR | MODEL_ERROR、PROTOCOL_ERROR、对应宿主错误码 |
| 操作者取消 | CANCELLED | USER_CANCELLED |
| 全部规则通过且所属容器停止确认 | ACCEPTED | VERIFICATION_PASSED |

优先级为：取消／控制面错误先保留自身语义；baseline 有不完整证据不进入修复；independent 中已经可靠确定的候选错误足以 REJECTED，后续其它用例的诊断中断不能洗掉该拒绝证据；没有确定拒绝但证据不完整为 INCONCLUSIVE；只有所有 gate 都完整通过才 ACCEPTED。强制终止产生的退出码不是普通构建／测试失败证据。

清理未能确认容器停止时保留主因和 cleanup_error。若之前唯一候选结论是 ACCEPTED，则必须改成 INCONCLUSIVE；已经确定的错误候选仍可 REJECTED，但不能声称资源已成功清理。

## 8. 预算语义

baseline、所有 agent_check 和 independent 都计入 Run 总墙钟预算。Agent 不能消耗预留的 verification_reserve_seconds，另外最后 10 秒属于清理。independent 每条命令的有效超时为 Task command cap 与 independent 剩余可执行时间的较小值；CTest 的单测试 timeout 不能越过宿主 deadline。

`verify-patch` 的墙钟从本次 Run 创建开始；读取输入、导入、准备和 baseline 共用总时长减 verification reserve 再减清理余量后的前段预算，不能提前侵占最终验证预留。它不设置模型／工具调用循环，也不把操作者先前生成补丁的时间和费用算成可控资源。报告中的 Agent 计数为零、生产者 token 用量未知；不把未观测的外部生成活动计成免费。

剩余时间不足以启动下一项必需验证时，明确记录未执行项并返回 INCONCLUSIVE，不能跳过 P2P 或拿 Agent 最近一次自检补齐。independent timeout 不返回模型继续“快速试一次”，不修改预算、不自动降低编译并行度再跑。需要不同资源或时间应创建新 Task／Run，并让评测记录条件变化。

baseline 或 independent 输出触及原始日志上限时，本次证据不完整，即使已看到期望失败字符串或通过字符串，也不能接受。命令输出限制的数值及停止行为只有 [执行文档](EXECUTION_AND_SECURITY.md) 一处定义。

## 9. 报告与验证返回值契约

### 9.1 EvaluationEvidence

`EvaluationEvidence` 是一次 baseline／agent_check／independent 的结构化观察，JSON 字段如下。所有字段必需，可空位置明确写 null；它本身不含 Run outcome。

| 字段 | 类型与语义 |
|---|---|
| `evaluation_id` | 32 位小写 UUID；同 Run 内唯一 |
| `evaluation_role` | baseline / agent_check / independent |
| `source_tree_sha256` | 本次实际快照的规范源码树摘要 |
| `source_manifest` | EvidenceRef；保存本次源树的完整清单 |
| `started_at`, `finished_at` | UTC RFC 3339；后者是控制端本次观察结束时间，无法确认清理时仍记录结束观察 |
| `configure`, `build`, `discovery` | CommandResult 或 null；未启动该命令时 null，不能构造 exit 0 |
| `inventory` | EvidenceRef 或 null；原始 `--show-only=json-v1` 输出 |
| `identities` | object，键为已成功核对的选定测试名，值为 identity_sha256；缺失键不代表测试不存在／通过 |
| `tests` | TestObservation 数组；每项对应本次计划执行的名字，保持 F2P 后 P2P 顺序；未执行也显式列出 |
| `commands` | 所有实际命令的 CommandResult 数组，含逐项 CTest 和有界证据读取；command_id 唯一，按启动次序排列 |
| `cleanup` | object：`container_id: str 或 null`、`confirmed: bool`、`errors: list[str]`；已证实未创建任何容器时可 confirmed=true 且 id=null；创建请求结果未知时即使无 ID 也为 false |

configure/build/discovery 与 commands 中同 command_id 的内容必须一致，只是便于读取的同一观察投影；不允许分别更新。测试 command_id 指向 commands 中对应 CTest 项。容器 cleanup.confirmed 只在明确停止／不存在后为 true；各命令的中间 cleanup_confirmed 不会覆盖该最终值。

测试、清单和日志产物统一使用 EvidenceRef。命令分别通过 Runtime 的 `stdout_log`、`stderr_log` 引用原始 `stdout.bin`／`stderr.bin`，事件 JSONL 不承担命令日志编码。JUnit 保留收到的 XML 原始 bytes。原始 inventory 也保存 bytes，解析后的 identities 独立计算，不能重序列化覆盖原证据。每个 TestObservation 的 result 缺失必须影响判定，不能仅在 Markdown 报告中加警告后仍通过。外部 producer trace 永远不进入 EvaluationEvidence 的 commands 或 tests。

`verification.py` 的候选验收返回一个小数据对象：

```python
@dataclass(frozen=True)
class VerificationResult:
    outcome: Literal["ACCEPTED", "REJECTED", "INCONCLUSIVE"]
    reason_code: str
    independent: EvaluationEvidence | None

def verify_candidate(
    task: ResolvedTask,
    baseline: EvaluationEvidence,
    candidate: CandidatePatch,
    run: RunContext,
) -> VerificationResult: ...
```

输入 baseline 必须已经满足第 4 节条件；函数从原始 commit 重建并核对候选，完成清理后返回。补丁应用失败时 independent 可为 null；宿主文件／数据库错误继续向任务边界传播，不能强行转换成 REJECTED。基线与 agent_check 复用普通 `evaluate_checks` 执行函数生成 EvaluationEvidence；只有上述入口可以根据完整基线、候选和 independent 生成 ACCEPTED。

### 9.2 report.json v1

最终 `report.json` 是一个 object，下列顶层字段全部出现。`state` 固定 FINISHED；未形成可信终态时不写假的最终报告，inspect 根据已有 DB／事件显示未完成。Phase 2 无法提交数据库的恢复失败另写 recovery-error.json，见状态文档。

| 字段 | 类型／准确结构 |
|---|---|
| `schema_version` | 整数 1；独立于 Task 与 DB 版本 |
| `run_id`, `task_id` | string；原 Run 和 Task 身份 |
| `input_mode` | `run` 或 `verify-patch`；记录本次实际入口，不从模型／外部 trace 推断 |
| `state`, `outcome`, `reason_code` | FINISHED、STATE_AND_RECOVERY 定义的 Outcome、稳定错误／结论码；本文 §7 为验证原因码权威 |
| `provenance` | object；字段见下方，不以缺省成功值填充未冻结输入 |
| `task_original`, `task_resolved` | EvidenceRef；后者可 null，例如 PREPARING 失败；前者为真实原 YAML |
| `timing` | object：`created_at`, `finished_at`, `deadline_at` 为 UTC RFC 3339；`elapsed_ms` 为非负整数 |
| `agent` | object：`agent_stop_reason` 为 AgentStopReason 或 null；`steps_used`, `tool_calls_used` 为非负整数；`http_attempts` 为非负整数或 null，规则见下方 |
| `engine` | object：`kind: agents-sdk \| fake \| none`、`versions: dict[str,str] 或 null`、`model_name: str 或 null`、`api_base: str 或 null`；规则见下方 |
| `producer` | object：`name: str 或 null`、`patch: EvidenceRef 或 null`、`trace: EvidenceRef 或 null`、`trace_trust: external-untrusted 或 null`；外部输入来源，不是可信执行日志 |
| `usage` | object：`input_tokens`, `output_tokens`, `total_tokens` 为非负整数或 null；`synthetic: bool`；Fake 为 true，外部生成用量未知 |
| `cost` | object 或 null；Phase 1 为 null；Phase 3 如可估计则 `{amount_usd, pricing_source, pricing_date}`，日期为 YYYY-MM-DD，不作账单硬上限 |
| `candidate` | CandidatePatch 的 JSON 表示或 null；tuple 编码成 array；仅合法冻结候选进入此字段 |
| `baseline` | EvaluationEvidence 或 null；从未取得可记录的 baseline 时为 null |
| `independent` | EvaluationEvidence 或 null；没有最终独立执行时为 null，不能用 agent_check 填入 |
| `cleanup` | object：`active_code_stopped: bool`、`workspace_retained: bool`、`errors: list[str]`；只有本 Run 的执行容器、Git／Docker 客户端及本地工具执行已确认停止时前者才为 true；不证明远端模型已停止或外部生产者已清理 |
| `events_last_seq` | 非负整数；本报告所依据的一致性事件截止序号 |
| `trace` | EvidenceRef 或 null；仅为 ReproPatch SQLite 导出的领域事件 JSONL，可引用本地 SDK 原生产物；不得用 producer.trace 填充，导出失败不得伪造空成功轨迹 |
| `diagnostics` | EvidenceRef 数组；脱敏诊断／未验候选等；空数组只表示无附加产物 |
| `limitations` | string 数组；至少声明固定 oracle 的覆盖范围、Docker 共享内核；run 声明模型生成不确定性，verify-patch 声明外部生成过程／预算未受管且 trace 未验证 |

`provenance` 必需字段为：`task_source_sha256: str`、`task_sha256: str 或 null`、`base_commit: str 或 null`、`image_id: str 或 null`、`image_repo_digests: list[str]`、`platform: str 或 null`、`software_version: str`、`implementation_sha256: str`、`tool_versions: dict[str,str]`。implementation_sha256 由本次实际执行的 ReproPatch 包内 Python 文件及固定提示／工具定义计算：按包内相对 POSIX 路径排序成 `{path,sha256,size_bytes}` 数组，对该数组使用与 SourceManifest 相同的 UTF-8／sorted keys／紧凑分隔／无末换行规则序列化后取 SHA-256；不包含时间和本地绝对路径。第三方包不假称已纳入源码哈希：开发／实验锁文件固定依赖，实际参与自动修复的 SDK 版本记录在 engine.versions，至少包含 `openai-agents` 及直接使用的 `openai`。tool_versions 记录实际观察到的 git、docker_client、docker_server、cmake、ctest、cxx、kernel；无法完成的项缺失并保留原因。空 RepoDigests 表示本地镜像没有可用仓库 digest，不代表没有 image ID。

`engine.kind` 表示已选择的运行方式：agents-sdk 使用指定模型及去除秘密信息的端点；fake 的 model_name、api_base 均为 null。versions 保存实际加载到的包版本，尚未加载时可为 null，不能从锁文件假造已运行版本。`verify-patch` 使用 `{kind: "none", versions: null, model_name: null, api_base: null}`，不借外部生产者名称伪装本地引擎。

`producer` 在 run 中四个字段全部为 null。verify-patch 的 name 来自可选 `--producer`，不提供则 null；patch 引用原始导入文件，复制未完成时 null；trace 引用整体复制的可选外部附件，有附件时 trace_trust 固定为 `external-untrusted`，否则两者均为 null。这些字符串和附件不执行、不自动作为 Markdown/HTML 渲染。producer.patch 与 candidate.patch 不同是允许的，必须用 §6.3 的导入效果与 §6.4 的字节往返来核对。

`agent.steps_used` 是本 Run 消费的 SDK 模型 turn 数，`tool_calls_used` 是准入的完整响应批次所包含的调用数；具体扣减规则只由 [Runtime](AGENT_RUNTIME.md) 定义。http_attempts 是实际观察到的模型 HTTP 请求尝试总数，不能把 turn 数直接复制到此字段；有重试或未知请求而无法完整观测时为 null。未进入 SDK 或使用不联网的 Fake 时 http_attempts 为 0。verify-patch 的 agent_stop_reason 为 null、steps_used/tool_calls_used/http_attempts 均为 0，这三个零只描述 ReproPatch 本次执行，不描述外部生成过程。

完整有效命令、允许文件和预算从 task_resolved 的 EvidenceRef 取得，实际 argv、阶段和结果从 EvaluationEvidence.commands／事件取得，不在报告中重新创造第二套 Task 字段。原生 SDK 输入／输出快照及 agent_check 由 ReproPatch 领域事件引用，不建立第二套四角色对话记录。不透明 continuation 只留在私有原生产物中，不作为推理文本展开或写入 report.md。读者校验所有被读取 EvidenceRef 的大小和 hash；缺失／损坏应显示“证据不可核查”，不把读取失败转换成新的测试失败或擅自修改原结论。

usage 的三个聚合字段分别只有在所有实际模型尝试均有该项已知用量时才能求和；出现未知请求或缺失 usage，该字段为 null。真实引擎显式设置 `ModelSettings(preserve_raw_usage=True)`，按原始 `raw_usage` 中各字段的存在性和 null 值判断是否已知，不能用 SDK 归一化时补出的零代表实际零消耗。已知部分的每次用量仍在事件中；Fake 写零并明确 synthetic=true。verify-patch 的三个 token 字段均为 null、synthetic=false，producer trace 的自报数字不提升为可信用量；成本同样不凭猜测补零。`elapsed_ms` 正常进程内取 monotonic 累计，恢复后的总用时按状态文档计入离线时间，并在时间基准异常时保留诊断，不倒改原 deadline。

### 9.3 生成和一致性

Harness 在清理后确定最终 outcome/reason_code，VerificationResult 中的验收判断按 §7 优先级合入 Run 报告；控制面错误或取消不能被候选通过覆盖。report.md 只是上述 JSON 的人类可读投影，必须区分“未运行”“失败”“通过”“未知”，不可用空数组和默认 true 补齐证据。

Phase 1 继续使用 SQLite 作为审计事件唯一来源，先提交最终审计事件，按 events_last_seq 导出 JSONL，再原子写 report.json／report.md。最终审计事件提交后 outcome 不再因导出失败改变：JSONL 导出失败时，若仍能写文件，则继续生成 trace=null 的 report.json；任一必需导出失败均向 stderr 报 ARTIFACT_EXPORT_FAILED，本次 CLI 操作退出 3，优先于基于 outcome 的普通退出码。report.json 成功而 report.md 失败也按此规则处理。inspect 从最终事件／P2 runs 表显示“运行已结束，报告导出不完整”，不因报告缺失重新执行 Run。JSON 与 Markdown 各自原子替换，不承诺跨文件原子性。Phase 2 的状态／事件事务和可重建报告见 [状态与恢复](STATE_AND_RECOVERY.md)，验证模块不另开 JSONL 状态机。报告生成不执行源码、不调用模型，也不把重导出当成新的修复尝试。

## 10. 能防什么、仍不能证明什么

冻结 Task、host-only edit、只读源码和全新 independent build 能防止修改 YAML 验收标准、直接编辑 tests/CMake、沿用 Agent 伪造的二进制、遗漏新增文件以及未跑测试却仅看 exit 0 等常见问题。测试身份及 JUnit 检查继续拒绝候选间接导致的删测、skip、选择集变化。

但测试程序与候选生产代码仍会在同一个受限环境中运行。生产代码可能识别测试输入、影响断言依赖、在 /build 内制造输出，甚至有意迎合有限 oracle。只读挂载和结构化 XML 都不会自动解决这些语义问题；本项目不声称生成的 JUnit 已得到密码学可信执行证明。面向这种对抗需求时，应另选更强的外部黑盒 oracle、审核补丁或升级隔离方案，而不是向 MVP 添加大量无依据的扫描器。

## 11. 实现验收要求

具体测试 ID 及命令以 [测试与评测](TESTING_AND_EVALUATION.md)、[实施计划](IMPLEMENTATION_PLAN.md) 为准。本模块只要求保护有独立价值的行为：

| 场景 | 应证明的行为 |
|---|---|
| 同一正确 fixture 的自动修复与外部 patch | 两条入口均实际建立 F2P 失败／P2P 通过的基线，再从 commit 加 patch 重建；外部路径不导入 SDK、不需要模型密钥 |
| F2P 原本通过／签名不符 | 不进入修复；分别在 stdout 或 stderr 命中可复现，只有跨流拼接才命中时拒绝复现 |
| 错误候选／P2P 回归 | 拒绝验收并定位失败用例 |
| 必需测试被移除、skip 或选择为空 | 不会因 CTest 返回 0 而接受 |
| Patch 包含非 editable 修改／mode／新增删除／越界路径 | 内置及外部候选共用范围检查，在运行最终候选前拒绝且宿主其它路径未改 |
| CRLF／末尾换行的普通文本编辑 | patch 往返后 bytes 和 mode 与冻结候选一致 |
| timeout 或损坏／缺失 JUnit | 无法确定；容器清理，不能调用默认成功 fallback |
| Agent 自检或外部 trace 宣称通过，但 independent 构建失败 | 最终仍拒绝；外部附件只进 producer，不提升为可信测试证据 |

同一小型 fixture 可参数化覆盖相关拒绝行为，不为 Git、CTest 自身的每个分支重复造测试。真实 Docker 主流程和一个真实模型接口的结果必须实际核查后才能满足 Phase 1 gate；本次规格交付不声称这些测试已经运行。
