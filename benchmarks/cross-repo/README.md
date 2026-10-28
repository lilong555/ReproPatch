# 跨仓库 C++ 修复实验

实验采用四道开发题、三十道正式题和五个实验臂，统一使用 Luna max、O3 Docker、独立完整冷 Oracle。已有任务复用历史证据。每次尝试包含修复、摘要和实际重试的请求上限为 24，总分配上限为 5,292。

正式选题依据生产 C++ 修复范围、原生 F2P/P2P、历史模型曝光和语义重复审查。开发题来自已有适配仓库；正式题优先覆盖 DuckDB、Slang、Glaze、Luau、jsoncpp 等新仓库。开发结果用于确定预登记的难度配额，正式题与六题重复集合在正式请求前冻结。

资格检查通过固定数据源恢复上游源码、官方测试和递归 Git 子模块，分别执行基线、C++ 参考修复与原始工程完整冷 Oracle。json 另外执行单头文件验证。准备源码与官方测试保存为 Git bundle，候选评分仅重放候选与官方测试。

零模型云端资格入口：

```bash
gh workflow run formal-benchmark.yml \
  --ref feat/cross-repository-benchmark \
  -f authorization=12 -f cross_stage=qualify \
  -f cross_instances=open-source-parsers__jsoncpp-1696,ninja-build__ninja-2749,stephenberry__glaze-2611
```

并发上限为两个 Job。每个原生冷阶段时限为三十分钟，任务资格时限为九十分钟。Actions 保存失败、取消、源码身份、日志、用例结果和归档 SHA，并下载上传后的证据核验内容。

Azure SSH 路由使用独立本地端口和固定转发目标。请求时间线记录客户端请求身份及首末字节时间，CPA 重试租约在失联二十分钟后恢复共享配置。

`calibrate` 阶段执行十二次公网与 SSH 配对请求。开发、正式、重复和基础设施复验阶段分别加载独立冻结协议，核验完整 CI、网络校准、资格归档和源码指纹，再认领各 Attempt 的请求额度。统计报告包含逐题配对差异、精确 McNemar 检验、Holm 校正和逐仓库宏平均；六题重复实验独立汇总。

已冻结的工具链通过 `cross_image` 输入复用相同 digest。资格检查为 Ninja 的原生进程压力测试保留 4,096 PID 额度；编译并行仍为两个线程。原生测试输入副本、动态库和生成文件使用独立构建目录。

[实验配置](campaign.json) · [候选索引](candidate-index.json) · [历史曝光快照](history-snapshot.json) · [Azure 控制验证](network-control.json)

## 验证状态

[公网与 Azure SSH 校准](network-calibration-40646051506.json)完成十二次请求，全部成功，实际输入 3,756 Token、输出 354 Token。正式模型修复阶段在开发题资格齐备后启动。

[jsoncpp-1696 的资格记录](docker-smoke-40642900596.json)包含 295 条原生用例，[jsoncpp-1693 的资格记录](docker-batch-40646271797.json)包含 293 条原生用例；两题均通过 O3 Docker、C++ 参考修复和完整冷 Oracle。各阶段记录绑定各自工具链身份。

共享工具链：

```text
ghcr.io/lilong555/repropatch-cross-cpp@sha256:411933ec8b67292c28c03b30c576c42bbed15eeca33ff06d553733b1a351e447
```

JSON 的嵌套构建沿用 GCC 11；Glaze 的 Clang 构建采用 libc++；Slang LLVM 后端来自经 SHA256 核验的官方 2026.5.2 附件。simdjson 的数据与 cxxopts 固定到提交，随准备源码归档。

正式冻结要求四道开发题的二十次冷评分完整、三十道正式题的缺陷语义与历史曝光审查完整，覆盖至少五个新仓库，按开发结果采用 18/8/4 或 24/4/2 的难度配额。六道重复题随正式协议预登记。基础设施复验使用独立 Attempt ID，全批次上限为二十次。
