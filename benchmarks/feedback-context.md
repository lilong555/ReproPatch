# 反馈与上下文

`run_command` 返回与初始基线共用的结构化模型视图，包含全部测试状态、配置/编译/发现状态、
失败命令双流预览、清理结果及完整证据引用。通过命令的日志、JUnit 和测试清单不重复放入反馈，
仍保存在原始 Run 中。配置、编译或发现失败时，即使尚无测试命令，也保留失败诊断。
SDK 原生历史与 Checkpoint 不裁剪，256 KiB 的输入边界保持有效。

## 历史数据的离线边界检查

使用已公开的 rc2 Catch2-2723 第九次原生输入、原始响应和自检结果，
通过固定 SDK 的公开 Runner、ScriptedModel 和 input filter 检查两种反馈。
ScriptedModel 返回同一已保存响应；工具只读已有证据，不重跑测试、不执行容器、不请求模型。

| 观察 | 原始反馈 | 当前视图 |
| --- | --- | --- |
| 工具 JSON 字节 | 385,200 | 40,317 |
| 后续完整原生输入字节 | 596,554 | 218,955 |
| 输入上限 | 262,144 | 262,144 |
| 下一次离线模型步骤 | 因 `CONTEXT_LIMIT` 未开始 | 成功到达 |
| 先前原生历史 | 完整保留 | 完整保留 |
| 测试观察 | 69 | 69 |
| 失败命令预览 | 2 | 2 |

结果见 [摘要](feedback-context.json)，实现与检查脚本身份见 [源码清单](feedback-source-manifest.json)。
本检查不判断新补丁正确性，也不增加真实 Benchmark 的尝试数或成功数。
所有失败输出也可能超过输入额度，此时继续明确停止，不隐式截断原生历史。

## 复核

从[首次两题数据附件](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-pilot-first-two-2026-10-21)
解压原始材料，并使用本版本固定 `agent` 依赖运行：

```bash
python scripts/check_feedback_context.py \
  --run-dir paid-pilot/catch2723-repropatch/runs/0b8f441ebe4d4ea8b1999025287e6995 \
  --output feedback-check
```

输出目录须不存在；历史 Run 只读打开，不恢复执行。检查期间禁止 socket 连接。
新生成的输入和定向测试原始结果保存在本产品版本的 Release Assets，Git 只保留摘要与源码清单。
