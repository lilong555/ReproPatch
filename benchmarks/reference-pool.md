# C++ 参考任务池

固定数据 revision、原始镜像内容身份、evaluator commit 与实际结果见
[reference-pool.json](reference-pool.json)。总任务分母保持 129。
本页全部是参考补丁与适配检查，不是 Agent 修复成绩；模型请求和费用均为零。

| Multi-SWE-bench 实例 | 原始官方镜像参考复核 | Task v2 参考验收 |
| --- | --- | --- |
| Catch2-2723 | 2 F2P、100 P2P 满足 | 2 F2P、67 CTest P2P，通过 |
| Catch2-2187 | 2 F2P、50 P2P 满足；仅源码参考部分 | 2 F2P、32 CTest P2P，通过 |
| Catch2-1608 | 完整参考补丁通过 | 仅源码参考部分仍缺 ApprovalTests，通过条件不满足 |
| Catch2-1448 | 完整参考补丁通过 | 待审查批准快照与修复范围 |
| Catch2-1422 | 完整参考补丁通过 | 待审查批准快照与修复范围 |

已验证的适配覆盖下界是 **2/129**；其余实例没有全部完成运行审查。
两个合格 Task 都需要环境兼容适配，不计作原始镜像直接兼容 ReproPatch。
不能把剩余 127 个实例记为模型修复失败，也不能将五个完整参考通过写成五个可运行的修复任务。
当前任务池集中于同一仓库，不能支持跨项目整体领先结论。

## Catch2-2187 的冻结输入

原始镜像保留 GCC 7.5；适配镜像提供 CMake/CTest 4.4.4 和 `/usr/bin/sleep` 路径，
移除上游源码历史、参考补丁与测试运行脚本，CPU、内存、用户和网络规则与 2723 一致。
[构建配置](environments/Catch2-2187.Dockerfile) 需要固定 CMake 分发目录。
实际编译器、镜像 ID、prepared commit、任务 hash 与容器删除记录均保存在结构化摘要中。

官方测试补丁固定到 prepared commit，测试源码对两组同样可见。
`catch_test_macros.hpp` 属于官方测试改动，作为受保护文件；允许编辑其他生产 C++ 源码。
参考修复只使用 `catch_run_context.cpp` 的改动，官方原始补丁中的两份文档保留在评测材料中。

[Approval 路径适配](fixtures/Catch2-2187.approval-path.patch) 仅将临时和 unapproved 输出
写入 CTest 的 `/build` 工作目录，批准快照、规范化和比较逻辑保持原样，源码仍然只读。
基线必须出现真实 `Results differed`，只读目录写入异常不能作为该回归的合格复现。
旧编译环境和只读输出路径造成的准备失败保留在原始材料中，模型尝试数不增加。

## 官方复核

使用原始官方镜像、未改写的 `/home/test-run.sh`、固定上游 `Catch2.parse_log` 与 `Report`。
每次新建容器，核对基线 HEAD 和干净工作树，应用参考补丁，保留双流日志并确认删除。
官方脚本与测试补丁的 SHA-256 写入原始输出；源码清单记录上游实际文件身份。

```bash
python scripts/check_multiswe_reference.py \
  --record SINGLE_ORIGINAL_DATASET_RECORD.json \
  --candidate PREPARED/reference.patch \
  --image sha256:917e179081a8dc28fc21b50c4a9574ec4a1893b1599a5607916fa6a0eb308367 \
  --evaluator-source FIXED_EVALUATOR_CHECKOUT \
  --output NEW_ORACLE_DIRECTORY
```

该命令在独立 oracle Python 环境运行，依赖固定上游 evaluator 的解析依赖。
仅接受已审查五个实例的完整参考或源码参考部分，不调用模型、不改写官方判定算法。
普通模型候选的批次调度与评分仍待 Harbor 产物桥接，不能把此命令称为完整 Benchmark Runner。

接受条件同时要求：执行退出 0、容器删除已确认、`Report.valid`，以及全部固定
F2P/P2P/S2P/N2P 组成员满足。1608 的仅源码参考部分有 `Report.valid=true`，
但退出 8 且缺少必需的 ApprovalTests，最终明确拒绝。
该例说明局部有效性不能代替完整任务通过；它不是模型尝试，也不计入 Harness 错误接受率。

完整原始材料通过结构化摘要链接的带哈希 Release Assets 提供；Git 仅保存摘要、固定配置与适配文件。
