# Actions 资源与优化依据

查询日期：**2026-10-24**。以下为官方文档所述规则；实际 Runner 信息由每次执行保存。
性能收益均以实测结果为准，尚未运行的配置标记 `NOT MEASURED`。

## 官方配额与执行限制

| 项目 | 当前官方规则 | 本项目选择 |
| --- | --- | --- |
| 公开仓库标准 Ubuntu Runner | 4 vCPU、16 GB RAM、14 GB SSD；标准 Runner 免费 | 固定 `ubuntu-24.04`，实际磁盘用 `df`/采样报告 |
| 单 Job / Matrix | 6 小时 / 最多 256 jobs | 每片保留归档时间；小规模 2–4 Job |
| 标准并发 | Free 20、Pro 40、Team 60 | 本项目自行限流；账号额度与模型供应商额度分开 |
| Cache | 默认免费 10 GB/仓库；7 天未访问淘汰；可选择付费扩容 | 保持默认额，限制单项目缓存大小 |
| Artifact 额度表 | Free 500 MB、Pro 1 GB、Team 2 GB，与一般 Packages 共享存储池 | 不以公开 Runner 免费推导无限存储；短期保留 |
| Artifact 保留 | 公开仓库 1–90 天，默认 90 天 | 预检 7 天；正式数据转长期归档 |
| Release | 每文件 <2 GiB，每 Release 最多 1000 assets；未设总大小/带宽上限 | 每批次一个 Release，分项目/分片打包 |
| GHCR | Container registry 镜像存储及带宽当前免费，改变政策提前至少一个月通知 | 工具链按 digest 固定，不保存逐任务源码镜像 |
| Docker Hub | Hosted Runner 拉公开镜像豁免 pull rate limit；私有镜像受限 | 复用公开工具链镜像 |
| 网络吞吐 | 所查标准 Runner 文档未给出可据此承诺批次耗时的固定下载带宽 | 拉取、缓存恢复、上传均单独实测，不据本地网络外推 |

来源：[Runner](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)、
[Actions limits](https://docs.github.com/en/actions/reference/limits)、
[计费](https://docs.github.com/en/billing/concepts/product-billing/github-actions)、
[Cache](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)、
[Artifact 保留](https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization)、
[Release](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)、
[GHCR 计费](https://docs.github.com/en/billing/concepts/product-billing/github-packages)。

当前保留规则自 2026-10-01 起也覆盖 checks、workflow runs、commit statuses。长期复核需要
离线结果与原始诊断，Run URL 作为补充。Cache 是可丢弃加速数据，正式证据独立保存。

GitHub [附加服务条款](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features)
要求 Hosted Runner 用于所在仓库软件的开发、测试、部署或发布，并限制不成比例的负载。
资格检查与修复评测用于验证 ReproPatch；每批固定并发、超时、任务与输出上限。

[学生包](https://education.github.com/pack)当前列有学生期间 GitHub Pro、Pro 级 Codespaces，
以及 18 岁以上学生 Azure $100 额度。学生权益不改变公开标准 Runner 的上述硬件。
实际可兑换权益以账号认证和供应商当前条件为准。

## Workflow 首次运行

官方 [workflow_dispatch 说明](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
要求 Workflow 文件存在默认分支。独立分支首次验证可通过明确限定的 push/PR 免费预检触发，
保留最小权限且不注入模型凭据。付费执行限定可信分支上的手动工作流。

## 性能决策

下表为采用顺序，收益通过配对测量确认。复杂度与风险是本项目的工程判断。

| 方法 | 理论收益 | 复杂度 | 可靠性风险 | CPU / 内存 / 磁盘 / 网络代价 | 本轮实测 | 决策 |
| --- | --- | --- | --- | --- | --- | --- |
| Ninja 代替 Make | 减少调度与依赖扫描 | 低 | 仍依赖正确的生成依赖 | 无远端传输；并行度另限 | 真实 fmt 目标交错 A/B，见性能报告 | 新资格/profile 采用，旧任务不静默改配置 |
| Run 内 ccache | 复用相同翻译单元 | 低 | 选项、头文件与编译器身份必须参与键 | 额外缓存空间及哈希 CPU，目标 1 GB | 真实 fmt 冷/热对照；头文件/宏变化负控制 | 核心自检采用，最终冷 Oracle 不使用 |
| Run 内保留 build | 省略无改动 configure 与重复目标 | 中 | 生成文件、依赖声明、时间戳 | 增加一个存活 build 树 | 真实 fmt 无改动、撤销修复、重新应用实验 | profile 已验证，核心暂缓 |
| CMake Presets | 固化配置、减少操作差错 | 低 | 本身没有编译提速保证 | 几乎无运行成本 | NOT MEASURED | 暂缓；当前 Task 已冻结 argv |
| 定向 target 编译 | 避免无关目标 | 低 | 错误 target 映射可能漏测 | 降 CPU/磁盘，维护目标映射 | fmt 资格 reference 阶段只构建 F2P target | 采用，最终全套不裁剪 |
| 编译型/运行型回归分开识别 | 将真实编译失败纳入 F2P | 低 | 不能把环境失败当编译回归 | 多一份编译诊断；保留原 CTest 名称 | 41 个 fmt 实例实际动态检查 | 采用受保护的 CTest adapter |
| reference F2P 后独立完整 P2P | 去除中间重复全回归 | 低 | 必须保留最终全套 | 降重复编译；仍有独立冷构建 | 新资格脚本实跑，未做旧/新全流程配对 | 采用；Agent reproduce/verify 语义不变 |
| candidate-only | 去除与外部 Oracle 重复的内部验收 | 低–中 | 候选完整性、待评分状态 | 降一次冷构建；增加少量身份校验 | 零模型 C++ fixture 正/错候选；项目端到端 NOT MEASURED | 采用为显式 Benchmark 选项 |
| 降低优化等级 | 减少优化器工作 | 低 | 可能改变 UB/数值/优化相关缺陷 | 降编译 CPU，程序测试可能变慢 | O0 批量资格；没有同条件 O3 全流程 A/B | 单独配置报告，不改历史正式身份 |
| 预编译头 PCH | 减少重复头文件解析 | 中 | 宏/选项必须一致，改变编译上下文 | 增 PCH 磁盘和峰值内存 | NOT MEASURED | 暂缓，优先默认工具链语义 |
| Unity Build | 合并翻译单元减少解析 | 中 | ODR、匿名 namespace、宏泄漏 | 降进程次数，单次编译内存可增 | NOT MEASURED | 正式集暂缓 |
| 远程 sccache | 跨 Runner 复用对象 | 中 | 缓存身份与认证 | 网络、远端存储、服务维护 | NOT MEASURED | 当前规模暂缓 |
| 浅 Checkout + 共享 Git 对象 | 避免每题完整历史与重复下载 | 低 | 固定 commit 必须实际存在 | 降磁盘/网络；按需 fetch | 两题冷准备 1.704 s、复用 0.107 s，各一次 | 采用；不是编译时间 |
| 固定对象池 + worktree/archive | 降克隆成本并隔离修改 | 低 | 共享对象不能被任务修改 | 各在途源码仍占空间 | batch 用 git archive；核心已有 worktree | 复用已有实现，不增加池服务 |
| 只读源码、写密集 build bind | 避免源码污染及容器写层小文件开销 | 低 | bind 权限、生成器写源码的兼容性 | build 占宿主磁盘，避免 tmpfs 内存压力 | 本机磁盘采样；OverlayFS A/B NOT MEASURED | 新 Docker 路径采用，待云端门禁 |
| 文件系统 reflink/COW 快照 | 减少源码复制 | 中 | 文件系统可用性与共享写入 | 更少初始写入，后续 copy-up | NOT MEASURED | 暂缓；固定 archive 路径更简单 |
| 同 Job 一镜像 + GHCR digest | 摊薄镜像安装/拉取 | 低–中 | 跨 Job 工具链必须相同 | 远端镜像带宽与维护 | Docker/GHCR NOT MEASURED | 一 Job 一镜像已实现，GHCR 待发布 |
| Docker 多阶段构建 | 去除运行时不需的工具 | 中 | 本任务运行阶段仍需要编译器 | 可能少量缩镜像，增加维护 | NOT MEASURED | 暂缓；不把所需工具链裁掉 |
| BuildKit 层缓存/cache mount | 减少镜像依赖安装 | 低–中 | 层缓存不等于持久运行期 ccache | 网络、缓存容量 | NOT MEASURED | GHCR 后再 A/B；不默认上传大缓存 |
| Actions source/ccache 缓存 | 跨 Job 减少下载/编译 | 低 | 恢复成本可能超过节省 | 上传、下载、解压和 10 GB 默认配额 | 本地输入很小；远端五段 NOT MEASURED | source 显式 opt-in；ccache 跨 Run 暂缓 |
| 分阶段删除临时 build | 限制磁盘峰值 | 低 | 先保留日志/XML，再删可重建文件 | 少写入和存活树，无网络 | 新实现有阶段字节记录；同条件峰值 A/B NOT MEASURED | 采用，原始41批次旧代码不追溯算收益 |
| CTest 并行与共享初始化 | 缩短测试 wall time | 低–中 | adapter 内多个 Ninja 会竞争同一树；测试临时文件冲突 | 增 CPU/内存，可能升 I/O | 当前测试时间占比低，未并行 A/B | 当前串行；按项目验证后再开 |
| F2P 失败优先、通过后冻结 | 更早反馈并减少后续无效检查 | 低 | 早停不能跳过最终 P2P | 通常省 CPU，可能影响 Agent 策略 | reference F2P 已使用；Agent 策略未 A/B | 只采用资格部分，策略实验单列 |
| 源码摘要与有界工具输出 | 减少重复日志和上下文 Token | 低 | 截断不能隐藏诊断事实 | 降内存/传输/输入 Token | wrapper 4 MiB/流边界测试；真实模型 Token NOT MEASURED | 保留现有工具语义，新增日志上限 |
| 相同源码重复自检去重 | 避免无修改重复构建 | 低–中 | 命令/环境可能变化，不能只按补丁键 | 增小型身份索引 | NOT MEASURED | 暂缓；先由 trace 统计重复比例 |
| 请求并发、429 与等待交错 | 降模型等待期间 CPU 空闲 | 中 | 隐性重试影响公平预算 | 模型配额、并发内存、复杂度 | 新模型请求 0，无 API A/B | 付费全局账本完成前不启用 |
| 1/2/4 槽与 LPT 分片 | 减少长尾，提高吞吐 | 低 | 同机资源竞争、估时偏差 | CPU/内存/临时树随并发增 | 本地固定目标并发实验单列；Actions NOT MEASURED | 云端先 2 Job，每 Job 一任务 -j2 |
| 按批压缩、内容哈希、去重输入 | 降日志和归档体积 | 低 | 压缩成功不等于远端已保存 | 压缩 CPU，较少网络/存储 | 小包 87,021→16,152 B，0.153 s 本地核验 | 采用；原始身份/候选/失败诊断保留 |
| 增量归档、zstd、外部对象存储 | 长期更小/更快归档 | 中 | 依赖链、索引与外部账号维护 | 额外工具或存储维护 | NOT MEASURED | 暂缓；当前独立 gzip 批次足够 |

技术依据：[Ninja](https://ninja-build.org/manual.html)、
[CMake compiler launcher](https://cmake.org/cmake/help/latest/prop_tgt/LANG_COMPILER_LAUNCHER.html)、
[ccache](https://ccache.dev/manual/latest.html)、[sccache](https://github.com/mozilla/sccache)、
[Unity Build](https://cmake.org/cmake/help/latest/prop_tgt/UNITY_BUILD.html)、
[PCH](https://cmake.org/cmake/help/latest/command/target_precompile_headers.html)、
[CTest](https://cmake.org/cmake/help/latest/manual/ctest.1.html)、
[BuildKit](https://docs.docker.com/build/ci/github-actions/cache/)、
[OverlayFS](https://docs.docker.com/engine/storage/drivers/overlayfs-driver/)、
[tmpfs](https://docs.docker.com/engine/storage/tmpfs/)。

ccache 保留默认安全检查；不启用 `sloppiness`。容器内部源码/build 路径固定，避免
`CCACHE_BASEDIR=/` 的依赖路径重写问题。最终独立验收使用全新构建目录并关闭编译缓存。
BuildKit `type=gha` 默认不会持久化 `RUN --mount=type=cache` 的内容；镜像层缓存与运行期
ccache 使用独立路径。新资格/profile 的写密集 build 使用 bind mount，避免容器写层的 copy-up 开销；
核心 Harness 的 `/build` 仍按原 Task 使用 tmpfs。

## 资源采样命令

```bash
python scripts/benchmark_resources.py \
  --output /tmp/repropatch-metrics/attempt-001 --timeout 1800 \
  --watch checkout=. --watch build=/tmp/build \
  --watch cache=/tmp/ccache --watch evidence=/tmp/results \
  -- python scripts/qualify_cpp_batch.py --help
```

`--output` 必须使用全新测量目录。凭据放环境变量，不放命令行参数。
采样器保存 `telemetry.json`、`samples.jsonl`、`stdout.log`、`stderr.log`；默认每秒观察
主机 CPU、主机/cgroup 内存、进程组 RSS、按 PPid 递归的进程树 RSS、文件系统已用/剩余空间，
每 30 秒扫描命名目录。进程树统计包含仍挂在命令下的新 session 子进程，避免遗漏独立进程组的编译器。
当 `/proc` 挂在外层 PID namespace 时，先以 `NSpid` 映射直接子进程，并保存 `proc_root_pid`。
目录使用已分配字节、单目录内硬链接去重；权限不足报告 `partial`，缺失报告 `missing`。
主机/cgroup 数据可能包含其他活动；RSS 求和可能重复计算共享页。进程树不包含已被重新收养的
子进程，也不包含 Docker daemon 所属的容器进程；容器资源须另采 cgroup 或 Docker 指标。
瞬时尖峰可能落在采样间隔内，因此采样峰值是下界。

本轮 39 题旧采样配置每 10 秒扫描整个 `/tmp` 等目录，记录的观察代码耗时为
185.84 s / 1761.46 s（约 10.55% wall time）。这一数值包含扫描与其他采样开销，
不能当作可直接从任务耗时扣除的纯阻塞成本。新的默认目录采样改为 30 秒，
CPU、内存与文件系统可用空间仍每秒采样；降低采样频率后的收益尚未做配对测量。
对 Docker 使用每阶段 `docker system df -v` 加目录/文件系统采样，不假装进程树 RSS
能涵盖 Docker daemon 管理的容器内存。

每输出流默认最多 4 MiB，超限终止并报告 `output_limit_exceeded`，超时报告 `timeout`，
取消报告 `cancelled`；SIGTERM 后最多 2 秒终止宽限。原始命令非零退出报告 `command_failed`，
启动/读写错误报告 `infrastructure_error`。结构化状态与原始 returncode 独立保存。

缓存决策比较 `编译节省时间` 和 `下载+解压+保存+上传时间`。正式报告分别列单任务 wall time、
整批 wall time 与各 Job 时长之和（Runner 分钟），并保留失败与取消的资源消耗。
归档数据采用 SHA-256 清单与下载复核；已经压缩的 Artifact 可使用
[`upload-artifact`](https://github.com/actions/upload-artifact) 的 `compression-level: 0` 避免重复压缩。
