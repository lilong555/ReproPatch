# 定位三组预检

固定任务 `fmtlib__fmt-2310`，A/B/C 各运行一次，共 72 次模型请求。三条轨迹的请求用量、实际源码曝光与独立评分记录完整，满足后续完整实验的接线检查条件。三条候选的最终冷评分均失败。

| 接口 | 冷评分 | 输入 Token | 输出 Token | 首次命中参考区间的工具调用 |
| --- | --- | ---: | ---: | ---: |
| A · native | 空候选 | 328,332 | 3,095 | 4 |
| B · bounded | 测试失败 | 498,691 | 10,573 | 3 |
| C · feedback | 测试失败 | 433,523 | 10,005 | 4 |

每条运行均用尽 24 次模型请求预算。该预检仅包含一个任务的一次重复；19 题配对结果见[完整实验](../full/README.md)。

源码为 `5b4a2b1efd609a3384aeca3757d3a8c84dcffb3b`，运行入口为 [42242783788](https://github.com/lilong555/ReproPatch/actions/runs/42242783788)。[results.json](results.json)和[summary.md](summary.md)保存原始汇总，[artifacts.json](artifacts.json)提供三个原始轨迹、三个评分归档、冻结计划及汇总的下载入口。
