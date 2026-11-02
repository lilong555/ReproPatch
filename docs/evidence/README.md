# 验收证据

Git 保存关键摘要、源码清单和少量解析器测试样本，完整原始日志、SQLite、JUnit 与模型附件按 SHA-256 归档。
[v0.4.0 工程摘要](v0.4.0/summary.json)关联被测源码、Core/SDK/Docker、
安装版三场景和 core-only 正反补丁验收。
[v0.4.0 Release](https://github.com/lilong555/ReproPatch/releases/tag/v0.4.0)
提供长期原件 `ReproPatch-engineering-v0.4.0.zip`、精确安装包、
`release-manifest.json` 与 `SHA256SUMS`。

下载本版附件后，在下载目录执行：

```bash
sha256sum -c SHA256SUMS
unzip ReproPatch-engineering-v0.4.0.zip -d engineering-v0.4.0
```

工程包内的 `evidence-manifest.json` 记录各原文件的大小和 SHA-256。
三场景与核心正反例保留独立 Run；报告重建后的派生索引按归档时的实际字节登记。
发布清单分别记录被测源码 Commit 与交付 tag，描述二者涉及的文档与证据范围。

## 历史证据

[附件索引](archive-index.json)记录历史归档的原始发布身份，
[v1/v2 证据清单](../../benchmarks/generalization-evidence.json)记录对应运行、资格、
用量和本地验证的文件数、哈希与发布状态。

[0.3.0 验证摘要](v0.3.0/summary.json)对应 338 核心、154 SDK、22 Docker 场景。
[v2 六次对照](../../benchmarks/generalization-final-results.md)包含全部首跑的原始请求、SSE、工具轨迹、候选与独立原生评分。
[v1 封存](../../benchmarks/generalization-v1-results.md)单列 110 次历史请求，
[累计账本审计](../../benchmarks/model-usage-audit.json)按请求 ID 去重并逐条核对正文哈希。

证据包提供冻结执行源码、两项 prepared bundle 和本机路径恢复工具。
[零模型复核命令](../../benchmarks/README.md#零模型复核)使用同一镜像重新运行独立验收。
Luna max 的客户端请求检查属于本地响应夹具，其模型费用计数保持 0。

下载附件和同名 `.sha256` 后，在项目根目录执行：

```bash
sha256sum -c ReproPatch-evidence-through-0.3.0rc1.tar.gz.sha256
tar -xzf ReproPatch-evidence-through-0.3.0rc1.tar.gz
```

附件中的 `evidence-manifest.json` 为每个文件记录路径、原始大小和 SHA-256。
历史文档中的原始证据路径对应解压后的路径；摘要引用的日志与附件也按此方式复核。
故意损坏的负例保持实际原始字节和不可核查结论。
契约测试数量与真实工程修复任务数量分别统计。
