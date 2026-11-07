# Localization A/B/C

固定 19 个历史暴露的 fmt 开发任务，比较三种定位接口：A `native` 使用 `search_code`，B `bounded` 使用文件摘要 `search_files`，C `feedback` 在 B 的候选池上按公开执行证据排序。三臂关闭 Tree-sitter，使用同一 baseline 上下文策略、源码窗口与总预算。

[114 条完整结果](full/README.md)：A/B/C 冷评分分别通过 32/38、33/38、30/38；B、C 的输入 Token 及首次命中工具成本高于 A，默认继续采用原生搜索。[三组预检](smoke/README.md)独立保存。

## 配置与预算

| 配置 | 固定值 |
| --- | --- |
| 模型 | `gpt-6-luna`，reasoning `max` |
| 整次运行 | 24 次模型请求、48 次工具调用；请求超时 600 秒；零重试 |
| 只读定位 | 最多 4 次模型请求、8 次工具调用；模型请求包含 summary/compaction，计入整次运行预算 |
| 阶段转换 | 任一定位预算耗尽或模型输出 final，下一次模型请求进入修复 |
| 只读工具 | `list_directory`、`read_file`、对应臂的搜索工具 |
| 拒绝操作 | 写入和执行返回错误并计入工具预算；同批超限调用返回预算错误 |
| Smoke | `fmtlib__fmt-2310`，三臂各一次，72 次请求上限 |
| Full | 19 题 × 3 臂 × 2 次重复 = 114 次运行，2,736 次请求上限 |
| 并发 | 8 workers；共享 `context-ablation-cpa-8`、`queue: max` |

任务合同、镜像、资格归档、上下文策略和运行时限由固定哈希的父协议继承。任务与重复构成配对块，块顺序及块内三臂顺序使用固定 seed 的 SHA-256 排序。矩阵保存随机化提交顺序；runner 事件保存实际启动时间，供并发和时间效应检查。

B/C 每个扫描块最多读取 16 MiB、128 个文件，每页最多 12 个候选及每文件 8 个命中行号。正式运行的原始响应预算为 22 KiB，为共享运行时包装预留空间；页容量依据共有候选池的最大记录和相同证据预留计算。分页索引采用最多 8 个扫描块、64 MiB 的 LRU 缓存，源码变化后失效，恢复后按需重建；扫描、缓存、排序与输出开销分别计量。

## 固定反馈

`prepare` 从经 SHA-256 校验的资格归档中仅提取 `baseline-configure.log`、`baseline-build.log`、`baseline-ctest.log`，生成 `<attempt>/visible-feedback.json`。包保存日志原文及各自 SHA-256，绑定任务 ID、prepared commit 和运行时相同的源码树哈希；完整 canonical JSON 上限 2 MiB。三臂读取同字节的公开包。

```json
{
  "schema": "repropatch.localization-feedback.v1",
  "instance_id": "fmtlib-fmt-2310",
  "prepared_commit": "<qualified commit>",
  "source_tree_sha256": "<source manifest SHA-256>",
  "logs": [
    {"name": "baseline-configure.log", "sha256": "<SHA-256>", "text": "<original log>"},
    {"name": "baseline-build.log", "sha256": "<SHA-256>", "text": "<original log>"},
    {"name": "baseline-ctest.log", "sha256": "<SHA-256>", "text": "<original log>"}
  ],
  "feedback_sha256": "<SHA-256 of canonical_json without this field>"
}
```

Worker 参数为 `--localization-mode native|bounded|feedback --localization-tool-budget 8 --localization-step-budget 4 --localization-feedback-file <path>`。生成记录另存整个文件的 SHA-256 和用于评分重建的源码归档哈希。

生成准备按当前任务 allowlist 读取 `task.yaml`、`control/test.patch`、三份 baseline 日志和清单。公开 base commit 来自冻结 coverage；公共测试补丁与固定 CTest adapter 构成单提交源码仓库，prepared commit、执行 Task 字节和源码清单均与资格合同核对。生成产物保存 `qualification-public.json` 安全投影，完整参考补丁及 oracle 证据在独立评分阶段读取。

`source-base.tar` 保存独立 Worktree 的准确文件集合与模式，`source-base.bundle` 保存同一 prepared commit 的 Git 身份。跨 job 评分从 bundle 创建真实仓库，核验唯一 HEAD、单提交历史和源码树哈希，恢复完整资格合同后执行冷验证。源码快照保留 `export-ignore` 文件，运行时的 `source_manifest` 安全契约保持一致。

## 执行链路

入口为 `formal-benchmark.yml` 的 `cross_stage=localization-ablation`。

`context_scope=smoke` 只运行三臂 smoke。`context_scope=full` 在同一次 dispatch 内依次执行 smoke 和 full；full 依赖 smoke 成功，并重新校验同源码的结果 artifact。两个阶段用 scope 隔离 Attempt、manifest、artifact 和 CPA 配额。

每个阶段先核验同源码 `ci.yml` 的 Python/C++、SDK、Docker 三项 CI 与定位离线测试，再冻结协议、源码文件哈希、任务矩阵及 Run 身份。生成作业全部终止后，独立评分作业读取参考补丁并运行定位评分与冷容器验证。评分作业不配置 CPA 凭据。

Smoke 门槛要求三臂具有真实请求、完整 provider 用量、完整曝光和阶段结束记录、冷评分结果以及一致的公开反馈包。最终补丁可以修复失败，结果完整保留。正式 full 的所有已登记任务、提前停止、未命中、基础设施异常和缺失 artifact 均进入报告。

```bash
PYTHONPATH=src:scripts python scripts/localization_ablation.py plan \
  --scope smoke --dry-run --output /tmp/localization-smoke-plan.json
PYTHONPATH=src:scripts python scripts/localization_ablation.py plan \
  --scope full --dry-run --output /tmp/localization-full-plan.json
PYTHONPATH=src:scripts python -m pytest -q \
  tests/test_localization_ablation.py tests/test_localization_preparation.py \
  tests/test_localization_cpa.py
```

Dry plan 仅生成本地矩阵，执行入口要求完整 gate、GitHub Run 身份和首次运行。CPA claims 持久化拒绝重复 Attempt；失败尝试保留原记录。

## 评分与判定

定位标签由 `scripts/score_localization.py labels` 从独立评分端的参考补丁和冻结旧源码生成；`score` 消费原始 run 事件和精确交付回执。主要记录 changed-span 预算内命中、上限首次命中工具成本、候选 Top-5 和完整 provider 用量，同时保留标签覆盖率、未命中与冷验证结论。纯插入锚点独立报告。

`eligibility.json` 的 SHA-256 在协议中冻结，预登记 14 个 changed-span 可评分任务和 5 个纯插入任务，full 每臂有 28 次 changed-span 可评分运行，按任务等权汇总。该注册表保存资格类型、布尔值和身份哈希；gold 路径与区间由评分端持有。全部运行的成本与冷验证保留在 19 题主表；整题评分缺失时，changed-span 主分母仍为 14，缺失命中计 0、上限工具成本计 8，并单列证据缺失。

曝光链路从 `localization_receipt_prepared` 开始：回执实际进入承载模型请求并取得确认响应后，登记实际交付事件。评分以确认交付的源码正文及其文件、行号、源码哈希与参考旧源码区间求交。候选路径摘要独立计量，预先生成的回执保留在准备记录中。末段只读回执可由首个 repair 请求承载；首次命中的模型请求数、真实 Token 和墙钟包含该承载请求，工具调用数沿用共享账本累计值。

先在每个任务内平均两次重复，再进行 B−A、C−B 的任务等权配对比较。默认方案采纳条件预登记为：冷成功率差值 ≥ 0、上限首次命中调用成本差值 < 0、真实输入 Token 差值 ≤ 0。主表同时报告命中与成本；测量缺失时保留缺失值，继续保持既有默认配置。

每个阶段输出 `localization-plan-<run>-<scope>`、逐 Attempt 原始归档及评分归档、`localization-results-<run>-<scope>`。归档含逐文件哈希，汇总保留冻结分母、配对明细和被拒绝的冲突证据。
