# ReproPatch 运行时实测证据

## 结论

完成95条历史轨迹重算、真实长输出离线投影、真实Docker暂停恢复和三类补丁验证。新增付费模型请求为 **0**。公开生产源码固定为 `9cf01099206131ba6f984661a97f7aa65ee8b68a`，与本地Git commit对象核对；执行使用隔离快照，工作区未提交模块保持原样。

恢复实验累计登记 **6个独立Run**：首批3个观察器错误完整保留；修正观察器后的独立批次 **3/3** 完成恢复与冷验收，恢复入口至下一模型调用准入中位 **0.530秒**，样本范围 **0.468–2.479秒**。这是ScriptedModel与真实Docker的运行时测量。

主要入口：[汇总JSON](summarize/summary.json)、[冻结协议](protocol.json)、[输入指纹](frozen-inputs.json)、[驱动](../../scripts/benchmark_runtime_evidence.py)、[定向测试](../../tests/test_runtime_evidence.py)。全部9个新Run的本地证据经公开 `inspect_run` 核验，完整性 **9/9**，见[检查表](summarize/artifact-inspections.csv)。

## 历史95条

19道已曝光fmt开发/配置复核题，每臂19个最终所选attempt；包含按历史规则承接的复验。累计收费历史118次另存，最终95条与累计118次分别计量。模型 `gpt-6-luna/max`，mini 2.4.6，Codex 0.163.0；历史请求上限24、工具上限48、单请求180秒、传输2MiB，详见 `../context-formal-protocol.json`。

| 臂 | 冷评分通过 | 实际请求 | 输入Token | 输出Token | 工具调用 | 上下文压缩 |
|---|---:|---:|---:|---:|---:|---:|
| Full | 18/19 | 340 | 5,196,230 | 106,696 | 325 | 0 |
| no-checks | 15/19 | 359 | 5,312,280 | 130,471 | 344 | 0 |
| shell-only | 19/19 | 335 | 8,193,067 | 188,681 | 314 | 6 |
| mini | 18/19 | 309 | 6,829,336 | 204,890 | 331 | 2 |
| Codex | 16/19 | 421 | 13,075,211 | 236,181 | 403 | 10 |
| 合计 | 86/95 | 1,764 | 38,606,124 | 866,919 | 1,717 | 18 |

各臂用量、工具数、worker、自检及冷Oracle耗时均有19/19条数值记录；耗时中位数与有效分母见 [history/summary.json](history/summary.json)。95/95归档SHA、95/95 worker结果SHA通过；逐SQLite账本与所选用量 **95/95吻合**。实际请求含1,746次repair、18次compact；compact本身消耗766,187输入及28,085输出Token。未知用量为0/1,764。

原生HTTP目录含1,775份请求正文，其中11份Codex预发送记录未获准发出。首遍文件枚举的84/95闭合状态保留在 `history/`；[账本核对](reconcile/summary.json)依据 `requests/pre_send` 表闭合为95/95，11次本地拒绝单列。

观察到4/95候选构建失败、5/95候选测试失败；停止状态为71/95 `COMPLETED`、24/95 `REQUEST_BUDGET_EXHAUSTED`，分别列示。失败逐条见 [failures.csv](history/failures.csv)，保持Oracle状态与停止原因，根因未作推断。

执行版本分母：`48826203...` 31条、`6cb341c8...` 22条、`58bc5e59...` 35条、`a6df2b18...` 3条、`152c7f04...` 4条。完整SHA、打包版本、attempt、原attempt、归档绝对路径及候选SHA见 [attempts.jsonl](history/attempts.jsonl)。历史成绩归属这五个版本。Full/no-checks及legacy/shell组合同时改变工具集合、提示或执行方式，采用配置组合比较口径。

模型逐请求：[models.csv](history/models.csv)、[实际账本请求](reconcile/requests.jsonl)。上下文事件：[context-events.csv](history/context-events.csv)，18事件/18attempt。工具逐事件：[tools.csv](history/tools.csv)，覆盖Full/no-checks/shell的57条、983次工具调用，各含开始和结束事件；mini/Codex的38条保留原执行器汇总口径。

## 长输出离线投影

先按 [protocol.json](protocol.json) 枚举95条的模型请求：超24KiB的唯一输出仅4份，均为mini的24,620字节已折叠结果。4/6预登记名额取得样本；再次折叠合计98,480→98,304字节，回读与协议检查4/4通过，见 [projection/](projection/summary.json)。

随后冻结 [完整原文协议](raw-output-protocol.json)，从57条ReproPatch轨迹选取最长6份原生工具结果，涉及5个attempt，均来自shell-only。按原 `call_id` 接回完整请求，仅替换该项输出；生产 `fold_tool_output`、`EvidenceRef`、`complete_rounds` 完成投影与检查。

| 计量 | 原文/展开输入 | 投影后 | 样本分母 |
|---|---:|---:|---:|
| 工具输出UTF-8字节 | 174,602 | 147,456 | 6份输出/5个attempt |
| 完整请求规范化JSON字节 | 916,093 | 888,680 | 6个重建请求 |
| 去不透明状态后的可见请求字节 | 642,787 | 615,374 | 6个重建请求 |

工具输出体积减少 **15.55%**；附件原文回读、工具轮次配对、其余请求字段保留均 **6/6**。见 [samples.csv](raw_projection/samples.csv)，各样本目录同时保存历史provider请求、展开输入、投影输入、完整附件与原始成员SHA。历史provider用量对应其当时已折叠请求；新展开/投影provider Token均为空，结论为离线体积测量。

## 暂停恢复

公开demo fixture的base为 `a98a31601ab70499baae3a2a254959d16b72f485`，SDK `openai-agents 0.24.0 / openai 3.35.1`，Python3.12.3。Azure共享主机Ubuntu24.04.5、2 CPU、936,230,912字节内存；Docker29.1.3，镜像 `sha256:c72159ee43e25d6f43b25224e08622ba4f9708809354236f80b64e020d0c0a6d`，由公开Dockerfile新建，CMake3.28.3、G++13.3.0。Task限额2 CPU、2GiB，wall900秒，12步/80工具，完整配置见各Run的 `task.resolved.json`。

| 第二批重复 | Run ID | 恢复入口至模型准入/秒 | 全部一致性检查 |
|---|---|---:|---:|
| 1 | `f63b2b300ec34d1da481d5893adf32b0` | 0.467888506 | 11/11 |
| 2 | `ec91285d26f74e5bb8e1082be000d7d1` | 2.479436889 | 11/11 |
| 3 | `5de8aa29bd394c3b8fa434c56b3ba382` | 0.530166631 | 11/11 |

计时从调用 `resume_run` 前的单调时钟开始，至原 `EventLog.emit(model_started)` 成功返回；观察器仅记录时刻。3/3从第3步的完整已提交输入恢复同Run，累计步骤3→5、工具3→4，deadline原值保留；源码哈希、实际下一输入与checkpoint一致，baseline/edit各一次，最终独立冷验收3/3。

首批观察器调用属性 `state()` 触发TypeError，生产轨迹记录 `MODEL_ERROR`，聚合计时随后记录缺失时间戳异常；3/3首批结果保留在 [runtime/](runtime/summary.json) 和 [首批驱动](runtime-driver-series1.py)。[第二批协议](runtime-observer-protocol.json)登记额外3次，结果见 [runtime2/](runtime2/summary.json)。累计6次中有3次有效计时；第二批中位数采用3个新登记样本，全部原始样本保留。

## 独立补丁验证

使用同一公开fixture、base、镜像及生产 `Harness(patch_file=...)`，每场景一次，均为新验证Run。提交补丁SHA与生产规范化补丁SHA分别保存。

| 场景 | 结果/分母 | F2P | P2P | 输入补丁SHA前缀 |
|---|---|---|---|---|
| 正常修复 | 接受1/1 | 1/1通过 | 3/3通过 | `61f75c2e9f836a62` |
| 正常修复+测试篡改 | `FORBIDDEN_PATCH`拒绝1/1 | 保护路径阶段停止 | 未执行冷测试 | `fb7d76198f05fb40` |
| 修复负数+引入空输入回归 | `REGRESSION_FAILED`拒绝1/1 | 1/1通过 | 2/3通过，empty失败 | `fa90de294609264c` |

正常及回归候选均在独立冷工作区执行，源码身份与候选一致2/2。保护路径拒绝另列。见 [validation.csv](summarize/validation.csv)；输入补丁在 `runtime/*.patch`，完整事件、JUnit、stdout/stderr及候选在 `runs/`。

## 构建复用与复算

复用历史 `fmt-4055/format-test` Docker样本，源码 `6c6222c5b0a93b6ce09f121db257b00e68297d9b`，数据来自 `../actions-scale/cloud-results.json` 的 `target_build_profile.samples`。冷Ninja与热ccache新build各n=3，中位13.267504→0.867762秒，减少93.46%；保留build且源码未改n=3，中位0.291896秒；首次填充n=1为14.302415秒，最终冷验收n=1为14.081920秒。

这是固定源码/目标的历史构建微基准；计时含配置、构建、测试、结果解析和逐命令Docker启动清理，源码准备、目录创建及镜像拉取另计。缓存通过目录跨容器复用；当前持久shell还保留容器生命周期。逐样本与环境随 [汇总JSON](summarize/summary.json) 的 `build_reuse` 保存。

公开复算入口见 [PORTABLE.md](PORTABLE.md)，使用本目录 `public-inputs/audit-index.json` 的相对路径索引及固定源码快照。`audit` 在新的输出目录核对输入哈希、95条SQLite账本、6份长输出和9个Run的完整原始状态，全程离线。

驱动阶段为 `freeze/history/projection/reconcile/raw_projection/runtime/summarize`；每阶段输出新目录，重算可用 `--label 新目录名` 保留旧结果。首轮运行前在新的输出根放置本目录协议并执行 `freeze`；使用 `--source` 指向固定commit快照，`--output` 指向输出根。历史归档索引默认使用可移植包，可通过 `--audit-index`指定。实际命令模板：

```bash
python scripts/benchmark_runtime_evidence.py history --source SNAPSHOT --output OUTPUT
python scripts/benchmark_runtime_evidence.py reconcile --source SNAPSHOT --output OUTPUT
python scripts/benchmark_runtime_evidence.py raw_projection --source SNAPSHOT --output OUTPUT
python scripts/benchmark_runtime_evidence.py runtime --source SNAPSHOT --output OUTPUT --private PRIVATE_RUNS --image IMAGE
```

原始远程路径 `/home/azureuser/runtime-evidence-20261106/{runs,runs2}` 已完整回收至本目录同名路径。生产事件保留原路径，离线核验结果提供本地相对位置。新增定向测试 **8/8通过**，Ruff检查通过；测试数属于工程验证。

