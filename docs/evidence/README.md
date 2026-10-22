# 验收证据

Git 保存关键摘要、源码清单和少量直接用于解析器测试的 CTest 样本。
完整原始日志、SQLite、JUnit、原生模型附件及运行快照由 GitHub Release Assets 保存。
[附件索引](archive-index.json) 记录下载地址、SHA-256、原始文件数量与大小。
当前[只读契约反馈对照](../../benchmarks/contract-results.md)提供 22 条评分的原始轨迹、
SQLite、公共 Oracle 记录和实际 FMT 工具链镜像。证据包支持独立解压后从账本重算结果。

下载附件和同名 `.sha256` 后，在项目根目录执行：

```bash
sha256sum -c ReproPatch-evidence-through-0.3.0rc1.tar.gz.sha256
tar -xzf ReproPatch-evidence-through-0.3.0rc1.tar.gz
```

附件中的 `evidence-manifest.json` 为每个文件记录路径、原始大小和 SHA-256。
历史文档中的原始证据路径对应解压后的路径；摘要引用的日志与附件也按此方式复核。
故意损坏的负例保持实际原始字节和不可核查结论。
契约测试数量与真实工程修复任务数量分别统计。
