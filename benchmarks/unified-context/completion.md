# 上游故障复验与中断候选冷评分

本批包含 7 次独立修复复验及 2 次零模型冷评分。正式请求沿用 2,520 次总额度，已使用 1,895 次，本批最多使用 168 次，累计上限为 2,063 次。模型为 `gpt-6-luna`，推理强度为 `max`，单请求总期限为 180 秒。

| 任务 | 实验臂 | 原始上游状态 | 本批操作 |
| --- | --- | --- | --- |
| fmt-1361 | Shell-only | HTTP 502 | 独立复验一次 |
| fmt-1361 | mini | HTTP 524 | 独立复验一次 |
| fmt-2292 | Full | HTTP 524 | 独立复验一次 |
| fmt-2292 | 关闭自检 | HTTP 524 | 独立复验一次 |
| fmt-2292 | Shell-only | HTTP 524 | 独立复验一次 |
| fmt-3727 | mini | HTTP 524 | 独立复验一次 |
| fmt-493 | mini | HTTP 524 | 独立复验一次 |

| 中断任务 | 实验臂 | 已发请求 | 冻结候选 | 本批操作 |
| --- | --- | ---: | --- | --- |
| fmt-3158 | Full | 20 | Checkpoint 20 | 独立冷 Oracle |
| fmt-1171 | Shell-only | 24 | Checkpoint 24 | 独立冷 Oracle |

复验使用原任务、prepared commit、O3 Docker 镜像及独立冷 Oracle，每次最多 24 次模型请求，自动重试为 0。每个原始故障对应独立 Attempt ID，首轮结果与原始请求账本继续保留，复验结果单独呈现。

中断候选按已归档 Checkpoint 的补丁 SHA-256 固定。原始 `USER_CANCELLED` 状态继续保留，冷评分记录补丁质量及完整构建测试证据，评分阶段模型请求为 0。

[冻结协议](../context-revalidation-protocol.json)包含候选身份、归档摘要、请求血缘、执行文件摘要、CI 门禁和确定的运行顺序。准入前逐项核验原始账本的 HTTP 502/524、请求与响应 SHA-256、已发请求数和候选 Checkpoint；上游修复作业并发为 2，零模型评分作业并发为 2。

执行命令：

```bash
gh workflow run formal-benchmark.yml \
  --repo lilong555/ReproPatch \
  --ref feat/unified-context-compaction \
  -f authorization=2520 \
  -f revalidation=true \
  -f recovery=false \
  -f inline_calibration=false
```
