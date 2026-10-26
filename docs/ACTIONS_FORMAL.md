# Luna max：GitHub Actions 正式实验

2026-10-26。21 道 O3 Docker 合格 fmt 缺陷的 84 次模型实验已结束。首批两题采用 90 秒模型超时，后续 19 题采用统一 180 秒超时，分别报告。

后续 19 题的冷 Oracle 通过数为 Full **7/19**、关闭自检组 **10/19**、mini **11/19**、Codex **11/19**。mini 的 3 次基础设施错误保留在 19 次尝试的分母中。全部 76 项已有终态，39 项通过、34 项候选失败、3 项供应商网关超时。

## 冻结执行条件

- 模型 `gpt-6-luna`，同一 CPA 端点，实际请求 `reasoning.effort=max`。866 份请求正文逐一核对账本 SHA-256 和推理字段。
- 每臂每题 12 请求、24 工具、单批 8 工具；每请求 8192 输出 Token、256 KiB 请求准入；重试为 0。
- Full 使用六个受控工具与 Run 内 ccache；关闭自检组移除 `run_command` 与 `run_shell`，保留四个文件工具。两组均使用 candidate-only，最终由相同冷 Oracle 评分。
- 模型执行源码 `9d9e4be7ddcb9573edc5c7540b3e1808713d5744`；核心指纹 `69f5a6b805e1cb5e3d670377e1a45b3053962ea9eeaeb8bbf984433330f85a84`。
- 固定镜像 `ghcr.io/lilong555/repropatch-benchmark@sha256:c00247e787729d6af3af364ab80cce196d90033832f77f2c1262a6e8f7cf111a`。
- [冻结协议](../benchmarks/formal-max-full-180s-protocol.json) SHA-256：`f0bb454d5dbd4e273517049509a9d67c667f39983740a51bff452d3fee38cc55`。
- [模型 Run](https://github.com/lilong555/ReproPatch/actions/runs/40212667694) 与[最终冷验收 Run](https://github.com/lilong555/ReproPatch/actions/runs/40224074698)全部完成。

这些任务在冻结前的仓库模型尝试审查中均无记录；资格阶段使用官方测试与参考补丁。任务来自同一个 fmt 仓库，每臂每题首跑一次。

## 19 题结果

| 实验臂 | Oracle 通过 | 基础设施错误 | 模型请求 | 输入 Token | 输出 Token | 未知用量请求 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ReproPatch Full | 7/19 | 0 | 220 | 2,517,400 | 52,680 | 0 |
| 关闭中途自检 | 10/19 | 0 | 226 | 2,558,103 | 53,599 | 0 |
| mini-SWE-agent 2.4.6 | 11/19 | 3 | 199 | 3,333,417 | 85,847 | 3 |
| Codex CLI 0.163.0 | 11/19 | 0 | 221 | 5,885,767 | 123,492 | 0 |

866/912 次正式请求，已知输入 14,294,687 Token、输出 315,618 Token，其中 reasoning Token 230,571。输出 Token 已包含 reasoning Token。三次 HTTP 524 的实际用量未知；金额随供应商账单记录，当前为 `UNKNOWN`。

| fmt 任务 | Full | 关闭自检 | mini | Codex |
| --- | --- | --- | --- | --- |
| 1171 | 编译失败 | 编译失败 | 通过 | 编译失败 |
| 1361 | 测试失败 | 空候选 | 测试失败 | 通过 |
| 1390 | 通过 | 通过 | 通过 | 通过 |
| 2070 | 通过 | 通过 | 通过 | 通过 |
| 2292 | 编译失败 | 通过 | HTTP 524 | 空候选 |
| 2310 | 空候选 | 测试失败 | 空候选 | 编译失败 |
| 2317 | 通过 | 通过 | 通过 | 通过 |
| 2610 | 空候选 | 空候选 | 空候选 | 通过 |
| 2940 | 通过 | 通过 | 通过 | 编译失败 |
| 3158 | 空候选 | 编译失败 | 编译失败 | 空候选 |
| 3248 | 通过 | 通过 | 通过 | 通过 |
| 3260 | 测试失败 | 编译失败 | 通过 | 通过 |
| 3272 | 空候选 | 通过 | 通过 | 空候选 |
| 3537 | 空候选 | 通过 | 通过 | 通过 |
| 3713 | 通过 | 通过 | 通过 | 通过 |
| 3732 | 空候选 | 空候选 | 编译失败 | 编译失败 |
| 3734 | 空候选 | 空候选 | 通过 | 通过 |
| 3819 | 空候选 | 空候选 | HTTP 524 | 空候选 |
| 493 | 通过 | 通过 | HTTP 524 | 通过 |

## 自检配对观察与计时

Full 与关闭自检组共同通过 7 题；关闭自检组另通过 fmt-2292、3272、3537；两组共同失败 9 题。Full 调用了 9 次 `reproduce`、7 次 `verify`，`run_shell` 调用为 0。16 次自检的 evaluation 累计耗时为 **751.25 秒**。

本批支持继续精简自检策略：Full 的成功数较关闭自检组少 3 题，已有成功题全部被关闭自检组覆盖。该配对同时涉及工具 Schema 和提示差异，后续机制分析应结合逐步编辑与反馈轨迹。当前冻结结果完整保留。

| 实验臂 | Worker 累计秒 | Worker 中位秒 | SDK 基线累计秒 | 冷 Oracle 累计秒 |
| --- | ---: | ---: | ---: | ---: |
| ReproPatch Full | 4022.34 | 204.63 | 1675.57 | 767.32 |
| 关闭中途自检 | 3296.10 | 167.19 | 1683.02 | 919.78 |
| mini-SWE-agent 2.4.6 | 2979.56 | 152.98 | 单列资格阶段 | 1081.41 |
| Codex CLI 0.163.0 | 3019.39 | 143.82 | 单列资格阶段 | 1032.71 |

Full 和关闭自检组的 Worker 包含 Harness 基线、修复、候选冻结与清理；Full 自检包含在其 Worker 内。mini 和 Codex 的 Worker 覆盖其原生客户端修复流程；两者使用已冻结的资格输入。冷 Oracle 在另一阶段独立计时。表中时间分别描述各自范围。

## 失败与验收证据

mini 的 fmt-2292、3819、493 均收到 CPA 端点的 HTTP 524，原始 HTML 标题为 `liyinlong.me | 524: A timeout occurred`，页面标识 Cloudflare。客户端配置为 180 秒，网关先返回超时响应，LiteLLM 将其报告为 `MODEL_REQUEST_FAILED:Timeout`。三次均无有效冻结候选，分别在第 5、9、3 个请求结束。

原模型 Run 的初始评分记录为 `PREPARED_COMMIT_MISMATCH`：派生资格目录缺少 Git 元数据，读取 HEAD 时落到外层仓库。冷验收依据固定上游、官方测试与原适配器恢复 prepared commit，逐文件核对源码清单，然后调用原有 Oracle。初始评分、候选 SHA-256 与最终评分同时保留；全部冷验收新增模型调用为 **0**。

[首次两题冷验收](https://github.com/lilong555/ReproPatch/actions/runs/40216295246)、[增量冷验收](https://github.com/lilong555/ReproPatch/actions/runs/40217801367)与最终全量冷验收，共 25 份原始压缩包、1,389 份文件逐项核验通过；重复的冷验收记录按 Run 保留。19 份模型证据压缩包均已核验；76 个 Worker 全部确认容器清理。

## 首批两题与总预算

首批 fmt-3727、3750 使用 90 秒模型超时，8 次首次实际模型运行共 76 请求，未知用量 4 次。Full 在 fmt-3750 通过 20 项测试，fmt-3727 编译失败；其余三臂两题均未通过。安装或准入失败且模型请求为 0 的尝试保留在原始 Run 中。

| 阶段 | 任务 × 实验臂 | 模型请求 | 未知用量 |
| --- | ---: | ---: | ---: |
| 首批，90 秒 | 2 × 4 | 76 | 4 |
| 正式全量，180 秒 | 19 × 4 | 866 | 3 |
| 正式合计 | 21 × 4 | **942/1008** | **7** |
| 独立 max 校准 | 1 次 | 1 | 0 |
| 冷验收 | 冻结候选 | 0 | 0 |

首批与后续 19 题按各自冻结配置报告。[首批逐运行记录](../benchmarks/actions-scale/formal-pilot-results.json)、[19 题逐运行记录](../benchmarks/actions-scale/formal-results.json)与[独立校准](../benchmarks/formal-max-calibration.json)保存来源和用量。历史 v2 的 medium 结果保留于原报告。

## 验证与复核

[冻结模型源码 CI](https://github.com/lilong555/ReproPatch/actions/runs/40212551852)通过 **614 项**：431 Core、160 SDK、23 真实 Docker，失败、错误、跳过均为 0。统计取三个根 JUnit，验证记录见 [CI 摘要](evidence/formal-max-2026-10-26/summary.json)。

原始模型请求、响应、工具轨迹、账本、失败、候选和原生 Oracle 均保存在对应 Actions Artifact，保留期为 14 天。归档清单见 [证据索引](../benchmarks/actions-scale/formal-evidence.json)，长期复核使用同名本地交付包及其 SHA-256。
