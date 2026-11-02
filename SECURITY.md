# ReproPatch 0.4.0 安全与执行合同

ReproPatch 用于单用户、操作者选定仓库的本地 Linux amd64 Docker 工作流。安全机制覆盖输入冻结、源码权限、容器 profile、执行预算、证据完整性与所属资源清理；验证入口见[测试报告](docs/TEST_REPORT.md)与[工程验收](docs/ACCEPTANCE.md)。

## 信任关系

操作者审核本地仓库、Task、构建镜像、验收测试与所选模型服务。CMake 配置、编译和测试均会执行仓库代码，执行环境由 Docker 管理。固定测试集合决定验收覆盖范围；补丁合并和扩展回归由仓库维护者审核。

宿主控制面负责 Git、模型客户端、SQLite 与资源管理。模型 API Key 在授权和配置校验后由宿主客户端读取，保留在客户端内存中。core-only `verify-patch` 使用补丁、Task 与验证器；外部生产者 trace 作为有界私有诊断附件保存，生产费用和用量保持原始已知或未知状态。

模型可见数据包括文件工具读取内容、工具结果、命令输出和证据摘要。Shell 可读取完整 prepared 源码快照；`files.readable` 限定结构化文件工具的可读集合。操作者按整个源码快照审核秘密、数据授权与模型服务的数据政策，凭据通过宿主环境变量提供。

Docker 共享宿主内核，容器逃逸风险随内核和 daemon 安全状态而变化。部署采用可信本地 daemon、已审核镜像与受控单用户工作区；敌对多租户任务采用专用 worker/VM 和独立安全设计。

## 执行路径与挂载

| 路径 | 源码权限 | 环境与构建状态 |
| --- | --- | --- |
| 基线与独立 verifier | 完整源码快照只读挂载到 /src | 每次使用全新容器和 /build tmpfs，固定镜像冷构建；独立工作树实际应用并核验候选 |
| legacy `run_command` | 当前源码快照只读 | 每次新容器配置、构建和自检；`--compiler-cache` 可复用本 Run 的 ccache |
| legacy `run_shell` | 当前完整源码快照只读 | 在临时容器的 /src 或 /build 执行 `/bin/sh -lc`；容器、临时文件与环境变量随调用结束释放 |
| shell-only `bash` | /src 整树只读，授权已有文件通过逐文件可写 bind mount 覆盖 | 同一修复阶段保留容器和 /build，执行 `/bin/bash --noprofile --norc -c`；每条命令后冻结容器、核对派生进程及源码 |

shell-only 命令结束后，宿主审计修改文件、原始字节清单和 Git mode，再同步修复工作树。授权范围由冻结的 editable 集合确定，构建和验收输入由 protected 集合保护。持久容器命令间保持已核验的静止进程集合；派生进程泄漏或源码分歧进入失败与清理流程。

`--compiler-cache` 使用独占 Run 的 /cache 可写挂载与 ccache namespace，缓存身份和统计进入资源及自检证据。缓存用于修复阶段，基线与最终独立验收保持冷环境。shell-only 恢复从已提交源码重建容器，/build、/tmp 和编译缓存重新开始。

实现：[DockerSandbox.bind_mounts](src/repropatch/sandbox.py)、[PersistentRepairSandbox](src/repropatch/repair_sandbox.py)、[修复与 Shell 调用](src/repropatch/harness.py)、[evaluate_checks](src/repropatch/verification.py)。

## 容器 profile 与资源管理

所有执行路径使用固定 profile：UID/GID 65534、`network=none`、只读根文件系统、`cap-drop=ALL`、`no-new-privileges`、PID/内存/CPU 限制、memory-swap 同内存限额、nofile/core ulimit。入口为固定 sleep，镜像已在本地准备；健康检查与重启关闭，额外镜像 VOLUME 进入配置拒绝检查。

挂载由只读源码、自检缓存与 shell-only 授权单文件组成；/build 和 /tmp 使用有界 tmpfs。Docker Socket、宿主 HOME/SSH、凭据目录与 Git 元数据保留在宿主。容器 HOME 指向 /tmp，环境由镜像与固定 profile 组成。创建后再次 inspect 实际镜像、权限、挂载和资源限制。

宿主执行采用显式精简环境，Docker 连接使用本地 daemon。WSL2 使用 Linux 引擎与发行版文件系统；远程 daemon、Windows 原生执行和 rootless 配置发现属于扩展范围。

命令 stdout/stderr 保存原始 bytes，两流合计上限 4 MiB，预览合计 64 KiB，预览转义控制字符。失败签名在完整有界原始单流内匹配。Run 非源码审计文件上限 256 MiB。进程采集使用独立进程组和单调期限，超时、取消、输出达限触发资源终止与清理。

容器清理在固定十秒预算内核对 ID、名称和 Run 标签，删除后 inspect 明确确认容器不存在。daemon 失联、身份变化或删除结果未确认记录清理故障，并保留所属证据供诊断。`retain` 管理修复树与诊断快照，活动容器在阶段结束时释放；跨 Run 历史证据由操作者管理。

实现：[process.py](src/repropatch/process.py)、[DockerSandbox.close](src/repropatch/sandbox.py)、[RunResources](src/repropatch/resources.py)。

## 源码、补丁与工具准入

Run 使用独占 0700 控制目录、工作区和文件锁，任务、日志、事件与清单使用 0600。源码与候选均保存完整路径、原始字节、大小和 mode；独立工作树从固定 commit 实际应用候选，核对完整源码清单与规范补丁往返。

Git 操作使用隔离配置，禁用 hooks/fsmonitor 与外部 diff/textconv；checkout 前审核本地配置、提交属性与 Git 管理身份。include/includeIf、活动 filter、外部程序、额外 worktree 配置、partial clone/promisor 等布局进入策略拒绝检查。属性由私有 index 中的 Git 原生解析，目录和管理指针在运行中复核。

文件工具按冻结 readable/editable/protected 集合操作。路径穿越、链接、未跟踪文件、未授权写入和超限文本产生稳定策略错误；CMakeLists.txt、.cmake 与声明的验收测试输入受保护。已有 C/C++ UTF-8 文本内容为授权修改对象，文件集合与 Git mode 保持一致。原子编辑与快照复制固定目录 fd，源码被外部修改时记录分歧。

每次模型响应整体核对注册工具、调用身份和预算，最多八次工具调用，串行执行。普通策略或参数错误反馈给模型；磁盘、Git、Docker、审计等基础设施异常终止运行。默认 legacy 原生输入传输上限 256 KiB；semantic-state 路径采用支持完整轮次压缩的策略与 2 MiB 传输上限，摘要请求计入累计步骤。

结构化 CTest inventory 和逐项 JUnit 固定测试身份；失败、crash、skip/disabled、缺失或畸形结果各自记录。候选接受要求完整声明测试、源码身份、必需证据与清理确认。

实现：[workspace.py](src/repropatch/workspace.py)、[tools.py](src/repropatch/tools.py)、[agent_runtime.py](src/repropatch/agent_runtime.py)、[verification.py](src/repropatch/verification.py)。

## 模型客户端

模型名与付费授权显式提供，服务使用 HTTPS 或字面回环地址 127.0.0.1/::1 的本机 HTTP。客户端关闭重试、重定向和 tracing，供应商 SDK 日志关闭。HTTP 错误返回安全分类，诊断执行凭据脱敏。

默认客户端使用独立 HTTPX 环境配置，`--use-env-proxy` 显式启用宿主代理与 TLS 环境设置；该选项作用于宿主模型客户端。模型连接参数和 Key 环境变量名随配置冻结，实际密钥与代理地址保留在宿主环境。

实现：[models.py](src/repropatch/models.py)、[SDK 运行适配](src/repropatch/agent_runtime.py)。

## 恢复与证据查询

Checkpoint 支持已提交的完整模型输入边界：附件与目录先持久化，SQLite 事务再提交引用、状态及累计计数。恢复核验同一 Run 的实现、Python/SDK、Task、镜像、模型配置、工具 schema、完整附件与源码，继续原 deadline 和累计预算；暂停等待计入原期限。

请求结果未知、工具片段未闭合、源码分歧、证据损坏、输入变化或所属资源未确认均产生明确恢复诊断。持久 Shell 恢复重建容器与空构建环境；任意崩溃自动接管、执行重放和跨版本恢复按独立扩展合同设计。

`inspect`、`diagnose`、`replay --mode trace` 只读查询数据库及证据；`export-trace` 导出到 stdout 或 Run 外的新文件。`report` 持锁从已提交事实重建 JSONL、报告与导出索引，原始证据继续按哈希核验。`resume` 执行续跑并追加事件。

实现：[recovery.py](src/repropatch/recovery.py)、[events.py](src/repropatch/events.py)、[reports.py](src/repropatch/reports.py)、[trace.py](src/repropatch/trace.py)。

## 问题报告

问题报告提供最小化 Task、版本与镜像身份、稳定错误代码和脱敏证据。密钥、敏感源码和代理凭据通过私有渠道处理，公开材料使用经过审核的最小复现。
