# ReproPatch 评测

[Luna max 四臂实验](../docs/ACTIONS_FORMAL.md)已完成 21 道新 fmt 缺陷的 84 次首次实际模型运行。
统一 180 秒模型超时的 19 题中，Full 7/19、关闭自检组 10/19、mini 11/19、Codex 11/19；mini 三次 HTTP 524 保留。
19 题共 866 请求；首批两题 90 秒实验另有 76 请求。独立 max 校准另计 1 次。
[正式逐运行 JSON](actions-scale/formal-results.json)和[首批记录](actions-scale/formal-pilot-results.json)分别保存配置、用量与原始评分。

## 历史 medium 对照

已发布版本的模型修复成绩为 [v2 六次固定预算对照](generalization-final-results.md)：Full 1/2、mini 0/2、Codex 0/2。
全部六次按预注册顺序执行，61 次正式请求与 1 次独立校准分别记账，用量均完整结算。
两题已有 v1 尝试，v2 用于冻结新配置后的复核；[v1 历史记录](generalization-v1-results.md)
保留 110 次请求、10 次评分、1 次取消和 5 项未执行。

[GitHub Actions 实验](../docs/ACTIONS_RESULTS.md)完成 21 题固定镜像 O3 Docker 重验，其中 21 题合格，
并完成构建缓存 A/B 与 1/2/4 Job 对照；新模型请求为 0。[逐题 CSV](actions-scale/cloud-qualification.csv)
和[完整 JSON](actions-scale/cloud-results.json)保存任务状态与原始归档身份。

## 历史 v2 协议与版本

| 项目 | v2 实际配置 |
| --- | --- |
| 模型 / 端点 | `gpt-6-luna` / `https://cpa.liyinlong.me/v1` |
| 实际推理强度 | 三框架响应均为 `medium`；Codex 请求显式传入 `medium` |
| ReproPatch | 0.3.0，核心指纹 `81cf1c1f0eeec5b7011e1387151d6e7eca0d1840bab3c3d0eab1a52a32fceaf7` |
| 执行源码 | `04d884e91fd1ed583c4d2766bee6de3d385162b9`，逐文件清单随证据归档 |
| mini-SWE-agent | 2.4.6，`04d809ceab9df28f9adaed044884180159172930` |
| Codex CLI | 0.163.0，主程序及配套运行组件分别固定 SHA-256 |
| 每次预算 | 12 请求、24 工具、单响应最多 8 工具、8192 输出 tokens、256 KiB 输入、90 秒模型超时 |
| 执行顺序 | fmt Full → mini → Codex；simdjson Full → mini → Codex，单槽位 |
| 评分 | 相同原始基线与完整外部原生 Oracle，所有首次运行保留 |

[冻结协议](generalization-protocol-v2.json)提供 Task SHA、prepared commit、镜像、时限与参数证据。
Full 使用六个函数工具和逐轮新容器；mini 与 Codex 使用原生 Shell/补丁接口和持久修复容器。
Full 的 worker 时间包含基线与内部独立验收，外部框架的时间覆盖修复和自检，外部 Oracle 耗时单列。

后续 Luna 对照默认 `max`，三个客户端的实际请求构造已通过零付费检查。
[Luna 配置](luna-max-config.json)记录检查证据；[独立供应商校准](formal-max-calibration.json)已确认实际响应 `max`。
每批实验须在请求前显式冻结推理强度、源码和总请求额度。v2 沿用其归档源码中的 `medium` 参数。
历史实验的框架版本以各次原始运行记录为准，本次 mini 的版本为 2.4.6。

## 数据集与独立验收

固定 [Multi-SWE-bench](https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-bench)
revision `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d`，C++ 任务池共 129 个实例。
v0.3.0 历史适配集 **10/129** 已完成 Task v2 参考验收，覆盖 Catch2、fmt、simdjson、nlohmann/json 四个仓库。
其中四题为 FMT 编译回归扩展，六题为逻辑回归任务；[准备状态](readiness.json)与[筛查清单](coverage.json)分别记录动态资格和完整任务池。

| v2 实例 | prepared commit | 内部测试 | 外部原生测试 |
| --- | --- | --- | ---: |
| fmt-4055 | `148a69d245a44b1cc74baa6c9e05922fd8cb1b30` | 1 F2P + 19 P2P | 20 |
| simdjson-1899 | `65d4d8f24f77034e5b900b5a9bc77f69f7615bf7` | 1 F2P + 92 P2P | 93 |

[资格报告](generalization-qualification.md)保存两题参考补丁的内部与外部通过结果，资格阶段模型请求为零。
FMT 的原始记录在构建阶段暴露缺陷；[准备脚本](../scripts/prepare_fmt_task.py)
将回归目标的编译与执行放入受保护的 CTest 节点。
[外部 FMT Oracle](../scripts/check_fmt_candidate.py)使用原始 CMake 完整构建和测试。
[simdjson 准备脚本](../scripts/prepare_simdjson_task.py)固定离线依赖，
[外部 Oracle](../scripts/check_simdjson_candidate.py)从原始提交重建并评分。

## 计分与修复观察

| 字段 | 含义 |
| --- | --- |
| `oracle_pass` | 统一外部原生验收全部通过，主指标 |
| `native_accepted` | ReproPatch 内部接受且外部通过 |
| `recovered_oracle_pass` | ReproPatch 原生未接受，但保存的候选通过外部验收 |
| `candidate_source` | 首个非空的证据引用、patch.diff、未验证诊断或外部工作树 diff |
| `infrastructure_failure` | 可定位的环境或运行基础设施失败 |
| `error_category` | 模型、预算、时间或执行错误，独立于补丁评分 |

空候选记录 `NO_PATCH`，其测试执行状态为未运行。Codex CLI 非零退出单列原因；本次两次均触达 12 请求上限。
Full 的三个 F2P 自检和一次全量自检有原始事件及阶段耗时。simdjson 的两次 F2P 自检约 86.0 秒、85.1 秒，
全量自检约 188.4 秒，均包含配置与编译。该案例观察到 F2P 反馈后的继续修改；机制归因需要独立配对实验。
两题的 `single_header_pass` 为 null，json-4537 的历史单头文件审计独立报告。

## 零模型复核

[证据清单](generalization-evidence.json)给出归档名称、SHA-256、文件数量与发布状态。
证据包含 v1/v2 原始请求、SSE、事件库、候选、Oracle 日志、资格记录、执行源码、prepared 仓库 bundle 和重算脚本。
运行镜像使用已归档的 [C++ 工具链](https://github.com/lilong555/ReproPatch/releases/download/benchmark-contract-comparison-2026-10-22/ReproPatch-cpp-toolchain-beb37ec7c757.tar.gz)，
镜像及归档校验值见[附件索引](../docs/evidence/archive-index.json)。

```bash
sha256sum -c ReproPatch-generalization-v2-2026-10-24.tar.gz.sha256
mkdir -p evidence
tar -xzf ReproPatch-generalization-v2-2026-10-24.tar.gz -C evidence
docker load -i ReproPatch-cpp-toolchain-beb37ec7c757.tar.gz
python evidence/generalization/.repropatch/restore_generalization.py \
  --evidence-root evidence/generalization --task simd1899 --output replay-simd1899
repropatch verify-patch replay-simd1899/task.yaml \
  --patch evidence/generalization/.repropatch/generalization-v2-2026-10-24/v2-simd1899-full-1/candidate.patch \
  --producer archived-full --json
```

恢复脚本从 bundle 创建本机仓库，仅重定位 Task 的宿主路径，并核对规范任务 SHA 与冻结协议一致。
同一补丁的模型生成过程保留为原始轨迹；上述命令重新执行独立验收。

## 真实模型执行入口

环境分别使用 `requirements/agent.txt` 和 `requirements/benchmark-mini.txt`。
`--provider local-luna` 从 `OPENAI_API_KEY` 环境变量读取凭据，鉴权头仅在宿主客户端使用。
原始正文保存实际模型参数和用量。运行前先完成协议冻结与零模型预检。

```bash
PYTHONPATH=scripts python -c \
  'from benchmark_budget import LocalUsageLedger; LocalUsageLedger.create(".repropatch/new-luna-usage.sqlite3")'
python scripts/run_benchmark_agent.py --check-only --provider local-luna \
  --agent repropatch --reasoning-effort max --task "$TASK" \
  --ledger .repropatch/new-luna-usage.sqlite3 --attempt registered-full-1 \
  --output .repropatch/registered-full-1
```

实际运行使用同一参数并移除 `--check-only`。mini 额外提供 `--mini-source`、`--mini-environment`、
`--common-input` 与 `--agent-seconds`；[Codex 入口](../scripts/run_codex_benchmark.py)还需 `--binary`。
Codex 代理逐块保存上游 SSE，完整响应通过 `admit_tools` 后交给 CLI；工具额度满后保留纯文本总结请求的机会。

[累计账本审计](model-usage-audit.json)按原始请求 ID 去重：Luna 913 次，15 次用量未知，
另有一个仅存历史响应摘要的连通性探针；DeepSeek 185 次，费用上界 ¥2.18923088。
Luna 账单金额保持未知，离线响应夹具独立于真实模型计量。

## 历史实验

| 范围 | 结果与证据 |
| --- | --- |
| Catch2 组合反馈消融 | [Full 6/6、mini 3/6、消融 3/6](contract-results.md)，两道开发题、每题三次 |
| 六题三框架历史对照 | [Full 4/6、mini 3/6、Codex 4/6](cross-framework-results.md)，端点与推理设置差异逐条保留 |
| 诊断与导航 | [五个诊断候选](diagnostic-feedback-results.md)与[导航实验](cpp-navigation-results.md)保留失败记录 |
| 批量调用研究组 | [simdjson 候选与原版复测](batched-repair-results.md)，候选已归档 |
| json-4537 | [原生测试](json4537-results.md)与[双头文件审计](json4537-header-audit.md) |
| json-4525 | [Full、mini、Codex 均通过 98 项；相关模板候选编译失败](json4525-results.md) |
| FMT 连续修复 | [相关模板候选 1/3 与其他首次结果](repair-followup-results.md) |
| 早期模型 | [Luna](luna-results.md)、[DeepSeek 预算反馈](repair-cycle-results.md)、[rc3](rc3-rerun.md)、[rc2](pilot-results.md) |

全部实验保留原始身份、失败、取消与独立编号的复测。组合反馈消融支持组合策略的开发集观察，
当前两题复核说明端到端流程及有限预算下的实际行为。额外任务、候选 Prompt 和可选 Dev 配对均未进入 v2。
