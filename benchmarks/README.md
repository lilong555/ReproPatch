# ReproPatch 评测

当前结果使用 `gpt-6-luna`，覆盖 Catch2、FMT、simdjson 六题，并加入原生 Codex CLI 对照。
[结果报告](cross-framework-results.md)、[逐次数据](cross-framework-results.json)和[准备状态](readiness.json)
记录每次尝试的源码身份、请求用量、候选及公共 Oracle 结论。
六题首次结果为 Full 4/6、mini 3/6、Codex 4/6；相同HTTPS端点四题子集为2/4、3/4、2/4。
simdjson中Full仍失败，mini通过；Codex首次传输中断、独立复测仍失败，两次完整保留。
[诊断反馈候选](diagnostic-feedback-results.md)保存五次0/5的后续实验，生产核心继续固定。
[批量修复与四组复测](batched-repair-results.md)保存 simdjson 候选2/2、第二轮原版成功、
mini与Codex目标回归失败，以及FMT构建失败与全部中断记录。

## 实验矩阵

| 任务 | 组别 | 每题每组次数 | 评分方式 |
| --- | --- | ---: | --- |
| Catch2-2187、2723；FMT-4310、4286、4057；simdjson-2178 | ReproPatch Full、mini-SWE-agent、Codex CLI | 1 | 同题共享的独立公共 Oracle |
| 历史Catch2-2187、2723 | ReproPatch Full、mini-SWE-agent、ReproPatch Ablation | 3 | 固定 Multi-SWE-bench 官方 Report |

Full 提供只读接口追踪反馈、文件可编辑状态和明确的构建工具说明。
Ablation 使用这些反馈加入前的核心源码，保留相同的预算反馈、执行与验收机制。
mini 固定为 2.4.6，commit `04d809ceab9df28f9adaed044884180159172930`；Codex CLI固定0.163.0。
各组使用同一模型标识、Issue、源码基线、修改范围、镜像及测试。
每次最多 12 个模型请求、24 次工具调用、每响应 8 次工具调用，输出上限 8192 token，
请求超时 90 秒，输入边界 256 KiB。

每题 Full 先运行，mini和Codex复用经 SHA-256 核验的领域输入；各组保留原生系统提示和工具协议。
mini 的执行时限扣除 Full 基线耗时及 10 秒清理余量。消融组自行执行干净基线。
最后两条尝试使用用户提供的新 CPA 地址，端点和控制器中断记录见结果报告。
两道 Catch2 题参与过开发诊断；FMT三题和simdjson按固定数据文件顺序选取。
完整端点、基线日志、原生工具协议和计时范围差异见当前报告；历史重复见[只读契约反馈实验](contract-results.md)。

## 数据集与适配

固定 [Multi-SWE-bench](https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-bench)
revision `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d`，C++ 任务池共 **129 个实例**。
当前 **6/129** 完成 Task v2 参考验收，其中三个 FMT 实例属于编译回归扩展。
[筛查清单](coverage.json)保留完整任务池；其余实例的动态兼容性仍待验证。

Catch2 的参考验收与测试组见[参考任务池](reference-pool.md)。公共 Oracle 固定 evaluator
`4b96a678b136f87c8760fa475697f3c98d5f9e5e`，分别要求 2 F2P + 50 P2P、2 F2P + 100 P2P。

FMT 原始记录的测试阶段为 `NONE`，F2P/P2P 为空，缺陷在构建阶段暴露。
[准备脚本](../scripts/prepare_fmt_task.py)将原生回归目标的编译及执行放入受保护的 CTest 节点，
形成 1 F2P + 20 P2P；4057为1 F2P +19 P2P。各组使用同一 prepared Task。
[公共 Oracle](../scripts/check_fmt_candidate.py)从原始 commit 应用官方测试补丁和候选，
使用原始 CMake 文件完整构建、运行 21 项原生测试；评分范围为本项目的编译回归扩展。
参考补丁仅用于环境资格检查。

[simdjson准备入口](../scripts/prepare_simdjson_task.py)固定原始提交、官方测试补丁及两项离线依赖，
将编译输出和大样本临时文件放到可写构建目录；Task为2 F2P +97 P2P。
[独立评分入口](../scripts/check_simdjson_candidate.py)重建原始提交，完整构建并运行99项原生测试。
prepared仓库bundle、原始测试、参考补丁及源码清单由当前Release附件提供。

[Codex运行入口](../scripts/run_codex_benchmark.py)复用mini的源码权限环境，
通过Unix套接字连接固定模型计量代理；容器内使用虚拟凭据，原始SSE和用量在宿主保存。
`--binary`指定固定版本的原生二进制及同目录配套运行组件，`--check-only`执行零模型环境检查。
同题的`--task`、`--mini-source`、`--mini-environment`、`--common-input`、`--ledger`、
`--attempt`、`--output`和`--agent-seconds`沿用现有输入，最终候选交给相同公共Oracle。

## 执行入口

安装环境分别使用 `requirements/agent.txt` 和 `requirements/benchmark-mini.txt`。
`--provider local-luna` 选择 CPA `https://cpa.liyinlong.me/v1`，从进程环境 `OPENAI_API_KEY` 读取密钥，
使用环境代理。原始 HTTP 正文保存模型参数和用量，鉴权头只在客户端使用。
CPA 使用独立用量账本，费用保留未知；DeepSeek 历史费用上界为 **¥2.18923088 / ¥20**。

```bash
PYTHONPATH=scripts python -c \
  'from benchmark_budget import LocalUsageLedger; LocalUsageLedger.create(".repropatch/luna-usage.sqlite3")'

python scripts/run_benchmark_agent.py --check-only --provider local-luna \
  --agent repropatch --task "$TASK" --ledger .repropatch/luna-usage.sqlite3 \
  --attempt luna-rp-1 --output .repropatch/luna-rp-1

python scripts/run_benchmark_agent.py --provider local-luna \
  --agent repropatch --task "$TASK" --ledger .repropatch/luna-usage.sqlite3 \
  --attempt luna-rp-1 --output .repropatch/luna-rp-1
```

`TASK` 指向冻结预算的 Task v2 文件。准备脚本的默认参数与实际实验配置分开记录。
预检检查 Task、账本和 mini 输入，保持零模型请求、零费用预留、零 Run 创建。
mini 额外提供 `--mini-source`、`--mini-environment`、`--common-input` 和 `--agent-seconds`。
其源码权限由准备脚本显式设置；首个请求前以实际容器用户读取全部可读文件。
每次尝试使用独立输出目录；相同批次持续使用同一账本。

## 计分与可靠性

非空候选交由各组共用的公共 Oracle 评分。预算耗尽后产生的有效补丁仍计成功。
空补丁记录 `NO_PATCH`，测试执行状态为未运行。环境故障、控制器中断、未知用量逐条保留。
ReproPatch 内部独立验收作为附加观察，与公共 Oracle 分开统计。

| 指标 | 分母与含义 |
| --- | --- |
| Resolved@1 | 单次尝试的 Oracle 成功率；重复实验按实例和重复编号展示 |
| Benchmark Coverage | 完成适配验收的实例 / 全部 129 个 C++ 实例 |
| False Acceptance Rate | Oracle 判无效但内部接受的候选 / Oracle 判无效的已评测候选；另列错误接受占全部接受的比例 |
| Cost per Resolved Task | 模型费用 / 成功数；账单缺失时为未知 |
| Wall-clock Time | 分开报告 Agent worker、基线、自检、独立验收和公共 Oracle 耗时 |

恢复机制的确定性证据复用[13 个故障场景](../docs/evidence/p2-04/recovery-gate/summary.json)：
3 个安全边界恢复成功、9 个明确拒绝恢复、1 个原控制器持锁。
本轮三组消融评价修复反馈；可靠性故障向量与真实修复成绩分别展示。

## 历史记录

[首次 Luna](luna-results.md) · [DeepSeek 预算反馈](repair-cycle-results.md) ·
[搜索上下文](cpp-navigation-results.md) · [rc3](rc3-rerun.md) · [rc2](pilot-results.md)。
各批次保留全部首次结果及接入故障。
原始轨迹、SQLite 和日志位于带 SHA-256 的 Release Assets，Git 保存摘要和源码清单。
[Harbor fixture pilot](harbor-pilot.md)保留为产物收集实验；通用 Harbor、额外 Agent 和执行器扩展暂停。
