# GitHub Actions C++ 实验

2026-10-25，在 GitHub-hosted Ubuntu Runner 上执行 Docker 资格、构建缓存与并发实验。
21 道明确缺陷中 **21/21 通过 O3 Docker 资格**；本轮模型请求、输入与输出 Token 均为 **0**。

执行源码：`6c6222c5b0a93b6ce09f121db257b00e68297d9b`；[代码 PR](https://github.com/lilong555/ReproPatch/pull/1) 已合入。
[完整 CI](https://github.com/lilong555/ReproPatch/actions/runs/40194625159) 通过 **584 项**：406 Core、155 SDK、23 真实 Docker。

## 固定环境与资格

全部手动批次使用同一共享工具链：

```text
ghcr.io/lilong555/repropatch-benchmark@sha256:c00247e787729d6af3af364ab80cce196d90033832f77f2c1262a6e8f7cf111a
```

镜像 ID：`sha256:e0fd90230315094b7ab52b7655dd09bc8280dbcd0e8b2c65be435c6689ff149b`。GCC 13.3.0、CMake 3.28.3、Ninja 1.11.1、ccache 4.9.1。
容器以非 root 身份运行，网络关闭、源码只读，每题两个构建进程，固定 `-O3 -DNDEBUG`。
每题依次检查原始代码的 F2P/P2P、参考补丁定向 F2P、独立全新构建目录中的完整原生 Oracle。
冷 Oracle 关闭编译缓存，使用原生测试入口。成功后导出完整 Task v2，并校验原始日志和归档清单。

[21 题完整 Run](https://github.com/lilong555/ReproPatch/actions/runs/40194807297) · [逐题 CSV](../benchmarks/actions-scale/cloud-qualification.csv) · [JSON 与哈希](../benchmarks/actions-scale/cloud-results.json)

| 状态 | 数量 |
| --- | ---: |
| QUALIFIED | 21 |

这 21 题来自 2026-10-24 原生预检中的明确缺陷，仓库历史模型尝试审查为无记录。
41 条 HOST_QUALIFIED 记录继续按原始 O0 环境保存；本报告列出的 Docker 资格对应新的固定 O3 环境。
语义审查、资格通过和模型修复分别记录；新的正式 Holdout 与模型首跑尚待冻结协议。

## 同一真实目标的构建 A/B

[构建实验 Run](https://github.com/lilong555/ReproPatch/actions/runs/40194849008) 固定 fmt-4055 的原始测试、参考修复和 format-test 目标。
重复变体各三个样本；计时包括配置、目标构建与目标测试。冷样本使用全新 build 并关闭 ccache，宿主页缓存保留。

| 变体 | 样本 | 中位耗时 |
| --- | ---: | ---: |
| 冷 Make | 3 | 18.362 秒 |
| 冷 Ninja | 3 | 13.268 秒 |
| ccache 首次填充 | 1 | 14.302 秒 |
| 热 ccache + 全新 build | 3 | 0.868 秒 |
| 保留 build、源码未改 | 3 | 0.292 秒 |
| 撤销参考补丁 | 1 | 3.342 秒 |
| 重新应用参考补丁 | 1 | 0.457 秒 |
| 最终独立冷构建 | 1 | 14.082 秒 |

热 ccache 相对冷 Ninja 的目标构建耗时减少 **93.46%**。
撤销修复后构建失败，恢复修复后通过，最终独立冷构建通过；16 次样本的观察均符合预定结果。
本测量描述同一 C++ 目标的重复构建；完整 Agent 的端到端收益保留为后续实验指标。

## GitHub Actions 1 / 2 / 4 Job 对照

三组使用相同四题、相同源码和镜像，每题两个编译进程，各配置运行一次。
四题为 fmt-3727、fmt-3734、fmt-3750、fmt-3819；每组全部通过资格。

| Jobs | 四题结果 | 资格 Job 跨度 | 资格 Job 活动 Runner 分钟 | 全工作流 wall |
| ---: | ---: | ---: | ---: | ---: |
| [1](https://github.com/lilong555/ReproPatch/actions/runs/40194858972) | 4/4 | 1020 秒 | 17.00 | 1042 秒 |
| [2](https://github.com/lilong555/ReproPatch/actions/runs/40194868713) | 4/4 | 524 秒 | 16.95 | 547 秒 |
| [4](https://github.com/lilong555/ReproPatch/actions/runs/40194878862) | 4/4 | 271 秒 | 17.33 | 291 秒 |

资格 Job 跨度从首个资格 Job 开始至最后一个资格 Job 结束，包含输入准备、镜像拉取、资格和归档。
活动 Runner 分钟为 API 记录的各 Job 活动区间之和；计费账单与活动时长分别记录。
每个配置一次；排队、Runner 主机与负载差异随原始记录保存。云端默认并发继续为两个 Job。

## 原始证据与失败记录

六个手动批次共注册 **36 次任务执行**，覆盖 **23 个唯一实例**；并发对照包含同题重复运行。
每个分片的原始压缩包都经过上传、重新下载和 SHA-256 核验；本地再次逐文件检查清单。
[Run 索引与归档 SHA](../benchmarks/actions-scale/cloud-runs.json)保存输入、时间、归档哈希和各次结果。
Actions 原始包保留 7 天，汇总保留 14 天；完整下载副本与逐文件清单另行交付。

[首次 PR smoke](https://github.com/lilong555/ReproPatch/actions/runs/40193853784) 的 Task 导出发生 YAML alias 错误。
该次运行的原始记录完整保留，资格成功计数为零；[独立重验](https://github.com/lilong555/ReproPatch/actions/runs/40194275983)两题通过。
一次 dispatch 数值参数校验返回 HTTP 422，未创建 Run；请求记录与后续有效派发分别保存。

本轮六个手动批次均为零模型运行。历史 v2 仍为 medium、6 次首跑、61 次正式请求，Full 1/2、mini 与 Codex 各 0/2。
后续 Luna 默认 max；真实供应商校准和新模型对照继续使用独立协议与预算。

## 复现入口

```bash
gh run download 40194807297 --repo lilong555/ReproPatch --dir artifacts/fmt21-O3
docker pull ghcr.io/lilong555/repropatch-benchmark@sha256:c00247e787729d6af3af364ab80cce196d90033832f77f2c1262a6e8f7cf111a
```

资格命令、候选评分和归档检查见 [Actions 执行说明](ACTIONS_BENCHMARK.md)。
