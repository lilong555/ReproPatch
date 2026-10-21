# 测试报告

当前版本：**0.3.0.dev2，Task v2**。验收日期：2026-10-21。
**425 项测试通过：291 项核心、115 项 SDK、19 项真实 Docker；0 失败、0 跳过。**
三组分别执行，未选中项目不计为跳过或通过。P2-02 已完成，完整 0.3.0 仍在开发。

## 执行结果

| 检查 | 结果 | 原始证据 |
| --- | --- | --- |
| Ruff 检查与格式 | 通过 | [检查](evidence/p2-02/ruff-check.log)、[格式](evidence/p2-02/ruff-format.log) |
| 核心测试 | 291 通过 | [日志](evidence/p2-02/core-tests.log)、[JUnit](evidence/p2-02/core-tests.xml) |
| SDK 契约及自动路径 | 115 通过 | [摘要](evidence/p2-02/sdk-contract/summary.json)、[日志](evidence/p2-02/sdk-contract/tests.log) |
| 真实 Docker | 19 通过 | [摘要](evidence/p2-02/docker-gate/summary.json)、[JUnit](evidence/p2-02/docker-gate/docker-tests.xml) |
| 干净核心 wheel | 无模型模块和 SDK 的正确/错误补丁验收通过 | [安装](evidence/p2-02/installation.json)、[路径验收](evidence/p2-02/packaging.json) |
| 干净 agent wheel | 固定依赖、原生 fake 自动修复、406 项非 Docker 测试通过 | [安装版测试](evidence/p2-02/installed-all/summary.json) |
| 报告与数据库 | 当前报告核验及重建；历史 29 份 schema v1/v2 报告保持可读且数据库未改写 | [核验](evidence/p2-02/artifact-checks.json) |
| 分发 | wheel/sdist 与当前执行源码一致 | [核验](evidence/p2-02/distribution-checks.json) |

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
十九项 Docker 场景包含真实暂停：编辑及容器自查结束后，两个所属容器删除确认，源码与 Checkpoint 保留。
安装版 CLI 暂停退出 0，summary 包含 paused=true、INTERRUPTED、outcome=null 和 Checkpoint 引用。
暂停并不表示补丁接受；恢复能力将在 P2-03 验收。

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

19 项真实 Docker 测试覆盖自动修复、错误候选、编码字节往返、只读/非 root/断网/凭据边界，
普通超时、双流输出上限、派生进程、tmpfs、中断清理、外部正确/错误补丁、skip/缺失与字面测试名，
以及 run_shell 的只读源码、双流日志、超时删除和预算拒绝。
固定镜像为 sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a，
镜像内 CMake/CTest 3.28.3、GCC 13.3.0。

核心 wheel 在干净 Python 3.12 环境只安装 PyYAML，从项目外调用且阻止模型模块导入。
agent wheel 验证固定依赖与安装目录，执行全部 406 项非 Docker 测试，并用 ScriptedModel 完成真实容器修复。
正确/错误补丁分别 ACCEPTED/REJECTED；四份报告删除重建前后数据库字节和结局一致。

## Phase 1 模型证据

0.2.0rc1 在 2026-10-20 经用户授权，使用 DeepSeek deepseek-flash 完成真实 Responses 修复。
5 个 turn、5 次工具调用，21.088 秒，正常 MODEL_FINISHED，独立 Docker 验收 ACCEPTED。
真实用量为 81,507 输入、632 输出、82,139 合计，费用未知。
[原始摘要](evidence/p1-08/live-deepseek/summary.json) 与 [完整契约](P1-08.md) 保持原版；
该结果属于 0.2.0rc1，本任务未重复付费请求，不用于声明 0.3.0 的新 V-LIVE 或一般修复率。

## 当前边界

当前支持完整输入 Checkpoint 与受控暂停，尚不提供 Resume、Replay、Harbor 或跨 Run 清扫。
开放片段、模型最终文本及完整工具日志都不构成可恢复输入边界。
报告导出失败不改写权威终态；无法核验的数据库或证据明确报错，不创建空库或推断成功。
下一任务为 P2-03。
