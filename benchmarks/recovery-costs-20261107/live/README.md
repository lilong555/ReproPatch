# 真实模型检查点恢复与重启配对结果

两道 fmt 任务、每题两次重复，共 **4 对、8 条最终轨迹**。恢复组冷验收 **3/4**，从基础源码重启组 **2/4**。恢复组故障后输入增加 **29.06%**；四对 Harness 执行时长合计增加 **11.31 秒**。检查点重建中位 **1.859 秒**，八项恢复一致性检查在四对中全部通过。

该结果体现可恢复运行时的状态保留和较快准入能力。后续生成轨迹的请求长度与修复行为共同决定完整任务开销，本批故障后净成本呈负收益。

## 成功率与故障后成本

| 指标 | 同 Run 恢复 | 基础源码重启 |
| --- | ---: | ---: |
| 冷验收通过 | 3/4 | 2/4 |
| 故障后输入 Token | 1,747,457 | 1,353,987 |
| 每对平均故障后输入 Token | 436,864.25 | 338,496.75 |
| Harness 执行时长合计 | 1,623.40 秒 | 1,612.09 秒 |
| 到首次模型准入的中位时间 | 2.286 秒 | 97.759 秒 |

共享前缀为三次模型请求，恢复组采用累计用量减去前缀，重启组采用自身完整用量。四对实际产生 **175 次请求**，包含四个共享前缀的十二次请求；八条最终轨迹的用量全部完整。两组故障后的请求上限均为 21 次，工具额度依据前缀已用数量派生。详细预算、墙钟边界及执行顺序见[冻结协议](../live-protocol.json)。

两道任务为此前使用过的开发任务。每对固定先执行恢复、再执行重启；冷评分使用相同独立验证方式。恢复始终沿用原绝对截止时间，重启获得从检查点派生的剩余时长。每条轨迹的模型结果、失败和用量均进入统计。

## 四对明细

“墙钟节省”为重启减去恢复的 Harness 执行时长，正值表示恢复更快。环境重建计时从恢复 API 调用前开始，到源码与运行环境恢复完成；首次模型准入单独计时。

| 配对 | 任务 | 恢复 / 重启通过 | 故障后输入：恢复 / 重启 | 重建秒数 | 墙钟节省秒数 |
| --- | --- | --- | ---: | ---: | ---: |
| pair-01-r1 | fmt-3732 | 是 / 是 | 395,629 / 329,095 | 1.609 | +110.12 |
| pair-01-r2 | fmt-3732 | 是 / 否 | 446,236 / 374,067 | 1.527 | −45.21 |
| pair-02-r1 | fmt-3727 | 否 / 否 | 498,792 / 342,652 | 2.663 | +53.80 |
| pair-02-r2 | fmt-3727 | 是 / 是 | 406,800 / 308,173 | 2.109 | −130.01 |

重建范围为 **1.527–2.663 秒**，首次模型准入范围为 **1.803–3.167 秒**。恢复组的故障后输入在四对中均更高；墙钟时间为两对较快、两对较慢。

## 状态恢复与失败原因

同 Run、原截止时间、事件前缀、累计计数、同一账本、账本前缀、模型步骤上限和工具上限八项检查均为 **4/4**。离线复核同时检查 SQLite 完整性、事件投影、检查点与附件哈希、前缀的三次供应方响应和完整冷评分。

| 配对 / 分组 | 停止原因 | 冷评分 | 构建日志中的失败点 |
| --- | --- | --- | --- |
| pair-01-r2 / restart | REQUEST_BUDGET_EXHAUSTED | ORACLE_BUILD_FAILED | `std::ratio` 实例化触发 `overflow in multiplication` 静态断言 |
| pair-02-r1 / resume | REQUEST_BUDGET_EXHAUSTED | ORACLE_BUILD_FAILED | 浮点 `duration` 转换到 `seconds` 时缺少匹配的 `safe_duration_cast` |
| pair-02-r1 / restart | REQUEST_BUDGET_EXHAUSTED | ORACLE_BUILD_FAILED | `safe_duration_cast` 的浮点时长转换模板匹配失败 |

失败原文和候选补丁见[逐条失败证据](failures.md)。`REQUEST_BUDGET_EXHAUSTED` 记录执行停止原因；成功组也包含预算用满但最终补丁通过冷评分的轨迹。

## 原始证据与复算

[Actions Run 42342132692](https://github.com/lilong555/ReproPatch/actions/runs/42342132692) 已完成，执行源码为 [`d15c9d8`](https://github.com/lilong555/ReproPatch/tree/d15c9d837cdb227cfd3bd93154580fd9b05fa85a)。四个原始包的 ZIP 摘要和 tar 逐文件清单全部通过，175 次请求的原始正文、响应与 SQLite 账本一致。

- [原始 CI 结果](results.json)、[独立复算汇总](summary.json)、[逐对核验与逐请求用量](attempts.jsonl)
- [完整轨迹下载入口](trajectories.md)、[归档索引与 SHA-256](artifacts.json)、[下载校验回执](downloads.json)
- [原始构建失败日志及补丁](failures.md)、[历史前缀成本核算](../history/summary.json)

下载每个配对包并解压到 `RAW_ROOT/recovery-raw-42342132692-pair-XX-rY/`，保留 ZIP、tar 相关文件和 `downloads.json` 中对应的 `download.json`。Python 3.12 和项目依赖下执行：

```bash
PYTHONPATH=src:scripts python scripts/audit_completed_usage.py recovery \
  --results benchmarks/recovery-costs-20261107/live/results.json \
  --artifacts benchmarks/recovery-costs-20261107/live/artifacts.json \
  --raw-dir "$RAW_ROOT" \
  --protocol benchmarks/recovery-costs-20261107/live-protocol.json \
  --output /tmp/recovery-live-audit
```

复算仅读取归档、SQLite 与供应方响应，模型调用为零。历史第 12 步前缀占比 48.17% 描述已发生的前置成本；本批实际净节省以四对新鲜轨迹的观测结果计量。
