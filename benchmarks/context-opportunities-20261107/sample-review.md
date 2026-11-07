# 固定样例核对

共核对 29 份固定样例。抽样按工具类型及入模长度分桶，以 `SHA256(attempt_id/tool_id)` 排序；另覆盖相同结果、同参数精确重复、新源码版本与后继检查关系。每桶或关系选取两个样本后按身份去重。

长片段提供候选压缩位置，具体保留范围由代码语义、当前修复状态与后续证据共同决定。精确错误、失败测试及临时文件状态保留在模型视图与原文索引中。

完整参数、路径、SHA-256、状态与错误片段见 [annotated-samples.json](data/annotated-samples.json)；原始抽样统计见 [review-samples.json](data/review-samples.json)。

| 样例 | 轨迹 / 工具调用 | 工具 | 入模代理 Token | 核对结果 |
|---|---|---|---:|---|
| S01 | [trial-019](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13504656968) / `s000014.t01` | `edit_file` | 135 | **保留短状态回执**：135 Token 的文件修改回执记录路径及修改前后哈希，承担源码状态关联。 |
| S02 | [trial-104](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13514495680) / `s000015.t01` | `edit_file` | 136 | **保留短状态回执**：136 Token 的修改回执提供 chrono.h 的前后哈希，适合继续保留。 |
| S03 | [trial-145](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13518506697) / `s000018.t01` | `list_directory` | 67 | **保留短目录结果**：两个源文件名提供目录结构，当前 67 Token 的回执已经紧凑。 |
| S04 | [trial-141](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13518601020) / `s000002.t01` | `list_directory` | 168 | **保留短目录结果**：13 个头文件条目提供候选目录信息，168 Token 的回执压缩空间有限。 |
| S05 | [trial-145](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13518506697) / `s000010.t01` | `read_file` | 813 | **候选：按任务裁剪代码**：75 行包含浮点格式化与相邻系统错误接口；裁剪需要当前定位目标，保留函数边界与可回读引用。 |
| S06 | [trial-072](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13510192275) / `s000002.t01` | `read_file` | 1317 | **候选：按任务裁剪代码**：100 行涉及 value 构造、类型特征和 arg_mapper，包含模板修复所需上下文；长度用于选择待审片段。 |
| S07 | [trial-178](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13520882873) / `s000007.t01` | `read_file` | 429 | **保留紧凑代码上下文**：429 Token 的枚举与格式参数定义与后续修复有关，低于本次 500 Token 候选阈值。 |
| S08 | [trial-018](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13503728882) / `s000010.t01` | `read_file` | 430 | **保留紧凑代码上下文**：430 Token 含 basic_format_specs 与参数引用，适合保留定义及源码位置。 |
| S09 | [trial-126](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13516822617) / `s000017.t01` | `run_command` | 7837 | **候选：保留失败诊断的摘要**：reproduce 工具完成，chrono-test 失败；原始 36,552 字节经现有折叠后仍有 7,837 代理 Token。保留文件行号、编译错误与失败测试，后续 s000019.t01 才通过。 |
| S10 | [trial-104](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13514495680) / `s000017.t01` | `run_command` | 7824 | **候选：保留失败诊断的摘要**：同样出现工具完成且 chrono-test 失败，后继检查通过。阶段状态分别记录，旧失败可在新证据到来后压缩为带引用的历史摘要。 |
| S11 | [trial-091](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13511427059) / `s000018.t01` | `run_command` | 1399 | **候选：按组汇总已通过测试**：verify 的 F2P/P2P 都通过，回执包含逐测试状态和日志引用；可保留检查角色、源码哈希、测试分组统计及原文入口。 |
| S12 | [trial-176](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13519969045) / `s000017.t01` | `run_command` | 1002 | **候选：汇总单次验证状态**：reproduce 的 chrono-test 通过，回执含构建与日志元数据。压缩应保留所检验测试、源码版本与验证角色。 |
| S13 | [trial-086](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13512725624) / `s000024.t01` | `run_command` | 未再入模 | **末尾回执：后续入模次数为 0**：verify 已通过，24 次模型请求预算之后没有后续请求；该回执的离线缩短对已记录运行的累计输入贡献为 0。 |
| S14 | [trial-062](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13509080308) / `s000024.t01` | `run_command` | 未再入模 | **末尾回执：后续入模次数为 0**：format-test 及 P2P 通过，结果停留在末尾；保留完整验收证据，输入机会统计按实际发送次数计量。 |
| S15 | [trial-135](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13517394133) / `s000020.t01` | `run_shell` | 8340 | **候选：聚合同类链接错误**：stderr 包含多条 fmt 符号 undefined reference，保留首个根因、不同缺失符号及命令配置。下一步出现文件缺失错误，需按不同故障分别保留。 |
| S16 | [trial-032](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13505434195) / `s000017.t01` | `run_shell` | 7497 | **候选：保留主错误的编译摘要**：宽字符字符串写入 std::ostream 引发 operator<< 不匹配和大量候选展开；主错误、操作数类型、用户代码位置属于关键证据。 |
| S17 | [trial-102](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13511804028) / `s000019.t01` | `run_shell` | 1179 | **候选：保留诊断因果链**：has_formatter 缺失带来连续解析错误；可按同一用户代码位置整理，保留建议符号、静态断言与原始诊断引用。 |
| S18 | [trial-139](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13517990232) / `s000012.t01` | `run_shell` | 615 | **候选：压缩已完成命令正文**：自建 memory_writer 检查返回 0；回执复述了完整命令和程序，可归纳检查内容、退出码与源码状态并保留原文。 |
| S19 | [trial-069](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13510841421) / `s000021.t01` | `run_shell` | 452 | **保留短错误与环境状态**：452 Token 回执报告 /build/chrono_check.cc 缺失；短错误准确解释本次编译失败与临时文件状态。 |
| S20 | [trial-135](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13517394133) / `s000021.t01` | `run_shell` | 432 | **保留短错误与环境状态**：432 Token 回执报告 /build/check.cc 缺失；它与前一轮链接失败是不同问题，应保留独立错误与命令身份。 |
| S21 | [trial-126](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13516822617) / `s000013.t01` | `search_code` | 581 | **候选：按目标选择搜索命中**：fmt_duration_cast 的定义与调用共存；摘要需要当前修复目标及完整原文入口。 |
| S22 | [trial-135](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13517394133) / `s000012.t01` | `search_code` | 1710 | **候选：按目标选择搜索命中**：测试文件含大量时间格式化断言，1,710 Token 的命中清单有裁剪空间；保留相关格式符、期望值与行号。 |
| S23 | [trial-106](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13514840862) / `s000006.t01` | `search_code` | 157 | **精确重复，收益较小**：与 s000004.t01 的源码、参数和结果一致，157 Token；引用替换仍有自身开销。 |
| S24 | [trial-106](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13514840862) / `s000001.t01` | `search_code` | 47 | **保留查询及空结果**：formatter<bool> 在指定路径下没有命中，47 Token 的负证据应连同查询身份保留。 |
| S25 | [trial-104](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13514495680) / `s000010.t01` | `search_code` | 182 | **保留不同查询语义**：回执 payload 与 s000001.t01 相同，但查询参数不同；两个查询身份都承载搜索路径信息。 |
| S26 | [trial-158](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13519860233) / `s000014.t01` | `search_code` | 82 | **精确重复，收益较小**：与 s000006.t01 的源码、查询与单个 grisu_format 命中相同，82 Token；替换长度需计入引用开销。 |
| S27 | [trial-128](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13517632875) / `s000009.t01` | `read_file` | 1367 | **候选：源码版本更新**：后续 read_file 读取了更新的 chrono.h，数值行号区间相交 25 行。旧片段涵盖 145 行，需结合补丁及定位目标确定保留范围。 |
| S28 | [trial-001](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13503376927) / `s000004.t01` | `read_file` | 1076 | **候选：源码版本更新**：后续 read_file 读取更新的 format.h，数值行号区间相交 26 行。保留版本哈希和范围，逐段判断旧证据用途。 |
| S29 | [trial-110](https://github.com/lilong555/ReproPatch/actions/runs/42219312911/artifacts/13514931752) / `s000010.t01` | `run_command` | 1993 | **候选：构建进度折叠与证据更新**：构建失败导致 chrono-test 尚未执行，后继 reproduce 仍未通过；进度行可汇总，主编译错误、not_run 与源码版本应保留。 |

两条长 `reproduce` 回执呈现 `tool_ok=true`、`test_passed=false`，后续检查才通过；`tool_ok` 表示工具完成，`test_passed` 表示该次业务测试判定。跨源码版本的数值行号相交与后继验证按“证据更新候选”记录。
