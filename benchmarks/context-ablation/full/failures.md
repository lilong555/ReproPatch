# 上下文五组实验逐题结果与失败明细

## 结论

19 道题、5 个 arm、每题每组 2 次重复，共 190 条 attempt，冷评通过 160 条、失败 30 条。五组通过数依次为 **baseline 34/38、diagnostics 31/38、dedup 33/38、state 32/38、combined 30/38**，与 [summary.md](summary.md) 一致。

失败集中在 6 道题：`fmtlib__fmt-3819` 10 条、`fmtlib__fmt-1361` 8 条、`fmtlib__fmt-2310` 5 条、`fmtlib__fmt-3260` 4 条、`fmtlib__fmt-3750` 2 条、`fmtlib__fmt-3734` 1 条。前两题占全部失败的 60%；其余 13 道题在五组中均为 2/2 通过。

冷评失败包含 8 条 `ORACLE_BUILD_FAILED` 和 22 条 `ORACLE_TESTS_FAILED`，其中 5 条测试失败同时涉及 P2P 回归。所有失败的停止原因均为 `REQUEST_BUDGET_EXHAUSTED`，请求数为 24/24；另有 21 条同样耗尽预算的 attempt 通过冷评。`candidate` 是结果分类，预算耗尽是停止状态；具体失败归因依据冷评日志、断言和候选补丁。

机制覆盖极低：诊断提取与结果去重全程各触发 0 次，状态感知压缩仅在 1 条成功 attempt 中触发 1 次。当前证据支持报告观察到的组间通过数差异，消融收益或损害的因果判断仍需充分的机制触发证据。

## 数据与口径

来源为 [results.json](results.json)、[summary.md](summary.md) 及 [GitHub Run 42219312911](https://github.com/lilong555/ReproPatch/actions/runs/42219312911)，仓库 `lilong555/ReproPatch`，运行源码提交 `2597016d80ea47c8bbc06c93598093c307a24ee7`。完整汇总下载入口为 [context-results-42219312911](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13522082827)。

统计范围为 `scope=full`，任务总体为 `previously_exposed_development_tasks`，即此前已接触的开发任务。每个任务与 arm 组合均有 repeat 1、2 两条记录，以 `accepted=true` 统计通过，190 条记录均与 `score.status=ORACLE_PASSED` 的判定一致。缺失、基础设施失败、未知结果及自动重跑均为 0，`rejected_artifacts=[]`；各组 `context_overflows={}`。

F2P 指待修复的测试目标，P2P 指应保持通过的回归目标。下文比例按汇总中的 CTest 目标计数；原轨迹中更细的测试项另行说明。`not_run` 表示该目标尚未执行。分析采用既有结果与归档日志的 CPU-only 静态核对。

## 19 题逐组通过数

每格为该题该组两次重复中的冷评通过数量。

| 任务 | baseline | diagnostics | dedup | state | combined |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fmtlib__fmt-1361` | 1/2 | 1/2 | 0/2 | 0/2 | 0/2 |
| `fmtlib__fmt-1390` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2070` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2292` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2310` | 1/2 | 1/2 | 1/2 | 1/2 | 1/2 |
| `fmtlib__fmt-2317` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2610` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2940` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3248` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3260` | 2/2 | 0/2 | 2/2 | 1/2 | 1/2 |
| `fmtlib__fmt-3272` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3537` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3713` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3727` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3732` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3734` | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 |
| `fmtlib__fmt-3750` | 2/2 | 1/2 | 2/2 | 2/2 | 1/2 |
| `fmtlib__fmt-3819` | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| `fmtlib__fmt-493` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| **overall** | **34/38** | **31/38** | **33/38** | **32/38** | **30/38** |

## 冷评与停止状态汇总

| arm | 通过 | 构建失败 | 测试失败 | 失败合计 | 预算耗尽合计 | 预算耗尽且通过 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 34 | 2 | 2 | 4 | 9 | 5 |
| diagnostics | 31 | 2 | 5 | 7 | 13 | 6 |
| dedup | 33 | 1 | 4 | 5 | 7 | 2 |
| state | 32 | 1 | 5 | 6 | 13 | 7 |
| combined | 30 | 2 | 6 | 8 | 9 | 1 |
| **合计** | **160** | **8** | **22** | **30** | **51** | **21** |

30 条失败均已执行冷评、保留非空候选补丁，且 `classification=candidate`、`accepted=false`、`worker_exit=0`、`score_exit=1`、`failure=null`、`context_overflow=null`、`local_rejections=0`。`failure=null` 是汇总字段值，冷评失败详情记录在 `score` 中。

## 每条失败 attempt

下表“预算耗尽，24/24”均对应原始 `stop_reason=REQUEST_BUDGET_EXHAUSTED`、`usage.requests=24`、`request_cap=24`。冷评列保留原始状态码。每行的 trial 链接直接指向该 attempt 的原始轨迹 artifact。

仅有汇总证据的条目已逐条注明“具体原因待原轨迹核对”。这些记录提供了失败阶段及测试目标，具体编译错误、断言、执行中间状态和补丁缺陷仍需对应日志支持；原轨迹核对所得细节只归属于列明的 attempt。

### fmtlib__fmt-1361

| attempt / 原始轨迹 | arm | repeat | 冷评判定 | 停止原因 | 已观察到的细节 |
| --- | --- | ---: | --- | --- | --- |
| [trial-156](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13519153098) | baseline | 1 | `ORACLE_BUILD_FAILED` | 预算耗尽，24/24 | F2P `format-impl-test`、`grisu-test` 均为 `not_run`；P2P 15/15 为 `not_run`。具体原因待原轨迹核对。 |
| [trial-166](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13520486459) | diagnostics | 1 | `ORACLE_BUILD_FAILED` | 预算耗尽，24/24 | F2P `format-impl-test`、`grisu-test` 均为 `not_run`；P2P 15/15 为 `not_run`。具体原因待原轨迹核对。 |
| [trial-145](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13518506697) | dedup | 1 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `grisu-test` 失败，`format-impl-test` 通过；P2P 15/15 通过。具体原因待原轨迹核对。 |
| [trial-158](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13519860233) | dedup | 2 | `ORACLE_BUILD_FAILED` | 预算耗尽，24/24 | F2P `format-impl-test`、`grisu-test` 均为 `not_run`；P2P 15/15 为 `not_run`。具体原因待原轨迹核对。 |
| [trial-130](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13516949164) | state | 1 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `format-impl-test` 失败，`grisu-test` 通过；P2P `format-test` 失败，其余 14/15 通过。具体原因待原轨迹核对。 |
| [trial-160](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13520770273) | state | 2 | `ORACLE_BUILD_FAILED` | 预算耗尽，24/24 | F2P `format-impl-test`、`grisu-test` 均为 `not_run`；P2P 15/15 为 `not_run`。具体原因待原轨迹核对。 |
| [trial-042](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13505429810) | combined | 1 | `ORACLE_BUILD_FAILED` | 预算耗尽，24/24 | F2P `format-impl-test`、`grisu-test` 均为 `not_run`；P2P 15/15 为 `not_run`。具体原因待原轨迹核对。 |
| [trial-031](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13505650344) | combined | 2 | `ORACLE_BUILD_FAILED` | 预算耗尽，24/24 | F2P `format-impl-test`、`grisu-test` 均为 `not_run`；P2P 15/15 为 `not_run`。具体原因待原轨迹核对。 |

### fmtlib__fmt-2310

| attempt / 原始轨迹 | arm | repeat | 冷评判定 | 停止原因 | 已观察到的细节 |
| --- | --- | ---: | --- | --- | --- |
| [trial-097](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13512932044) | baseline | 2 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `format-test` 失败；P2P 16/16 通过。原轨迹确认 `format_test.width` 中 `fmt::format("{:>06.0f}", 0.00884311)` 得到 `"     0"`，期望 `"000000"`；该目标内 104 项测试通过 103 项。 |
| [trial-090](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13512286124) | diagnostics | 2 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `format-test` 失败；P2P 16/16 通过。具体原因待原轨迹核对。 |
| [trial-089](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13511846295) | dedup | 1 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `format-test` 失败；P2P 16/16 通过。具体原因待原轨迹核对。 |
| [trial-133](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13516798869) | state | 1 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `format-test` 失败；P2P 16/16 通过。具体原因待原轨迹核对。 |
| [trial-175](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13520412710) | combined | 1 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `format-test` 失败；P2P 16/16 通过。具体原因待原轨迹核对。 |

### fmtlib__fmt-3260

| attempt / 原始轨迹 | arm | repeat | 冷评判定 | 停止原因 | 已观察到的细节 |
| --- | --- | ---: | --- | --- | --- |
| [trial-082](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13510619036) | diagnostics | 1 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `chrono-test` 失败；P2P `xchar-test` 失败，其余 18/19 通过。具体原因待原轨迹核对。 |
| [trial-075](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13509843049) | diagnostics | 2 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `chrono-test` 失败；P2P `compile-test` 失败，其余 18/19 通过。具体原因待原轨迹核对。 |
| [trial-162](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13520055801) | state | 1 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `chrono-test` 失败；P2P `compile-test` 失败，其余 18/19 通过。具体原因待原轨迹核对。 |
| [trial-049](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13507087712) | combined | 1 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `chrono-test` 失败；P2P `compile-test` 失败，其余 18/19 通过。原轨迹中两者均标为 `SEGFAULT`；段错误的具体代码根因仍待进一步核对。 |

### fmtlib__fmt-3734

| attempt / 原始轨迹 | arm | repeat | 冷评判定 | 停止原因 | 已观察到的细节 |
| --- | --- | ---: | --- | --- | --- |
| [trial-147](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13519126229) | combined | 2 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `format-test` 失败；P2P 19/19 通过。具体原因待原轨迹核对。 |

### fmtlib__fmt-3750

| attempt / 原始轨迹 | arm | repeat | 冷评判定 | 停止原因 | 已观察到的细节 |
| --- | --- | ---: | --- | --- | --- |
| [trial-165](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13521270415) | diagnostics | 2 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `format-test` 失败；P2P 19/19 通过。具体原因待原轨迹核对。 |
| [trial-006](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13502983165) | combined | 2 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `format-test` 失败；P2P 19/19 通过。具体原因待原轨迹核对。 |

### fmtlib__fmt-3819

| attempt / 原始轨迹 | arm | repeat | 冷评判定 | 停止原因 | 已观察到的细节 |
| --- | --- | ---: | --- | --- | --- |
| [trial-017](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13503454410) | baseline | 1 | `ORACLE_BUILD_FAILED` | 预算耗尽，24/24 | F2P `args-test`、P2P 19/19 为 `not_run`。原轨迹确认补丁在 `include/fmt/format.h:4272` 调用 `parse_context.advance_arg_id(arg_id)`，编译器报 `basic_format_parse_context<char>` 缺少 `advance_arg_id` 成员。 |
| [trial-011](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13503931973) | baseline | 2 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `args-test` 失败；P2P 19/19 通过。具体原因待原轨迹核对。 |
| [trial-187](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13522346272) | diagnostics | 1 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `args-test` 失败；P2P 19/19 通过。具体原因待原轨迹核对。 |
| [trial-058](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13507234361) | diagnostics | 2 | `ORACLE_BUILD_FAILED` | 预算耗尽，24/24 | F2P `args-test` 均为 `not_run`；P2P 19/19 为 `not_run`。具体原因待原轨迹核对。 |
| [trial-078](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13509129365) | dedup | 1 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `args-test` 失败；P2P 19/19 通过。具体原因待原轨迹核对。 |
| [trial-142](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13518776481) | dedup | 2 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `args-test` 失败；P2P 19/19 通过。具体原因待原轨迹核对。 |
| [trial-066](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13511135167) | state | 1 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `args-test` 失败；P2P 19/19 通过。具体原因待原轨迹核对。 |
| [trial-025](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13505092250) | state | 2 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `args-test` 失败；P2P 19/19 通过。具体原因待原轨迹核对。 |
| [trial-022](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13504602906) | combined | 1 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `args-test` 失败；P2P 19/19 通过。具体原因待原轨迹核对。 |
| [trial-171](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13519858097) | combined | 2 | `ORACLE_TESTS_FAILED` | 预算耗尽，24/24 | F2P `args-test` 失败；P2P 19/19 通过。具体原因待原轨迹核对。 |

## 原始轨迹中的具体证据

以下三条均来自对应 artifact 内的 `context-attempt.tar.gz`。冷评证据位于 `score/oracle/`，候选补丁位于 `score/candidate.patch`；修复阶段的请求、事件和中间命令日志位于 `worker/runs/`。

### trial-017：成员调用导致编译失败

任务 `fmtlib__fmt-3819`，baseline，repeat 1。候选补丁在命名参数处理的 `on_arg_id` 中增加 `parse_context.advance_arg_id(arg_id)`。冷评的 `score/oracle/logs/native-oracle-build.log` 明确记录 `include/fmt/format.h:4272:21` 编译错误：`basic_format_parse_context<char>` 缺少 `advance_arg_id` 成员。`score/oracle/commands.json` 记录 configure 退出码 0、build 退出码 1。该成员调用与编译报错直接对应，F2P 与 P2P 随后均保持 `not_run`。

### trial-049：两个测试目标发生段错误

任务 `fmtlib__fmt-3260`，combined，repeat 1。`score/oracle/logs/native-oracle-ctest.log` 第 83、84 行分别记录 `chrono-test (SEGFAULT)`、`compile-test (SEGFAULT)`。候选补丁修改了 `include/fmt/chrono.h` 中 `formatter<std::tm, Char>` 的对齐、动态宽度解析与格式化路径。现有证据确认两个目标的段错误；具体触发位置与代码根因仍待进一步核对。

### trial-097：零填充与显式对齐组合输出错误

任务 `fmtlib__fmt-2310`，baseline，repeat 2。`score/oracle/logs/native-oracle-ctest.log` 第 100 至 105 行记录 `format_test.width` 的失败断言：

```text
/src/test/format-test.cc:748
fmt::format("{:>06.0f}", 0.00884311)
实际值："     0"
期望值："000000"
```

候选补丁在 `include/fmt/core.h` 的 `specs_setter::on_zero()` 中增加 `specs_.align == align::none` 条件，将设置 numeric 对齐和零填充限制在该分支。此改动与显式右对齐场景保留空格填充的观察一致。`format-test` 内 104 项测试通过 103 项，失败项为 `format_test.width`；全部 16 个 P2P 目标通过。

## 机制触发覆盖

下表采用 `arms.<arm>.mechanisms` 的统计口径，单元格为“触发过的 attempt 数 / 本组全部 attempt 数”。三个机制在每组均有 38 条观测、缺失 0 条；开关启用与实际触发分别记录。

| arm | diagnostic_extraction | deduplicate_results | state_aware_compaction |
| --- | ---: | ---: | ---: |
| baseline | 0/38 | 0/38 | 0/38 |
| diagnostics | 0/38 | 0/38 | 0/38 |
| dedup | 0/38 | 0/38 | 0/38 |
| state | 0/38 | 0/38 | 1/38 |
| combined | 0/38 | 0/38 | 0/38 |

唯一触发记录为 [trial-013 原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13503094921)：任务 `fmtlib__fmt-3727`，state，repeat 1，冷评通过、请求预算耗尽。其 `state_aware_compaction.trigger_count=1`，事件 `sequence=24`、`measurement=retained_state_message`、`input_bytes=0`、`output_bytes=3515`、`saved_bytes=0`。这条记录支持“保留状态消息 3515 字节”的描述，节省字节数记录为 0。该题五组均为 2/2 通过。

30 条失败 attempt 的三个机制触发计数均为 0。当前结果体现此前已接触的开发任务上的一次运行结果；诊断提取、去重与状态压缩的收益判断，需要结合实际触发覆盖及可配对的有效处理差异。各题的任务、指令和工具摘要一致，每题 10 条首请求却有 10 个不同的输入摘要；输入差异的具体内容待原请求核对。

## Artifact 下载索引说明

上文 30 条失败行的链接逐条对应 `context-raw-42219312911-<trial-NNN>`。artifact ID 来自 GitHub API 的实际返回，查询日期为 2026-11-07：

```bash
gh api repos/lilong555/ReproPatch/actions/runs/42219312911/artifacts --paginate
```

该运行共有 382 个 artifact，其中原始轨迹 190 个。本文链接的 30 个失败轨迹、1 个机制触发轨迹及汇总 artifact 在查询时均为 `expired=false`，到期日期均为 2026-12-06。下载包内另附 `context-attempt.tar.gz.sha256` 和 `context-attempt.tar.metadata.json`，可用于定位与核验归档。
