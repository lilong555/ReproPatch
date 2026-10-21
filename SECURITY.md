# 安全边界

ReproPatch 当前用于单用户、操作者选定仓库的本地研究和开发。它没有通过外部安全审计。

## 已实施

- API Key 只由宿主机模型适配器读取；容器不运行模型客户端，不继承宿主机环境。
- 唯一 bind mount 是导出的只读源码；不挂载 Docker Socket、HOME、SSH、Git 元数据或凭据目录。
- Docker 参数包含非 root UID/GID、network=none、read-only、cap-drop=ALL、
  no-new-privileges、pids-limit、memory、memory-swap、CPU 限制、nofile/core ulimit。
- 固定 sleep 入口、禁用健康检查和重启，拒绝额外镜像 VOLUME；创建后核对实际固定 profile 和资源限额。
- 构建仅写入 Task 限额的 tmpfs。超时、取消、原始输出达限时删除整个容器，十秒清理预算内再次 inspect。
  只有明确不存在才确认删除；daemon 失联、ID 或 Run 标签不符不能继续或报告通过。
- Run 独占 0700 控制目录和工作区，持有文件锁；任务、事件、日志与清单为 0600。
- stdout/stderr 保存原始 bytes，两流合计达到 4 MiB 即停止；Run 非源码审计文件限 256 MiB。
  预览限 64 KiB，首尾取样并转义控制字符；失败签名只在完整原始单流内匹配。
- 普通成功诊断快照使用后释放；retain 只保留所属 repair 工作树和最近诊断快照，不保留活跃容器。
  身份不明的目录或容器停止清理并记录错误，不执行全局 prune。
- 模型不能发送任意 argv/shell，只能请求人审核清单中的固定验证动作。
- 文本工具拒绝路径穿越、链接、未跟踪文件、超出预算文件和未获 files.editable 授权的写入。
  readable/editable/protected 从固定 commit 展开并检查交集；CMakeLists.txt 和 .cmake 始终受保护。
- 所有 Git 操作禁用 hooks/fsmonitor，diff 禁用外部 diff/textconv；清理任务 Worktree。
- Git 本地配置禁止 include/includeIf、活动 filter、额外 worktree 配置、外部程序与 partial clone/promisor。
  提交属性由私有 index 中的 Git 原生解析，拒绝 filter；记录并复核真实 Git 管理目录、根身份与指针。
- 完整 SourceManifest 与候选证据引用固定原始字节、大小与 mode；独立工作树实际应用补丁并检查完整往返。
  原子编辑及快照复制逐级固定目录 fd，拒绝链接和路径替换；外部修改触发运行错误。
- HTTPS 模型请求拒绝重定向，不回显 HTTP 错误响应体或凭据。
- 基线构建失败、测试超时、预期退出码/标记不符、空补丁都不会产生 ACCEPTED。
- 结构化 CTest 固定测试身份与逐项 JUnit；skip/disabled/缺失/畸形证据不能被退出码 0 掩盖。
- 外部 patch/trace 先复制为有界私有普通文件；trace 不执行、不解包、不提升为可信观察。
  verify-patch 不导入模型、SDK 或模型密钥，外部生成费用和用量不填零。

## 操作者负责审核

本地仓库、任务 YAML 和编译镜像由操作者选定。支持的 Git 配置与属性在 checkout 前接受审查；
仍应自行准备仓库并审核其来源，当前边界不等于对全部 Git 特性的安全认证。
禁止将密钥提交进源码，导出器不会替你检测所有业务秘密。
命令白名单不等于 CMake 安全：CMake 配置会运行代码，因此它始终在容器里执行。

默认使用本地 Docker daemon，不继承 DOCKER_HOST/DOCKER_CONTEXT 等环境变量；
没有 daemon 时直接失败。当前已验证 WSL2 Ubuntu 与 Docker Desktop Linux 引擎；不支持远程 daemon、Windows 原生
路径转换、rootless daemon 配置目录发现或 Windows 原生宿主执行。

## 现有局限

Docker 共享宿主机内核，不能保证抵御容器逃逸；敌对多租户任务应使用专用 worker/VM。
不允许自定义 seccomp 放宽，沿用 daemon 默认 seccomp/AppArmor；宿主机管理员仍可改变默认策略。
容器内不可信程序可能伪造输出或构造针对测试的补丁。独立工作区保护验收输入及构建隔离，
不能证明补丁语义普适正确；需要有覆盖面的固定回归和后续隐藏测试。
模型文件工具只读取 frozen readable 文本；编译容器可见完整源码快照，报告也包含命令输出。
禁止在仓库内放置不愿发送给所选模型服务的内容。
单源文件、整树、编辑、候选补丁、原始双流日志与每 Run 审计文件均有上限。
retain 管理每 Run 工作区；跨 Run 的历史审计文件仍由操作者管理，不提供全局磁盘配额或自动清扫。

真实 Docker 的非 root、凭据、网络、只读与超时清理测试已通过，证据见 docs/TEST_REPORT.md。
源码与补丁字节往返、Run 所有权/锁、容器删除确认、日志硬限额及 retain 已验收。
结构化 CTest 与独立 verify-patch 已提供；SDK 基础入口具备原生 Items、有限 timeout、取消传播与离线凭据哨兵；六工具与整批预算已经接入自动路径。
当前提供同一 Run、相同配置与版本下的有限恢复：只有数据库已提交、附件完整且关闭修复片段的
Checkpoint 才能继续。请求结果未知、工具执行边界未关闭、源码分歧、证据损坏或资源清理未确认时拒绝恢复。
恢复不重设原始 deadline 或累计额度，不重做未知副作用，不承诺 Exactly Once、跨版本恢复或掉电后必然接管。
Trace Replay 和 export-trace 只读数据库及证据，不执行模型、工具或恢复，也不把历史成功文字当作执行权限。

发现问题时请先本地复现并最小化；公开报告中不要包含密钥、敏感仓库内容或未处理凭据。

SDK 基础入口在授权和输入校验后读取指定环境变量，凭据仅属于客户端，不进入 Run context。
客户端关闭重试和重定向，默认不继承代理；`--use-env-proxy` 显式启用 HTTPX 的宿主代理及 TLS 环境配置。
该选项只影响宿主模型客户端，代理地址和模型密钥不写入 Task、报告或容器环境。
tracing 全局与每次运行均关闭，供应商 SDK 日志被关闭。
模型名必须显式提供，拒绝由 Runner 隐式选择模型和默认凭据。HTTP 错误仅返回安全分类，不附响应体。
静态工具必须使用真正的 async 回调；SDK 的异步包装器不证明其内部没有同步线程。
取消与 timeout 不代替资源拥有者的删除确认，异步 finally 可能被 SDK 的后续取消中断。

自动路径没有宿主 Shell 或后台工具线程。run_shell 只在所属 Docker 的 /src 或 /build 执行 /bin/sh -lc，
每次使用新快照与容器，源码只读且没有网络；cd/export/tmpfs 不跨调用保存。
工具函数仅捕获 PolicyError 并返回有稳定代码的 JSON，磁盘/Git/Docker/审计错误终止运行。
工具批次在公开 on_llm_end 中整体审核；未知执行项、重复/空调用身份、未完成输出或超额批次均不能执行。
原生输入/输出分别限制 256 KiB/1 MiB；不手裁上下文，不自动重试收费请求，不额外请求总结。
