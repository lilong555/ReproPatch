# C++ 只读契约反馈对照

同一 `gpt-6-luna` 模型下，两个 Catch2 实例各运行三次：ReproPatch Full **6/6**、
mini-SWE-agent **3/6**、ReproPatch Ablation **3/6**。
三组端点相同的五个配对子集分别为 **5/5、3/5、3/5**。
另选两个 FMT 编译回归任务，双方均 **1/2**。
当前收益集中在 Catch2 的接口与实现追踪，FMT 的连续修复仍有失败样本。

[逐次结构化结果](contract-results.json) · [源码与依赖清单](contract-source-manifest.json) ·
[完整证据](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-contract-comparison-2026-10-22)

## 固定矩阵与指标

Catch2 使用固定官方 Oracle：2187 要求 2 F2P + 50 P2P，2723 要求 2 F2P + 100 P2P。
下表分母为两个实例的六次单次尝试，逐次结果完整保留。

| 组别 | Oracle 成功 / 尝试 | 模型请求 | 输入 token | 输出 token |
| --- | ---: | ---: | ---: | ---: |
| ReproPatch Full | 6/6 | 69 | 1,355,336 | 3,973 |
| mini-SWE-agent | 3/6 | 62 | 1,320,883 | 7,630 |
| ReproPatch Ablation | 3/6 | 68 | 1,344,380 | 4,262 |

端点完全相同的 Catch2 子集：

| 组别 | Oracle 成功 / 尝试 | 模型请求 | 输入 token | 输出 token |
| --- | ---: | ---: | ---: | ---: |
| ReproPatch Full | 5/5 | 57 | 1,099,321 | 3,467 |
| mini-SWE-agent | 3/5 | 52 | 1,090,556 | 6,239 |
| ReproPatch Ablation | 3/5 | 56 | 1,096,354 | 3,556 |

FMT 原始记录的测试阶段为 `NONE`、F2P/P2P 为空，属于编译回归扩展。
prepared Task 保护 CMake 与测试，将原生回归目标的编译及执行映射为 CTest；
公共 Oracle 在原始 CMake 下重新构建并执行全部 21 项原生测试。

| 组别 | 原生 Oracle 成功 / 尝试 | 模型请求 | 输入 token | 输出 token |
| --- | ---: | ---: | ---: | ---: |
| ReproPatch Full | 1/2 | 17 | 133,473 | 748 |
| mini-SWE-agent | 1/2 | 11 | 91,163 | 2,001 |

四个不同实例的首轮结果为 Full **3/4**、mini **1/4**。
适配覆盖率为 **4/129（3.10%）**，其中两个是 FMT 编译回归扩展。
Catch2 两题参与开发诊断；固定两题重复衡量此范围内的稳定性。
FMT 任务按固定数据文件的前两条记录选取，4310、4286 的顺序保留。
这些样本用于工程能力诊断，广泛 C++ 修复收益仍需独立任务验证。

## 全部逐次结果

| 实例 | 组别 | 重复 | 请求 / 工具 | Agent 停止原因 | 补丁字节 | 公共 Oracle |
| --- | --- | ---: | ---: | --- | ---: | --- |
| catchorg__Catch2-2187 | mini-SWE-agent | 1 | 9 / 9 | Submitted | 0 | NO_PATCH |
| catchorg__Catch2-2187 | ReproPatch Full | 1 | 11 / 10 | MODEL_FINISHED | 657 | ORACLE_PASSED |
| catchorg__Catch2-2187 | ReproPatch Ablation | 1 | 10 / 9 | MODEL_FINISHED | 0 | NO_PATCH |
| catchorg__Catch2-2187 | mini-SWE-agent | 2 | 11 / 11 | Submitted | 1211 | ORACLE_PASSED |
| catchorg__Catch2-2187 | ReproPatch Full | 2 | 11 / 10 | MODEL_FINISHED | 657 | ORACLE_PASSED |
| catchorg__Catch2-2187 | ReproPatch Ablation | 2 | 11 / 10 | MODEL_FINISHED | 636 | ORACLE_PASSED |
| catchorg__Catch2-2187 | mini-SWE-agent | 3 | 12 / 12 | LimitsExceeded | 1261 | ORACLE_PASSED |
| catchorg__Catch2-2187 | ReproPatch Full | 3 | 11 / 10 | MODEL_FINISHED | 636 | ORACLE_PASSED |
| catchorg__Catch2-2187 | ReproPatch Ablation | 3 | 11 / 10 | MODEL_FINISHED | 636 | ORACLE_PASSED |
| catchorg__Catch2-2723 | mini-SWE-agent | 1 | 12 / 12 | LimitsExceeded | 834 | ORACLE_FAILED |
| catchorg__Catch2-2723 | ReproPatch Full | 1 | 12 / 12 | STEP_BUDGET | 795 | ORACLE_PASSED |
| catchorg__Catch2-2723 | ReproPatch Ablation | 1 | 12 / 11 | MODEL_FINISHED | 690 | ORACLE_FAILED |
| catchorg__Catch2-2723 | mini-SWE-agent | 2 | 8 / 8 | Submitted | 997 | ORACLE_PASSED |
| catchorg__Catch2-2723 | ReproPatch Full | 2 | 12 / 12 | STEP_BUDGET | 874 | ORACLE_PASSED |
| catchorg__Catch2-2723 | ReproPatch Ablation | 2 | 12 / 11 | MODEL_FINISHED | 797 | ORACLE_PASSED |
| catchorg__Catch2-2723 | mini-SWE-agent | 3 | 10 / 10 | Submitted | 1082 | ORACLE_FAILED |
| catchorg__Catch2-2723 | ReproPatch Full | 3 | 12 / 12 | CONTROLLER_SIGTERM | 795 | ORACLE_PASSED |
| catchorg__Catch2-2723 | ReproPatch Ablation | 3 | 12 / 12 | STEP_BUDGET | 0 | NO_PATCH |
| fmtlib__fmt-4286 | mini-SWE-agent | 1 | 6 / 6 | Submitted | 845 | ORACLE_FAILED |
| fmtlib__fmt-4286 | ReproPatch Full | 1 | 12 / 12 | STEP_BUDGET | 901 | ORACLE_FAILED |
| fmtlib__fmt-4310 | mini-SWE-agent | 1 | 5 / 5 | Submitted | 412 | ORACLE_PASSED |
| fmtlib__fmt-4310 | ReproPatch Full | 1 | 5 / 4 | MODEL_FINISHED | 478 | ORACLE_PASSED |

`NO_PATCH` 表示候选为空、Oracle 测试未运行；`ORACLE_FAILED` 表示候选已实际评分且未通过。
步骤耗尽后产生的有效候选仍计成功。Catch2 原始日志包含固定评分组之外的测试观察，
成功按官方必需组判断；逐项缺失、通过和失败计数均保留。

## 输入、权限与执行身份

Full 核心 SHA-256：`6c13e9efed3f3c13206bf225c8aaed5413e438e27786af92f8adff98d63e7338`。
Ablation 核心 SHA-256：`27facf988076312ebf374552a2409fac1bfd2ce91fda3ba811916b8e2c032b02`。
消融使用只读契约反馈加入前的核心，保留相同预算反馈、持久化和独立验收。
本轮核心源码在重复实验期间冻结。

mini 固定 2.4.6，commit `04d809ceab9df28f9adaed044884180159172930`。
数据 revision `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d`；
evaluator commit `4b96a678b136f87c8760fa475697f3c98d5f9e5e`。
各组固定 12 请求、24 工具、每响应最多 8 工具、8192 输出 token、90 秒请求超时及 256 KiB 输入边界。
各次 HTTP 正文、响应模型标识及实际采样设置在原始证据中保存。

Full 先运行，mini 使用经哈希核验的同一首次领域输入，保留各自原生系统提示与工具协议。
mini 时间额度扣除 Full 基线耗时及 10 秒清理预留；消融组自行执行干净基线。
修复容器均非 root、断网、限制 CPU/内存和可写文件。
mini 在首请求前以实际容器用户读取全部授权源码；八条正式 mini 尝试均通过该检查。
两套框架的 worker 计时范围不同：Full 含基线、自检和独立验收，mini 为原生 Agent 与工作区自检。
公共 Oracle 耗时另列在 JSON；当前结果支持按阶段核查开销。

原端点为 `http://127.0.0.1:8317/v1`。用户提供新地址后，仅最后两条
`2723-mini-3`、`2723-ablation-3` 使用 `https://cpa.liyinlong.me/v1`，经环境代理连接。
模型标识和请求参数相同，供应商后端实例身份未提供。
完整矩阵和同端点子集同时呈现；端点迁移的源码快照与记录保存在证据包中。

## 中断、环境事件与验收

`2723-rp-3` 的控制器收到 SIGTERM：12 次模型响应均已保存，最后一次只读自检仍在进行。
原数据库保持原样，最后已提交 Checkpoint 包含全部完成的源码编辑。
该候选独立复制、核对哈希后通过公共 Oracle；模型和工具重放次数均为零。
内部独立验收结论及完整 worker 耗时保持未知。

正式矩阵之前另有一个暂停中断尝试（8 请求，其中 1 次用量未知），以及一个源码权限事件批次
（4 条尝试、33 请求）。权限事件中 mini 的源码根目录为 0700，容器用户读取失败；
该批标记 `comparison_valid=false`，完整保存为矩阵外记录。
显式目录与文件权限及真实读取预检完成后，正式对照使用新的独立目录。

Full 已完成的七次内部独立验收接受六条候选、拒绝一条 FMT-4286 错误候选，公共 Oracle 与之相符。
Catch2 的一条中断候选仅有公共 Oracle 评分。错误接受数为零；各分母及未知观察详见 JSON。

## FMT 失败定位

4310：双方生成相同的上下文参数访问修复，原生 21 项测试全部通过。
4286：Full 在第 9、10 轮修改模板类型及依赖基类调用，第 11 轮自检完成编译，
暴露宽字符运行错误；第 12 轮继续读源码后预算耗尽。mini 的候选保留编译错误。
两组候选均在公共 Oracle 中失败。后续工作集中于尽早形成可验证候选，
为编译修复后新暴露的运行错误保留足够编辑轮次。

## 用量与复核

本轮所有批次共 **268 次模型请求**，其中正式矩阵 **227 次**，
矩阵外权限批次 33 次、早期中断 8 次；未知用量 **1 次**。
CPA 费用和每成功任务成本保持未知；DeepSeek 历史费用上界为 **¥2.18923088 / ¥20**。
此前 Luna 任务及接入 41 请求、探针 1 请求单列，累计 Luna 请求为 **310 次**。

原始证据：[ReproPatch-contract-comparison-2026-10-22.tar.gz](https://github.com/lilong555/ReproPatch/releases/download/benchmark-contract-comparison-2026-10-22/ReproPatch-contract-comparison-2026-10-22.tar.gz)，SHA-256：
`b1cdc8be90b93d1df9274de7989885a25a5422ba363f834e0dfddb9cefe94995`。
实际 FMT 工具链镜像：[ReproPatch-cpp-toolchain-beb37ec7c757.tar.gz](https://github.com/lilong555/ReproPatch/releases/download/benchmark-contract-comparison-2026-10-22/ReproPatch-cpp-toolchain-beb37ec7c757.tar.gz)，
SHA-256：`6f79c0b3f74771741baff791f1efca74386dac9149540a7e253e1a9fe2629080`。
镜像平台为 linux/amd64，配置身份和镜像 ID 已核对。

下载同名 `.sha256` 后执行 `sha256sum -c`；镜像可通过 `docker load -i` 导入。
证据解压目录为 `contract-comparison/`，逐文件哈希位于 `evidence-manifest.json`。
在解压目录执行 `python3 summarize-contract.py` 可从请求账本、源码快照、候选和 Oracle 重算结果。
归档已完成凭据哨兵与格式扫描、独立解压逐文件核验及结果重算。
定向检查为 15 项通过，Ruff 检查与格式通过；完整 CI 状态见[准备状态](readiness.json)。
