# 跨仓库候选资格

候选集为 30 题，覆盖 9 个仓库，含 25 道新仓库题和 5 道既有仓库新题。难度登记为 19 道复杂、9 道中等、2 道编译控制。完整名单与记录身份保存在 `formal-preparation.json` 和 `formal-selection-review.json`。

`candidate-qualification.yml` 默认调度完整候选集。`qualification-repair.json` 中登记的已通过题目复用固定运行、归档 SHA256 和结果 SHA256，其余题目并行执行资格验证。所有资格任务的模型请求数为 0。

## 运行合同

共享 O3 Docker 镜像：

```text
ghcr.io/lilong555/repropatch-cross-cpp@sha256:688d9f65c08c283a203d1ff03e7fc60f8b57167cfa925eaa26fb70d2d8b94533
image_id: sha256:5db0bcee1c240e8abac6bac6756edc983c661b8806c70e95fefa8aa8558335f8
```

| 仓库 | 执行配置 |
| --- | --- |
| DuckDB | 12288 MiB 内存、4096 PID；按数据集命令选择默认集合或显式 `*`；阶段期限 3600 秒、总资格期限 9000 秒。 |
| Slang | 构建目录提供原始 prelude/include 资源；PATH 包含 Clang 19；保留各题的数据集测试参数与预期失败列表。 |
| CAF | 启用原生测试与示例；从 CMake 生成的测试文件恢复延迟构建目标。 |
| glslang | 完整 Test 输入复制至可写构建目录，原生脚本在该目录执行。 |
| mold | Docker `--init` 回收提前退出进程留下的子进程。 |
| Glaze | Clang/libc++ 构建为系统 Asio 显式提供 `<exception>`。 |
| JSON | 原生冷 Oracle 与单头文件回归均纳入资格。 |

资格容器记录 OOM、PID 上限事件与退出信号。镜像拉取对临时网络故障最多尝试三次，保留每次结果；失败记录随归档发布。

## 准入与证据

每道题要求基线 F2P 失败、全部 P2P 通过，参考修复经独立原生冷 Oracle 通过。汇总检查归档与逐文件哈希、固定镜像、准备源码、原生测试合同、逐项测试结果和清理状态。

输出为 `eligibility.json`、`eligible-instances.txt` 和 `summary.md`。全部选定题资格齐备后，`freeze_cross_repo.py` 结合开发结果、校准、历史曝光和选题配额冻结正式协议。

正式实验使用 Luna `max`，CPA 请求并发最多 3，单次模型请求总期限 180 秒。
