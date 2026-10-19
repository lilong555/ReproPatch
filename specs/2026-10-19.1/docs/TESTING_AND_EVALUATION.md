# 开发测试、评测与发布规范

状态：目标规范；本轮仅审查规格，没有重新执行产品测试。旧测试证据及其限制见[CURRENT_STATE](CURRENT_STATE.md)。本文统一测试 ID、指标分母、CI 和 release gate；逐任务顺序见[实施计划](IMPLEMENTATION_PLAN.md)。

## 1. 测试选择原则

测试应保护“用户获得可信补丁与明确失败”的行为。现有测试有价值则保留；不因旧数字较多就删除，不以74项或100%覆盖率作为目标。新增测试必须在函数注释／PR说明中用一句话说明阻止什么重要回归；简单属性读取、直接转发和第三方SDK自身行为不单独测试。

优先级为：主链路 → 错误验收 → 真实隔离与清理 → 当阶段实际增加的恢复／评测逻辑。每个测试ID代表一个**行为义务**，可由少量参数化案例覆盖，不代表必须创建等量测试类。尽量使用临时目录、真实小Git仓库、固定Mock脚本；不搭建模拟云服务、复杂mock图或测试编排框架。

## 2. 最小测试矩阵

| ID | 保护的行为和最少情形 | 为什么需要 | 阶段／建议位置 |
|---|---|---|---|
| T01 | 合法v2解析、v1明确拒绝、重复key／越界路径／可变commit或image拒绝、规范集合排序 | 防协议漂移和输入锁定失效；不逐字段排列几十种相似错误 | P1 `tests/test_task.py` |
| T02 | 基线目标正常失败＋P2P通过；目标已通过；错误签名；P2P失败；用例未执行 | 防把环境／错误测试当Bug复现；用一组参数化基线结果测试 | P1 `tests/test_verification.py` |
| T03 | 正确补丁从base干净应用、byte manifest一致、全部验证通过，原分支和未提交文件不变 | 主要用户路径；含CRLF／无尾换行的一项往返样本 | P1 `tests/test_harness.py` |
| T04 | 错误／无补丁不能ACCEPTED；修改tests/CMake／新增删除mode变更被拒；skip／空／缺用例不能通过 | 防最重要的错误验收；不测试CTest库自身所有分支 | P1 `tests/test_verification.py`,`test_workspace_tools.py` |
| T05 | 真实容器内派生sleep或后台子进程超时后消失；输出洪泛达到上限会终止；daemon失败清理未确认不能继续 | 防孤儿进程、无限日志和假清理；不能只mock docker rm返回0 | P1 `tests/test_docker_integration.py`,`test_process_sandbox.py` |
| T06 | .git/宿主哨兵/API key不可见、/src不能写、网络与权限受限；路径穿越／symlink拒绝；清理不碰其它Run | 验证真正的权限边界；使用哨兵，不接触真实秘密 | P1 `tests/test_docker_integration.py`,`test_workspace_tools.py` |
| T07 | 顺序工具组、max_steps=1仍执行已返回工具、tool/time耗尽、组裁剪、不合法模型响应、请求子进程deadline | 防无限循环、最后一步丢修改、错误finish、模型等待失控 | P1 `tests/test_models_cli.py`,`test_harness.py` |
| T08 | report与DB事件对应、JSONL可重导、未知usage不变成0、错误保留cause/traceback、查询退出码不随outcome变化 | 防审计不一致与误导性诊断 | P1 `tests/test_events_reports.py` |
| T09 | 事务边界/有效checkpoint恢复、完整结果未checkpoint、未完整工具组、未知模型结果、损坏文件、重复控制器 | 防预算重置、重付费、状态伪成功；仅P2实现时添加 | P2 `tests/test_recovery.py` |
| T10 | Trace Replay不调用Model/工具/Docker，只读取既有事件 | 防将看日志变成外部副作用 | P2 `tests/test_recovery.py` |
| T11 | 小型手算指标表含环境失败、无最终report的中断、仅登记未启动、未知／缺失usage；重复实验身份不覆盖、两策略配置一致 | 防错误分母、删除失败样本和成本造零；从attempt清单与DB证据重算 | P3 `tests/test_evaluation.py` |
| T12 | Execution Replay新Run不调用模型；相同动作得到可比较patch/verdict，旧Run字节不变 | 防伪重放和覆盖历史 | P3 `tests/test_replay.py` |

T03可用tests内的可信本地fixture执行器快速开发，必须标 `isolated=false`；发布证据还要在Docker版本跑同一主链。该执行器不接受任意用户Task、不随生产包暴露。小测试解析预录CTest结构化数据即可，唯隔离／进程终止义务必须有真实Docker测试。

## 3. 阶段验证 gate

| Gate | 必须做什么 | 不得替代它的证据 |
|---|---|---|
| V-DOCKER | 显式启用Docker标记，真实daemon下跑正确修复、错误补丁、超时和隔离；报告isolated=true | host fixture通过、mock docker命令、Docker代码存在 |
| V-LIVE | 人工授权一个真实端点／模型，至少完成一次合法工具调用回传及正常结束；保存模型配置、usage和实际结果 | Mock脚本成功、伪造HTTP成功、只列了SDK依赖 |
| V-CURATE | 每项真实任务锁commit/image/测试/provenance，人工确认原失败及参考补丁通过；参考补丁不提供给Agent | 只找到issue链接、假定上游benchmark全部兼容 |
| V-RELEASE | 干净安装＋本地CI等价命令＋真实Docker gate＋可重导报告／trace＋文档／包内容检查 | 历史旧HEAD报告、skip而非执行、截图 |

V-LIVE验收的是适配兼容性，随机模型未修好任务也须如实报告。面向公开展示的稳定版本应另保留至少一次真实模型修复成功的可复核案例；不能用这一个案例估计一般成功率。若当前无模型凭证，P1其它工作可继续，但这一gate保持未完成，不能说已完成全部里程碑。

## 4. Phase 2 故障注入范围

只选会改变恢复决策的边界，不枚举每个SQL语句和每行Python代码：

1. edit intent后、文件替换前／后、result提交前：用before/after hash核对；第三态拒绝。
2. 模型请求STARTED后、响应durable前：结果未知，RECOVERY_FAILED，不能再收费。
3. 模型响应durable后、一个工具组执行到中间：清理容器、回到上次checkpoint，重做至多该组，新attempt继续扣预算。
4. 工具组结果及post manifest均durable，checkpoint未提交：核对并补提交，不丢最后一次修改、不额外耗尽预算。
5. 模型正常最终回复durable、候选冻结前：恢复直接走FREEZE_CANDIDATE，不能再次问模型。
6. checkpoint文件rename后、DB引用前／后：未引用孤儿可忽略；缺失／hash不符拒绝；不得自动建空DB。

用受控测试进程和一两个命名failpoint注入SIGKILL；它们仅在测试构造参数中出现，不成为生产策略DSL。每种故障验证旧事件保留、budget不退款、owned容器停止、正确终态或明确恢复失败。

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

## 6. Suite 和对照策略

P3 suite是静态列表，不是调度系统。示意格式：

```yaml
version: 1
id: cpp-bugs
tasks:
  - task: ../tasks/negative-maximum.v2.yaml
    split: smoke
    source_kind: fixture
    provenance: ../provenance/negative-maximum.json
```

路径相对于suite；task id不重复。`split`只允许smoke/evaluation，`source_kind`只允许fixture/real；默认eval只统计evaluation，smoke另表展示，防止把反复调试的演示题当独立测试集。整个suite文件及所有Task hash组成suite fingerprint。

Baseline与Enhanced使用同一代码库、相同Model Adapter、工具、权限、基线／独立验收和预算。只切换有明确名称的策略：

| 策略 | 上下文 | 故障后恢复 | 其它部分 |
|---|---|---|---|
| baseline | 同样256KiB上限，达到时停止 | 不Resume，明确失败／中断 | 与enhanced完全相同 |
| enhanced | 丢弃最旧完整工具组 | 使用P2已实现恢复 | 与baseline完全相同 |

实验分别研究“正常运行下上下文策略”和“相同故障注入点下恢复能力”，不能把两者混在一个成功率里归因。基线同样做独立验收，不允许它自报成功，以免比较口径失真。mini-SWE-agent可作为以后锁版本的外部对照；工具／prompt不同须披露，不与内部ablation混称同条件实验。

每个(task,strategy,repeat)生成新Run。初始建议3次重复，仅作小样本观察；不能根据中途结果反复换seed／删掉失败。记录model name、endpoint、参数是否发送、temperature/seed（仅端点支持时）、模型可用版本ID、SDK／Harness commit、dirty diff hash、prompt hash、tools schema hash、预算、镜像、CPU／内核和运行时间。没有固定revision能力的远程模型必须注明；固定温度／seed也不意味着服务完全确定。

评测输出目录的`attempts.json`是尝试归属清单，不能从最终report目录反推样本。它包含schema_version、suite/config fingerprints，以及按执行顺序排列的`task_id/strategy/repeat/run_id/run_dir/launch_confirmed`。发起每个合法tuple前，先分配新Run ID，以临时文件、fsync和原子替换写入`launch_confirmed=false`的条目；然后由既有Run初始化提交DB中的`CREATED`与`run_created`，再将清单中的启动确认置为true，之后才进入动态准备、模型或工具执行。清单写入失败不得继续发起该任务。

清单只记录归属和启动凭据，Run状态与结果仍以各Run的SQLite为权威。DB已提交而启动确认尚未回写时，重算可从匹配Run ID的创建记录确认已启动；不声称两份文件跨事务原子提交。重算只读取证据，不重新执行遗漏任务，不隐式Resume baseline，也不新增评测恢复框架。已确认启动但DB丢失／损坏的条目仍保留并标记证据缺失。

本地顺序执行，两个策略交替安排／记录执行顺序以减小服务时段及缓存差异。默认并发1，没有队列、异步worker、scheduler。模型超时和API错误属于观察结果，不能从分母删除。

## 7. 指标的精确定义

令 `N` 为attempt清单中实际发起的合法任务尝试数，以DB的Run创建提交或其`launch_confirmed=true`持久化凭据确认，包含PREPARING环境失败及中断。`B` 为有完整持久化证据证明基线F2P签名符合且全部P2P通过的次数，`A` 为权威DB已记录`FINISHED/ACCEPTED`且独立验收证据可核对的次数。suite静态不合法、或仅登记且确认尚未创建Run的条目记`not_started`并单列，不计入N。启动是否发生也无法核对时保留不确定条目，相关分母不能确定的比率写null，不能默默降为not_started。

非终态的中断Run即使没有最终report，也计入N、不计入A；只有已持久化完整基线成功证据才计入B，缺失基线证据单列为未知。不能因没有report就删除样本，不能把未知基线解释为已观察到基线失败。若DB已有可核对的终态及证据、仅派生report丢失，仍按DB计数并可重新导出report。评测读取不得为补齐统计而写入Run终态、Outcome或伪造测试结果。

| 指标 | 定义 | 解释限制 |
|---|---|---|
| 基线复现成功率 | B/N | 是已确认复现比例；同时列NOT_REPRODUCED、ERROR、INCONCLUSIVE及基线证据未知数，不能将未知都解释为复现失败 |
| 端到端验收率 | A/N | 包含环境成本和失败；不能只报告成功启动模型的子集 |
| 条件修复成功率 | A/B | 仅在有效基线中衡量；B=0写null/N/A |
| 已知错误补丁误验收率 | 错误patch被ACCEPTED数 / 注入已知错误patch总数 | 是受控验证器实验；不能外推为未知真实patch的绝对误验收率 |
| 验收结果中的已知错误占比 | 已确认错误且ACCEPTED / 已审查ACCEPTED | 与上一项分母不同；无独立审查则不报告 |
| 可恢复故障完成率 | 恢复后完成预期验证的次数 / 预先定义可恢复故障次数 | 非可恢复的模型未知状态另列；不能删掉其安全失败记录 |
| 未知操作安全终止率 | 正确核对或明确RECOVERY_FAILED / 未知结果注入次数 | 关注不盲重副作用，而不是都必须恢复成功 |
| Token | SDK已知input/output/total的总和，另列unknown请求数 | 重复计费可能未知；不能将缺失usage当0 |
| 工具调用 | tool attempts；另列policy error、重做、NOT_EXECUTED | 内部configure/build不重复算tool call |
| 时间 | 总Run elapsed及prepare/model/tool/verify/cleanup分项 | duration用单调时钟；有恢复时同时报告停机时间 |
| 估计成本 | 已知usage×带日期的操作者价格表 | 价格／usage缺失为null；不等于账单，unknown计费单列 |

失败按outcome＋reason_code汇总；模型／协议、工具策略、基线、补丁、验证环境、预算和恢复各保留维度，不能都归为“模型不会”。样本很少时同时显示整数分子／分母、逐任务结果、最小值／中位数／范围；不对3次运行计算看似精确的p95。置信区间可后续用标准方法增加，首版不引统计框架。

统计必须可由`attempts.json`、各Run的权威DB与其引用的原始执行证据重算，现有report用于核对及展示，不是筛选样本的依据。`eval.json`保存schema_version、suite/config fingerprints、attempt清单快照、每项证据来源与完整性、聚合值、缺失项和excluded/not_started；非终态Run保留原状态和`outcome=null`。`eval.md`是从它生成的说明；没有数据时只生成模板而非成功率。

## 8. 依赖、开发与CI

保留`pyproject.toml`、setuptools和`pip install -e '.[dev]'`。生产直接依赖PyYAML和openai；开发用pytest、Ruff、build。pytest-cov可保留为本地诊断，不设`--cov-fail-under` gate。不为几个命令切到新包管理器。

P1在干净Python3.12环境中确定经过测试的依赖版本，保存`requirements/constraints-py312-linux.txt`（完整已解析版本，排除editable本项目）。CI和发布证据使用这份constraints；pyproject使用合理兼容范围。constraints须由干净环境产生并审查，禁止把开发者所有无关包freeze进去。版本升级作为独立小任务，实际跑相关gate后更新，不引用未经测试的“latest”。

最小本地验证命令，需在相应阶段实现后使用：

```bash
python -m pip install -e '.[dev]' -c requirements/constraints-py312-linux.txt
ruff check src tests scripts
ruff format --check src tests scripts
pytest -m 'not docker'
REPROPATCH_DOCKER_TESTS=1 pytest -m docker -v
python -m build
```

默认本地pytest可跳过Docker测试并显式显示原因；一旦设置`REPROPATCH_DOCKER_TESTS=1`，daemon／镜像缺失必须失败。CI只需两个Linux job：①Python质量＋可信小fixture＋打包；②准备固定镜像后跑Docker gate。无Windows/macOS矩阵、无真实模型key、无每次PR大型benchmark。不可用的GitHub runner条件应记录为未执行，不能绿色跳过当发布证明。

PR应尽量一项Task一条分支，可用`spec/<topic>`、`feat/<topic>`、`fix/<topic>`；不强制复杂GitFlow。提交说明具体问题和行为，如“Reject skipped verifier tests”；不改不相关文件，不重置已有dirty改动，不添加自动归属文字。涉及公开契约时同步权威Spec、例子、测试和README；新增依赖需说明取舍。

日志使用稳定error_code＋run/step/tool/operation身份。开发异常traceback进入受控diagnostics，终端打印短原因和相对日志路径。正常工具失败不输出整页Python堆栈；基础设施异常不静默吞掉。仅报告实际执行的命令、通过／失败／跳过和未解问题。

## 9. 发布门槛与版本管理

0.2.0标记新MVP契约，0.3.0恢复，0.4.0评测；1.0.0在Linux支持范围和协议稳定后发布。0.x可以有明确记录的不兼容调整；Task版本变更必须说明迁移，不增加永久兼容层。P2数据库只支持已测迁移路径，旧P1审计Run不可因此自动Resume。

发布前必须：干净checkout安装wheel可运行、全部相关gate实际通过、文档示例指向真实存在的镜像／fixture输入、保留运行证据、CHANGELOG说明兼容与限制、核验Apache-2.0及上游任务／镜像许可、不含key和私有轨迹。远程push/tag/PyPI发布需要用户明确授权，规格验收本身不授权发布。

README应先给可复跑5–10分钟的小任务入口（这是文档目标，实际耗时必须测量后再写数字），随后解释独立验证、失败分类、支持范围与真实模型例子。项目展示必须同时给失败和限制，不能只挑一张成功截图作为评测。
