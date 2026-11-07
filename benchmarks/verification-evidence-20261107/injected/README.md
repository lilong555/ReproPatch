# 旧构建产物污染与生产独立冷验收

一个 C++ 旧二进制污染场景固定重复 3 次：源码引入空输入回归后，旧二进制运行相同的 4 项 CTest 全部通过；生产 `Harness(patch_file=...)` 在独立工作树和新容器中重编译，3 次均返回 `REJECTED / REGRESSION_FAILED`。全部 14 项证据检查通过，新增模型请求为 0。

## 实测结果

| 重复 | 旧二进制 CTest | 变更后源码编译 | 重编译后 CTest | 生产冷验收 | 证据检查 |
| --- | --- | --- | --- | --- | --- |
| 1 | 4/4 通过 | 成功 | 3/4 通过，空输入失败 | REGRESSION_FAILED | 14/14 |
| 2 | 4/4 通过 | 成功 | 3/4 通过，空输入失败 | REGRESSION_FAILED | 14/14 |
| 3 | 4/4 通过 | 成功 | 3/4 通过，空输入失败 | REGRESSION_FAILED | 14/14 |

场景覆盖数为 1，重复检出为 3/3。自然轨迹的观测误接受结果为 [0/153](../README.md)，两个分母分别保存。

## 冻结场景

负载使用生产演示资源 `src/repropatch/demo_assets/cpp-bugs`。基线在全负样本下错误返回 0。先修复该问题并编译正确二进制，然后仅将空输入分支从 `return std::nullopt` 改为 `return 0`，保持 `CMakeLists.txt` 和测试源码原样。

旧二进制检查在变更后的源码旁运行，记录源码清单、二进制哈希和实际 CTest XML。随后在同一探索容器中强制重编译，再运行同一组测试。最终候选通过生产 `Worktree.freeze_candidate` 冻结，交由生产 `Harness` 复现基线并独立验收；故障测试 `negative_values` 修复通过，回归测试 `empty_values` 失败。

三次运行使用同一冻结补丁和源码身份：

| 对象 | SHA-256 / 标识 |
| --- | --- |
| Harness 源码提交 | `1841f6e97ced42d9c914ac494b0e5ab8a0c388f5` |
| 冻结补丁 | `4e1b21918db8e478880c173952d23abfc98fc8065af9aff1a380b00201784f86` |
| 最终源码清单 | `b19b71907976654b790c3f8a3dfcb9e7695e0ae0636e616355fc168e77c9264c` |
| Docker 镜像 | `sha256:500d13919a823b0673d645dfd22b242d6b4bf1069fab2b4efade2a5a27de2e41` |

## 证据核验

运行时逐项检查旧二进制保持一致、新二进制发生变化、受保护测试输入保持一致、最终源码与冷验收源码一致、候选补丁逐字节一致、冷验收关闭编译缓存、容器身份独立及清理确认。正式运行结束后，离线核验完整源码、实际二进制、命令双流日志、CTest XML、SQLite 持久化结局和零模型调用记录，3/3 通过。

| 文件 | 内容 |
| --- | --- |
| [summary.json](summary.json) | 正式三次运行、逐项判定和完整独立验收结果 |
| [protocol.json](protocol.json) | 预登记场景、重复数、36 个生产源文件哈希和测量脚本哈希 |
| [offline-verification.json](offline-verification.json) | 下载后的独立离线复核结果 |
| [smoke-summary.json](smoke-summary.json) | 真实 Docker 冒烟结果 |
| [raw-evidence.tar.gz](raw-evidence.tar.gz) | 完整原始产物，1,254,863 字节、882 个文件 |
| [raw-evidence.tar.gz.sha256](raw-evidence.tar.gz.sha256) | 原始归档 SHA-256 |
| [raw-manifest.json](raw-manifest.json) | 归档内各文件大小与 SHA-256 |
| [Dockerfile](Dockerfile) / [image.json](image.json) | 固定基础镜像与实际镜像身份 |

原始包的 `formal/` 保存正式协议及 3 次运行；`smoke*/` 保存预检记录。各次运行均保留 `events.sqlite3`、冻结 Patch、源码清单、命令日志、原始测试 XML、旧/新二进制和生产报告。

## 复算与复现

离线复算使用原始归档，执行源码、日志和判决核验：

```bash
mkdir -p /tmp/repropatch-stale-evidence
tar -xzf benchmarks/verification-evidence-20261107/injected/raw-evidence.tar.gz \
  -C /tmp/repropatch-stale-evidence
PYTHONPATH=src:scripts python scripts/verify_stale_build_evidence.py \
  --evidence-dir /tmp/repropatch-stale-evidence/formal \
  --output /tmp/repropatch-stale-offline.json
```

实际 Docker 测量使用全新输出目录，固定运行三次：

```bash
docker build -t repropatch-fp-evidence:local \
  -f benchmarks/verification-evidence-20261107/injected/Dockerfile .
PYTHONPATH=src python scripts/benchmark_stale_build_evidence.py \
  --image repropatch-fp-evidence:local \
  --source-commit "$(git rev-parse HEAD)" \
  --output-dir /tmp/repropatch-stale-build \
  --repeats 3
```

定向证据语义测试：

```bash
PYTHONPATH=src:scripts python -m pytest -q \
  tests/test_false_positive_audit.py tests/test_stale_build_evidence.py
```

本次结果为 28 项通过。
