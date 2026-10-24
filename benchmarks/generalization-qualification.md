# 两项新实例资格

FMT-4055 与 simdjson-1899 均完成零模型资格检查。参考补丁分别通过 20 项、93 项完整原生测试，同时通过 ReproPatch 新工作树独立验收。结构化身份与日志引用见 [资格结果](generalization-qualification.json)，正式顺序与采用标准见 [实验协议](generalization-protocol.json)。

| 实例 | 固定上游提交 | 基线 F2P | P2P | 参考补丁完整原生 Oracle |
|---|---|---|---:|---:|
| fmtlib/fmt-4055 | `1408f1824d6a23643e178ee6e46478fb550a0963` | `format-test` 编译失败 | 19 | 20/20 |
| simdjson/simdjson-1899 | `5809e51ae405d763700ec19083009a2a1cdbfdbc` | `basictests` 将 `-1e-999` 解析为正零 | 92 | 93/93 |

FMT 的官方 `std::string_view` 回归已实际进入编译，基线报告 `no matching function`；受保护的 CTest 入口负责构建并运行同一原生目标。完整外部 Oracle 使用原始 CMake 文件。首次资格运行等待 `static assertion failed`，实际 GCC 输出为 `error:`；签名对齐后，基线与参考补丁均取得预期结果。

simdjson 的 DOM 回归通过 `std::signbit` 与零的倒数核对符号。官方 On-Demand `issue_1898` 在固定环境中通过，归入 P2P。93 项原生集合按该提交的数据记录冻结；参考 Oracle 的原始执行退出码为 0，评分使用保存日志与固定官方解析器完成。

这两项提供新实例验证，仓库均已出现在历史实验中。FMT-4055 属于 formatter 继承兼容性扩展；simdjson-1899 的各组输入保留原始 Issue 中的局部修复线索。正式矩阵为 Full、冻结批量候选、mini、Codex 各题两次，共 16 次、最多 192 请求。原生测试集合、策略源码、执行顺序与工程采用门槛均在模型调用前冻结。
