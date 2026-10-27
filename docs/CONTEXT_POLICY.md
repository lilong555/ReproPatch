# 上下文计量与压缩合同

已完成的[五组配置复核](../benchmarks/unified-context/results.md)归集21题、105个槽位。19题完整配对结果、3次人工中断、全部收费尝试与校准分别保存；模型总期限保持180秒。

ReproPatch、mini-SWE-agent 和 Codex CLI 共用版本化上下文策略。`ContextPolicy` 定义 Token 窗口、压缩触发与目标水位、输出预留、物理传输上限和请求额度；冻结实验协议保存完整策略。历史批次使用 `legacy-256k`，统一压缩批次使用 `v1.0-unified-compaction`。

每次输入估算以供应商上次真实 `input_tokens`、被保留响应的 `output_tokens` 及新增明文工具结果为基准。明文增量采用确定性的 UTF-8 字节数除以 3 向上取整；`encrypted_content` 单独统计物理字节，通过历史真实 Usage 归因。历史替换后按保留项和摘要重置，下一次供应商响应重新建立真实 Usage 锚点。

`LocalUsageLedger` 先提交完整正文、SHA-256、用途、序号与估算结果，再进行准入。请求分为 `repair`、`compact` 和 `retry`；三者之和受每个 Attempt 的静态额度约束。本地拒绝单列，`issued_requests` 记录已准入并交给传输的请求。`cached_input_tokens` 属于输入用量，`reasoning_tokens` 属于输出用量，累计总量各计算一次。

ReproPatch 在整批工具完成、结果归档且资源静止后压缩。摘要只引用当前可见信息，包含目标与范围、定位、修改、反馈、失败方向、下一步和证据引用。旧 Runner 在安全边界结束，公开 SDK 入口装入固定头部、摘要和最近完整工具轮次。SQLite Checkpoint 引用压缩状态与原生下一轮输入，保存累计预算和原始期限。

mini 适配器直接替换固定 `DefaultAgent` 的公开 `messages` 列表。原始历史保存为独立证据，上游源码保持固定提交。超大工具输出完整归档，模型收到头尾及 `/build` 日志引用。

Codex CLI 固定为 `0.163.0`，显式设置 `model_context_window` 和 `model_auto_compact_token_limit`，使用自定义 provider 的本地摘要路径。摘要仍经 `/v1/responses` 计量。代理保存完整 SSE、结算 Usage、执行整批工具准入，然后转发。首字节、流空闲和总请求期限分别记录，结果快照在代理处理器结算后生成。[固定源码](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/compact.rs)

停止原因与 Oracle 结果分别记录。传输上限返回 HTTP 413，请求额度和本地上下文额度返回 400，真实供应商限流保留 429，模型总期限返回 504。压缩失败时冻结已有候选，冷 Oracle 继续独立评分。

离线门禁覆盖三种 ReproPatch 模式、mini 适配、固定 Codex 原生摘要、不透明状态、完整工具配对、24 次请求连续计数、失败候选、Checkpoint 恢复及 Full 隐藏拒绝。全量批次内置完整 CI 和最多 12 次端点校准，门禁通过后自动执行 105 次修复尝试，正式请求上限为 2520。可选四题 Pilot 工具保留 480 次额度，本次直接全量批次使用 CI 与校准门禁。

云端校准采用公共窗口 128,000 Token、触发水位 48,000 Token、目标水位 21,600 Token，正文上限为 2 MiB。窗口值由校准中供应商实际接受的输入和输出确认。触发水位为 Codex 固定指令与工具定义预留空间，并覆盖历史长轨迹区间。每次尝试共用 24 次上游额度和原批次的 48 次工具额度，修复与摘要共同计费计数。

可选 Pilot 在四道固定题上检查全部二十次冷评分和用量，并要求三类执行器各出现真实的摘要后工具执行；逐组报告实际触发次数。正式批次冻结执行文件指纹和上下文参数，每题五组的调度顺序提前固定。协议文件、执行源码、CI 和前置阶段归档分别记录哈希。

历史审计覆盖 105 次尝试，确认 32 次受到旧传输阈值影响，其中 16 次的候选通过冷 Oracle。[逐次审计](evidence/context-audit-2026-10-26/audit.csv)和[离线拒绝回放](evidence/context-audit-2026-10-26/replay.json)保存原始分类、拒绝层、载荷大小与 Usage 锚点。

```bash
pytest -m 'not docker' tests/test_context_compaction.py tests/test_context_campaign.py
python scripts/audit_context_history.py \
  --source .repropatch/context-audit-20261026/artifacts \
  --output .repropatch/context-audit-20261026/report
python scripts/check_codex_compaction.py \
  --binary /path/to/codex-0.163.0 \
  --output .repropatch/context-gates/codex-native
python scripts/check_mini_compaction.py \
  --mini-source /path/to/mini-at-04d809c \
  --output .repropatch/context-gates/mini-native
```

模型上下文与传输载荷分别度量；供应商会在内存中处理回传的不透明推理项。公开 API 行为参考 [Reasoning models](https://developers.openai.com/api/docs/guides/reasoning)，CPA 的有效窗口和传输能力由独立校准记录确定。
