# 测试报告

当前开发实现的预算反馈与短修复循环通过 20 项定向离线检查：Agent Runtime 19 项与原生恢复预算 1 项。
覆盖整批准入后的剩余额度、失败工具反馈、最后一轮编辑及恢复后的累计计数。Ruff 检查与格式通过。
开发实现提交 `4e780edf41e6611c60da1044bfc0cfc951885b97` 的
[核心、SDK 与真实 Docker CI](https://github.com/lilong555/ReproPatch/actions/runs/39721519709) 全部通过。
本实现的真实修复成绩待新批次评测，已发布 rc3 的成绩及 CI 记录如下。

当前版本：**0.3.0rc3，Task v2**。验收日期：2026-10-21。
当前本地范围为 6 项定向检查：基线与自检规模反馈 2 项、配置/编译/测试发现失败诊断 3 项、
SDK 自动修复与独立验收 1 项。完整执行证据不因精简模型视图而删除。
另从 rc2 的真实 Catch2 历史输入和自检证据，经过公开 SDK Runner 进行离线输入边界检查：
旧反馈对应下一输入 596,554 字节，触发 `CONTEXT_LIMIT`；当前视图为 218,955 字节，
69 个测试观察和两个失败命令预览保留，历史前缀逐字相同，网络已禁用，无 HTTP 模型请求。
这些数据只验证输入反馈，不是修复重跑，不计入 Resolved@1。
复核方法见 [反馈上下文](../benchmarks/feedback-context.md)。

rc3 核心实现提交 `5beb579325f9eabd8cd449dc80abd37dfd716492` 的
[CI](https://github.com/lilong555/ReproPatch/actions/runs/39630705838)
已通过：323 项核心、147 项 SDK 与 21 项真实 Docker，共 491 项；发布时本地 6 项结果单列保留。
Benchmark 启动预检的定向范围为 `tests/test_benchmark_budget.py` 的 5 项，
包括三个原账本场景、价格变更和无付费预检两个场景。
启动预检代码提交 `b78a3b0151afefb13cc1943a26a271f8070f19be` 的
[CI](https://github.com/lilong555/ReproPatch/actions/runs/39717468270)
已通过 325 项核心、147 项 SDK 和 21 项真实 Docker，共 493 项。

## 当前 rc3 真实对照与免费演示

2026-10-22 两题、两组、各一次的真实尝试已完成：ReproPatch 0/2、mini-SWE-agent 0/2，
47 次模型请求，费用上界 ¥0.54663080，未知用量 0 次。
四条候选均为空，Oracle 入口记录 NO_PATCH；两组所属容器删除已确认。
逐条预算、轨迹、耗时与原始证据见 [rc3 对照](../benchmarks/rc3-rerun.md)。

免费核心演示已用现有固定镜像和核心环境执行：正确补丁 ACCEPTED、错误补丁 REJECTED，
doctor、inspect、report 和 export-trace 均通过，模型步骤为零。
演示报告与命令输出保存在本轮证据包中；此次使用既有环境。

## rc2 上下文与真实修复对照

rc2 的本地范围为 21 项定向回归：初始基线视图 1 项、Agent Runtime 19 项、原生历史恢复 1 项。
另在真实 Catch2 环境执行两轮 ScriptedModel 和一次源码读取，69 个测试观察完整，
输入分别为 71,131 / 74,395 字节，结果为预期的 `REJECTED / NO_PATCH`，容器删除已确认。
同一镜像下的原生 mini-SWE-agent 无模型权限检查通过。
两题真实收费模型首次对照为 ReproPatch 0/2、mini 1/2，45 次 HTTP 请求，费用上界 ¥0.52158136，
其成绩属于 rc2；详见 [原始对照报告](../benchmarks/pilot-results.md)。当前批次见上方 rc3 记录。
详情见 [上下文记录](../benchmarks/context-check.json) 与 [mini 环境](../benchmarks/mini-environment.md)。

## rc1 完整验收

**483 项测试通过：315 项核心、147 项 SDK、21 项真实 Docker；0 失败、0 跳过。**
以下结果属于 0.3.0rc1，三组分别执行，未选中项目不计为跳过或通过，不计作 rc2 的完整回归。

## 执行结果

| 检查 | 结果 | 原始证据 |
| --- | --- | --- |
| Ruff 检查与格式 | 通过 | [检查](evidence/p2-04/ruff-check.log)、[格式](evidence/p2-04/ruff-format.log) |
| 核心测试 | 315 通过 | [日志](evidence/p2-04/core-tests.log)、[JUnit](evidence/p2-04/core-tests.xml) |
| SDK 契约及自动路径 | 147 通过 | [摘要](evidence/p2-04/sdk-contract/summary.json)、[日志](evidence/p2-04/sdk-contract/tests.log) |
| 真实 Docker | 21 通过 | [摘要](evidence/p2-04/docker-gate/summary.json)、[JUnit](evidence/p2-04/docker-gate/docker-tests.xml) |
| 干净核心 wheel | 无模型模块和 SDK 的正确/错误补丁验收通过 | [安装](evidence/p2-04/installation.json)、[路径验收](evidence/p2-04/packaging.json) |
| 干净 agent wheel | 固定依赖、原生 fake 自动修复、462 项非 Docker 测试通过 | [安装版测试](evidence/p2-04/installed-all/summary.json) |
| 报告与数据库 | 当前报告核验及重建；历史 64 份 schema v1/v2 报告保持可读且数据库未改写 | [核验](evidence/p2-04/artifact-checks.json) |
| 只读轨迹 | 18 项核心用例及无 SDK 安装版 CLI 通过 | [安装版](evidence/p2-04/installed-trace-checks.json) |
| 恢复故障 gate | 13 场景：3 安全恢复、9 明确失败、1 控制器拒绝，失败场景零新增模型/工具调用 | [摘要](evidence/p2-04/recovery-gate/summary.json) |
| 分发 | wheel/sdist 与当前执行源码一致 | [核验](evidence/p2-04/distribution-checks.json) |

源码与固定依赖的实际执行字节见 SDK/Docker gate 的 source-manifest.json。
历史 Git HEAD 不代替执行身份；安装包与实现 SHA-256 见 RELEASE.json。

## 外层事务

19 项专项测试来自 tests/test_recovery.py，其中 16 项仅需核心依赖，3 项使用公开 SDK ScriptedModel。
数据库只有 runs/events/checkpoints；状态、预算和事件同事务，自动路径在完整输入边界提交 Checkpoint。
准备成功必须同时提交冻结输入与 REPRODUCING；执行阶段核对冻结引用、实际身份和原 Task 预算。
请求开始必须先提交步骤扣减、未知用量和 segment_open=1；工具整批准入提交失败时不执行任何本批工具。
已消费预算不能退款，超出冻结上限拒绝；deadline_at 始终使用创建时的原值。

真实子进程在提交前后调用 os._exit，强制缓存溢出覆盖 SQLite 原生回滚日志。
持锁打开已有数据库后，状态、事件前缀、计数和片段保持一致；不由 JSONL 或 report.json 重建数据库。
第二写者、非法阶段、被篡改的冻结输入、状态与事件分裂、损坏/缺失/未知/链接数据库均拒绝。
schema 0/1 按原版读取且写打开返回 RESUME_UNSUPPORTED，不做 schema 迁移。
实际 SDK 请求前可从独立只读连接观察到 model_started 与 segment_open=1；只有完整输入 Checkpoint 事务才会关闭修复片段。

## Checkpoint 与暂停

29 项专项测试来自 tests/test_checkpoints.py，其中 17 项核心、12 项 SDK。SDK 的完整输入 filter 保存全部原生 Items，
包括整批 function_call_output 及必要 opaque continuation；首次 step=0 允许空 patch。
输入、补丁、SourceManifest 和 manifest 全部 durable 后才提交数据库引用、累计预算和关闭片段。
暂停与该事务一起进入 INTERRUPTED/outcome=null，不执行下一请求；模型正常结束优先走独立验收。
原始期限保持不变，普通 retain=none 也不会清除暂停依赖的修复源码；容器及构建快照均清理。

测试覆盖文件持久化失败、Checkpoint 事务拒绝、真实子进程在文件写完与数据库提交之间退出、
孤儿目录不参与恢复点选择、版本/计数/期限/指纹及引用 hash 损坏、暂停导出失败、
核心报告删除重建、用户取消，以及损坏的暂停 manifest 不显示证据完整。
二十一项 Docker 场景包含真实暂停：编辑及容器自查结束后，两个所属容器删除确认，源码与 Checkpoint 保留。
安装版 CLI 暂停退出 0，summary 包含 paused=true、INTERRUPTED、outcome=null 和 Checkpoint 引用。
暂停并不表示补丁接受；有限恢复契约见 [P2-03](P2-03.md)。

## 有限恢复

38 项专项测试包括 6 项核心、32 项 SDK；从安全边界使用剩余脚本与 Runner turn，累计工具额度和未知用量不退款。
真实子进程覆盖请求开始、回复保存、编辑完成、Checkpoint 文件/事务窗口、安全边界与恢复过程中退出。
只有关闭的 Checkpoint 可继续；模型结果未知或未闭合片段明确失败，不重发、补交、回滚或重做工具。
预算、SDK/工具身份、源码分歧、丢失工作区、孤儿附件、再次暂停与取消均有外部行为验收。

真实 Docker 测试确认暂停后恢复并独立验收 ACCEPTED；另一控制器退出后，其登记容器仍在运行，
恢复命令删除并核验后以 UNSUPPORTED_RECOVERY_PHASE 停止，没有模型请求。
安装版 CLI 从冻结脚本暂停后成功 resume；五份派生报告删除重建，数据库与结局未改变。

## 只读轨迹与故障 gate

18 项 tests/test_trace.py 核心测试禁止进程、SDK、模型、执行工具或恢复，核对原 Run 文件不变。
覆盖真实 v1/v2 事件及旧 kind 展示、缺失/伪造派生产物、缺失原生和嵌套证据、开放片段与暂停、
逐字节 JSONL、原 Run/既有目标/链接/穿越拒绝、坏数据库与不可信终端文本。
Trace 只展示领域观察和引用，不展开原生模型内容；未知附件不改写原 outcome，不把 JSONL 导入为权威状态。

恢复 gate 指定重复执行 13 项既有用例，不增加唯一测试数。3 个场景安全恢复至 ACCEPTED，
9 个以明确 RECOVERY_FAILED 结束，1 个持锁控制器拒绝接管；失败场景没有新增模型或工具调用。
所有原始期限保留，已完成工具 ID 不重复。故障前缀不是独立试验，不用于估计模型修复率。
32 份当前报告包含 1 个故意损坏 Checkpoint 的负例，按不可核查保留，不修补原始文件。

## SDK 与独立验收

自动路径使用公开 Runner、六个 async function tools 和原生 Responses Items，不自建模型循环。
当前固定 openai-agents 0.24.0、openai 3.35.1、httpx2 2.15.1、pydantic 2.14.1。
原生 reasoning/opaque continuation/function_call/output 关联、整批准入、串行工具、最后允许 turn 执行、
上下文与阶段预算、缺失/部分/显式零 raw_usage、超时/取消/协议失败保持原有契约。
模型开始但没有结果的用量保持未知；最终报告从已提交外层行取得累计预算与用量。

模型或协议错误保留未验补丁，取消不进入 independent；同步 helper 在自己的有限期限内完成。
verify-patch 只需核心依赖，不导入 models/agents/openai，也不读取模型 key。
独立验证从固定 commit 应用规范 patch，核对完整字节清单及再次导出的 patch，重建并执行固定 CTest。
F2P 必须在基线普通失败且匹配原始签名，P2P 必须通过；skip、缺失、身份变化或无效 JUnit 均不能获得 ACCEPTED。

## 容器与安装

21 项真实 Docker 测试覆盖自动修复、错误候选、编码字节往返、只读/非 root/断网/凭据边界，
普通超时、双流输出上限、派生进程、tmpfs、中断清理、外部正确/错误补丁、skip/缺失与字面测试名，
以及 run_shell 的只读源码、双流日志、超时删除和预算拒绝。
固定镜像为 sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a，
镜像内 CMake/CTest 3.28.3、GCC 13.3.0。

核心 wheel 在干净 Python 3.12 环境只安装 PyYAML，从项目外调用且阻止模型模块导入。
agent wheel 验证固定依赖与安装目录，执行全部 462 项非 Docker 测试，并用 ScriptedModel 完成真实容器修复。
正确/错误补丁分别 ACCEPTED/REJECTED；五份报告删除重建前后数据库字节和结局一致。

## Phase 1 模型证据

0.2.0rc1 在 2026-10-20 经用户授权，使用 DeepSeek deepseek-flash 完成真实 Responses 修复。
5 个 turn、5 次工具调用，21.088 秒，正常 MODEL_FINISHED，独立 Docker 验收 ACCEPTED。
真实用量为 81,507 输入、632 输出、82,139 合计，费用未知。
[原始摘要](evidence/p1-08/live-deepseek/summary.json) 与 [完整契约](P1-08.md) 保持原版；
该结果属于 0.2.0rc1，本任务未重复付费请求，不用于声明 0.3.0 的新 V-LIVE 或一般修复率。

## 当前边界

当前支持完整输入 Checkpoint、受控暂停、有限 Resume 和只读 Trace Replay，尚不提供 Execution Replay、Harbor 或跨 Run 清扫。
开放片段、模型最终文本及完整工具日志都不构成可恢复输入边界。
报告导出失败不改写权威终态；无法核验的数据库或证据明确报错，不创建空库或推断成功。
下一任务为 P3-01。
