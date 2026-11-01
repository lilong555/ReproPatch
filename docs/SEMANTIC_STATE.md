# C++ 结构证据状态

Full 可以使用 Tree-sitter C++ 结构索引和持久修复状态，在授权源码中查找定义、语法引用与包含关系。每条查询保留文件位置和源码 SHA；修改使相关索引失效。模型可按工具 ID 读取先前可见的完整诊断和工具输出。

`query_code` 提供 `definitions`、`references`、`includes`、`state`、`evidence` 五种查询。结构关系使用语法解析精度标注；查询返回解析错误、分页位置和截断信息。

初始任务合同与基线观察分别保存，压缩后保留当前修改、可见检查结果及证据索引。Checkpoint 保存修复状态，恢复时核对工具 schema 并按需重建解析缓存。

```bash
python -m pip install -e '.[agent,semantic]'
repropatch run task.yaml --engine sdk --model gpt-6-luna \
  --allow-paid-model --semantic-state --candidate-only
```

Task v2 中 `budget.max_steps: null` 和 `budget.max_tool_calls: null` 表示开放累计次数。请求、摘要、工具调用和未知用量持续计量，单请求及运行期限由冻结任务声明。

三臂实验通过 `scripts/freeze_semantic_native.py` 固定任务、环境、执行源码和 CI 身份。Full 启用结构证据状态；mini 使用固定上游的原生历史和输出处理；Codex 使用固定 CLI 的原生压缩提示与触发策略。CPA 请求并发由共享 Actions 并发组和三个串行请求 Worker 控制。

实验主指标是独立冷 Oracle 通过数，同时报告候选交付、结构检索、上下文故障、请求与 Token、自检和修复耗时。全部首次尝试和恢复身份保留。
