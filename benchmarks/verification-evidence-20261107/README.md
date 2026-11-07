# 最终补丁探索检查与独立冷评分

完整审计 190 条冻结轨迹。153 条最终补丁的最近一次结构化自检有源码身份和实际 CTest XML 支撑，通过该检查后，独立冷评分拒绝 0 条；观测误接受比例为 0.00%。

该比例使用“同一最终补丁最近自检通过且冷评分可判定”作为分母。各运行的完整状态、未检查和失败记录均保留。

## 完整分母

| 指标 | 数量 |
| --- | ---: |
| 预定轨迹 | 190 |
| 候选补丁可用 | 190 |
| 候选多份哈希与评分身份一致 | 190 |
| 最终源码清单身份核验 | 190 |
| 独立冷评分身份核验 | 190 |
| 最终补丁有结构化探索检查 | 163 |
| 最近探索检查通过且冷评分可判定 | 153 |
| 探索通过后独立冷评分拒绝 | 0 |

## 分组结果

| 组别 | 全部轨迹 | 最终补丁有检查 | 自检通过分母 | 冷评分拒绝 | 比例 |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 38 | 30 | 30 | 0 | 0.00% |
| combined | 38 | 33 | 29 | 0 | 0.00% |
| dedup | 38 | 35 | 33 | 0 | 0.00% |
| diagnostics | 38 | 31 | 29 | 0 | 0.00% |
| state | 38 | 34 | 32 | 0 | 0.00% |

## 最终自检状态

| 状态 | 轨迹数 | 冷评分通过 | 冷评分失败 |
| --- | ---: | ---: | ---: |
| passed | 153 | 153 | 0 |
| final_patch_not_tested | 13 | 5 | 8 |
| no_exploration_check | 14 | 2 | 12 |
| tests_failed | 9 | 0 | 9 |
| build_failed | 1 | 0 | 1 |

## 不一致记录

| 轨迹 | 任务 / 组别 | 探索事件 | 冷评分 | 可见测试同名失败 | 新增测试失败 | 原始轨迹 |
| --- | --- | --- | --- | --- | --- | --- |
| 无观测不一致 | — | — | — | — | — | — |

## 口径与复算

审计读取工具调用结束事件，核验原始回执、完整评价、源码清单和 CTest XML 的 SHA-256。探索检查以实际非空测试及其退出状态为据。最终补丁通过工作区导出、worker、score 和 oracle 四处候选哈希连接；源码清单同时保留文件模式。最后检查之后的源码变化在最终源码匹配中自然剔出，相关运行列为最终补丁尚未检查。

独立冷评分固定同一候选补丁与镜像，使用新构建目录并关闭编译缓存。F2P/P2P 集合及每项失败保留在记录中。同名测试失败先作为不一致观察记录；构建残留、测试修改和波动归因需要额外复现证据。

`run_command(reproduce)` 运行 F2P，`run_command(verify)` 运行 F2P/P2P；两者的实际测试范围逐项保存。纯编译成功、空测试、自述成功均有各自状态。主表使用严格源码哈希层；所有证据错误保留具体原因。

```bash
PYTHONPATH=src:scripts python scripts/audit_false_positives.py \
  --raw-dir /path/to/context-raw \
  --results benchmarks/context-ablation/full/results.json \
  --artifacts benchmarks/context-ablation/full/artifacts.json \
  --output-dir /tmp/final-patch-audit
```

`attempts.jsonl` 保存完整逐条证据，`attempts.csv` 用于筛选，`summary.json` 保存分组统计及输入哈希。原始归档来自 [Actions 42219312911](https://github.com/lilong555/ReproPatch/actions/runs/42219312911)，下载入口逐条保留。

[冻结分析源码](analysis-source/audit_false_positives.py)对应 `summary.json` 的分析脚本 SHA-256，可结合完整原始归档复算。

已有测试篡改与回归构造案例见 [运行时证据](../runtime-evidence-20261106/report.md)。这些主动注入的案例单独报告；本页统计来自冻结队列自然产生的最终候选。

## 旧构建产物污染注入

[真实 Docker 注入报告](injected/README.md)覆盖一个旧二进制污染场景、固定三次重复：旧二进制运行相同四项测试全部通过，生产独立冷验收三次均判定 `REGRESSION_FAILED`。完整源码、补丁、二进制、CTest XML、SQLite 轨迹与离线复核结果随报告保存。该场景的重复检出为 3/3。
