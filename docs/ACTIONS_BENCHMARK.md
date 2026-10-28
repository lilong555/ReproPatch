# C++ Benchmark 云端执行与效率改动

GitHub Actions 提供零模型 C++ 资格检查、固定共享工具链、构建性能测量和完整证据归档。
云端结果见 [Actions 实验报告](ACTIONS_RESULTS.md)，本地原生环境记录见
[构建与资格报告](BENCHMARK_SCALE_REPORT.md)。正式版本 `v0.3.0` 的发布身份和模型成绩按原始记录保存。
资源依据与优化取舍见 [Actions 资源依据](ACTIONS_RESOURCES.md)。

## 当前可执行范围

| 入口 | 实际行为 |
| --- | --- |
| `.github/workflows/benchmark.yml` | 手动资格检查、真实 fmt 构建性能试验、零消费正式实验计划 |
| `.github/workflows/toolchain.yml` | 手动构建共享工具链并发布 GHCR digest，保存镜像身份与工具版本 |
| `scripts/qualify_cpp_batch.py` | 固定数据集与源码，动态判断基线 F2P/P2P，参考补丁定向验证，独立冷构建原生全套 Oracle |
| `scripts/verify_qualification_evidence.py` | 核对每份原始证据与冻结清单；原件不变，合格执行与完整证据分别记录 |
| `scripts/check_qualified_cpp_candidate.py` | 对已合格任务冻结的候选执行相同冷 Oracle，单列空候选、无效补丁、范围违规、构建/测试及基础设施错误 |
| `scripts/score_benchmark_attempt.py` | 绑定 worker、Attempt、Task、prepared commit、镜像与候选哈希，优先区分准备/基础设施错误，调用同一外部 Oracle |
| `scripts/profile_cpp_build.py` | 同一真实上游任务的 Make/Ninja、ccache、增量构建配对计时，并撤销/重新应用参考补丁检查结果正确性 |
| `scripts/benchmark_resources.py` | 有界日志、超时/取消、CPU/内存/磁盘采样、阶段 wall time |
| `scripts/actions_benchmark.py` | 冻结计划、分片、共享源码输入、SHA-256 归档、包含全部注册任务的 JSON/CSV/Markdown 汇总 |
| `repropatch run --candidate-only --compiler-cache` | 导出完整性检查过的候选；Run 内自检使用 ccache；统一外部 Oracle 决定最终成绩 |

本轮工作流没有模型调用执行分支；`allow_paid_model=true` 明确失败。
`plan-formal` 生成各框架唯一 Attempt ID 和请求分配，实际可执行总请求上限始终为 **0**。
这提供可审查的正式计划；供应商费用上限、跨 Job 请求账本和真实模型执行仍需后续接入。

## Actions 使用

工作流位于默认分支 `main`，通过手动入口运行指定任务。代码提交执行常规 CI，已有合格任务复用冻结记录。
手动运行使用 Actions 页面或以下命令：

```bash
gh workflow run benchmark.yml --ref main \
  -f mode=qualify -f task_set=smoke -f parallel_jobs=2 \
  -f optimization=O3 -f batch_id=cpp-smoke \
  -f allow_paid_model=false

gh workflow run benchmark.yml --ref main \
  -f mode=qualify -f task_set=fmt-all -f parallel_jobs=4 \
  -f optimization=O0 -f batch_id=fmt41-O0 \
  -f allow_paid_model=false

gh workflow run benchmark.yml --ref main \
  -f mode=profile -f task_set=smoke -f parallel_jobs=2 \
  -f optimization=O3 -f batch_id=fmt-build-ab \
  -f allow_paid_model=false
```

O0 是单独的准备配置，保持 `-DNDEBUG`；不能将 O0 和 O3 结果合并为同条件对照。
每个任务都必须在其冻结配置下真实失败并经参考修复通过。建议先完成 O3 smoke，
再按本轮 O0 结果挑选大批量重验任务。

### 分片与资源

工作流选择 1、2 或 4 个 `ubuntu-24.04` Runner；每个 Runner 顺序执行一组任务，
单个任务使用两个编译进程。同项目任务共用一次 Python 安装、一个工具链镜像和一个 Git 对象池。
没有逐题 Job，也不并行启动多个重量级编译树。

`plan --estimates FILE` 可读入 `{ "instance_id": measured_seconds }` 并使用最长任务优先的
贪心分片。O0 工作流读取本轮成功资格任务的本地估时，计划保存估时文件哈希；
这些值只指导相对分片，不承诺 GitHub Runner 时长。无测量时使用同一默认估时，
因此不能声称已取得最优负载平衡。
工作流没有持久调度服务。

任务最长 1800 秒，资格批次外层最多 16200 秒；Job 最多 350 分钟，并给取消清理和归档留出余量。
超时先发 SIGTERM，外层最多等待 90 秒再终止。最后仅清理当前批次标签的容器。
Runner 硬终止仍可能阻止归档上传；汇总保留缺失任务，不能把缺失证据写成成功。

### 权限与身份

Benchmark 工作流使用 `contents: read`，拉取固定工具链的 Job 另有 `packages: read`。
工具链发布工作流仅在发布 Job 使用 `packages: write`。
Checkout 结束后移除 Git 凭据；运行环境使用固定官方 Action SHA，模型 API Secrets 保持未配置状态。
批次 ID 包含 GitHub Run ID 与 Run Attempt；原有已完成尝试不被覆盖。

`toolchain.yml` 使用独立 Job 的 `packages: write` 权限发布工具链，输出
`ghcr.io/lilong555/repropatch-benchmark@sha256:...` 和对应 image ID。
批量实验传入 `toolchain_image` 后，各 Job 按同一 digest 拉取镜像，汇总时核对镜像回执与任务 image ID。
工具链发布与拉取分别保存身份和计时，注册表凭据在步骤结束后移除。
手动 smoke 默认每个 Job 本地构建镜像，记录各自不可变 image ID；配对实验使用固定共享 digest。

```bash
gh workflow run toolchain.yml --ref main
gh run download TOOLCHAIN_RUN_ID --pattern 'toolchain-*' --dir toolchain
gh workflow run benchmark.yml --ref main \
  -f mode=qualify -f task_set=smoke -f parallel_jobs=2 \
  -f optimization=O3 -f batch_id=cpp-shared-smoke \
  -f toolchain_image=ghcr.io/lilong555/repropatch-benchmark@sha256:DIGEST
```

## 本地零模型预检

下面命令要求新输出目录，避免覆盖既有记录：

```bash
python -m pip install -e .
python scripts/actions_benchmark.py plan \
  --mode qualify --tasks smoke --parallel 2 --batch local-smoke \
  --backend native --optimization O3 --output .repropatch/local-plan.json
python scripts/actions_benchmark.py prepare \
  --plan .repropatch/local-plan.json \
  --instances fmtlib__fmt-4055,fmtlib__fmt-3863 \
  --output .repropatch/inputs
python scripts/benchmark_resources.py \
  --output .repropatch/local-metrics --timeout 4000 --kill-grace-seconds 90 \
  --watch inputs=.repropatch/inputs --watch evidence=.repropatch/local-smoke \
  -- python scripts/qualify_cpp_batch.py \
  --dataset .repropatch/inputs/dataset --repository .repropatch/inputs/fmt \
  --instances fmtlib__fmt-4055,fmtlib__fmt-3863 \
  --backend native --jobs 2 --build-jobs 2 --optimization O3 \
  --output .repropatch/local-smoke
python scripts/verify_qualification_evidence.py \
  --batch .repropatch/local-smoke \
  --output .repropatch/local-smoke-audited/audit \
  --summary-output .repropatch/local-smoke-audited/batch-summary.json
python scripts/actions_benchmark.py aggregate \
  --plan .repropatch/local-plan.json --source .repropatch/local-smoke-audited \
  --output .repropatch/local-summary
```

Native 成功为 `HOST_QUALIFIED`，只允许可信上游测试与参考补丁。
它不生成隔离成绩，也不允许用原生后端执行任意模型候选。
Docker 重验成功后才产生 `QUALIFIED` 和可供 Harness 使用的 Task v2。
详见 [资格契约](BENCHMARK_QUALIFICATION.md)。

## 自检缓存与统一评分

核心采用较短改动路径：每次自检仍创建全新容器和 `/build`，只共享本 Run 的 ccache。
缓存使用固定容器路径、编译器内容身份和独立 Namespace；未启用 `sloppiness`。
Baseline、`run_shell`、内部最终验收和外部 Oracle 不挂载该缓存。
ccache 的 `1G`（1 GB）是淘汰目标，峰值仍由资源采样监督。

持久 build 目录仅在性能实验中验证，尚未进入核心自检；依赖 Ninja、头文件或生成文件
修改的重建正确性仍需项目级门禁。CMake/Ninja 配置属于任务身份，不能静默改动已冻结正式任务。

`candidate-only` 完成候选冻结、干净 Worktree 重新应用、源码清单及补丁往返校验后，记录：

```json
{
  "outcome": "INCONCLUSIVE",
  "reason_code": "EXTERNAL_ORACLE_REQUIRED",
  "verified": false,
  "candidate_roundtrip_verified": true,
  "benchmark": {
    "candidate_only": true,
    "internal_verification": "skipped_candidate_only",
    "final_oracle_required": true
  }
}
```

该状态表示候选等待外部评分。它不是成功修复，也不能自动计作基础设施错误。
`verify-patch` 保留完整独立冷验收能力，不能使用这两个 Benchmark 选项。
后续公平对照须为四个框架臂提供同一固定源代码、测试和统一最终 Oracle；各自工具协议和
实际请求/Token 用量继续单列。

两个 worker 现均保存 `task.original.yaml`，摘要中的 `task_sha256` 明确定义为 Task 文件原始字节哈希，
与原生 report 的 resolved-contract 哈希分开。评分脚本要求 Docker `QUALIFIED`：

```bash
python scripts/score_benchmark_attempt.py \
  --worker-result .repropatch/attempt-001/result.json \
  --attempt-id attempt-001 \
  --qualification .repropatch/qualification/fmtlib__fmt-3727/result.json \
  --dataset .repropatch/inputs/dataset --repository .repropatch/inputs/fmt \
  --output .repropatch/score-001 --check-only
```

`--check-only` 不构建，身份一致且有候选时记录 `PENDING_ORACLE`。
去掉该选项后才在固定 Docker 工具链中冷构建评分。原生 `HOST_QUALIFIED` 在这一入口不能执行。
评分新增请求为 0，原 worker 的真实用量保留；源码不变的正常编译错误与明确的
Docker 启动失败/资源终止分别分类，后者不猜测为 OOM。
桥接的身份和错误分类已通过离线契约检查，真实 Docker 端到端评分仍待执行。

## 证据与缓存生命周期

Git 仅保存代码、冻结配置、任务状态、摘要与哈希。原始日志、JUnit、候选、工具链身份、
资源采样和失败诊断按批打包。`pack` 排除可重建的源码、Git 对象、build、ccache，
生成逐文件清单并重新读取压缩包核验 SHA-256，成功后才原子更名。

Workflow 在打包前核验资格阶段保存的原始清单，生成独立的审定摘要。聚合器只接受
`VERIFIED` 或 `RECOVERED_EXACT` 且审计文件 SHA 相符的合格记录；其余执行通过项降为
`EVIDENCE_INCOMPLETE`，保留 `execution_status`。原始失败、取消与诊断不会被覆盖。
`--recover-commands` 仅允许从冗余 `result.commands` 恢复与原始哈希逐字节一致的命令清单，
写入独立恢复目录；其他缺失或损坏日志需要新的显式 Attempt，不通过更新哈希“修复”。

```bash
python scripts/actions_benchmark.py pack \
  --source .repropatch/local-smoke \
  --output .repropatch/archives/local-smoke.tar.gz
(cd .repropatch/archives && sha256sum -c local-smoke.tar.gz.sha256)
```

本地核验状态为 `LOCAL_ARCHIVE_VERIFIED`；包内冻结时的远端状态保持 `NOT_UPLOADED`。
Workflow 上传后会重新下载原始包，对照上传前 metadata 中的 SHA-256，另存
`archive-receipt.json`；只有这一步成功才记录 `ARCHIVE_VERIFIED_REMOTE`。
上传、下载或校验失败时，即使测试通过，云端聚合仍降为 `EVIDENCE_INCOMPLETE`，
同时保留执行状态和具体归档失败原因。云端 Run 与下载校验记录见
[机器可读汇总](../benchmarks/actions-scale/cloud-results.json)。
Actions 原始产物保留 7 天，聚合结果 14 天，已压缩文件使用上传 `compression-level: 0`。
正式证据应复用现有按批 Release 的方式长期公开保存，每包低于 2 GiB，附下载 SHA-256。
本工作流尚未实现自动发布 Release；短期 Artifact 不能代替长期证据。

| 存储 | 适合内容 | 成本与维护取舍 |
| --- | --- | --- |
| GitHub Releases | 冻结批次原始证据、清单和小型源代码快照 | 公开可下载、无显式总带宽/体积上限；必须按附件限制分包并核验 |
| Actions Artifact | Smoke、失败诊断、上传中转 | 与执行关联简单，但有保留期限和账户存储额度 |
| GHCR | 固定工具链镜像及依赖层 | 当前存储/带宽免费；镜像按 digest 引用，避免每题一个镜像 |
| 外部对象存储 | 超大规模历史归档、镜像复制 | 引入账号、访问策略、账单及长期维护；当前规模暂缓 |
| Actions Cache | 可丢弃 Git 输入和将来经过 A/B 验证的紧凑缓存 | 10 GB 默认免费额度、7 天未访问可淘汰；不保存唯一证据 |

Actions 输入缓存通过 `cache_inputs=true` 显式启用，默认关闭；同 Job 的源码对象池复用一直有效。
本机两题首次准备仅 1.70 s、复用已有输入为 0.107 s（各一次），因此没有足够依据保证
Actions 下载/解压缓存比直接获取更快。可用该开关做云端 A/B，来源 SHA 每次仍重新核验。
缓存只含小型数据集和源代码对象；完整 build、跨 Job ccache、BuildKit 远端缓存均未默认启用。
在同一 Runner 测量恢复、解压、构建、保存与上传五段总耗时，再决定是否改默认值。

## 正式模型实验准入

建议先选两题、四臂、每次 12 请求：计划上限 **96 次**；30 题为 **1440 次**，
50 题为 **2400 次**，供应商参数校准单独分配。请求上限不能换算为确定金额。
正式启动前须冻结供应商实际模型、响应确认的推理档位、输入/输出 Token 上限、
可核对的单价与批次总金额上限。未知金额记 `UNKNOWN`。

下一步采用静态不可转移的 Attempt 预算分配；每个分片的硬上限之和不得超过批次上限，
原生客户端重试计入同一分配，取消后不自动补跑。结果必须覆盖全部预注册尝试，
保持首次结果、空候选、超时、429、未知用量和基础设施失败。
已有单槽代理账本可复用，但跨 Job 的令牌/费用硬上限尚未实施，不能宣称已具备全局付费控制。
四臂计划中的关闭自检臂也尚未接入执行器；正式运行前须明确禁用哪些执行/测试工具，
保存这一工具协议差异，并验证同一外部 Oracle。
