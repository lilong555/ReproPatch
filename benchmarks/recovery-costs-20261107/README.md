# 检查点恢复成本实验

19 道真实 C++ 缺陷任务的 190 条历史轨迹已完成逐项复算，覆盖 3,584 次模型请求、52,842,882 个输入 Token。新鲜模型配对实验使用 2 道任务、每题 2 次重复，共 4 对，衡量故障后继续原 Run 与从基础源码重新执行的成本和冷验收结果。

## 已完成的历史成本核算

原始批次为 [Actions Run 42219312911](https://github.com/lilong555/ReproPatch/actions/runs/42219312911)，包含 baseline、diagnostics、dedup、state、combined 五组。每组均为 19 题 × 2 次重复。复算逐一核对原始下载摘要、tar SHA256、SQLite 完整性、事件投影、供应方响应及 usage、检查点引用和累计用量。

| 已提交的模型步边界 | 有效前缀 / 全部轨迹 | 前缀平均输入 Token | 前缀平均墙钟时间 | 前缀占整条轨迹输入的平均比例 |
| --- | ---: | ---: | ---: | ---: |
| 第 3 步 | 190 / 190 | 21,111.09 | 107.98 秒 | 9.42% |
| 第 6 步 | 190 / 190 | 49,857.41 | 123.18 秒 | 22.20% |
| 第 12 步 | 163 / 190 | 131,502.25 | 207.92 秒 | 48.17% |

全部可达前缀的源码、模型输入、配置及引用哈希完整，累计供应方用量与原生事件一致。第 12 步统计保留 163 / 190 的可达分母。墙钟时间包含原始基线复现与执行准备，使用持久化 UTC 事件时间戳计算。

baseline 单独覆盖 38 条轨迹、701 次请求、10,005,093 个输入 Token。其第 3 步平均前缀输入为 21,231.11 Token；第 12 步 32 / 38 条可达，平均前缀输入为 128,192.56 Token。

这些比例描述检查点之前已经发生的成本。故障后净节省、环境重建时间及质量差异由新鲜配对实验记录。历史 Run 已结束且原截止时间已过，归档复算保持其只读身份。

材料入口：

- [汇总及五组明细](history/summary.json)
- [190 条轨迹的完整复算记录](history/attempts.jsonl)
- [逐检查点 CSV](history/prefixes.csv)
- [原始轨迹下载索引](../context-ablation/full/artifacts.json)

## 新鲜模型配对协议

[冻结协议](live-protocol.json)选择所有历史任务按 `SHA256("recovery-v1/" + task_id)` 升序排列的前两题：`fmtlib__fmt-3732`、`fmtlib__fmt-3727`。每题重复两次，使用同一模型 `gpt-6-luna`、`max` 推理设置、原生六工具和 baseline 上下文策略。任务属于已经使用过的开发任务集。

每对依次执行以下流程：

1. 从基础源码启动真实 Agent，在第 3 个完整模型输入边界提交检查点并暂停，保存共享前缀的用量、源码、工具计数及截止时间。
2. 新进程恢复同一个 Run，沿用原 24 次请求账本，剩余 21 次请求，保留累计工具计数和原绝对截止时间。
3. 另一新进程从基础源码重新执行，Task 明确分配 21 次请求、`48 − 检查点已准入工具数` 次工具调用，以及 `floor(原截止时间 − 检查点提交时间)` 秒。
4. 两组完成后分别进行独立冷评分，保存全部候选、失败原因、原始请求、供应方 usage、源码及 SQLite 轨迹。

共享前缀单独列出。恢复组的故障后成本为累计账本减去前缀，重启组使用自身全部账本。输入 Token 包含缓存输入，缓存量另列。压缩等辅助请求计入同一上限。结果汇总保留失败、缺失用量、缺少检查点的样本和负节省；成本比较同时展示两组冷验收结果。

每对实际请求上限为 `3 + 21 + 21 = 45`，四对为 **180 次**。CPA 按既有认领接口为每个 attempt 分配 24 次，8 个 attempt 的登记上限为 **192 次**；重启组本地账本和 Task 共同执行更严格的 21 次限制。

计时分别记录：恢复 API 到源码重建完成、到首次模型准入、Harness 执行时长、检查点暂停至恢复启动的间隔，以及包含 Python 启动和监督轮询的子进程观测时长。每项时间保留测量起止和计时来源。

## 执行与证据

CPA 已注册 `recovery-costs-20261107-v1`；[注册回执](registration.json)包含服务脚本 SHA256、8 项临时认领验证、原租约与配置连续性，以及生产环境恢复认领数 `0`。新鲜模型结果由 Actions 完成后发布。

调度入口为 `formal-benchmark.yml` 的 `cross_stage=recovery-costs`。该入口与正在执行的上下文批次共用 `context-ablation-cpa-8` 队列，`cancel-in-progress=false`；四对按 `max-parallel=1` 串行。执行前核对前序 [Run 42335967622](https://github.com/lilong555/ReproPatch/actions/runs/42335967622) 已完成。

```bash
gh workflow run formal-benchmark.yml --repo lilong555/ReproPatch \
  --ref "$REPROPATCH_REF" \
  -f cross_stage=recovery-costs -f authorization=192 \
  -f cross_protocol=benchmarks/recovery-costs-20261107/live-protocol.json
```

工作流产出每对 `recovery-summary-<Run>-<Pair>` 与 `recovery-raw-<Run>-<Pair>`，汇总为 `recovery-results-<Run>`。完整原始证据采用逐文件 SHA256 清单封装，Actions 保留 30 天。每条结果包含原始 artifact 名称、下载页面、冷验收状态及失败原因。

历史复算命令：

```bash
python scripts/benchmark_recovery_costs.py audit \
  --artifacts-index benchmarks/context-ablation/full/artifacts.json \
  --raw-root "$REPROPATCH_RAW_ROOT" --output "$REPROPATCH_AUDIT_OUTPUT" --workers 2
```

单对准备与执行命令：

```bash
python scripts/run_recovery_pair.py prepare \
  --protocol benchmarks/recovery-costs-20261107/live-protocol.json \
  --pair pair-01-r1 --output .repropatch/recovery/prepared
python scripts/run_recovery_pair.py execute \
  --protocol benchmarks/recovery-costs-20261107/live-protocol.json \
  --pair pair-01-r1 --prepared .repropatch/recovery/prepared \
  --output .repropatch/recovery/execution
```

测量方法的离线验证覆盖 usage 缺失、哈希损坏、剩余额度派生、负收益保留、队列串行、CPA 认领边界，以及真实 Agents SDK 配合离线 HTTP 响应的暂停与恢复。实际故障后质量和成本以新鲜模型结果为准。
