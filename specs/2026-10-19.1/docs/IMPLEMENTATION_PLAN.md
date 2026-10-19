# 实施计划与逐项完成标准

状态：**本轮完成Phase 0规格；以下功能任务是后续实施计划。** 本轮没有修改产品代码或重跑旧测试。先读[现状](CURRENT_STATE.md)与[总纲](../SPEC.md)，不得从空项目重建。FR/NFR见[需求](REQUIREMENTS.md)，T01–T12与验证gate见[测试规范](TESTING_AND_EVALUATION.md)。

## 1. 每个Coding Agent会话如何推进

一次会话只选一个Task ID。开始前检查当前分支、dirty修改和该任务前置条件，读关联权威文档；用最少文件改变完成一个可观察行为。完成后给出改动、原因、实际命令与结果、未解问题。不要把未执行的检查写为通过，Docker缺失／付费模型未调用必须保持明确未验收。

任务完成的Definition of Done：实现与Spec一致；相关必要测试实际通过；没有无用抽象、重复流程或无关重构；公开契约／例子同步；结果可核查；剩余问题有具体后续Task ID。新增测试说明防止的重要回归。文档变化不能代替未完成的功能。

复杂度S表示一个边界清晰的小改动，M表示一个需集成验证的完整行为；均以单个Coding Agent会话可实现并验证为目标，不作工时保证。若发现实际任务无法独立完成，先按独立验收点拆分并更新本计划，禁止把未完成的大块代码以“基本完成”提交。

开发顺序原则：先证明现有Docker路径可用，再升级任务输入和执行边界，再补模型／工具，随后验证／报告；进入P2前必须能跑完整P1。P3可以复用P2已稳定状态，不能用评测框架绕过MVP缺口。

## 2. Phase 0：定义与工程基础

**目标：** 明确已有实现、冻结MVP和全部关键数据／执行语义。范围为规格、可读示例、迁移和验收计划；不生成产品骨架或未经需求证明的新抽象。前置为用户任务和可读取的既有工作区。组件为本交付全部文档、Task示例和审查记录。

### P0-01 — 现状与设计冻结

- Task ID：P0-01；所属Phase：0；状态：本轮完成。
- 目标：确定应保留的现有代码及新Spec的真实起点。
- 前置依赖：读取原仓库、README、依赖和历史证据。
- 涉及文件或模块：CURRENT_STATE、SPEC、DECISIONS、架构／需求等权威文档。
- 具体工作：记录HEAD、dirty、remote、工具／Task v1、Docker与模型验收限制；调研官方资料；冻结v2、只读快照、F2P/P2P、阶段边界。
- 验收标准：当前源码与目标能力分开，所有重要决策有依据；未提交改动未覆盖。
- 需要运行的测试：只读目录／Git／证据核查和文档审查；不运行产品测试。
- 预计复杂度：M。

### P0-02 — 完整规格交叉检查

- Task ID：P0-02；所属Phase：0；状态：本轮完成。
- 目标：让后续Agent能按单一契约开始实现。
- 前置依赖：P0-01、完整文档和Task示例已创建。
- 涉及文件或模块：所有Spec、examples/task.example.yaml、SPEC_REVIEW。
- 具体工作：核对相对链接、YAML字段／默认、Phase、状态枚举、预算、事件、恢复窗口和FR→模块→任务→测试映射；直接修复发现的问题。
- 验收标准：没有未解决的关键文档矛盾；示例占位明确；不虚构产品测试结果。
- 需要运行的测试：本轮静态文档／YAML检查；人工审查控制流与图示；记录实际范围。
- 预计复杂度：M。

**阶段风险：** 把已有v1代码误当空项目，或把旧host证据当Docker验收。**交付物：** 本Spec包及审查记录。**退出条件：** 所有权威文件完整、可交叉导航、MVP无P2强制依赖。

## 3. Phase 1：最小真实端到端

**目标：** 新Task协议下的可运行修复—验收链路。范围包括基本超时、安全和审计，它们不能推迟到可靠性阶段；非目标是Checkpoint、Resume、通用调度和正式评测。前置为Phase0冻结、可用Linux/amd64 Docker主机、用户可准备的固定镜像。主要组件保留原Python模块，仅按真实职责提取verification.py。

### P1-01 — 核验现有改动与真实Docker基线

- Task ID：P1-01；所属Phase：1。
- 目标：解决现有“代码已有但Docker未验收”的第一风险。
- 前置依赖：P0-02；在有Docker能力的Linux主机上工作。
- 涉及文件或模块：既有harness.py、sandbox.py、test_process_sandbox.py、Dockerfile、TEST_REPORT／证据。
- 具体工作：检查并保留三项dirty清理错误修复，确认其原始意图；把Spec合入独立工作分支；构建镜像，先运行旧fixture的真实Docker gate；只修妨碍当前主链的真实缺陷，不同时重写Task或SDK。
- 验收标准：原用户改动无丢失；已知正确／错误补丁在Docker路径符合旧验收预期，isolated=true；明确这还不等于v2最终gate。
- 需要运行的测试：现有相关pytest＋`REPROPATCH_DOCKER_TESTS=1 pytest -m docker -v`；保存当前HEAD/dirty与日志。daemon缺失即记录阻塞，不host替代。
- 预计复杂度：S；环境修复超出能力时只阻塞该gate，不伪造成功。

### P1-02 — Task v2与演示输入锁定

- Task ID：P1-02；所属Phase：1。
- 目标：形成一种明确、不可漂移的运行输入。
- 前置依赖：P1-01代码基线；TASK_FORMAT。
- 涉及文件或模块：task.py、cli.py、scripts/init_example.py、examples/tasks、test_task.py。
- 具体工作：按v2解析一次边界、完整OID/image身份、readable/editable/protected集合；生成canonical hash；v1返回明确迁移错误；init脚本输出实际commit和image ID，更新旧示例。
- 验收标准：有效fixture可静态验证并冻结；HEAD／tag／重复key拒绝；不同目录／hash seed不改变同执行契约hash；占位示例不能被当真实可运行资源。
- 需要运行的测试：T01；`repropatch validate-task examples/tasks/negative-maximum.v2.yaml`；doctor检查实际镜像。
- 预计复杂度：M。

### P1-03 — 工作区、快照、补丁与执行清理

- Task ID：P1-03；所属Phase：1。
- 目标：把源文件和执行权限边界落实为可验证行为。
- 前置依赖：P1-02；EXECUTION_AND_SECURITY。
- 涉及文件或模块：workspace.py、sandbox.py、process.py、相关集成测试。
- 具体工作：落实Git元数据前置边界、所有权记录；导出无.git只读快照；Task资源限额；流式日志上限；整容器timeout清理；仅已有文本M变更，完整byte manifest与patch往返。保留原本已满足的实现，不全模块重写。
- 验收标准：原工作树不变；当前源码快照与patch一致；路径／链接／mode／新增删除拒绝；超时后确认容器消失；无法确认清理不继续。
- 需要运行的测试：T03往返、T05、T06；使用真实Docker测派生进程和只读mount。
- 预计复杂度：M；若现有代码差距过大，可按“patch往返”和“容器清理”独立拆分，不跨会话悬置安全边界。

### P1-04 — 成熟SDK与可终止模型请求

- Task ID：P1-04；所属Phase：1。
- 目标：替换自制HTTP，得到一个可替换且预算受控的模型接口。
- 前置依赖：P1-02，AGENT_RUNTIME；process.py有流式deadline能力。
- 涉及文件或模块：models.py、process.py、pyproject.toml、constraints、模型测试。
- 具体工作：保留Model Protocol/Mock；引入official openai SDK；显式关闭重试；冻结finish_reason／usage错误映射；一个宿主请求子进程实现总deadline，有界JSON通信和最小key环境；不加worker池。
- 验收标准：合法tools response可还原；未知usage为null；截断回复不算finish；请求超时子进程回收；key不进入argv／日志／容器；旧HTTP仅在替代路径验证后删除。
- 需要运行的测试：T07模型边界与子进程阻塞fake；T06秘密哨兵。真实服务V-LIVE留P1-08人工授权一次。
- 预计复杂度：M。

### P1-05 — 工具与最小Agent Loop闭环

- Task ID：P1-05；所属Phase：1。
- 目标：模型能检查和精确修改源码，预算停止语义一致。
- 前置依赖：P1-03、P1-04；AGENT_RUNTIME。
- 涉及文件或模块：tools.py、harness.py、Mock脚本、runtime测试。
- 具体工作：补list_directory和隔离run_shell；沿用read/search/edit/self-check；串行工具组；max_steps／tool/time gate；256KiB完整组裁剪；最终回复／预算后候选交给验收器。自查接口可以先使用已有执行helper，P1-06替换统一验证逻辑。
- 验收标准：Mock读取→修改→诊断→结束；仅授权源码变化；max_steps=1时已取得的工具仍执行；上下文不产生孤立tool消息；预算不足不再发模型请求。
- 需要运行的测试：T07，加T03主链预验；不新增每个getter的测试。
- 预计复杂度：M。

### P1-06 — 基线与独立F2P/P2P验收

- Task ID：P1-06；所属Phase：1。
- 目标：最终结论完全来自冻结测试契约与独立执行证据。
- 前置依赖：P1-03、P1-05；VERIFICATION。
- 涉及文件或模块：verification.py、harness.py、tools.py、test_verification.py。
- 具体工作：提取共用configure/build/CTest观察；固定inventory、单测试结果和签名；基线P2P；原commit新树精确应用patch；空build重建；结果矩阵与证据结构；禁止测试修改／skip假成功。
- 验收标准：T02各类别有正确outcome；正确补丁全部通过；错误补丁、missing/skip/保护文件变更从不ACCEPTED；原始命令失败与候选失败区分。
- 需要运行的测试：T02、T03、T04，以及真实Docker正确／错误补丁。
- 预计复杂度：M。

### P1-07 — 单一事件权威、报告与查询CLI

- Task ID：P1-07；所属Phase：1。
- 目标：正常运行的结果可检查、可导出且不会产生DB/JSONL两份事实。
- 前置依赖：P1-06；STATE的P1部分、CLI。
- 涉及文件或模块：events.py、harness.py、cli.py、report渲染及tests。
- 具体工作：SQLite审计单写，结束时或显式读取导出JSONL；原子JSON/Markdown报告；inspect/report；统一exit codes、reason、脱敏traceback、usage和分阶段计时；run.json记录资源但不宣称Resume。
- 验收标准：report、events、trace互相指向有效证据；无候选不造空成功patch；错误归因保留；删除导出文件可由DB重建；inspect失败Run仍正常退出。
- 需要运行的测试：T08，必要T01 CLI错误；不实现P2表和Resume命令。
- 预计复杂度：M。

### P1-08 — MVP验收与0.2.0候选发布记录

- Task ID：P1-08；所属Phase：1。
- 目标：证明新契约整条路径在真实环境中成立。
- 前置依赖：P1-01..P1-07；可授权真实模型的用户。
- 涉及文件或模块：README、Task／Mock示例、测试证据、constraints、CHANGELOG。
- 具体工作：干净环境安装，锁实际镜像；运行正确修复／错误拒绝／超时隔离gate；经用户显式授权做一次V-LIVE；记录支持范围与模型观察，准备0.2.0候选说明。
- 验收标准：V-DOCKER、T01–T08相关义务实际通过；V-LIVE有合法工具交互证据；无未解决的错误验收／主机边界问题；未授权远程发布时只保留本地候选。
- 需要运行的测试：Ruff、`pytest -m 'not docker'`、显式Docker gate、`python -m build`、真实模型smoke；缺项明确未完成。
- 预计复杂度：S，主要是验收与修复已发现的阻塞。

**阶段风险：** 现有Docker能力未证实、第三方模型协议不一致、CTest空跑、最后一步预算误停。**交付物：** 可安装CLI、锁定fixture Task、实际patch/report/trace、最小Docker测试和真实模型接口证据。**退出条件：** P1-08通过；Checkpoint/Resume仍未提供。

## 4. Phase 2：执行可靠性

**目标：** 在可解释的边界恢复中断Run。范围为单机／单writer／完整工具组checkpoint；非目标是任意指令级续跑、跨版本续跑、外部不可逆工具和分布式Exactly Once。前置P1全部通过。组件为state.py、recovery.py及既有events/workspace/sandbox的必要增量。

### P2-01 — 事务状态与操作记录

- Task ID：P2-01；所属Phase：2。
- 目标：状态、预算和事件从同一数据库事务读取。
- 前置依赖：P1-08；STATE_AND_RECOVERY。
- 涉及文件或模块：state.py、events.py、harness.py、test_recovery.py。
- 具体工作：每Run四表；状态转移校验；CREATED未冻结字段允许null；intent/result与预算原子；本地flock；P1旧审计仍可读但不可Resume；数据库损坏不重置。
- 验收标准：非法转移拒绝；并发第二writer拒绝；崩溃后无半条状态／事件提交；准备失败也可形成完整ERROR记录。
- 需要运行的测试：T09中的事务／锁／损坏；T08保持报告兼容。
- 预计复杂度：M。

### P2-02 — 有界Checkpoint与资源登记

- Task ID：P2-02；所属Phase：2。
- 目标：保存一个可以重新构建工作区的完整边界。
- 前置依赖：P2-01。
- 涉及文件或模块：recovery.py、workspace.py、harness.py、state.py。
- 具体工作：BASELINE_CONFIRMED／TURN_COMPLETED／CANDIDATE_FROZEN时记录patch、manifest、对话、budget、next_action；文件先fsync/rename再DB引用；记录container/worktree所有权；完整组post manifest持久化以补交checkpoint。
- 验收标准：从checkpoint重建字节一致；不保存build／进程；缺文件／hash不符拒绝；未引用孤儿文件不当有效checkpoint。
- 需要运行的测试：T09的文件／DB提交窗口与全组完成窗口；不加入通用快照服务。
- 预计复杂度：M。

### P2-03 — Resume和未知副作用核对

- Task ID：P2-03；所属Phase：2。
- 目标：有限恢复可恢复Run，对未知收费／失控进程明确失败。
- 前置依赖：P2-02。
- 涉及文件或模块：recovery.py、cli.py、harness.py、state.py。
- 具体工作：验证Run fingerprint、deadline、ownership；停止遗留容器；核对edit前后hash；已存reply未完整组回滚重做至多一组；全部结果已存则补checkpoint；保存最终回复／next_action避免重复问模型；预算不退款。
- 验收标准：工具中断可有证据继续；未知模型响应RECOVERY_FAILED；第三态文件／清理不确认／预算不足明确失败且保留原候选；终态不可resume。
- 需要运行的测试：T09主要故障点，真实Docker至少一例中断清理；绝不使用真实付费请求做自动故障测试。
- 预计复杂度：M。

### P2-04 — Trace Replay、故障回归与0.3.0门槛

- Task ID：P2-04；所属Phase：2。
- 目标：提供安全的历史查看与完整恢复验收证据。
- 前置依赖：P2-03。
- 涉及文件或模块：cli.py、recovery.py、事件导出、README、recovery tests。
- 具体工作：实现export-trace和trace replay；显示原事件与重做／superseded关系；按T09选定边界注入SIGKILL，汇总恢复／安全失败；记录P2限制。
- 验收标准：T09/T10通过；trace模式不调用任何执行API；故障后预算和来源可追溯；既有P1 E2E无回归。
- 需要运行的测试：T09、T10、已有P1主路径与真实Docker清理；不扩大无关覆盖率。
- 预计复杂度：M。

**阶段风险：** 模型结果未知被重收费，已完成编辑在回滚后丢失，文件／DB非原子，两个控制器接管同Run。**交付物：** 状态schema、Checkpoint、Resume、Trace Replay和故障证据。**退出条件：** P2-04通过；Execution Replay留P3。

## 5. Phase 3：评测与公开工程质量

**目标：** 用少量真实数据说明Harness行为，并准备可复核开源版本。范围为本地串行评测、少量curated任务、可重算指标、开发文档；非目标是leaderboard冲榜或通用benchmark平台。前置P2稳定，已有固定模型／预算／镜像。

### P3-01 — 固定Fixture Suite

- Task ID：P3-01；所属Phase：3。
- 目标：得到不依赖服务可用性的稳定任务集和验证器负例。
- 前置依赖：P2-04；测试文档的fixture定义。
- 涉及文件或模块：examples/cpp-bugs、examples/tasks、examples/suites、provenance。
- 具体工作：保留negative-maximum；按测试文档的具体分支与非零输入补充range-sum，再补parse正常断言失败案例；分别锁Task／正确及错误参考patch；区分smoke/evaluation，不把gold patch放Agent快照。
- 验收标准：每项F2P失败/P2P通过；参考修复通过、错误补丁拒绝；suite引用真实文件和hash。
- 需要运行的测试：T02–T04在新增小案例上运行；V-CURATE的fixture子集。
- 预计复杂度：M。

### P3-01R — 一项真实C++任务入库

- Task ID：P3-01R；所属Phase：3；每会话只导入一个实例，后续用R2/R3后缀追踪独立实例。
- 目标：增加一个符合现有边界、具有来源和可复现证据的真实缺陷。
- 前置依赖：P3-01；公开源码／许可／可获得构建依赖。
- 涉及文件或模块：examples/tasks、provenance、受信任测试patch、独立镜像准备材料。
- 具体工作：从上游官方材料选实例；必要时在原bug commit上只添加审核后的测试生成prepared commit；锁镜像和名字；手工验证baseline／参考patch／成本；记录排除与适用限制。
- 验收标准：V-CURATE通过；不猜测commit／失败签名；任务不需要放宽安全配置；元数据完整，参考patch不泄给Agent。
- 需要运行的测试：实际任务baseline、reference patch的干净Docker验收；无需复跑无关全套unit。
- 预计复杂度：M；构建无法落在预算内就记录excluded，不临时扩大产品范围。

### P3-02 — 对照评测与成本汇总

- Task ID：P3-02；所属Phase：3。
- 目标：在同模型／任务／预算下比较明确策略，并输出可重算报告。
- 前置依赖：P3-01和至少一个完成的P3-01R；TESTING_AND_EVALUATION。
- 涉及文件或模块：evaluation.py、cli.py、tests/test_evaluation.py、实验报告。
- 具体工作：解析静态suite；每个tuple新Run且启动前持久化attempts.json归属清单，再核对DB创建记录；baseline/enhanced开关固定；采集fingerprint、失败原因、known/unknown token和耗时，从清单、DB与引用证据重算JSON/Markdown，不增加eval恢复框架。
- 验收标准：手算小表与程序一致；环境失败及无最终report的已启动中断不被删除，未启动条目不混入N；基线未知与已观察失败分开，统计不伪造Run终态；同配置比较有来源；真实实验无数据时不填虚假值。
- 需要运行的测试：T11含一个无最终report的中断样本及一个仅登记未启动样本；先Mock小suite验证，真实模型重复实验须用户显式授权预算；次数与成本实际记录。
- 预计复杂度：M。

### P3-03 — Execution Replay

- Task ID：P3-03；所属Phase：3。
- 目标：将重看记录与重新执行历史动作明确分开。
- 前置依赖：P2-04、P3-01。
- 涉及文件或模块：evaluation.py、recovery.py、cli.py、tests/test_replay.py。
- 具体工作：完整可重放trace前置检查；新Run复制冻结输入；顺序执行有效历史动作、不调用模型；对edit前置hash和最终patch／验证对比；记录replay_of和分歧，旧Run不变。
- 验收标准：T12通过；缺少输入或记录不完整时拒绝；不声称stdout／耗时逐位确定；重放中的失败是真实结果。
- 需要运行的测试：T12及固定fixtureDocker replay；不调用付费模型。
- 预计复杂度：M。

### P3-04 — 最小CI与稳定版公开材料

- Task ID：P3-04；所属Phase：3。
- 目标：他人能够从干净安装复跑项目声明。
- 前置依赖：P3-02、P3-03及对应gate。
- 涉及文件或模块：.github/workflows/ci.yml、pyproject、README、CONTRIBUTING、SECURITY、CHANGELOG、docs示例证据。
- 具体工作：收敛为Linux质量/fixture和Docker两个job；constraints固定；wheel安装smoke；说明支持范围、真实实验、失败分类、费用／源码边界、协议迁移；发布前检查许可证和敏感信息。
- 验收标准：V-RELEASE、P1/P2相关gate实际通过；报告可重算；至少一个真实模型成功案例有证据但不虚构通用成功率；1.0候选文档无未实现命令混入当前帮助。
- 需要运行的测试：Ruff、必要pytest／Docker、build及干净wheel安装；经授权才push/tag/PyPI，不自动发布。
- 预计复杂度：M。

**阶段风险：** 自有题过拟合、真实库构建过重、模型版本漂移、错误分母、引用上游许可不全。**交付物：** 固定suite、来源、原始Run、结构化对照报告、Execution Replay、最小CI和开源文档。**退出条件：** 未通过的实例如实排除／列失败，支持范围内的所有gate通过。

## 6. Phase 4：有证据才扩展

本阶段无整体完成日期和必做数量；任何候选项都要先说明现有实现的具体痛点、最小替代方案、测量方法与维护代价。没有触发条件就保持“不实施”，不留下无追踪TODO。每项先是一个调查／原型任务，再按独立验收能力拆编码任务。

### P4-01 — C++20执行器收益验证

- Task ID：P4-01；所属Phase：4。
- 目标：仅在Python进程控制形成实际瓶颈或无法可靠表达所需Linux能力时决定是否自研执行器。
- 前置依赖：P3分阶段profile，至少一个可重复的性能／进程管理缺陷；先排除Docker启动／编译本身占主导。
- 涉及文件或模块：实验profile、DECISIONS；成立后才创建executor/和CMake目标。
- 具体工作：测当前实现；比较Python修复、标准工具和独立C++原型；最多定义一次command/result JSON协议，复用既有deadline/日志/cleanup语义；考虑process group、pidfd等需求而非为语言展示重写。
- 验收标准：有可复核收益或必要能力证据，否则决策为“不引入”；引入后可替换一处执行路径，无重复两套核心逻辑。
- 需要运行的测试：同一进程树／输出／timeout契约T05，实测开销；不先编全量C++测试框架。
- 预计复杂度：M（决策／小原型），正式实现需另拆批准任务。

### P4-02 — 第二种真实模型协议

- Task ID：P4-02；所属Phase：4。
- 目标：解决一个实际使用的第二端点无法通过现有adapter表达的问题。
- 前置依赖：真实用户需求、明确协议差异和测试端点。
- 涉及文件或模块：models.py或一个新增adapter模块、protocol tests、DECISIONS。
- 具体工作：比较同SDK配置是否足够；确需另一SDK才添加一个小adapter，保持Turn与工具契约不变；记录usage／取消／finish语义差异。
- 验收标准：两adapter均满足同一工具／预算契约；没有为未来提供商建registry或routing DSL。
- 需要运行的测试：T07共用契约＋人工授权的第二端点smoke。
- 预计复杂度：M。

### P4-03 — 上下文策略改进

- Task ID：P4-03；所属Phase：4。
- 目标：解决已测得的CONTEXT_LIMIT或遗失关键信息问题。
- 前置依赖：实际失败trace、固定suite和基线；不能仅凭“更智能”立项。
- 涉及文件或模块：harness上下文函数、evaluation报告。
- 具体工作：先试更合适的窗口／结构化保留，再评估tokenizer或摘要额外依赖；改变一个策略变量并记录额外token、延迟和错误。
- 验收标准：同条件对照证明收益，完整工具组和固定前缀不受破坏；无收益则不合并。
- 需要运行的测试：T07上下文契约＋固定实验；不创建向量数据库／检索服务作为默认方案。
- 预计复杂度：M。

### P4-04 — 外部Benchmark／Harbor集成

- Task ID：P4-04；所属Phase：4。
- 目标：满足已经出现的跨任务集比较需求，减少自行维护安装／验证逻辑。
- 前置依赖：本地Task和报告稳定、目标benchmark明确、阅读当前上游接口。
- 涉及文件或模块：单个外部adapter、映射文档、integration smoke。
- 具体工作：优先复用上游任务与verifier；Harbor考虑external agent模式保持模型控制面外置；列出Task/patch/reward映射与不支持部分；不挂Docker socket、不Docker-in-Docker绕过边界。
- 验收标准：一个真实外部任务跑通，原本独立验收和secret边界保持；不能映射时明确拒绝，不制造完整第二平台。
- 需要运行的测试：一个锁版本任务的外部集成＋本地主链回归；不首轮跑大规模benchmark。
- 预计复杂度：M（映射和单案例），扩大任务数按实测成本决定。

**阶段交付物：** 每项可复核立项／不立项记录，成立时才交付小模块与对照证据。**主要风险：** 重复框架、双状态机和功能膨胀。**验收方法：** 同一契约＋实际收益；无数据不自动进入编码。

## 7. 建议给下一个Coding Agent的工作指令

> 阅读SPEC.md、docs/CURRENT_STATE.md与docs/IMPLEMENTATION_PLAN.md。检查现有Git状态，保留全部用户未提交修改。本次只执行P1-01：核验现有清理错误修复并在真实Docker上验证旧fixture主链，记录准确证据。不要重建项目骨架，不改Task协议，不进入恢复／C++执行器开发。若Docker不可用，明确给出缺少的前置条件并完成其余可做的只读检查；禁止回退宿主运行任意Task。完成后报告实际测试和下一任务P1-02。

后续会话将Task ID替换成下一项，并读取其依赖的权威文档即可。每个Phase结束都要更新当前可用能力，而不是把全计划一次贴进README当已完成。
