# 2026-10-24 原生资格与本地性能记录

[GitHub Actions 运行与 Docker 资格](ACTIONS_RESULTS.md)记录云端结果。

日期：2026-10-24 UTC。审查基线为最新 `main`
[`fbdb60570602c61545d4c5b73e2fed92fbe319f6`](https://github.com/lilong555/ReproPatch/commit/fbdb60570602c61545d4c5b73e2fed92fbe319f6)。
本轮代码在独立本地分支 `feat/actions-benchmark-scale`；新模型请求 **0**，新模型 Token **0**。
历史正式实验与本轮准备、开发和性能实验分别报告。

## 交付状态与实际边界

已实现独立无模型 Actions Workflow、fmt 批量资格检查、统一候选 Oracle、Run 内 ccache、
候选导出、资源采样及可核验压缩归档。真实 fmt 任务已完成冷/热构建实验。
CLI 和本地原生验证已运行；Docker、GitHub-hosted Runner 与付费模型实验未在本轮运行。

连接的 GitHub 插件成功读取最新代码、提交、CI 和 Release；创建独立远端分支返回
**HTTP 403 — Resource not accessible by integration**。因此没有新增远端分支、PR 或 Actions Run。
本机也没有可用 Docker daemon，原生预检成功只标记 `HOST_QUALIFIED`。
该权限阻碍没有被当作代码或模型失败，未改写历史发布清单。

实现入口和可复现命令见 [执行说明](ACTIONS_BENCHMARK.md)。
机器可读证据摘要在 [`benchmarks/actions-scale/`](../benchmarks/actions-scale/)。

## 一、重新核验的仓库基线

| 项目 | 最新代码与证据支持的事实 |
| --- | --- |
| 正式版本 | v0.3.0，2026-10-24 发布 |
| 最新 main CI | [40099198765](https://github.com/lilong555/ReproPatch/actions/runs/40099198765)，success；这是已有 main CI |
| Multi-SWE-bench C++ 候选池 | 129：fmt 41、nlohmann/json 55、simdjson 20、Catch2 12、cpp-httplib 1 |
| 历史隔离动态资格 | 10/129；四个仓库，每题已有模型尝试；本轮语义审查为 8 个明确 bug + 2 个不确定项 |
| 最新三框架冻结对照 | 两题、六次运行；两题已有 v1 暴露记录 |
| 无仓库模型尝试记录的池内候选 | 119；这不代表已合格，也不代表供应商预训练无暴露 |
| 已冻结且完成正式首跑的全新 Holdout | 0 |
| 另一个真实上游 smoke 集 | 5/5 参考修复 ACCEPTED，有自写回归测试；官方原生 Oracle 0 次，模型请求 0 |

10 个已资格验证并有模型尝试的实例为 Catch2-2187/2723、fmt-4310/4286/4057/4055、
json-4537/4525、simdjson-2178/1899。详见完整
[`task-status.json`](../benchmarks/task-status.json)，包括逐题暴露来源。
其中 Catch2-2187、fmt-4055 的缺陷/功能混合属性仍需审查；这个保守分类不改写历史测试结果。

辅助 smoke 集为 fmt-compiled-ranges、fmt-hexfloat-padding、pugixml-empty-encoding、
pugixml-copy-unset、tinyxml2-delete-null。它们使用真实上游 base/fix，但每题是 1 F2P + 2 个
仓库自写 P2P，不能与 10 道原生 Oracle 任务合并为同一质量口径。
按实际任务准备能力计，仓库已适配六个 C++ 项目：Catch2、fmt、json、simdjson、pugixml、tinyxml2；
cpp-httplib 只有候选记录。

本轮下载重核了正式 v2 原始附件：50,459,248 字节，SHA-256
`91788186c7c0aa6cd036e292c5f401e0791d0c0ffc8f0c50f19c3134e49d803f`。
历史资格附件 SHA-256 为 `f94e47d32974a501e01c8059f8299ed535203e6d679e3ac6d9f232220df9adb9`；
辅助 smoke 附件为 `0085d5c24f00f7329eb4310480b830edd5bf19f9accd3ffb26b71a32a12e6498`。
原始地址和逐报告哈希保存在索引与 `baseline-audit.json`。

### 原有可复用能力

已有 SourceManifest、补丁往返校验、受控 Docker 生命周期、阶段 deadline、有界诊断、
SQLite 事件/用量账本、候选来源回退、三框架单次适配器、外部 Oracle 和 Release 证据归档。
本轮复用这些边界，没有引入新的模型循环或调度服务。

原有 `evaluate_checks()` 每次 configure/build/CTest，新容器中的 `/build` 为独立 tmpfs；
已有候选导出仍在内部最终验收之后，没有真正的 candidate-only 模式。
基线没有编译器缓存、持久增量 build 或 Actions Benchmark 分片工作流。
已有预算代理适用于原先单槽实验；不能直接宣称可跨多个独立 Runner 控制总金额。

## 二、真实性能瓶颈

从已核验 Release 原始 report 与 v2 逐运行摘要提取：

| 阶段 | fmt-4055 Full | simdjson-1899 Full |
| --- | ---: | ---: |
| 基线完整准备/验证 | 86.99 s | 195.18 s |
| Repair 阶段，含中途自检 | 91.24 s | 439.09 s |
| 其中中途自检 | 34.65 s | 359.51 s |
| 内部独立验收 | 58.95 s | 192.20 s |
| Worker 外层总时长 | 240.37 s | 845.46 s |
| 外部 Oracle | 58.23 s | 157.02 s |
| Worker + 外部 Oracle | 298.59 s | 1002.48 s |

自检已包含在 Repair 中，不能重复相加。历史 report 内部 Harness 时钟与外层 Worker 有
少量封装开销差异；这里总时长统一采用外层记录。

瓶颈顺序为：重复 C++ 编译；完整内部验收与外部 Oracle 重复；基线与项目测试环境准备；
多次源码/工具输出造成的上下文成本。不能根据总 Repair 时长直接推断模型等待时间。
当前核心仍逐条保存 command 时间；新资源 wrapper 补上初始化、镜像和批次级采样。

随规模近似线性增长的是任务×框架×尝试×冷编译次数、Runner 分钟、模型 Token 和原始轨迹。
保留每题完整源码/build 会让磁盘随在途任务及保留任务累积；源码对象池和完成后清理可将
构建峰值约束到并发槽数。内存压力引起的换页、磁盘 I/O 竞争、缓存抖动和重试会造成超线性成本。
模型每轮重复带入增长上下文也可能使单 Run 输入 Token 随轮数呈二次增长趋势；实际用量由账本衡量。

## 三、实施的效率改动与真实 A/B

### Run 内 ccache 与冷最终验收

核心新增 `--compiler-cache`：仅 agent_check 挂载 Run 专属缓存，容器和 `/build` 继续独立。
最终 Oracle 禁用缓存。缓存目录、Namespace 和清理使用现有资源所有权契约。
缓存统计放在 CTest 结束后，因为一些 F2P 是 CTest 节点内的编译回归；统计失败不改变测试结论。

### candidate-only

`--candidate-only` 冻结候选并核验干净 Worktree 重放，标记内部独立验收已跳过，
返回 `EXTERNAL_ORACLE_REQUIRED`。独立 `verify-patch` 路径保持完整。
自有 C++ fixture 的正确候选通过外部冷 Oracle，错误候选被外部拒绝；这是零模型路径验证。
单次 fixture 中，含内部验收的 worker 为 6.39 s，候选导出 worker 为 5.23 s，
后者另有 9.52 s 外部 Oracle，合计 14.74 s。前者没有附同条件外部 Oracle，
两者不能比较端到端提速。内部验收命令消耗 2.375 s；这些记录用于验证执行路径和裁决正确性。

历史 simdjson 的 192.20 s 内部验收是可去除的成本位置，约占原 Worker+Oracle 的 19.2%；
这是基于历史阶段计时的机会估算，尚未跑出优化后的完整 simdjson Agent 对照。

### 真实 fmt-4055 构建实验

早期试验保存在 `performance-pilot.json/csv`，其中两份命令日志的现存 SHA 与原记录不符。
这些原始字节和差异审计均保留，状态为 `PILOT_EVIDENCE_INCOMPLETE`，不作为最终主要 A/B。
本轮随后使用冻结代码、独立本地临时目录与固定四 CPU 重新执行完整对照。

固定 upstream `1408f1824d6a23643e178ee6e46478fb550a0963`、官方测试补丁、参考补丁与
`format-test` 目标；GCC 13.3.0、CMake 4.4.4、Ninja `1.13.2.git.kitware.jobserver-pipe-1`、
ccache 4.9.1、Release/O3/`-DNDEBUG`，每次 `-j2`。进程固定 affinity 为四 CPU（0–3），
从 `/tmp` 中的冻结代码与 Python 包执行，未使用可变的 editable 包。
冷表示全新 build 且编译缓存禁用，宿主文件页缓存没有清空。

| 变体 | N | 中位数 | 范围 | 结果 |
| --- | ---: | ---: | ---: | --- |
| 冷 Make：configure + build + test | 3 | 46.791 s | 46.648–59.999 s | 全通过 |
| 冷 Ninja：configure + build + test | 3 | 38.358 s | 38.138–59.134 s | 全通过 |
| ccache 首次填充 | 1 | 60.782 s | 单次 | 通过；不据此估计稳定冷开销 |
| 热 ccache + 全新 build | 3 | **2.449 s** | 1.488–2.647 s | 全通过 |
| 保留 build、无改动增量 | 3 | **0.506 s** | 0.418–0.679 s | 全通过 |
| 撤销真实参考修复 | 1 | 10.068 s | 单次负控制 | 正确重新出现编译失败 |
| 重新应用参考修复 | 1 | 0.585 s | 单次正控制 | 通过 |
| 最后独立冷目标构建 | 1 | 38.458 s | 单次冷控制 | 通过 |

Make→Ninja 的中位数减少 **18.02%**；冷 Ninja→热 ccache 减少 **93.61%**；
冷 Ninja→无改动增量减少 **98.68%**。各变体使用相同的当前监测代码，计时包含监测开销。
第三对冷样本明显更慢，仍全部保留。N=3 只给描述性统计，不据此声称显著性或普遍收益。

这些是同一目标的编译/测试数据，不能推广成整个 Agent、完整项目或 30 题批次提速。
首次填充不会带来热命中收益；核心 ccache 只供 Run 内重复自检复用，不承诺首个检查更快。
完整 build 目录复用只存在于实验脚本；核心采用范围更小的 ccache，最终验收仍冷构建。
另有小型 fixture 验证头文件与 `-DSCALE` 改动导致重新编译，热/冷正确对象 SHA 相同。

证据核验：**43/43 命令日志 SHA、44 份 telemetry 的 824 条样本计数、30 份执行源码快照**
全部通过。主表为 `performance-verified.json/csv/md`；旧 pilot 没有混入任何计算。
新 profile 脚本 SHA 为 `595fcbc57b680801751677655e20dca4199a6fa2117e2e627fb533e75b3d77ff`。
已核验的原始 A/B 包为 281,506 B，SHA-256：
`dbca287923af04976519484753a88ce43fe98c2b8708b57030c8c38cc3cc18ed`。


## 四、批量资格与数据集质量

本轮固定 revision `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d`，对全部 41 个 fmt 候选执行
静态预筛选和动态资格。详细终态与阶段计时由本轮 `qualification-summary.json/csv/md` 给出。

| 本轮口径 | 结果 |
| --- | ---: |
| 唯一 fmt 候选实际动态尝试 | 41 |
| 最终选用的完整证据原生通过 | **41 HOST_QUALIFIED** |
| 其中明确 bug_fix | **24** |
| 其中明确缺陷且无仓库历史模型尝试记录 | **21** |
| 功能增强 / 混合不确定项 | 13 / 4，分别标记 |
| 新 Docker 隔离资格 / 新正式模型任务 | **0 / 0** |
| 新冻结 Final Holdout | **0** |

41 个选定记录来自原续批的 37 条完整证据，加四条明确补验。完整尝试账目有 88 个注册项：
45 次完成原生资格（包含四次证据重验）、39 个调度取消项、2 个前置 Git 初始化修正取消项，
以及 2 个 O3 基线环境失败项。39 个调度取消项中有未开始任务，不能说成 39 次完成编译。
所有旧结果与取消记录均保留；未因失败重试而覆盖正式样本，模型调用始终为零。

原始 41 题清单在执行前已保存。当前汇总文件是事后证据审定视图，明确标为
`POST_EXECUTION_AGGREGATION_PLAN`，不把事后筛选描述成新的预注册实验。
选定任务 wall time 合计 **7473.16 s**，P50 **200.26 s**，P90 **228.12 s**，P95 **240.81 s**；
来自不同准备批次和源码快照，不能当成一个完全同负载的延迟分布。
41 题选定命令计时中，build 合计 **6918.51 s**、configure **155.14 s**、
CTest **340.68 s**、inventory **34.15 s**；部分编译型 F2P 的编译时间位于 CTest 内。
逐任务冻结的 CTest 节点合计 43 个 F2P、723 个 P2P，同名节点在不同任务间重复，
不把这个合计当成 766 个独立缺陷或独立测试场景。

严格证据门槛发现并保留了两份旧日志哈希不一致、两次早期执行缺源码快照的问题。
其中一份冗余命令清单还能按原 SHA 精确恢复，恢复文件另存，没有覆盖原件。
最终四题重新执行后均通过并完成严格清单核验。空清单、缺少必需阶段证据、源码快照缺失，
以及远端归档失败均不能计入完整合格；原因不明的文件变化仍记为 `UNKNOWN`。

新明确缺陷涉及模板/API 兼容、字符类型、整数与数值格式、边界条件、容器与迭代器等，
但集中于 fmt 单项目。本轮没有用人为配额改变原有任务分布；跨项目与内存生命周期覆盖仍不足。
逐题修复类型、Issue、参考补丁路径和判定理由均在语义审计 JSON 中。

历史与本轮相交的 fmt 任务有四个，因此跨环境具有动态记录的是 47 个唯一上游任务，
其中 29 个归为明确缺陷（历史 8 个 + 新增 21 个）。这是跨批次证据覆盖口径，
**不能改称 47 个 Docker 合格任务或 29 个同条件正式 Benchmark 样本**。


资格流程要求：基线准确的原生测试 inventory、真实失败且至少一个 P2P、参考补丁 F2P 通过、
无适配器的独立冷全套 Oracle 全部通过。缺失可执行文件、环境错误或未执行测试不能充当 F2P。
对编译型回归，仅将官方测试补丁所触及 target 的编译放入对应 CTest 节点，保留测试名称与程序。
参考适配器只运行 F2P，最终独立原生阶段仍执行全套，避免重复完整参考构建。

41 条来源是实际上游 PR，但包含功能增强、兼容扩展及重叠 Issue，不能全部称为独立缺陷。
[`fmt-scope-audit.json`](../benchmarks/actions-scale/fmt-scope-audit.json)保守区分明确 bug 修复、
纯功能增强与不确定项。正式缺陷计数采用语义合格与动态合格的交集，并去除同源重复。
例如 3912/3913 是同一 Issue、同一 base 的两个功能实现，不是两个独立缺陷。

本轮还逐题审查了剩余 88 条记录，结果见
[`remaining-candidate-audit.json`](../benchmarks/actions-scale/remaining-candidate-audit.json)。
整个 129 池的保守语义分类为：

| 项目 | 上游任务记录 | 明确缺陷候选 | 功能增强 | 混合或不清楚 |
| --- | ---: | ---: | ---: | ---: |
| fmt | 41 | 24 | 13 | 4 |
| nlohmann/json | 55 | 31 | 12 | 12 |
| simdjson | 20 | 3 | 15 | 2 |
| Catch2 | 12 | 5 | 4 | 3 |
| cpp-httplib | 1 | 1 | 0 | 0 |
| **合计** | **129** | **64** | **44** | **21** |

64 是语义缺陷候选上限，不是动态通过数；这个池不能直接承诺产出 100 个独立真实缺陷。
json 9 条、simdjson 6 条的原始与修复阶段 passed-name 集合不同，可能来自新增测试或结果变化，
需要重新发现原生 inventory，不能直接复用旧测试数量。部分 Catch2 测试补丁触及生产路径，
需要逐项范围复查；这不是已经证实答案泄漏的结论。现有 2187 适配已将官方测试修改的源码保护，
旧资格和正式成绩保持原样，后续正式缺陷榜采用一致的新口径。

本轮 O0 批次明确记录 `-O0 -DNDEBUG`。早期 O3 预检发生可执行文件权限环境故障，
记录被保留，未纳入合格；后续构建移至可执行的 `/tmp` scratch。
将双 worker 切换为四 worker 时保留取消记录，在新目录显式继续剩余实例。
这属于准备重试，未产生模型调用，不能隐藏为一批没有失败的运行。

Development：已有模型尝试的 10 题及性能调试题。Validation：后续从未模型尝试的成功任务中
冻结少量端到端验证题，策略调整后继续标记为开发暴露。Final Holdout：本轮未宣告冻结，
需要先完成 Docker 镜像重验、去重、类型审查和配置冻结。Synthetic：保持独立，
本轮没有生成 100 题来替代真实样本。

### 50–100 题的实际路径

| 候选来源 | 规模 | 下一步与投入判断 |
| --- | ---: | --- |
| 当前 fmt | 41 条 PR | 复用本轮结果，优先将新增明确缺陷 Docker 重验；功能增强单独标记 |
| nlohmann/json | 55 | 复用离线 test-data、CMake fixture 及双入口审计；先选现有适配版本附近的 10–20 题 |
| simdjson | 20 | 仅 3 条归为明确缺陷，其中 2 条已有历史资格；先做新增 1896，其他功能项单列，保留生成单头文件合同 |
| Catch2 | 12 | 复用现有适配，逐版本检查 approval snapshots、原生 runner 与工具链 |
| cpp-httplib | 1 | 目前无适配，先审网络/服务测试的离线可复现性；优先级低于前三者 |

历史静态筛选中大量 `NO_RECORDED_TEST_PHASE_FAIL_TO_PASS` 可能属于编译型回归或数据缺字段，
不等于无法修复；本轮动态筛选正用于补足这一缺口。
50–100 是跨项目累计目标；成功数必须由资格结果决定，不能按 129 候选数量预先承诺。

优先新增 20 条的具体队列为 json-3514/3463/3543/3037/3008/2963/2866/2332，
simdjson-1896，json-3073/2019/3109/3332/1301/969/1821/4512/3664/3663，以及 Catch2-2128。
这些是没有仓库模型尝试记录的明确缺陷候选，尚未动态资格验证；优先级基于补丁范围与适配接近度，
不是新编译时间的实测排序。JSON 优先参数化已有两题 CASES、保留离线数据与双入口合同，
再加入按实际 CTest inventory 判定编译型 F2P 的能力。

新来源的逐实例交集审计见 [`cpp-expansion-sources.json`](../benchmarks/cpp-expansion-sources.json)。
[SWE-bench Multilingual](https://www.swebench.com/multilingual.html) 的 12 条 C++ 中，
8 条与现有池重叠，只有 fmt-1683/2457/3901、json-4237 四个新增 ID。
[SWE-bench-Live/MultiLang](https://huggingface.co/datasets/SWE-bench-Live/MultiLang)
在固定 revision `3638632e8153a10ca422c1022bed79023084b5c9` 的 C++ split 有 142 条、43 仓库，
按 instance ID 与现有 129 无重叠；136 条含非空 F2P/P2P。后者仍需要任务语义、Issue 交集、
脚本及动态资格复查，不能把 ID 不同等同于无语义重叠。
优先审 fmt-4490、Ninja-2749、两条 jsoncpp 和 11 条 OpenCC；大型 duckdb/slang 暂缓。
来源自带镜像是 tag，使用前须解析固定 digest；不能直接执行数据集里的未审脚本。

备用来源还包括 [BUGSCPP](https://ku-selene.github.io/publications/an2023bugscpp) 和
[Defects4C](https://github.com/defects4c/defects4c)。任务单位、环境和 Oracle 不同，
Defects4C 的函数修复不能直接并入仓库级主榜。当前最短路径仍是扩展已有四项目适配，
再按上述少量轻量新项目扩大覆盖。

## 五、时间、空间与云端未测项

新完整 A/B 外层 wall 为 **407.88 s**，内部 **407.37 s**；外层采样观察代码为 **2.88 s**，
约占外层 wall 的 **0.71%**。这个比例与旧资格批次的目录范围、负载不同，
不能据此声称降低采样频率单独带来了多少提速。
本机为 8 CPU quota、8 GiB cgroup 限额，profile 固定四 CPU affinity；不是 GitHub Runner。
新 profile 的进程树 RSS 采样峰值 **900,579,328 B**，共享 cgroup 峰值 **3,258,441,728 B**。
最初 pilot 的进程组 RSS 受 namespace 与独立进程组影响低估，后来采样器补上
`NSpid` 映射及 PPid 进程树；原始数据没有回填。RSS 求和可能重复计算共享页，峰值是采样下界。

另实跑了工作流的零模型输入准备：新对象池获取两条固定 commit 和数据集为 **1.704 s**，
已有输入复用为 **0.107 s**，最终输入目录 **1,781,760 B**（各一次，本地网络）。
因此 Actions 远端输入缓存改为显式开关、默认关闭，待测恢复/上传后再决定默认策略。
同 Job 的基础仓库复用继续启用。上述时间不是 C++ 基线资格时间。

对早期 pilot 证据试打包（包含已标记的两份不完整日志）：62 个文件、87,021 B 原始日志/脚本压缩为 **16,152 B**，
排除可重建源码/build/cache 后，打包及重读 SHA 核验为 **0.153 s**。
这个小包没有上传到 Actions，不能用其本地压缩耗时代替远端传输测量。

| 内容 | 本轮本地测量 | 解释 |
| --- | ---: | --- |
| ReproPatch Git 元数据 | 1,622,016 B | 性能实验采样 |
| 共享 fmt Git 输入对象池 | 20,283,392 B | 39 题续批采样，全批复用，无逐题 clone 下载 |
| 新性能实验目录采样峰值 | 19,312,640 B | 含源码、build、cache、日志；30 秒目录采样，下界 |
| 最后目标 build | 8,122,368 B | 不是完整工程 build 峰值 |
| 新 A/B 最后 ccache | 1,548,288 B | 同一 Run 的目标缓存，不是全项目缓存容量 |
| Docker 镜像/BuildKit/容器写层 | NOT MEASURED | 无 Docker daemon |
| Python 独立虚拟环境 | NOT MEASURED | 使用共享运行时，不能归因全局 site-packages |
| 新模型 Trace/Token | 0 | 未调用模型 |
| Actions 缓存恢复/上传与 Artifact | NOT MEASURED | 当前 GitHub 写权限阻止云端执行 |

本轮 39 题续批外层 wall 为 **1761.46 s**，内部批次时钟为 **1760.86 s**；
所有原始 resource sample 数量与 telemetry 声明一致（1690 条）。该阶段的峰值来自共享宿主，
不是容器独占指标：cgroup 内存 **5.51 GiB / 8 GiB**，整个文件系统已用峰值 **2.27 GiB**；
`/tmp` 分配空间采样峰值 **803.87 MiB**，资格目录 **362.36 MiB**，Git 对象池 **19.34 MiB**。
目录采样每 10 秒一次，这些值为采样下界，`/tmp` 包含其他本地文件，不能直接标为 build 峰值。

另对同一任务保存的完成阶段目录量做了可核对的清理前后观测：

| 任务 | 旧逻辑：三个完成构建树保留到末尾 | 新逻辑：最大单阶段完成树 | 降幅 |
| --- | ---: | ---: | ---: |
| fmt-3824 | 209,613,441 B | 98,748,916 B | 52.89% |
| fmt-3912 | 206,274,741 B | 99,318,242 B | 51.85% |

指标为文件逻辑字节，不是已分配字节、Docker 峰值或全系统瞬时峰值。旧结果文件的哈希完整，
旧任务的两份日志仍保留“不完整”标记；补测使用相同 base、参考补丁、O0 配置与工具链。
这证明减少存活构建树能降低已完成构建产物保留量，未做独立控制的系统磁盘峰值 A/B。
详见 `build-retention.json` 与 `qualification-resources.json`。


| 用户关注的端到端指标 | 优化前 | 优化后 | 当前可作出的结论 |
| --- | ---: | ---: | --- |
| 基线完整准备 | 有历史两题阶段计时 | NOT MEASURED 同条件 A/B | 新批次有逐阶段数据，不能跨机器/配置直接作比 |
| 重复 F2P 目标构建 | 冷 Ninja 38.358 s | 热 ccache 2.449 s | 本地真实 fmt 目标减少 93.61%；相同源码重复构建 |
| 完整独立最终验收 | 历史 simdjson 192.20 s | NOT MEASURED | candidate-only 已实现，待项目级端到端 A/B |
| 单任务 Agent 总时间 | 历史 simdjson 1002.48 s 含外部 Oracle | NOT MEASURED | 没有用局部构建加速冒充整任务加速 |
| 30 任务整批 Agent 时间 | NOT MEASURED | NOT MEASURED | 冻结任务后记录 batch wall 与所有 Job 分钟 |
| Docker/build 磁盘峰值改善 | NOT MEASURED 同条件对照 | NOT MEASURED | 现有 native 峰值与缓存体积独立报告 |
| Actions 1/2/4 Job 吞吐对照 | NOT MEASURED | NOT MEASURED | 下表为固定四 CPU 的本地 worker 对照，不能替代多 Runner 测量 |
| Runner 分钟 | NOT MEASURED | NOT MEASURED | 本地 task wall 时间之和不转换为 GitHub Runner 分钟 |

### 固定四 CPU 的本地并发对照

每组执行相同的四次 fmt-4055 `format-test` 独立冷构建，固定 affinity 为 CPU 0–3、
Ninja、O3、每 worker `-j2`，禁用 ccache。三组顺序为 1→2→4，每种配置只有一组。
先核验完整的 20 项测试 inventory，但每次仅编译并执行 `format-test`；
这 12 次构建没有增加独立任务、完整资格记录或模型样本。

| Workers | 同样四次构建的 group wall | 吞吐 builds/min | 单任务 active P50 | 进程树 RSS 采样峰值 | 通过 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 200.959 s | 1.194 | 49.319 s | 0.82 GiB | 4/4 |
| 2 | 153.085 s | 1.568 | 76.540 s | 1.41 GiB | 4/4 |
| 4 | 101.235 s | 2.371 | 96.794 s | 2.46 GiB | 4/4 |

四 worker 的吞吐为单 worker 的 **1.985 倍**，组 wall 减少 **49.62%**，但单任务 active
P50 增加到 **1.963 倍**。active 不包含排队等待，JSON 另存 queue+active。
四 worker 各启动两个编译线程，已超过四 CPU affinity 的并行容量；这个设置提高了本次
整组吞吐，但不能据此认定所有 C++ 项目都应使用四 worker。

各组共享 cgroup 峰值为 3.03/3.59/4.59 GiB，包含同机其他进程；临时 build 目录的
30 秒采样峰值为 6.48/9.63/15.97 MiB，短暂峰值可能遗漏。三个临时构建目录均已清理。
采样器观察用时分别占外层 wall 的 2.39%/4.34%/5.91%；这是包含在 wall 内的观察代码
elapsed 时间，不等于可直接相加的 CPU 开销。三组顺序固定、宿主页缓存保留、共享宿主
负载变化且每种配置仅一组，不给出推断性置信区间。

31 份冻结源码、48 份命令日志 SHA 和三份 telemetry 的 441 条样本计数全部核验。
见 `concurrency-verified.json/csv/md`。原始包 332,066 B，SHA-256：
`c58bc60d4e4d22a92c3d9d70bf6b1d7858d481fff927390949d5f67ac5c7b441`。
下一步仍需在相同任务、镜像、配置下实测 GitHub Actions 1/2/4 Job 的 wall、Runner 分钟、
磁盘峰值与失败率；工作流默认采用两个 Job、每 Job 同时一题，等待云端数据后再调整。

## 六、正式模型成绩与公平性

本轮正式新实验数为 0。历史 v2 保持原值：

| 框架 | Oracle 通过 | 请求 | 输入 Token | 输出 Token | 空候选 |
| --- | ---: | ---: | ---: | ---: | ---: |
| ReproPatch Full | 1/2 | 23 | 399,532 | 1,944 | 0/2 |
| mini-SWE-agent | 0/2 | 14 | 176,690 | 2,712 | 1/2 |
| Codex CLI | 0/2 | 24 | 583,746 | 3,218 | 1/2 |
| 合计 | 1/6 | 61 | 1,159,968 | 7,874 | 2/6 |

额外一次参数校准单列；正式用量无 unknown request，金额仍为 `UNKNOWN`。
四份非空候选中三份通过编译，一份编译失败；两个空候选不伪造编译尝试。
simdjson Full 为 93/93，mini/Codex 为 92/93；历史基础设施失败 0/6。
Full 中途自检共 3 次 reproduce、1 次 verify。

两题样本不足以证明框架普遍优劣；Full 的 95% Wilson 区间约 9.5%–90.5%，
两组 0/2 的区间约 0%–65.8%。已有题目暴露也限制了外推能力。
正式新批次需同任务配对四臂、相同实际模型/推理配置、完整首次结果与唯一 Attempt ID；
工具能力和调用语义不同，应同时报告请求数、工具数、Token、墙钟和最终 Oracle。

新候选 Oracle 可接收各框架冻结补丁。新增 `score_benchmark_attempt.py` 已绑定
三类 worker 的 Attempt、Task 原始字节 SHA、prepared commit、image 和 candidate SHA，
优先区分准备/基础设施状态，再调用同一个冷 Oracle。身份篡改、待评分、空候选、
正常编译失败、环境终止和归档失败等路径已做离线契约测试。
真实 Docker 桥接端到端、关闭自检的第四臂、正式多 Job 执行和全局费用控制仍未完成。
`EXTERNAL_ORACLE_REQUIRED` 为待评分；基线/基础设施失败必须先分类，再判断空候选。
不能按 Worker 退出码或 Harness 的 INCONCLUSIVE 直接计分。

## 七、下一步执行清单

### 本轮代码验证

较早实现快照的完整非 Docker 回归为 **501 passed、22 deselected，238.35 s**。
随后修改的路径做了定向门禁：Actions/归档 **18 passed**、评分桥接与证据门槛
**26 passed**、资格证据和 Git deadline/cancel **3 passed**；真实小型 C++ 正/错候选
和缓存失效验证也保留了原始记录。Ruff 检查、79 个 Python 文件格式检查、actionlint 1.7.12
与 `git diff --check` 均通过。

按 JUnit `(classname, name)` 去重，跨执行快照有 **558 个唯一通过用例**，其中新增测试模块
66 个；这不是当前最终树一次 `558 passed` 的完整 suite。中间一次受限环境内的完整复跑
在 SDK MockTransport 检查处被停止，状态单列，未伪装成通过；对应受影响检查在允许的执行
环境中单独通过。新增 Docker 缓存集成用例和真正云端 CI 均未运行。
精确命令、JUnit 哈希和去重口径见 `verification.json` 及原始证据包。

| 优先级 | 目标与修改位置 | 验收标准 | 收益、成本与风险 |
| --- | --- | --- | --- |
| P0 | 为当前 GitHub 连接开放仓库写入；推送分支并创建 PR | PR 免费 smoke 有真实 Run URL、Docker 正/负门禁、下载 SHA 核验 | 解除当前发布与云端测量阻碍；不需要模型费用 |
| P0 | 发布固定 GHCR 工具链；`docker/Dockerfile`、Workflow | 所有 Job 使用同一可拉取 digest；记录平台、编译器及包版本 | 减少重复镜像构建并固化环境；需要 Packages 写权限 |
| P0 | 新成功缺陷 Docker 重验；`qualify_cpp_batch.py` 与任务索引 | 基线 F2P/P2P、参考 F2P、完整 native suite 全通过，去重且身份冻结 | 将 host 证据变成可正式使用任务；实际 Runner 成本待测 |
| P1 | 三框架评分桥接 Docker 门禁与关闭自检臂；worker、`score_benchmark_attempt.py`、统一汇总 | 真 Docker 正/错/空/无效候选与基础设施状态正确，四臂全部 Attempt 有身份和证据 | 离线桥接已完成；补云端端到端与消融协议，复用现有 worker/账本 |
| P1 | 2 题×4 臂有界正式 pilot | 最多 96 正式请求；另冻结校准额度、Token/金额上限与供应商价格依据 | 检查用量、模型档位和归档；当前未获总金额授权，未执行 |
| P1 | json/simdjson/Catch2 扩展；`prepare_json_task.py`、`check_json_candidate.py`、`prepare_simdjson_task.py`、`score_benchmark_attempt.py` | json 先尝试 10–20 条，simdjson 先做剩余明确缺陷 1896，再做 Catch2 队列；评分器按固定 repository 分派既有 Oracle | 提升跨项目覆盖；json 离线数据和单头分发检查是主要适配成本；当前新增批量管线仍只支持 fmt |
| P2 | 同批任务 Actions 1/2/4 Job A/B | 固定任务、镜像和配置；比较 wall、Job 分钟、峰值、失败率 | 选择并发，避免把更多 CPU 当成算法加速 |
| P2 | ccache 跨 Job 缓存与 Release 自动发布 | 五段总耗时收益为正；上传失败不报成功；下载哈希可核验 | 节约重复计算并长期归档；先控制存储与传输成本 |
| P3 | 单独 generated regression >100 | 每题变异算子、seed、真值和正负控制可复核，成绩单列 | 用于快速机制开发；不代替真实缺陷数量 |

本轮没有启用 PCH、Unity Build、远程 sccache 或复杂共享 build：它们会扩大输入语义、
资源竞争或维护范围，当前有更短的实测收益路径。详细逐项取舍见
[Actions 资源与优化依据](ACTIONS_RESOURCES.md)。
