# 真实工具回执的离线上下文投影

四份真实归档共包含 89 条工具回执。使用各自冻结的上下文策略和本目录结果记录的实现，对同一回执分别计算原生输出折叠与诊断投影：原生返回合计 239,884 字节，投影后 205,505 字节，减少 34,379 字节。

| 项目 | 结果 |
| --- | ---: |
| 独立 Run / 工具回执 | 4 / 89 |
| 诊断投影候选 / 实际触发 | 4 / 4 |
| 触发回执的原生 / 投影字节 | 70,207 / 35,828 |
| 单条触发回执的字节减少比例 | 14.65%–70.60% |
| 相同源码及参数的精确去重候选 | 0 |
| 回放中的模型请求 | 0 |

计量对象是按模型工具返回格式离线生成的文本，以 UTF-8 字节统计；原生基线包含 `fold_tool_output`。原始工具结果、完整 stdout/stderr 和源码检查点保持只读。供应方 Token 消耗、模型后续行为及冷验证结果由独立模型批次测量；请求级状态压缩在该工具回执回放的测量范围之外。

## 数据与身份

[results.json](results.json) 保存逐回执原生/投影字节、候选与触发原因、源码检查点、证据哈希、原批次身份及回放实现文件哈希。`archive` 字段是 GitHub artifact 内的相对路径。同一 Run 的相同逻辑证据计一次，冲突证据与不完整的配置身份直接拒绝。

原始输入来自 [Actions 42219312911](https://github.com/lilong555/ReproPatch/actions/runs/42219312911) 的 `trial-001`、`trial-002`、`trial-005`、`trial-006`。原执行源码为 `2597016d80ea47c8bbc06c93598093c307a24ee7`，冻结清单 SHA-256 为 `c182f496b5cd432210d4f6a253f02d45bb4f6aac8fdf175d9cff2482f798cf8a`。

末尾一条编辑回执缺少后续源码检查点，逐行结果将其记为 `missing_source`，该处使用原生返回。归档完整性、冻结配置绑定与各检查点来源分别记录。

## 复算

回放实现固定在 [`b9e6b49aeca8aa46db0e4d74f00daec73bbbe79b`](https://github.com/lilong555/ReproPatch/tree/b9e6b49aeca8aa46db0e4d74f00daec73bbbe79b)。该提交提供审计脚本和被测投影模块，`results.json.audit_source_sha256` 给出逐文件核验值。

安装仓库 `agent` 依赖后创建固定源码工作树、核验文件，再下载输入执行：

```bash
git worktree add --detach .repropatch/trigger-audit-source b9e6b49aeca8aa46db0e4d74f00daec73bbbe79b

jq -r '.audit_source_sha256 | to_entries[] | "\(.value)  .repropatch/trigger-audit-source/\(.key)"' \
  benchmarks/context-ablation/trigger-replay/results.json | sha256sum --check

gh run download 42219312911 --repo lilong555/ReproPatch \
  --pattern 'context-raw-42219312911-trial-00[1256]' \
  --dir .repropatch/context-trigger-inputs

PYTHONPATH=.repropatch/trigger-audit-source/src:.repropatch/trigger-audit-source/scripts \
  python .repropatch/trigger-audit-source/scripts/audit_context_triggers.py \
  --archive .repropatch/context-trigger-inputs/context-raw-42219312911-trial-001/context-attempt.tar.gz \
  --archive .repropatch/context-trigger-inputs/context-raw-42219312911-trial-002/context-attempt.tar.gz \
  --archive .repropatch/context-trigger-inputs/context-raw-42219312911-trial-005/context-attempt.tar.gz \
  --archive .repropatch/context-trigger-inputs/context-raw-42219312911-trial-006/context-attempt.tar.gz \
  --output .repropatch/context-trigger-replay
```

归档按原工作流保留期限提供下载。回放报告写入单独目录，输出路径与输入归档的符号链接、硬链接及路径别名均受保护。跨机器比较逐回执数据、哈希和统计字段，下载目录路径按本机位置记录。
