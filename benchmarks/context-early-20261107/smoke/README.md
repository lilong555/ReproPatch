# 提前压缩预检结果

固定任务 `fmtlib__fmt-2070` 的三组运行均通过独立冷验收，三条原始轨迹、46 次供应方响应和 SQLite 用量均核验通过。预检使用正式实验的相同源码与协议，结果单独统计。

| 配置 | 冷验收 | 输入 Token | 输出 Token | 模型请求 |
| --- | ---: | ---: | ---: | ---: |
| baseline | 1/1 | 131,104 | 2,022 | 13 |
| early | 1/1 | 116,642 | 5,845 | 13 |
| early_state | 1/1 | 168,937 | 6,107 | 20 |

预检确认两种 early 配置均实际发出辅助提取请求，并保存完整用量与冷评分。正式实验的固定分母为另外的 36 条轨迹，见[正式结果](../full/README.md)。

材料：[Actions Run 42343788196](https://github.com/lilong555/ReproPatch/actions/runs/42343788196)、[原始结果](results.json)、[清单](plan.json)、[冷评分核验](analysis.json)、[逐用途用量](usage-audit/summary.json)、[原始轨迹入口](trajectories.md)、[下载摘要](artifacts.json)、[下载回执](downloads.json)。
