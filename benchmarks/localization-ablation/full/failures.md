# 定位消融实验：逐题结果与失败证据

本轮 19 个历史暴露开发任务、三组各重复两次，共 114 条轨迹，冷评分通过 95 条。A 原生检索通过 32/38，B 文件摘要检索通过 33/38，C 证据排序检索通过 30/38。19 条失败集中在 7 道题，包含 8 条空候选、6 条测试失败和 5 条构建失败。C 相对 B 少通过 3 条；changed-span 定位命中由 17/28 降至 9/28。以下结论对应本轮开发任务及实际记录。

结果来自 [GitHub Run 42242783788](https://github.com/lilong555/ReproPatch/actions/runs/42242783788)。A、B、C 分别对应 `native`、`bounded`、`feedback`；三组共享每条 24 次模型请求、48 次工具调用的总预算，以及定位阶段 4 个模型步、8 次工具调用的上限。全部注册轨迹均有冷评分与完整定位评分，缺失结果为 0。

| 组 | 冷评分通过 | 空候选 | 测试失败 | 构建失败 |
| --- | ---: | ---: | ---: | ---: |
| A `native` | 32/38（84.21%） | 3 | 2 | 1 |
| B `bounded` | 33/38（86.84%） | 1 | 2 | 2 |
| C `feedback` | 30/38（78.95%） | 4 | 2 | 2 |

逐题通过数如下，每个单元格的分母均为 2。“原行改动”任务进入主要 changed-span 定位统计；“纯插入”任务采用独立的插入锚点统计。

| 任务 | 定位标签 | A 通过 | B 通过 | C 通过 |
| --- | --- | ---: | ---: | ---: |
| `fmtlib__fmt-493` | 原行改动 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-1361` | 原行改动 | 1/2 | 1/2 | 1/2 |
| `fmtlib__fmt-1390` | 原行改动 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2070` | 纯插入 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2292` | 原行改动 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2310` | 原行改动 | 0/2 | 0/2 | 0/2 |
| `fmtlib__fmt-2317` | 原行改动 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2610` | 原行改动 | 2/2 | 2/2 | 1/2 |
| `fmtlib__fmt-2940` | 原行改动 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3248` | 原行改动 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3260` | 原行改动 | 2/2 | 1/2 | 1/2 |
| `fmtlib__fmt-3272` | 原行改动 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3537` | 纯插入 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3713` | 纯插入 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3727` | 原行改动 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3732` | 原行改动 | 2/2 | 2/2 | 1/2 |
| `fmtlib__fmt-3734` | 纯插入 | 1/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3750` | 原行改动 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3819` | 纯插入 | 0/2 | 1/2 | 0/2 |

**停止状态与评分原因。** 以下 19 条失败的生成阶段都用满 24/24 次模型请求，`agent_stopped.reason` 均为 `REQUEST_BUDGET_EXHAUSTED`，实际工具调用均为 24/48。空候选的原生状态为 `BUDGET_EXHAUSTED`；已有候选的 11 条原生状态为 `INCONCLUSIVE`，内部验证状态为 `skipped_candidate_only`，由独立冷评分给出构建或测试结果。全轮共有 37 条请求预算耗尽，其中 18 条冷评分通过。预算状态描述生成过程何时结束，下面的日志描述最终交付候选的具体表现。

表中的原始证据位于归档 `worker/runs/<native_run_id>/` 下：`events.jsonl` 保存工具与停止事件，`agent/tool-results/` 保存工具回执，`patch.diff` 保存候选差异。`native_run_id` 可在原始归档的 `worker/result.json` 或评分归档的 `score/worker-result.json` 中查到。

**空候选，8 条。** 这 8 条的 `candidate_available=false`、`candidate_bytes=0`，原始 `patch.diff` 均为 0 字节，冷评分记为 `EMPTY_CANDIDATE`、`oracle_executed=false`。工具序列直接说明到预算截止时的工作内容；这类轨迹的代码根因保持未判定。

| 轨迹 | 任务 | 组·重复 | 工具与回执证据 | 停止事件 seq | 归档入口 |
| --- | --- | --- | --- | ---: | --- |
| `trial-009` | fmt-3734 | A · r1 | 16 次 `search_code`、8 次 `read_file`；工具记录全部为检索和阅读。 | 297 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13524470953) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13532666743) |
| `trial-015` | fmt-3819 | C · r1 | 10 次 `search_files`、14 次 `read_file`；工具记录全部为检索和阅读。 | 297 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13524152342) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13531961865) |
| `trial-044` | fmt-3819 | C · r2 | 12 次检索、11 次阅读后，第 24 步唯一一次 `edit_file` 返回 `EDIT_MATCH_NOT_FOUND`；回执 `s000024.t01.json`，事件 seq 295。 | 297 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13527081002) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13532772950) |
| `trial-045` | fmt-3819 | A · r2 | 1 次 `list_directory`、13 次 `search_code`、10 次 `read_file`。 | 297 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13526861429) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13532463288) |
| `trial-090` | fmt-2310 | A · r1 | 1 次 `list_directory`、14 次 `search_code`、9 次 `read_file`。 | 285 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13528653267) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13534115161) |
| `trial-105` | fmt-2610 | C · r2 | 8 次检索、13 次阅读、3 次 `run_shell` 编译探针；第 18、20、24 步探针均退出 1。第 24 步报告 `fmt::v8::detail::has_formatter` 成员缺失，回执 `s000024.t01.json`。 | 311 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13529847174) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13533034632) |
| `trial-106` | fmt-3260 | B · r2 | 11 次检索、13 次阅读；第 22 步检索返回 `INVALID_ARGUMENT / LOCALIZATION_CURSOR_INVALID`，随后继续两次阅读；错误事件 seq 279。 | 297 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13532030066) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13534585483) |
| `trial-108` | fmt-3260 | C · r2 | 13 次 `search_files`、11 次 `read_file`；工具记录全部为检索和阅读。 | 297 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13532330095) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13534260895) |

**测试失败，6 条。** 这 6 条完成冷构建，目标 fail-to-pass 测试仍有断言失败，已登记的 pass-to-pass 测试全部通过。独立评分均为 `ORACLE_TESTS_FAILED`。下表行号指评分归档中的 `score/oracle/logs/native-oracle-ctest.log`；字符串的空格属于断言内容。

| 轨迹 | 任务 | 组·重复 | 候选字节 | 冷测试中的直接观察 | 日志行 | 归档入口 |
| --- | --- | --- | ---: | --- | --- | --- |
| `trial-013` | fmt-3819 | A · r1 | 1211 | `args_test.named_with_automatic_index` 期望 `"1 2 3 4"`，`fmt::vformat("{} {a1} {a2} {}", store)` 实际为 `"1 2 3 2"`。 | 22–27 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13524002990) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13531543676) |
| `trial-088` | fmt-2310 | B · r1 | 444 | `format_nan`、`format_infinity` 失败；`{:+06}` 的 NaN 期望 `"  +nan"`，实际为 `"00+nan"`，Infinity 同样出现零填充。 | 132–184 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13529161594) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13533229627) |
| `trial-089` | fmt-2310 | C · r1 | 1897 | `format_nan`、`format_infinity` 失败；`{:<+06}` 期望 `"+nan  "`，实际为 `"  +nan"`；居中形式也得到右对齐结果，Infinity 同类。 | 132–154 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13528264862) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13534310110) |
| `trial-112` | fmt-2310 | B · r2 | 1377 | `format_nan`、`format_infinity` 失败；左对齐实际为 `"+nan00"`，居中实际为 `"0+nan0"`，右对齐实际为 `"00+nan"`。 | 132–164 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13531348000) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13534500950) |
| `trial-113` | fmt-2310 | A · r2 | 1057 | `format_nan`、`format_infinity` 失败；默认形式实际为 `"00+nan"`，左对齐为 `"+nan00"`，居中为 `"0+nan0"`。 | 132–184 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13531037882) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13534870661) |
| `trial-114` | fmt-2310 | C · r2 | 1372 | `format_nan`、`format_infinity` 失败；左对齐实际为 `"+nan00"`，居中为 `"0+nan0"`，期望使用空格填充。 | 132–154 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13531916490) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13533513307) |

**构建失败，5 条。** 这 5 条的冷配置成功、构建退出码为 1，独立评分为 `ORACLE_BUILD_FAILED`，已登记的 fail-to-pass 与 pass-to-pass 测试均为 `not_run`。下表行号指 `score/oracle/logs/native-oracle-build.log`，代码对应同一评分归档的 `score/candidate.patch`。

| 轨迹 | 任务 | 组·重复 | 候选字节 | 编译或链接日志及对应代码 | 日志行 | 归档入口 |
| --- | --- | --- | ---: | --- | --- | --- |
| `trial-014` | fmt-3819 | B · r1 | 1251 | `include/fmt/base.h:731` 的构造函数初始化 `auto_indexing_`，类中缺少该成员；候选补丁新增了这项初始化。 | 8、18 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13524357661) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13532281939) |
| `trial-026` | fmt-1361 | B · r1 | 3102 | 链接 `color-test` 时报告 `grisu_format<double, 0>` 的 `undefined reference`；补丁将对应实现重命名为 `grisu_format_impl`，原有声明和调用仍指向 `grisu_format`。 | 15–25 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13526430058) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13532966883) |
| `trial-041` | fmt-1361 | A · r2 | 5335 | 新增 float 实例化经 `fallback_format<float>` 进入 `fp<float>`，`bit_cast<uint64_t>(float)` 触发 `size mismatch` 静态断言，日志显示比较为 `(8 == 4)`。 | 5–21 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13525494031) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13533360280) |
| `trial-042` | fmt-1361 | C · r2 | 3944 | 补丁为 `grisu_format` 增加第六个 `bool` 参数，`src/format.cc:15` 的实例化函数指针仍为五参数类型；编译器报告 `no matches converting function`。 | 5–14 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13526666347) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13532147814) |
| `trial-076` | fmt-3732 | C · r2 | 1387 | 新增 `on_day_of_year()` 将 duration 转为 `std::ratio<86400>` 天；attosecond 周期换算实例化 `__safe_multiply<1000000000000000000, 86400>`，触发 `overflow in multiplication`，随后出现 `Factor::num/den` 错误。 | 16–35、68–77 | [原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13528203094) · [评分](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13533496343) |

**定位指标口径。** 主要 changed-span 指标覆盖 14 个有原行改动的任务，每组 28 条轨迹。`fmt-2070`、`fmt-3537`、`fmt-3713`、`fmt-3734`、`fmt-3819` 为纯插入任务，每组 10 条，单独记录插入锚点命中与冷评分。冷评分的完整分母始终是每组 38 条。

| 指标与分母 | A | B | C |
| --- | ---: | ---: | ---: |
| changed-span 命中，14 题 × 2 | 16/28（57.14%） | 17/28（60.71%） | 9/28（32.14%） |
| 封顶首次命中工具数，14 题等权均值 | 4.964 | 5.071 | 6.393 |
| 候选文件前五命中，14 题 × 2 | 摘要产出 0/28 | 26/28（92.86%） | 24/28（85.71%） |
| 纯插入锚点命中，5 题 × 2 | 5/10 | 7/10 | 6/10 |
| 纯插入任务冷评分通过，5 题 × 2 | 7/10 | 9/10 | 8/10 |

原始 A 组 `candidate_top5_hit` 数值为 0，28 条 eligible 轨迹的 `candidate_top5` 均为空。评分器从 `search_files.candidates` 收集候选摘要，按定位阶段的交付顺序累计前五个不同文件；A 使用 `search_code.matches` 输出源码行。A 的这个零值反映候选摘要的输出结构，跨组检索效果应结合 changed-span 命中比较。B 的 28 条、C 的 27 条 eligible 轨迹产出了候选摘要。

114 条轨迹的只读定位阶段均以 `model_step_budget` 结束，实际为 4 个模型步、4 次工具调用。`capped_first_hit_tools` 对定位阶段未命中的轨迹按协议记为 8；A、B、C 的工具数总和分别为 139、142、179，除以各组 28 条得到表中均值。这个统计量包含封顶删失计分。第 4 次只读工具的结果在第 5 次、已进入修复阶段的模型请求中确认交付，仍按协议归入定位曝光，相关请求费用也计入命中成本。

**两组可见回执的配对观察。** 以下配对按同题、同重复比较，展示查询和实际源码窗口；它们为轨迹诊断提供直接证据。

| 配对 | B 的定位轨迹 | C 的定位轨迹 | 结果与原始入口 |
| --- | --- | --- | --- |
| fmt-2310 · r1 | `trial-088`：第 3 次工具搜索 `write_nonfinite`，第 4 次读取 `include/fmt/format.h:1550–1604`，覆盖参考改动行。 | `trial-089`：先搜索 `isfinite`、`zero`，第 3 次读取 `format.h:1740–1839`，第 4 次才搜索 `write_nonfinite`。三个搜索回执均为 `evidence_outside_candidate_pool`，候选排序原因均为 `text_order`。 | changed-span：B 命中、C 未命中；两者冷测试均失败。[B 原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13529161594) · [C 原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13528264862) |
| fmt-3750 · r1 | `trial-063`：先定位并读取 `format_locale` 测试，再搜索 `write_int`，读取 `format.h:1960–2179`，覆盖参考改动行。 | `trial-062`：首个相同查询得到同一测试文件，并带 `same_file` 证据标记；之后搜索 `loc_value`，读取 `format.h:1050–1149`。`loc_value` 搜索使用 `text_order` 回退。 | changed-span：B 命中、C 未命中；两者候选前五命中且冷评分通过。[B 原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13527008460) · [C 原始](https://github.com/lilong555/ReproPatch/actions/runs/42242783788/artifacts/13526669263) |

在 fmt-2310 配对中，两组 `write_nonfinite` 搜索返回相同的候选池哈希 `435639b7105d5c909a9ce9b4e7fb410adbdd37febcbb0940703e0edf2491572b`；在 fmt-3750 配对中，首个 `format_locale` 查询的候选池哈希同为 `7b1f2da2db2a8107f53015dc128fabba8655178289ec72e5a2141cfb5ce4ce69`。对应回执分别位于各原始归档的 `agent/delivered/s000003.t01.json` 与 `s000004.t01.json`，以及 `s000001.t01.json`。

直接观察是两组在有限定位窗口内选择了不同查询、不同源码区间；文件级候选命中可以与 changed-span 未命中同时出现。C 组相对 B 组的全局差异是本轮测得结果，“反馈标记影响后续查询或阅读策略”属于待验证的因果假设，当前配对同时包含模型生成与自适应查询的差异。

**原始入口与完整性。** [完整聚合结果](results.json)、[全部 114 条原始/评分归档索引](artifacts.json)、[实验协议](../protocol.json)、[冻结评分源码](https://github.com/lilong555/ReproPatch/blob/5b4a2b1efd609a3384aeca3757d3a8c84dcffb3b/src/repropatch/localization_scoring.py)共同给出结果、分母和计分实现。上表所有 artifact ID 均来自该 Run 的 GitHub artifact API。报告使用的 21 个原始 tar 均通过归档 SHA-256 和逐文件清单核验，共 10,540 个文件；19 个失败评分归档的 195 个清单文件均通过核验，评分 JSON 与聚合结果逐条相同，worker 结果哈希与冷评分绑定一致。评分中的模型请求数均为 0。
