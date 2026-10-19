# 需求与验收映射

状态：设计冻结；“必须”约束所属阶段完成时的行为，**不表示既有代码已满足**。模块职责见[架构](ARCHITECTURE.md)，测试 ID 见[测试与评测](TESTING_AND_EVALUATION.md)，任务 ID 见[实施计划](IMPLEMENTATION_PLAN.md)。不另建重复的需求管理系统。

## 1. 用户、场景与输入输出

| 用户／场景 | 输入 | 用户需要的结果 |
|---|---|---|
| C++ 维护者复现一个回归 | 审核后的 Task、本地仓库、完整 commit、工具链镜像、失败用例 | 原始故障是否符合契约，以及可核查原因 |
| 维护者试用代码修复 Agent | 同一任务、所选模型、明确调用预算 | 候选 patch、从干净源码得到的验收结论、执行轨迹 |
| Harness 开发者调试失败 | Run ID、日志与固定 fixture | 区分模型判断、工具失败、预算停止与环境问题 |
| 研究执行可靠性 | 固定任务集／模型／预算、注入的中断 | 恢复是否有证据、有没有重复未知副作用、实际成本 |
| 开源使用者复核项目展示 | 源代码版本、镜像身份、Task／patch／报告 | 可自行重跑并验证声明，不依赖截图和虚构指标 |

基础输入是 Task YAML；Bug Report 与 CI Failure 可由用户整理进 description／失败签名，不要求 MVP 自动解析任意日志或接入 GitHub。输出是一个 Run 目录，不是自动提交／推送的 Git 分支。

## 2. 功能需求

| ID | 必须行为与验收条件 | 阶段 | 主要模块 | 开发任务／验证 |
|---|---|---|---|---|
| FR-001 | 解析 Task v2；拒绝重复 key、未知字段、类型错误和 v1，给字段级错误 | P1 | task,cli | P1-02 / T01 |
| FR-002 | 固定完整 commit 和实际 image ID；后续输入漂移不能改变同 Run | P1 | task,workspace,sandbox | P1-02 / T01,T03 |
| FR-003 | detached Worktree 不改原分支／未提交内容；只操作已登记的自身工作区 | P1 | workspace | P1-03 / T03,T06 |
| FR-004 | 只读无.git快照进入容器；Docker 不可用时明确错误，无 host fallback | P1 | sandbox,workspace | P1-03 / T05,T06 |
| FR-005 | 先配置编译成功，再逐个核验 F2P 名称、正常失败及签名 | P1 | verification | P1-06 / T02 |
| FR-006 | 基线 P2P 全部存在、实际运行并通过，否则不启动 Agent | P1 | verification,harness | P1-06 / T02 |
| FR-007 | 无法复现、环境错误、预算停止、补丁错误和证据不足分别报告 | P1 | verification,harness | P1-06,P1-07 / T02,T04,T08 |
| FR-008 | 提供 list/read/search/edit/run_command/run_shell 固定工具接口及明确结果 | P1 | tools | P1-05 / T03,T06,T07 |
| FR-009 | 仅允许已声明已有文本源码变更；拒绝越界、测试、mode、新增／删除／链接变更 | P1 | tools,workspace | P1-03,P1-05 / T04,T06 |
| FR-010 | 一个官方 SDK 驱动的真实模型接口和一个 Mock；模型协议错误不得变成成功 | P1 | models | P1-04 / T07,V-LIVE |
| FR-011 | 串行 Agent Loop，保存可见对话和工具响应；模型结束不等于验收通过 | P1 | harness | P1-05 / T03,T04 |
| FR-012 | 模型尝试／工具尝试／总时间／单次输出／验证预留受控；不无限循环 | P1 | harness,process,models | P1-04,P1-05 / T05,T07 |
| FR-013 | 上下文按完整工具组裁剪；固定规则不可被删；过大时明确停止 | P1 | harness | P1-05 / T07 |
| FR-014 | 导出完整候选 diff、patch hash、byte manifest；不悄悄漏掉越界修改 | P1 | workspace | P1-03 / T03,T04 |
| FR-015 | 从原 commit 创建干净验收树，精确应用 patch，校验候选字节一致，无旧构建复用 | P1 | verification,workspace | P1-06 / T03,T04 |
| FR-016 | 验收 F2P、P2P 全通过；空集合／skip／缺用例不能验收；保留原始证据 | P1 | verification | P1-06 / T02,T04 |
| FR-017 | 命令超时或输出超限后销毁整容器；未确认清理不得继续成功路径 | P1 | sandbox,process | P1-03 / T05 |
| FR-018 | SQLite 审计是事件权威；JSONL 从数据库导出；正常终止产生一致 JSON/Markdown 报告 | P1 | events,harness,cli | P1-07 / T08 |
| FR-019 | 提供 run/doctor/validate-task/inspect/report，机器输出和退出码有稳定约定 | P1 | cli | P1-07 / T01,T08 |
| FR-020 | 状态转移、预算消耗、operation intent/result 与对应事件同事务提交 | P2 | state,events | P2-01 / T09 |
| FR-021 | 完整工具组边界生成可校验 checkpoint，保存源码／上下文／预算，不保存进程 | P2 | recovery,workspace | P2-02 / T09 |
| FR-022 | Resume 先核对资源和未知副作用；不盲重复未知模型请求，不退款；无有效依据明确失败 | P2 | recovery | P2-03 / T09 |
| FR-023 | Trace Replay 只读取事件；不会启动 Docker、调用模型或修改旧 Run | P2 | recovery,cli | P2-04 / T10 |
| FR-024 | 支持固定 suite、baseline/enhanced 同模型预算对照；持久化attempt清单，含中断样本的指标分母可重算 | P3 | evaluation | P3-01,P3-02 / T11 |
| FR-025 | Execution Replay 在新 Run 重放已存动作，不重新请求模型，比较 patch／测试结果 | P3 | evaluation,recovery | P3-03 / T12 |
| FR-026 | 保存 model usage、工具次数和阶段时间；成本缺数据时 null，未知计费单列 | P1基础/P3汇总 | models,events,evaluation | P1-07,P3-02 / T08,T11 |
| FR-027 | 真实任务有来源／许可／commit／环境／测试依据；纳入 suite 前先人工验证 | P3 | examples,evaluation | P3-01R（及后续R2/R3实例） / V-CURATE |
| FR-028 | 运行报告足以定位错误：原因、执行身份、stderr、证据引用及未解决问题 | P1 | errors,events,harness | P1-07 / T08 |
| FR-029 | 公开发布含安装、真实复跑流程、限制、协议版本和变更说明 | P3 | README,docs,CI | P3-04 / V-RELEASE |
| FR-030 | 额外模型、C++ executor、Harbor 等扩展必须先提供实际需求／测量证据 | P4 | 对应局部模块 | P4-01..P4-04 / 扩展立项记录 |

## 3. 非功能需求

| ID | 约束和可衡量标准 | 阶段／验收 |
|---|---|---|
| NFR-001 | 首版仅 Linux/amd64、Python 3.12、本地 Docker Engine、CMake/CTest≥3.26；其它平台明确不支持 | P1 doctor + V-DOCKER |
| NFR-002 | 容器非 root、无网络、无额外 capabilities、只读 root、无 socket/home/key 挂载；源码只读 | P1 T06 实际 Docker 检查 |
| NFR-003 | 不声称 Docker 可完全防御恶意代码；信任 Task、镜像、验收与本地Git元数据的范围须在 SECURITY/README明确 | P1 安全文档审查 |
| NFR-004 | healthy daemon 条件下，timeout 后限定清理尝试窗口为10秒；无法确认消失则停止且报告；不存在静默遗留后继续 | P1 T05；不设虚假全环境成功率 |
| NFR-005 | source／patch／原始日志／preview／上下文均有明确大小界限，执行时流式实施，不靠事后提醒 | P1 T05,T07，数值由执行与Runtime文档定义 |
| NFR-006 | 密钥不进入容器、Task、事件和可导出报告；工具输出和库异常中的已知秘密值在入口过滤 | P1 T06，注入哨兵值测试 |
| NFR-007 | 所有隔离代码路径保持宿主argv调用，无模型字符串宿主Shell求值 | P1 T06 + 定向代码审查 |
| NFR-008 | 非法路径／symlink／清理所有权失败必须拒绝，不删除用户原仓库或其它Run | P1 T06，P2 T09 |
| NFR-009 | 已知正确fixture补丁从固定commit干净应用后可验收；已知错误补丁、测试缺失／skip不能误验收 | P1 T03,T04；这是确定性夹具义务，不是通用模型成功率 |
| NFR-010 | 单Run单writer；P2 DB状态＋事件原子；JSONL丢失可重导；损坏不建空DB掩盖 | P1 T08，P2 T09 |
| NFR-011 | 不隐式重试付费模型请求；usage未知与0区分；同Run预算恢复不重置 | P1 T07，P2 T09 |
| NFR-012 | 实现无插件注册器、依赖注入容器、服务分层套壳；每个新增生产依赖给具体收益和直接维护成本 | 每任务DoD审查 |
| NFR-013 | 只在明确边界校验／捕获；内部意外异常保留traceback，不能转换成业务成功 | P1 T08 + 代码审查 |
| NFR-014 | 测试有具体回归目标；无覆盖率硬门槛、无真实模型默认CI、无镜像／Docker缺失静默跳过发布gate | 各阶段T集合＋V-RELEASE |
| NFR-015 | 性能与成功率只能来自保留配置／原始Run的实验；报告给分母、未知／失败数、样本限制 | P3 T11 + 实验审查 |
| NFR-016 | 不自动发PR、推送、合并、发消息；补丁验收与发布授权分开 | P1 CLI能力检查 |
| NFR-017 | 相同执行契约的task hash不因本地目录变化；模型／工具／prompt／策略另记fingerprint | P1 T01、P3 T11 |

## 4. 阶段验收目标

**Phase 1 的核心门槛**是一条在真实 Docker 中运行的确定性完整路径：固定 Task→基线 F2P失败/P2P通过→Mock 修改→干净 patch 应用→F2P/P2P通过→报告。配套错误补丁拒绝、超时整容器清理、源码只读／密钥隔离、原工作树不变必须实际验证。真实模型适配必须有一次人工授权的工具调用 smoke evidence；它的随机修复成功不由 Fake 测试代替。

Phase 2 需要证明在约定中断点恢复或明确失败，不能把“能读取旧日志”当 Resume。Phase 3 需要一份真实完成且可重算的对照报告；不预设模型修复成功率，也不以所有任务成功作为1.0的必要条件。稳定发布要求支持范围内的协议、错误分类和回归门槛可靠。

## 5. 工程风险与控制

| 风险 | 具体失败情形 | 控制与阶段 |
|---|---|---|
| 环境不可复现 | 任务用HEAD/tag，镜像变了或依赖缺失 | 完整OID/image锁定；离线镜像显式准备；P1 |
| 错误验收 | Agent去掉测试、空selector、使用旧binary | 非空固定名单、保护文件、干净构建、字节往返；P1 |
| 主机受影响 | Git配置触发filter，挂Docker socket，清理错目录 | 可信本地Git边界、危险配置拒绝、无控制面挂载、所有权核对；P1 |
| 超时留下进程 | 只kill docker CLI | 整容器销毁与确认；P1 |
| 密钥／源码出境 | 将宿主env传容器、日志包含key | 最小环境、已知秘密过滤、明确真实模型数据边界；P1 |
| 不可解释的恢复 | DB记录了开始但外部操作结果未知 | intent/result、checkpoint、先核对、无盲重付费；P2 |
| 维护范围失控 | 尚无稳定demo就做framework/C++/benchmark平台 | 冻结阶段、任务DoD、按数据立项；全阶段 |
| 实验结论误导 | 小样本、过滤环境失败、模型配置不同 | 预先冻结suite、披露排除、双分母、重复实验；P3 |
| 真实库构建过重 | 两次全量build超过预算／tmpfs | 首批挑小任务，测阶段耗时，超限排除并记录，不静默降低验收 |

当前没有必须阻塞规格的产品方向问题。待实作确认的是 Docker 主机能力、实际镜像digest、所选模型端点和真实任务来源；这些是阶段gate，不是本轮虚构默认结果的理由。
