# 实施计划与逐项完成标准

状态：**Spec 2026-10-19.2；本轮完成Phase 0的生态审查与规格修订，以下功能任务是后续实施计划。** 本轮没有修改产品代码或重跑旧测试。先读[现状](CURRENT_STATE.md)与[总纲](../SPEC.md)，不得从空项目重建。FR/NFR见[需求](REQUIREMENTS.md)，T01–T12与验证gate见[测试规范](TESTING_AND_EVALUATION.md)。

## 1. 每个Coding Agent会话如何推进

一次会话只选一个Task ID。开始前检查当前分支、dirty修改和该任务前置条件，读关联权威文档；用最少文件改变完成一个可观察行为。完成后给出改动、原因、实际命令与结果、未解问题。不要把未执行的检查写为通过，Docker缺失／付费模型未调用必须保持明确未验收。

任务完成的Definition of Done：实现与Spec一致；相关必要测试实际通过；没有无用抽象、重复流程或无关重构；公开契约／例子同步；结果可核查；剩余问题有具体后续Task ID。新增测试说明防止的重要回归。文档变化不能代替未完成的功能。

复杂度S表示一个边界清晰的小改动，M表示一个需集成验证的完整行为；均以单个Coding Agent会话可实现并验证为目标，不作工时保证。若发现实际任务无法独立完成，先按独立验收点拆分并更新本计划，禁止把未完成的大块代码以“基本完成”提交。

开发顺序：P1-01→P1-02→P1-03→P1-06，先交付无模型依赖的独立patch验收；随后P1-04→P1-05接现成SDK，P1-07→P1-08完成两条路径与发布gate。Task编号不是必须按数值顺序执行。P2必须等P1稳定；P3用Harbor复用作业，不写另一层调度器。

## 2. Phase 0：定义与工程基础

**目标：** 明确已有实现、冻结MVP和全部关键数据／执行语义。范围为规格、可读示例、迁移和验收计划；不生成产品骨架或未经需求证明的新抽象。前置为用户任务和可读取的既有工作区。组件为本交付全部文档、Task示例和审查记录。

### P0-01 — 现状与设计冻结

- Task ID：P0-01；所属Phase：0；状态：本轮完成。
- 目标：确定应保留的现有代码及新Spec的真实起点。
- 前置依赖：读取原仓库、README、依赖和历史证据。
- 涉及文件或模块：CURRENT_STATE、SPEC、DECISIONS、架构／需求等权威文档。
- 具体工作：记录最新HEAD／clean状态与旧证据区别；核查SDK、mini、OpenHands、Codex、Harbor官方资料及固定源码；冻结SDK复用、verify-patch、三表安全恢复和P3Harbor边界。
- 验收标准：当前源码与目标能力分开，所有重要决策有依据；既有提交与用户改动均未覆盖，产品未自动重写。
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

**目标：** 新Task协议下的可运行修复—验收链路。范围包括基本超时、安全和审计，它们不能推迟到可靠性阶段；非目标是Checkpoint、Resume、通用调度和正式评测。前置为Phase0冻结、可用Linux/amd64 Docker主机、用户可准备的固定镜像。主要组件保留原Python模块，提取真实验证职责；SDK替代旧Loop/HTTP，纯验证不安装SDK。

### P1-01 — 继续现有分支并解除Docker验收阻塞

- Task ID：P1-01；所属Phase：1；状态：已有准备记录，真实Docker gate仍阻塞。
- 目标：以当前提交建立可信执行基线，不重复推翻已完成修复。
- 前置依赖：P0-02；读取CURRENT_STATE；可提供Docker的Linux/amd64主机。
- 涉及文件或模块：现有work/spec-p1-01分支、清理修复、Dockerfile、规格归档、验收记录。
- 具体工作：重新检查Git状态，确认ab6e4c4后的变化；保留已提交三处清理修复；在代码仓库中归档本修订并将当前Spec入口指向新版；运行原fixture的真实Docker gate，只修本门槛实际暴露的缺陷。
- 验收标准：修订入口可追溯、用户改动无丢失；Docker正确／错误补丁和清理用例实际运行，isolated=true。已有76/4记录不能代替这个gate，也不宣称已满足v2。
- 需要运行的测试：现有相关pytest＋`REPROPATCH_DOCKER_TESTS=1 pytest -m docker -v`，保存准确HEAD与日志。无daemon时在可用Linux runner执行，保持阻塞结论，不host fallback。
- 预计复杂度：S；权限或环境不可得时先完成可做部分，明确缺少的前置条件。

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

### P1-04 — 直接接入上游SDK与测试模型

- Task ID：P1-04；所属Phase：1。
- 目标：用现成Runner/Responses替换旧手写循环与HTTP模型层的基础入口。
- 前置依赖：P1-02；AGENT_RUNTIME；本次核查的固定SDK公开API。
- 涉及文件或模块：models.py、pyproject.toml、requirements/constraints、SDK边界测试。
- 具体工作：agent extra引入openai-agents/openai，复用OpenAIResponsesModel、ScriptedModel和公开原生类型；显式timeout／重试关闭／raw_usage／encrypted continuation／tracing关闭；先接一个无副作用function tool。删除模型worker/JSON RPC计划，不新建Model基类。
- 验收标准：ScriptedModel通过Runner完成一轮tool回传与结束；缺usage保留null；原生items不被四role压平；公开API可实现准入顺序；核心安装不加载SDK。无fork、无私有_state。
- 需要运行的测试：T07中SDK输入／输出／超时／错误传播最小契约；T06密钥哨兵。V-LIVE留P1-08经授权运行。
- 预计复杂度：M。

### P1-05 — 六工具接入SDK及预算停止

- Task ID：P1-05；所属Phase：1。
- 目标：在SDK Loop中完成受控源码修复，候选交给同一验证器。
- 前置依赖：P1-03、P1-04、P1-06；AGENT_RUNTIME。
- 涉及文件或模块：tools.py、harness.py、SDK脚本与runtime测试。
- 具体工作：六个async function tools复用现有受控helper；failure_error_function=None，policy错误局部返回、infra穿透；串行工具与整批准入；总deadline和context超限停止；public hooks写领域事件；原生Items附件保存；删除不再使用的旧自写Loop与裁剪逻辑。
- 验收标准：SDK ScriptedModel读取→修改→Docker自查→结束；最后允许turn的合法工具可执行；超额批次一个都不执行；取消后无后台线程继续编辑；不启用默认Shell/MCP/skills；两条路径同样独立验证。
- 需要运行的测试：T03自动路径、T06权限边界、T07准入／上下文／async取消契约；只测本项目组合行为。
- 预计复杂度：M。

### P1-06 — 独立验证器与verify-patch入口

- Task ID：P1-06；所属Phase：1；建议早于P1-04/P1-05实施。
- 目标：无需模型即可验收现成Coding Agent产生的C++补丁。
- 前置依赖：P1-03；VERIFICATION、CLI；不依赖SDK。
- 涉及文件或模块：verification.py、workspace.py、cli.py、harness.py、验证集成测试。
- 具体工作：提取共用configure/build/CTest观察，基线F2P/P2P与固定inventory；实现有界外部patch/trace复制、政策校验、canonical patch和manifest；干净base应用与空build独立验证；接入verify-patch，写最小实际报告。
- 验收标准：仅核心安装可运行；正确patch通过，错误／测试修改／skip／缺用例拒绝；外部trace写成功也不能影响结局；invalid patch可早拒，任何ACCEPTED都有本次基线；无key读取与模型请求。
- 需要运行的测试：T02、T03外部路径、T04；一个真实Docker正确／错误patch；纯核心wheel导入检查。
- 预计复杂度：M；共用执行与patch模块已由P1-03提供，不在本任务重做容器运行时。

### P1-07 — 领域事件、报告与查询CLI

- Task ID：P1-07；所属Phase：1。
- 目标：两条输入路径的结果可读、可导出且来源可信度明确。
- 前置依赖：P1-05、P1-06；STATE的P1部分与CLI。
- 涉及文件或模块：events.py、harness.py、cli.py、report渲染、tests。
- 具体工作：SQLite审计单写，JSONL派生；记录engine/producer/native附件区分、raw usage、command两流日志；实现inspect/report及原子导出；结束先清理再提交结局再导出；删旧双写与Base64日志协议。
- 验收标准：report/DB/证据hash对应；导出失败不改outcome且CLI退出3；未知usage不变0；外部生成不伪装受控；查询失败Run仍正常读取；不预建P2表。
- 需要运行的测试：T08及T01少量CLI参数错误；纯核心report导入；报告丢失重导出。
- 预计复杂度：M。

### P1-08 — MVP验收与0.2.0候选发布记录

- Task ID：P1-08；所属Phase：1。
- 目标：证明新契约整条路径在真实环境中成立。
- 前置依赖：P1-01..P1-07；可授权真实模型的用户。
- 涉及文件或模块：README、Task／SDK ScriptedModel示例、测试证据、constraints、CHANGELOG。
- 具体工作：干净环境安装，锁实际镜像；运行SDK自动修复／外部补丁验收／错误拒绝／超时隔离gate；经用户显式授权做一次V-LIVE；记录支持范围与模型观察，准备0.2.0候选说明。
- 验收标准：V-DOCKER、T01–T08相关义务实际通过；V-LIVE有合法工具交互证据；无未解决的错误验收／主机边界问题；未授权远程发布时只保留本地候选。
- 需要运行的测试：Ruff、`pytest -m 'not docker'`、显式Docker gate、`python -m build`、真实模型smoke；缺项明确未完成。
- 预计复杂度：S，主要是验收与修复已发现的阻塞。

**阶段风险：** 现有Docker能力未证实、第三方模型协议不一致、CTest空跑、最后一步预算误停。**交付物：** 可安装CLI、锁定fixture Task、实际patch/report/trace、最小Docker测试和真实模型接口证据。**退出条件：** P1-08通过；Checkpoint/Resume仍未提供。

## 4. Phase 2：执行可靠性

**目标：** 在可解释的边界恢复中断Run。范围为单机／单writer／SDK完整输入边界checkpoint；非目标是任意指令级续跑、跨版本续跑、外部不可逆工具和分布式Exactly Once。前置P1全部通过。组件为既有events.py的事务增量与recovery.py；不为几行转发新增state/manager层。

### P2-01 — 外层三表与执行片段事务

- Task ID：P2-01；所属Phase：2。
- 目标：让外层状态、预算和事件同事务，而不创建另一套Agent会话DB。
- 前置依赖：P1-08；STATE_AND_RECOVERY。
- 涉及文件或模块：events.py、harness.py、tests/test_recovery.py。
- 具体工作：runs/events/checkpoints；flock单writer；状态转移与累积steps_used/tool_calls_admitted；on_llm_start之前提交segment_open；保留命令事件但不建operations调度表；旧P1审计可读不可resume。
- 验收标准：非法转移与第二writer拒绝；DB损坏不建空库；崩溃后状态/事件不分裂；模型开始前已记片段不确定性；没有逐工具重做状态。
- 需要运行的测试：T09事务／锁／损坏代表用例，T08报告不回归。
- 预计复杂度：M。

### P2-02 — 公开输入边界Checkpoint与受控暂停

- Task ID：P2-02；所属Phase：2。
- 目标：保存可重建源码和SDK下一次输入的安全边界。
- 前置依赖：P2-01；AGENT_RUNTIME公开input_filter契约。
- 涉及文件或模块：recovery.py、events.py、workspace.py、harness.py、cli.py。
- 具体工作：input_filter中前轮工具清理完毕后保存base patch、manifest、native input/instructions、SDK/Task指纹与预算；文件先durable再DB引用并关闭segment；实现--pause-after-step N，提交后明确HarnessPause→INTERRUPTED，不新建PAUSED状态。
- 验收标准：N小于max_steps且大于已用turn；暂停后无下一模型调用；无进程/构建目录快照；缺文件/hash不符拒绝；未引用孤儿无恢复效力。
- 需要运行的测试：T09安全暂停与文件/DB窗口；用ScriptedModel，真实工具已结束。
- 预计复杂度：M。

### P2-03 — 有限Resume及未知片段安全失败

- Task ID：P2-03；所属Phase：2。
- 目标：从安全Checkpoint继续；在未知副作用时保存证据并停止。
- 前置依赖：P2-02。
- 涉及文件或模块：recovery.py、cli.py、events.py、harness.py。
- 具体工作：核对所有权／指纹／deadline与容器；segment_open=true一律RECOVERY_FAILED，不补交、不回滚重做；安全边界从base+patch恢复并校验字节，native Items传Runner，剩余turn/工具预算不退款；fake从已冻结脚本按已用turn取剩余steps。
- 验收标准：受控暂停可恢复到预期验证；未知模型／半轮工具／未checkpoint完整回复都不重新执行；终态／跨SDK版本／损坏／清理不确定明确拒绝。安全Checkpoint的修复预算耗尽按正常预算停止处理，已有候选仅在剩余验证时间允许时验收；保存未验候选供新verify-patch使用。
- 需要运行的测试：T09安全与不安全片段参数化代表例；至少一次真实Docker中断后的所属容器核对清理；无付费故障实验。
- 预计复杂度：M。

### P2-04 — Trace Replay与恢复门槛

- Task ID：P2-04；所属Phase：2。
- 目标：以只读轨迹和故障证据证明受限恢复语义。
- 前置依赖：P2-03。
- 涉及文件或模块：cli.py、recovery.py、事件导出、README与tests。
- 具体工作：export-trace／trace replay只读领域事件与native引用；选定T09故障点注入，统计安全恢复和明确失败；更新0.3限制说明；删除旧superseded/attempt重做展示。
- 验收标准：T09/T10通过；trace不调用模型、Docker或工具；未知操作不因查看日志而重试；P1主链仍通过；不宣称Exactly Once。
- 需要运行的测试：T09、T10与已有主链／真实Docker清理gate，停止无关覆盖率扩张。
- 预计复杂度：M。

**阶段风险：** 模型结果未知被重收费，SDK快照被错误当安全点，文件／DB非原子，两个控制器接管同Run。**交付物：** 状态schema、Checkpoint、Resume、Trace Replay和故障证据。**退出条件：** P2-04通过；Execution Replay留P3。

## 5. Phase 3：评测与公开工程质量

**目标：** 用少量真实数据说明Harness行为，并准备可复核开源版本。范围为Harbor窄桥接、少量curated任务、可重算指标与开发文档；非目标是leaderboard冲榜或通用benchmark平台。前置P2稳定，已有固定模型／预算／镜像。

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

### P3-02 — Harbor单fixture产物接入

- Task ID：P3-02；所属Phase：3。
- 目标：实际复用Harbor producer作业与产物收集，不重写评测运行器或下载器。
- 前置依赖：P3-01；通过P1的verify-patch；TESTING_AND_EVALUATION §6。
- 涉及文件或模块：integrations/harbor.py、静态task-map/export-harbor/verify-harbor、独立Harbor环境锁、单fixture集成记录。
- 具体工作：锁定Harbor并导出一个Task的producer job（verifier.disable=true，显式artifact）；用原生CLI收集；verify-harbor仅导入已结束本地trial的有界patch，调用既有verify-patch；关联trial/collection/RP结论，不回写reward，不连接在线环境。
- 验收标准：V-HARBOR实际通过；正确／错误／缺patch／验证异常均保留分类，计数不丢；没有Docker socket进入容器，没有新ContainerBackend、在线BaseVerifier或job scheduler；不能映射的输入明确拒绝。
- 需要运行的测试：单个可信fixture的Harbor确定性生产者→显式artifact→本地验证E2E，含收集失败映射；先不调用真实模型。不把只生成配置当已集成。
- 预计复杂度：M；若锁定版本结果布局不符明确拒绝，禁止fork调度／远程下载fallback。

### P3-05 — 可重算指标与真实对照报告

- Task ID：P3-05；所属Phase：3。
- 目标：给出有可信分母、费用来源和限制说明的实验结果。
- 前置依赖：P3-02、至少一个P3-01R；评测 §6/7。
- 涉及文件或模块：evaluation.py、cli.py、tests/test_evaluation.py、实验数据与报告。
- 具体工作：eval只读Harbor trial清单／少量明确手动Run记录和RP证据；正常/中断/未开始/缺usage分类；以小手算表核验；SDK baseline/enhanced只比较安全恢复变量，外部mini/Codex等单列系统对照；用户授权后执行小规模真实实验并保留配置。
- 验收标准：无report、producer无patch、DB损坏样本不会消失；B覆盖不足明确；未知成本不造0；重算与原报告一致；没有数据就保持未实验，不能提前宣称改进比例。
- 需要运行的测试：T11；先用确定性数据；真实模型实验需明确预算授权，逐条保留试验身份与完整结果。
- 预计复杂度：M。

### P3-03 — 补丁Execution Replay

- Task ID：P3-03；所属Phase：3。
- 目标：在新Run重新验证保存候选，复核同条件结论。
- 前置依赖：P2-04、P3-01。
- 涉及文件或模块：recovery.py、cli.py、tests/test_replay.py。
- 具体工作：校验原Task／base/image／patch引用；新Run调用同一verify-patch流程，保存replay_of与差异；不解析执行历史工具轨迹、不请求模型、不修改旧Run。
- 验收标准：相同补丁可重新复现/验证并比较verdict；缺必要输入拒绝；模型与历史Shell零调用；结果差异如实记录，不保证stdout／耗时逐位相同。
- 需要运行的测试：T12与一个固定fixtureDocker replay，不重复整套Agent测试。
- 预计复杂度：S。

### P3-04 — 最小CI与稳定版公开材料

- Task ID：P3-04；所属Phase：3。
- 目标：他人能够从干净安装复跑项目声明。
- 前置依赖：P3-02、P3-05、P3-03及对应gate。
- 涉及文件或模块：.github/workflows/ci.yml、pyproject、README、CONTRIBUTING、SECURITY、CHANGELOG、docs示例证据。
- 具体工作：收敛为Linux质量/SDK fixture和Docker两个job；constraints固定；纯核心及agent extra的wheel安装smoke；说明支持范围、真实实验、失败分类、费用／源码边界、协议迁移；发布前检查许可证和敏感信息。
- 验收标准：V-RELEASE、P1/P2相关gate实际通过；报告可重算；至少一个真实模型成功案例有证据但不虚构通用成功率；1.0候选文档无未实现命令混入当前帮助。
- 需要运行的测试：Ruff、必要pytest／Docker、build及干净wheel安装；经授权才push/tag/PyPI，不自动发布。
- 预计复杂度：M。

**阶段风险：** 自有题过拟合、真实库构建过重、模型版本漂移、错误分母、引用上游许可不全。**交付物：** 固定suite、来源、Harbor产物接入实际证据、原始Run、结构化对照报告、补丁Execution Replay、最小CI和开源文档。**退出条件：** 未通过的实例如实排除／列失败，支持范围内的所有gate通过。

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

### P4-02 — 第二个实际模型端点

- Task ID：P4-02；所属Phase：4。
- 目标：支持确有需求、当前已认证路径不能表达的模型服务。
- 前置依赖：具体端点需求、公开协议差异和可测试访问。
- 涉及文件或模块：models.py、SDK现成adapter或可选extra、DECISIONS。
- 具体工作：优先配置同SDK或其已有模型adapter；只认证一种新组合；说明原生Items、usage、timeout与重试差异；不恢复自有Turn/fourroles或provider registry。
- 验收标准：满足相同安全工具／预算语义；支持差异明确，不能兼容就拒绝；不引入自动多级fallback。
- 需要运行的测试：T07受影响契约与授权后的第二端点smoke，相关P1主链。
- 预计复杂度：M。

### P4-03 — 深度嵌入另一个开源Coding Agent的必要性验证

- Task ID：P4-03；所属Phase：4。
- 目标：只有外部patch／Harbor方式不能满足真实需求时才嵌入第二个Runtime。
- 前置依赖：具体需求、已有外部对照结果；重新核对上游版本、许可与执行接口。
- 涉及文件或模块：小型集成实验、DECISIONS；通过后才建单一adapter。
- 具体工作：比较Codex官方Python SDK/exec-server、OpenHands自定义工具、pi SDK；证明所有执行落点、断连失败、凭证、网络、取消清理；复用原生会话与轨迹，不叠第二套持久化。
- 验收标准：有收益且无需fork／主机执行fallback／双会话DB；否则决定继续只接patch。不能把externalSandbox配置名当Docker安全证明。
- 需要运行的测试：一个固定fixture与隔离／断连／取消契约，T06；不把全部供应商一起接入。
- 预计复杂度：M（决策及窄试验）。

### P4-04 — 复用上游上下文压缩

- Task ID：P4-04；所属Phase：4。
- 目标：处理真实出现并阻碍任务的CONTEXT_LIMIT。
- 前置依赖：失败trace、固定任务和模型预算；现有停止策略的实际数据。
- 涉及文件或模块：SDK上下文配置、harness预算钩子、评测报告。
- 具体工作：先评估上游compaction／context管理；额外调用计入预算，原生continuation保持有效；改变一个变量比较收益与额外token／耗时；不自制摘要器／向量数据库。
- 验收标准：公开API足够、同条件证据显示实际收益；无收益就不引入；压缩失败明确停止，不偷偷改变模型或任务。
- 需要运行的测试：T07相关原生输入契约、固定小实验与费用统计；不增加大型框架。
- 预计复杂度：M。

**阶段交付物：** 每项可复核立项／不立项记录，成立时才交付小模块与对照证据。**主要风险：** 重复框架、双状态机和功能膨胀。**验收方法：** 同一契约＋实际收益；无数据不自动进入编码。

## 7. 建议给下一个Coding Agent的工作指令

> 阅读Spec修订2026-10-19.2的SPEC.md、CURRENT_STATE和IMPLEMENTATION_PLAN。先检查work/spec-p1-01分支及当前Git状态，保留已有提交和新用户修改。本次只继续P1-01：将现有规格入口对齐本修订，在具备Docker的Linux/amd64主机运行原fixture真实Docker gate并记录证据。此前4个Docker失败是环境阻塞，不能用76个普通测试通过代替。无合适Docker环境时明确未完成的前置条件，完成其它已授权准备，不回退宿主执行Task。不要同时重写Agent或恢复系统。完成后报告实际结果和下一任务P1-02。

后续会话将Task ID替换成下一项，并读取其依赖的权威文档即可。每个Phase结束都要更新当前可用能力，而不是把全计划一次贴进README当已完成。
