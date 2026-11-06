# 公开复算入口

本目录提供可移植输入、只读审计命令和发布文件清单。实验数字见 [report.md](report.md)；首批3次观察器故障和第二批3次恢复结果分别保留。

## 一条命令

在仓库根目录，使用已安装项目 `agent` 依赖的 Python 3.12 环境：

```bash
python scripts/benchmark_runtime_evidence.py audit \
  --package benchmarks/runtime-evidence-20261106/public-inputs \
  --output /tmp/repropatch-public-audit
```

输出目录须为新目录。命令离线核对文件哈希、95份历史SQLite账本、6份长输出投影，以及9个新Run的SQLite和附件完整性。解压与复算结果写入输出目录，原始输入保持只读；无需Docker、API密钥或历史私有目录。

依赖尚未安装时，可在独立虚拟环境中安装包内固定源码：

```bash
python -m pip install './benchmarks/runtime-evidence-20261106/public-inputs/source[agent]'
```

## 输入与身份

| 文件 | 内容 |
|---|---|
| [audit-index.json](public-inputs/audit-index.json) | 95个所选attempt；归档路径相对于索引所在目录 |
| `public-inputs/archives/*.tar.gz` | 原始SQLite、worker结果、provider请求/响应、原生工具结果和事件的选定成员 |
| [archive-members.json](public-inputs/archive-members.json) | 每个选定原始成员的路径、字节数和SHA256 |
| [runtime-state.tar.gz](public-inputs/runtime-state.tar.gz) | 9个新Run的完整状态，含原始SQLite、事件、checkpoint、候选、JUnit和日志 |
| [runtime-state-members.json](public-inputs/runtime-state-members.json) | 完整状态包内1,292个文件的逐文件SHA256 |
| `public-inputs/source/` | 固定公开commit的生产源码及复算所需冻结输入，共37个文件 |
| [input-manifest.json](public-inputs/input-manifest.json) | 包内输入与源码哈希；核心30个文件与Git对象核对 |
| [portable-verification.json](portable-verification.json) | 从另一目录运行审计的验证结果 |

95份历史输入归档共216,245,551字节；新Run状态包764,787字节。索引同时保留重打包SHA和上游完整归档SHA，选定成员字节保持原样。公开包覆盖最终95条所选轨迹；105槽和118次累计收费历史的摘要保存在冻结 `final-results.json` 中。

历史provider请求中的不透明状态按原件保留。凭据模式检查扫描4,864个历史成员，命中0，见 [credential-scan.json](credential-scan.json)。

## 验证结果

异目录审计核对176项输入哈希；95/95历史账本闭合，1,764次实际请求、11次未发出预发送记录，输入38,606,124、输出866,919 Token。6/6投影回读与协议检查通过，9/9新Run的SQLite完整性及生产证据检查通过。

新增定向测试14/14通过，见 [portable-tests.xml](portable-tests.xml)。测试和包审计均为工程核验，模型新增请求为0。

## Git 与资源

[publication-files.txt](publication-files.txt) 使用仓库相对路径，只列本轮脚本、测试及本实验目录的公开文件；主线程可在仓库根使用：

```bash
git add --pathspec-from-file=benchmarks/runtime-evidence-20261106/publication-files.txt
```

本目录 `.gitignore` 排除展开态 `runs/`、`runs2/`，完整原件通过显式收录的 `runtime-state.tar.gz` 发布，避免嵌套fixture Git仓库成为gitlink。当前公开文件哈希清单为 [manifest.json](manifest.json)；首轮交付清单另存为 `initial-delivery-manifest.json`。

Azure专用目录与镜像在备份逐文件核对后清理，见 [azure-backup-verification.json](azure-backup-verification.json) 和 [azure-cleanup-final.json](azure-cleanup-final.json)。共享容器及SSH control socket保持原样。本地固定源码快照 `/home/li/.cache/repropatch-runtime-evidence-20261106/public` 保留供协作使用。
