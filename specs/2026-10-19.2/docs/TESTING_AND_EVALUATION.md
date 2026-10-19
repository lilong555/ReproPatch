# 开发测试、评测与发布规范

状态：目标规范；本轮仅审查规格，没有重新执行产品测试。旧测试证据及其限制见[CURRENT_STATE](CURRENT_STATE.md)。本文统一测试 ID、指标分母、CI 和 release gate；逐任务顺序见[实施计划](IMPLEMENTATION_PLAN.md)。

## 1. 测试选择原则

测试应保护“用户获得可信补丁与明确失败”的行为。现有测试有价值则保留；不因旧数字较多就删除，不以历史测试数量或100%覆盖率作为目标。新增测试必须在函数注释／PR说明中用一句话说明阻止什么重要回归；简单属性读取、直接转发和第三方SDK自身行为不单独测试。

优先级为：主链路 → 错误验收 → 真实隔离与清理 → 当阶段实际增加的恢复／评测逻辑。每个测试ID代表一个**行为义务**，可由少量参数化案例覆盖，不代表必须创建等量测试类。尽量使用临时目录、真实小Git仓库、SDK ScriptedModel脚本；不搭建模拟云服务、复杂mock图或测试编排框架。

## 2. 最小测试矩阵

| ID | 保护的行为和最少情形 | 为什么需要 | 阶段／建议位置 |
|---|---|---|---|
| T01 | 合法v2解析、v1明确拒绝、重复key／越界路径／可变commit或image拒绝、规范集合排序 | 防协议漂移和输入锁定失效；不逐字段排列几十种相似错误 | P1 `tests/test_task.py` |
| T02 | 基线目标正常失败＋P2P通过；目标已通过；错误签名；P2P失败；用例未执行 | 防把环境／错误测试当Bug复现；用一组参数化基线结果测试 | P1 `tests/test_verification.py` |
| T03 | SDK ScriptedModel自动修复与纯核心verify-patch均可接受正确patch；干净往返、manifest一致、原仓库不变 | 主链及实际开源复用入口；含CRLF／无尾换行往返，不用模型网络证明业务流程 | P1 `tests/test_harness.py` |
| T04 | 错误／无补丁不能ACCEPTED；修改tests/CMake／新增删除mode变更被拒；skip／空／缺用例不能通过 | 防最重要的错误验收；不测试CTest库自身所有分支 | P1 `tests/test_verification.py`,`test_workspace_tools.py` |
| T05 | 真实容器内派生sleep或后台子进程超时后消失；输出洪泛达到上限会终止；daemon失败清理未确认不能继续 | 防孤儿进程、无限日志和假清理；不能只mock docker rm返回0 | P1 `tests/test_docker_integration.py`,`test_process_sandbox.py` |
| T06 | .git/宿主哨兵/API key不可见、/src不能写、网络与权限受限；路径穿越／symlink拒绝；清理不碰其它Run | 验证真正的权限边界；使用哨兵，不接触真实秘密 | P1 `tests/test_docker_integration.py`,`test_workspace_tools.py` |
| T07 | SDK只注册6工具、公开hook先准入；最后turn工具执行、整批超预算不执行、context超限停止、原生reasoning项保留、timeout／infra异常穿透 | 防复用SDK时丢失预算／权限／错误语义；全部用ScriptedModel与有界工具，不测SDK全部内部行为 | P1 `tests/test_models_cli.py`,`test_harness.py` |
| T08 | report与DB事件对应、JSONL可重导、未知usage不变成0、错误保留cause/traceback、查询退出码不随outcome变化 | 防审计不一致与误导性诊断 | P1 `tests/test_events_reports.py` |
| T09 | 安全input边界pause/resume；open segment拒绝；缺损checkpoint／重复controller拒绝；预算不退款 | 防未知副作用重做、上下文损坏、重复付费；只在P2实现时加入 | P2 `tests/test_recovery.py` |
| T10 | Trace Replay不调用Model/工具/Docker，只读取既有事件 | 防将看日志变成外部副作用 | P2 `tests/test_recovery.py` |
| T11 | 手算表含Harbor producer失败、验证未开始、缺report／DB损坏、未知usage；新旧native状态映射严格且分类不丢 | 防只统计有report样本、把reward0混为同一种失败、造零费用 | P3 `tests/test_evaluation.py` |
| T12 | Execution Replay新Run只重新验收保存patch；不调用模型或执行历史Shell，原Run字节不变 | 防把重放记录变成重复执行不可信动作 | P3 `tests/test_replay.py` |

T03可用tests内的可信本地fixture执行器快速开发，必须标 `isolated=false`；发布证据还要在Docker版本跑同一主链。该执行器不接受任意用户Task、不随生产包暴露。小测试解析预录CTest结构化数据即可，唯隔离／进程终止义务必须有真实Docker测试。

## 3. 阶段验证 gate

| Gate | 必须做什么 | 不得替代它的证据 |
|---|---|---|
| V-DOCKER | 显式启用Docker标记，真实daemon下跑正确修复、错误补丁、超时和隔离；报告isolated=true | host fixture通过、mock docker命令、Docker代码存在 |
| V-LIVE | 人工授权一个真实端点／模型，至少完成一次合法工具调用回传及正常结束；保存模型配置、usage和实际结果 | Mock脚本成功、伪造HTTP成功、只列了SDK依赖 |
| V-CURATE | 每项真实任务锁commit/image/测试/provenance，人工确认原失败及参考补丁通过；参考补丁不提供给Agent | 只找到issue链接、假定上游benchmark全部兼容 |
| V-HARBOR | 固定Harbor版本／1个fixture，显式artifact收集→本地产物导入→RP独立Docker判定，包含收集失败／无patch／未知样本 | 只生成task.toml、把Harbor默认sandbox当RP profile、用原生reward冒充验收 |
| V-RELEASE | 干净安装＋本地CI等价命令＋真实Docker gate＋可重导报告／trace＋文档／包内容检查 | 历史旧HEAD报告、skip而非执行、截图 |

V-LIVE验收的是适配兼容性，随机模型未修好任务也须如实报告。面向公开展示的稳定版本应另保留至少一次真实模型修复成功的可复核案例；不能用这一个案例估计一般成功率。若当前无模型凭证，P1其它工作可继续，但这一gate保持未完成，不能说已完成全部里程碑。

## 4. Phase 2 故障注入范围

只测试会改变恢复判定的少量边界，不为每条SQL或每个SDK内部状态构造测试：

1. 通过`--pause-after-step 1`在公开input_filter提交安全checkpoint：恢复使用相同native Items与源码效果，累计额度／deadline不重置；不产生第二次已完成工具调用。
2. `segment_open=true`提交后到下一安全边界之间，包括模型请求未知、工具修改已发生但未到完整边界、完整回复已存但未提交checkpoint：一律核对清理后RECOVERY_FAILED，不自动补交／回滚／重做。参数化两三个代表时点即可。
3. checkpoint文件写入后DB引用前，以及已引用文件缺失／hash不符：孤儿不当有效checkpoint；损坏不可恢复，不创建空DB掩盖。
4. 重复controller与真实Docker遗留容器：互斥锁拒绝第二writer，恢复先停止确认属于本Run的容器；无法确认清理不得继续模型或验收。

测试用ScriptedModel、临时Git仓库和少量命名failpoint，不用真实付费模型做SIGKILL实验。中断发生在PREPARING／REPRODUCING／VERIFYING不自动续执行，用新verify-patch Run重新做完整验收。每项核对保留的候选、事件、累计预算及明确结局。

本版主动降低恢复范围。高“恢复成功率”不能通过盲重未知操作获得；安全失败同样是预期结果，但必须单列，不能算成修复成功。

## 5. Fixture 与真实任务演进

第一批规划如下，除了negative-maximum已有代码外，其余尚未实现：

| 任务 | 源码缺陷 | F2P／P2P设计 | 用途 |
|---|---|---|---|
| negative-maximum | 用0初始化最大值，全负输入错误 | F2P negative_values；P2P positive_values/empty_values/mixed_values | P1完整路径与面试演示；已有历史受信任本地证据 |
| inclusive-range-sum | 仅`l == 0`分支遗漏闭区间右端；`l > 0`和空区间分支正确 | F2P prefix_singleton/prefix_full；P2P suffix_interval/suffix_singleton/empty_interval，具体输入见下文 | P3边界语义；不靠UB或挂起复现 |
| parse-signed-integer | 合法负号／边界状态处理错误 | 负数转换F2P；合法正数、非法字符、空输入P2P | P3第二类实现逻辑；固定输入输出 |

`inclusive-range-sum`使用0-based闭区间，前缀和定义为`prefix[0] = 0`、`prefix[i+1] = prefix[i] + values[i]`。原缺陷仅为`l == 0`时返回`prefix[r]`；`l > 0`时正确返回`prefix[r+1] - prefix[l]`，`l > r`先返回0。固定非零输入`[2, 5, 7]`：F2P的`[0,0]`应为2、`[0,2]`应为14，原实现分别返回0和7；P2P的`[1,2]`为12、`[2,2]`为7、空区间`[2,1]`为0，原实现均通过。各输入独立命名为表中CTest用例；F2P检查失败时打印固定签名并正常返回非零，不用abort、未定义行为或挂起复现。

给每个任务保留一个已知正确参考补丁和一个已知错误补丁，用于验证器实验；Agent初始上下文和可读快照不得包含参考补丁。fixture是自有测试案例，不能宣传成真实开源仓库缺陷。

Phase 3目标先收集2–3个可以在预算内构建的真实C++缺陷；数量是工作目标，最终以真实通过curation的实例为准。可考察SWE-bench Multilingual涉及的C++仓库，必须逐实例审核，不自动接受整套任务。上游说明与评测语义来源：[Multilingual](https://www.swebench.com/multilingual.html)、[Evaluation guide](https://www.swebench.com/SWE-bench/guides/evaluation/)。

真实历史Bug的回归测试常在后续提交才出现。不要把基线测试不存在的任务塞入MVP协议：curator可先把**经过人工审核、只增加测试的oracle patch**应用于原Bug commit，创建独立prepared commit，再把该完整OID作为Task base。provenance记录上游Bug commit、oracle patch hash、prepared commit、原始issue/fix链接、许可、镜像、参考修复证据。这是任务准备过程，不由修复Agent进行；源码实现仍保持原缺陷。最终源码补丁基于prepared commit导出，向上游应用前人工核对。

不兼容当前CTest／文件／预算边界的任务先标 excluded及原因，不为了导入一个任务临时增加一套通用测试解析器。若大规模使用SWE-bench，优先复用其上游runner／安装脚本而非复制各种仓库特殊逻辑。

## 6. 复用 Harbor 的小型评测路径

### 6.1 Task目录清单

suite只是一份内容目录，不包含条件、重试、工作流或调度算法：

```yaml
version: 1
id: cpp-bugs
tasks:
  - task: ../tasks/negative-maximum.v2.yaml
    split: smoke
    source_kind: fixture
    provenance: ../provenance/negative-maximum.json
```

路径相对suite；Task ID不重复。split为smoke/evaluation，source_kind为fixture/real。默认评价evaluation，开发中反复使用的smoke另表展示。suite与Task、prepared commit、image hash组成fingerprint；不另定义一套Harbor任务DSL。

P3目标先3个小fixture、2–3个真实C++任务，以实际curation通过为准。不强制导入整个SWE-bench；不能用自有fixture冒充真实缺陷。每次实验开始前冻结参与任务、排除理由、producer版本／模型、预算与重复次数。

### 6.2 两段式产物接入

官方Harbor已有作业、Coding Agents、轨迹、artifact collection和原生separate verifier。本项目直接使用它的**producer作业与产物收集**，在已结束的本地结果之后复用既有verify-patch；不自建任务调度、worker池、队列、下载器或ATIF方言。[Agent集成](https://docs.harborframework.com/agents/pre-integrated-agents)、[原生产物收集](https://docs.harborframework.com/jobs/artifact-collection)、[已有独立环境](https://docs.harborframework.com/tasks/separate-verifier)。

P3-02只实现一个`integrations/harbor.py`，负责静态导出、读取锁定版本的本地结果格式及现有验证函数的串行调用，不实现Harbor内部插件：

1. `export-harbor`从审核Task生成任务目录、instruction、固定源码输入和可信`task-map.json`。producer允许在自己的临时副本修改代码，必须输出`/logs/artifacts/candidate.patch`；不复制宿主原仓库的Git配置／凭证。必要的用于生成diff的Git仓库在producer环境内初始化，原base源码内容由Task hash／manifest标识。
2. job配置显式关闭Harbor验证：`verifier.disable: true`。Harbor只生成补丁，不输出ReproPatch验收reward。显式声明artifact，不依赖即将移除的`/logs/artifacts`自动收集；并发固定1、job重试0、明确producer timeout和资源。使用上游CLI `harbor run -c producer-job.yaml`，本项目不再包装一个收费任务启动器。
3. Harbor完成producer与artifact collection后，操作者执行`verify-harbor --job DIR --task-map FILE`。本项目只读取已结束本地job/trial元数据与collection manifest；目标patch为`<trial-dir>/artifacts/candidate.patch`。不连接正在运行的Harbor环境，不调用BaseEnvironment下载、不从URL取文件。
4. 对有效本地普通文件，按P1相同8MiB／路径／类型规则复制冻结，调用同一verify-patch应用函数，得到新RP Run与完整baseline/independent证据。Task只能由可信task-map选择；producer提供的路径、命令、Task YAML、测试结果和report不可覆盖它。
5. 每次verify-harbor调用创建独立导入目录及index.json，位置以[CLI](CLI.md#13-harbor批次与eval输入)为准，结构见下节。关联Harbor job/trial、Task fingerprint、RP Run ID和report hash。每trial最多验证一次；再次调用是明确的新验证观察，不覆盖旧索引，不自动恢复缺项。中断留下的未关联条目在eval中为verification_missing，不会删除原trial。
6. Harbor拥有producer及其下载／收集过程；ReproPatch拥有之后新建的baseline/verify容器。安全保证从本地patch导入开始，不能声称保护了未受托管的生成或上游下载阶段。任务使用者须按Harbor自身文档配置该阶段权限；首批使用受信任fixture。

与这个接口对应的**目标job配置片段**如下，Task导出和选定Agent／模型字段需在P3固定版本pilot中补齐：

```yaml
n_concurrent_trials: 1
retry:
  max_retries: 0
verifier:
  disable: true
artifacts:
  - source: /logs/artifacts/candidate.patch
    destination: candidate.patch
```

这些是上游配置字段，不是新增Task DSL。[Job配置](https://docs.harborframework.com/jobs/configs)明确支持verifier.disable；它与install_only不同，后者连Agent阶段也不运行。Artifact collection的ok/empty/failed/skipped状态必须保留；收集失败不一定使trial本身失败，不能从trial成功推定patch存在。

task-map包含schema版本、导出Harbor task name、原Task的受信任本地定位／hash、source manifest和固定image；生成不包含API key、gold patch或可被Agent修改的验收命令。job路径和task-map由操作者给出，导入检查所有解析后的路径在指定根内，拒绝symlink、特殊文件、超限和未知版本。元数据同样有界：每个JSON文件≤4MiB，单次导入≤1000个trial；超出是SCOPE_LIMIT，不偷偷截短统计。

本版**不实现进程内BaseVerifier桥接**。官方通用download_file没有确认可用的max_bytes/stream参数，exec也不是本项目的有界捕获器；不能假造这项能力，再自写Shell取文件／RPC补齐。Harbor原生separate verifier与BaseVerifier是真实已有能力，但本方案不叠加第二个验证容器。以后确有内联评分需求时，另行核对公开接口，并选择一个验证容器所有者。[公开环境接口](https://docs.harborframework.com/sandboxes/custom-sandboxes)。

Harbor在P3安装并锁定实际版本，导出/导入仅支持该已测版本布局；本轮没有冒称已兼容最新版。若结果schema不符，明确版本不支持，不悄悄猜字段或扫描日志文本补全。

<a id="batch-index"></a>
### 6.2.1 一个明确的批次索引

index.json只关联已选择的输入与Run，不是状态数据库、工作队列或恢复指令。全部字段在顶层出现，空值按下表保留；文件≤4MiB、entries最多1000项且不能重复sample_id。输出位置与命令退出码由CLI定义。

| 字段 | 类型／内容 |
|---|---|
| schema_version | 整数1 |
| batch_id | 32位hex UUID；每次导入新建，少量手动SDK实验也分配新值 |
| source_kind | harbor或manual-sdk；一种索引不混合来源 |
| created_at, finished_at | UTC RFC3339；未完成时finished_at为null |
| complete | bool；全部计划条目已处理且索引写入成功才为true，不表示全部ACCEPTED |
| source | harbor为`{job_dir, task_map_path, task_map_sha256, harbor_version}`，两路径为操作者所选文件／目录的绝对路径；manual-sdk为null |
| source_records | 数组，每项`{path, sha256, size_bytes}`；path为job_dir下实际读取的相对POSIX元数据路径，含用于完整尝试清单和collection判定的文件。hash对应读取的原始bytes；manual-sdk为空数组 |
| entries | 下述逐样本记录数组；按sample_id排序，保留所有计划条目 |

每个entry固定为`{sample_id, task_id, task_sha256, trial_path, producer_launch, collection, run_id, report_sha256, processed}`。sample_id是批次内稳定且唯一的样本标签，≤128字符；task_id来自可信Task map／实验计划；task_sha256是冻结执行契约hash，尚不可得时为null。harbor的trial_path相对于job_dir，manual-sdk为null。producer_launch取started／not_started／unknown；collection取ok／empty／failed／skipped／unknown／not_applicable，其中manual-sdk固定not_applicable。run_id是关联的RP UUID或null；report_sha256是实际report.json的hash或null；processed为bool。**该表不复制outcome和usage作为新权威**，eval读取关联Run的SQLite／完整证据重新判定；来源状态也须与source_records核对。

导入先枚举完整计划样本，写入complete=false、全部processed=false的索引，然后串行调用已有验证函数。在创建子Run之前分配并保存其run_id，每项完成后原子替换index.json；未启动或无可用补丁的条目也标为已检查并保留来源状态。run_id只是关联预留，不能单凭它证明子Run已启动；索引与Run之间不承诺跨文件事务。崩溃后有UUID但没有Run创建证据仍为verification_missing，不能“补跑一次”。SIGKILL可能只留下索引前缀状态，eval由完整条目清单和已落盘Run识别未知观察。

所有关联Run位于批次目录的`runs/<run_id>/`；使用目录身份及Run ID核对，拒绝越界／symlink。eval必须核对声明的原生来源文件hash、Task fingerprint及全部实际使用的Run证据。缺失／损坏不删样本、不选择另一个Run替换，也不把external元数据提升为本项目测试证据；目录迁移后原生来源不可定位时明确报告证据缺失，不扫描宿主查找猜测路径。

少量SDK baseline/enhanced实验不需要Harbor或新的启动器：操作者在预先指定的实验目录创建同结构manual-sdk索引，并通过既有CLI把各Run输出到该目录的runs。entries用明确的试验标签关联Run，producer_launch由Run创建及执行证据核对，不能由操作者填写的started直接决定分母。手动输入与自动导入都经同一个只读聚合器；没有第二套实验数据库。每条件的主索引必须预先确定，重验另建索引，遵守§7的主验证规则。

### 6.3 结果与证据映射

| 观察 | 本地索引／评测分类 |
|---|---|
| RP ACCEPTED且证据可核对 | accepted，关联完整RP结论；不回写或伪造Harbor reward |
| RP REJECTED或NOT_REPRODUCED | 分别保留outcome／reason，不归并为同一种模型失败 |
| RP BUDGET_EXHAUSTED | budget_stop单列 |
| RP ERROR／INCONCLUSIVE／RECOVERY_FAILED或缺必需证据 | 验证错误／未知，样本保留 |
| producer已运行但没有提交patch | producer_no_patch；不伪造空补丁成功；可以没有RP Run |
| artifact manifest为failed/skipped/empty或文件缺失 | collection_failed／artifact_missing等来源状态；不能默认解释为模型未生成 |
| producer未启动／静态配置无效 | not_started单列 |
| producer运行后崩溃／未有完整trial终态 | 已发起且producer_error／unknown；不导入运行中产物，不删除分母 |
| 导入中断／RP索引不完整 | verification_missing；不写伪结果，可显式另起导入批次 |

SDK内部Run的报告和外部Harbor trial并非同一个状态机。Harbor状态、artifact状态和ReproPatch结论分别保留，不能用native reward或Agent“完成”填入ACCEPTED。相同producer结果的重新验证属于验证重复实验，不是新的模型修复样本，不准挑最好的重验结果抬高修复率。

### 6.4 比较方式

| 比较 | 固定内容 | 变量／结论限制 |
|---|---|---|
| SDK Baseline与ReproPatch Enhanced的故障消融 | 同SDK、model/fake、prompt、6工具、Task、预算、独立验证与故障时点 | baseline不恢复；enhanced只恢复安全边界。正常无故障循环相同，不预设修复率提高 |
| 原生mini-SWE-agent／Codex／OpenHands与SDK路径 | 同Task、base、验收、可比模型与总时间／费用条件 | prompt、工具、上下文、内部step含义不同，属于外部系统对照，不是单变量消融 |
| 验证器负例 | 固定原始Task＋人工确认错误patch | 测误验收，不需要任何模型调用 |

第一次SDK故障消融直接复用T09的可核查运行证据，可只用ScriptedModel，明确是恢复机制实验。真实模型比较须另获预算授权，不从fake结果估计模型能力。自动路径正常运行没有历史裁剪策略差异，删除旧版“baseline停止／enhanced手工裁剪”的未验证优势。

可以先用少量明确CLI调用产生SDK对照Run，在实验目录登记准确Run ID与已发起记录；不为几个案例写调度系统。批量外部实验交给Harbor。跨engine不能把一次native turn强行映射为相同HTTP请求数；报告不同预算单位、实际usage和未观测项。

固定模型name、endpoint、实际版本（若可得）、发送的参数、SDK／producer／Harness commit、dirty diff hash、prompt/tool schema hash、资源、镜像、机器／内核和运行时间。模型无固定revision或温度／seed不受支持时直接披露，不发送自动探测请求。建议每条件3次重复作为小样本起点；保存执行顺序，不看结果后选择性删样本。

## 7. 指标与权威样本来源

`eval`只读取，**不启动／重试／恢复Run**。样本清单来自Harbor job/trial的创建和启动记录；少量手动SDK实验提供预先登记的明确尝试清单及Run创建证据。规范化表是可重新生成的派生数据，不再实现旧版跨文件launch_confirmed提交协议。

令N为有可靠证据已发起的合法trial/修复尝试数，包括环境／producer失败、执行中断、无patch和验证尚未启动的条目。B为有完整ReproPatch证据证明该尝试所对应baseline符合F2P/P2P的次数；A为该尝试最终获得权威ACCEPTED且证据可核对的次数。

静态不合法或已确认尚未启动的条目为not_started；排除理由保留。是否启动也无法核对时记launch_unknown，相关分母不确定的比率为null。不能从“有report的目录”反推N，也不能把未观察baseline写成NOT_REPRODUCED。一个trial的regrade是独立验证观察，不能重复计为新的模型修复样本或挑最好的一次计入A。

实验条件必须预先声明每个producer trial的主验证关联，例如第一次计划中的verify-harbor导入批次；A与B都只使用该关联的证据。主验证缺失、失败或结果未知时保留其状态，不用之后更有利的重验替换。额外导入／regrade单列为验证重复实验，不增加N；关联选择及理由写入eval.json，不能看到结果后才选批次。

下列所有比率在分母为0、分母未知或无法可靠归属时均为null，并同时保留已知整数计数与原因；不能将“没有样本”显示为0%或100%。

| 指标 | 定义 | 限制 |
|---|---|---|
| 已确认基线复现率 | B/N | 同时列baseline_unknown；外部producer无patch未运行baseline时属于未知，不是已观测复现失败 |
| 端到端验收率 | A/N | 包含producer／环境／中断成本 |
| 条件修复成功率 | A/B | B=0为null；B覆盖不足时注明选择偏差，不能外推全部任务 |
| 已知错误补丁误验收率 | 人工确认错误且被ACCEPTED数／注入错误patch数 | 仅受控负例实验，不代表未知真实patch的绝对正确率 |
| 已验收结果中的已确认错误占比 | 审核后确认错误的ACCEPTED／已人工审查ACCEPTED | 没有独立人工审查就不报告 |
| 安全边界恢复完成率 | 成功恢复到预期验证／预先定义可恢复故障数 | 不把未知segment放进“应恢复”分母后任意剔除 |
| 未知操作安全停止率 | 正确拒绝盲重并记录明确终态／未知片段故障数 | 不等于修复成功率；与恢复率分开 |
| Token | 原生可观察input/output/total总和＋未知turn数 | SDK raw_usage缺失不能使用归一化0；外部自报独立标注来源，不填入RP受控usage |
| 工具与模型调用 | SDK turns、admitted calls、HTTP可观察次数分列；外部native计数另列 | 无NOT_EXECUTED／自动重做计数，不把compile内部进程算function call |
| 时间 | producer、RP baseline、repair、verify、cleanup与总elapsed | 外部verify-patch Run不包含生成时间；缺失即未知；P2停机另列 |
| 估计成本 | 已知usage乘带日期的操作者价格表 | 无价格／usage为null；已知部分可报告subtotal，不能冒充完整账单 |

对于先生成patch再验证的外部trial，B只覆盖实际到达验证的样本；应同时报告N中有baseline观察的比例。若希望比较任务固有复现性，另运行冻结任务集的独立baseline审查，不混为本次producer成功率。内部run则总是先做baseline。

失败保留outcome＋reason与层级：producer、基线、工具政策、模型／协议、预算、验证环境、证据与恢复。Harbor外部trace可作为标有来源的cost补充，但不能提升为可信测试结果。小样本列整数分子／分母、逐题结果、中位数／范围，不给3次实验制造精确p95或宣称统计显著。

输出`eval.json`含schema_version、suite/条件指纹、原始job/trial与artifact manifest来源、所选导入批次、每个RP Run关联和hash、已发起／未知／未发起清单、完整性、分子分母、失败分类、成本来源。`eval.md`派生于它。重算读取原生trial与RP DB/证据；不修补Run终态、不重执行缺失工作。没有实验数据就明确“未实验”，不填假成功率。

## 8. 依赖、开发与CI

保留`pyproject.toml`、setuptools和`pip install -e '.[agent,dev]'`。核心生产依赖只有PyYAML；agent extra显式包含openai-agents及直接使用的openai，开发测试装agent＋pytest、Ruff、build。Harbor作为P3单独可选集成环境，不强装进核心。pytest-cov可保留为本地诊断，不设`--cov-fail-under` gate。不为几个命令切到新包管理器。

P1在干净Python3.12环境中确定经过测试的依赖版本，保存`requirements/constraints-py312-linux.txt`（完整已解析版本，排除editable本项目）。CI和发布证据使用这份constraints；pyproject使用合理兼容范围。constraints须由干净环境产生并审查，禁止把开发者所有无关包freeze进去。版本升级作为独立小任务，实际跑相关gate后更新，不引用未经测试的“latest”。

最小本地验证命令，需在相应阶段实现后使用：

```bash
python -m pip install -e '.[agent,dev]' -c requirements/constraints-py312-linux.txt
ruff check src tests scripts
ruff format --check src tests scripts
pytest -m 'not docker'
REPROPATCH_DOCKER_TESTS=1 pytest -m docker -v
python -m build
```

默认本地pytest可跳过Docker测试并显式显示原因；一旦设置`REPROPATCH_DOCKER_TESTS=1`，daemon／镜像缺失必须失败。CI只需两个Linux job：①Python质量＋SDK ScriptedModel／可信小fixture＋打包；②准备固定镜像后跑Docker gate。第一个job额外用临时venv安装仅核心wheel，证明verify-patch无需SDK/key；第二个job复用同一正确patch验收场景，不为optional dependency新增复杂矩阵。无Windows/macOS矩阵、无真实模型key、无每次PR大型benchmark。不可用的GitHub runner条件应记录为未执行，不能绿色跳过当发布证明。

PR应尽量一项Task一条分支，可用`spec/<topic>`、`feat/<topic>`、`fix/<topic>`；不强制复杂GitFlow。提交说明具体问题和行为，如“Reject skipped verifier tests”；不改不相关文件，不重置已有dirty改动，不添加自动归属文字。涉及公开契约时同步权威Spec、例子、测试和README；新增依赖需说明取舍。

日志使用稳定error_code＋run/step/tool/command身份。开发异常traceback进入受控diagnostics，终端打印短原因和相对日志路径。正常工具失败不输出整页Python堆栈；基础设施异常不静默吞掉。仅报告实际执行的命令、通过／失败／跳过和未解问题。

## 9. 发布门槛与版本管理

0.2.0标记新MVP契约，0.3.0恢复，0.4.0评测与Harbor产物接入；1.0.0在Linux支持范围和协议稳定后发布。0.x可以有明确记录的不兼容调整；Task版本变更必须说明迁移，不增加永久兼容层。P2数据库只支持已测迁移路径，旧P1审计Run不可因此自动Resume。

发布前必须：干净checkout安装wheel可运行、全部相关gate实际通过、文档示例指向真实存在的镜像／fixture输入、保留运行证据、CHANGELOG说明兼容与限制、核验Apache-2.0及上游任务／镜像许可、不含key和私有轨迹。远程push/tag/PyPI发布需要用户明确授权，规格验收本身不授权发布。

README应先给可复跑5–10分钟的小任务入口（这是文档目标，实际耗时必须测量后再写数字），随后解释独立验证、失败分类、支持范围与真实模型例子。项目展示必须同时给失败和限制，不能只挑一张成功截图作为评测。
