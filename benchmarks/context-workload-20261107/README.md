# C++ 上下文优化候选负载

固定版 Multi-SWE-bench Flash 包含 300 道任务，其中 C++ 为 40 道。其 C++ 子集与当前 ReproPatch 的 19 道 fmt 开发任务重合 9 道，另有 31 道候选，其中 22 道来自其他仓库。清单核验使用零次模型请求，构建资格与冷验收适配单独登记。

| 仓库 | Flash C++ 任务 | 与当前 19 题重合 | 额外候选 |
| --- | ---: | ---: | ---: |
| fmtlib/fmt | 18 | 9 | 9 |
| catchorg/Catch2 | 12 | 0 | 12 |
| simdjson/simdjson | 6 | 0 | 6 |
| nlohmann/json | 4 | 0 | 4 |
| 合计 | 40 | 9 | 31 |

[flash-cpp-manifest.json](flash-cpp-manifest.json) 保存全部 40 道题及 base commit；[inventory.json](inventory.json) 保存与现有合同的逐题交集、差集及输入摘要。

数据集为 `ByteDance-Seed/Multi-SWE-bench-flash`，版本 `b0485dbebaf8a1317ebf140e80e6fc6c02d3502b`。[固定 JSONL 文件](https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-bench-flash/resolve/b0485dbebaf8a1317ebf140e80e6fc6c02d3502b/multi_swe_bench_flash.jsonl)的 SHA-256 为 `48d6d02cc976a71a06b494cc60581d92e82c06c2793c0d412c52c63e6956bebe`。

## 实验顺序

现有 190 条轨迹的机会分析优先检验提前处理文件回执的价值。下一独立实验比较原始策略、提前选择性提取、提前选择性提取加状态摘要，三组共享任务、模型、工具、预算与独立评分。辅助提取和摘要请求、原文恢复请求全部计入用量，并报告每次干预后实际发生的修复请求数。

文件回执在后续两个完整模型步骤完成后进入候选检查。逐行重复和成功编辑锚点支持局部裁剪；其余内容采用保留路径、行号、源码身份与原文入口的受约束提取。最近错误、测试状态及尚未验证的改动进入保留信息集。完整文件和短错误保留各自证据记录。

跨仓库阶段记录全部 40 道题的构建资格、失败原因和准备开销，再按事先固定的资格规则确定可执行任务。任务使用自然结束条件，持续时间来自真实定位、修复和验证过程。当前清单仅核对与 19 题合同的重合关系；各任务的其他历史使用记录在执行登记时一并关联。

[论文依据与计量口径](../../docs/CONTEXT_RESEARCH.md) · [完整历史模型结果](../context-ablation/full/README.md)
