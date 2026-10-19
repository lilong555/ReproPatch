# 安全边界

ReproPatch 当前用于单用户、操作者选定仓库的本地研究和开发。它没有通过外部安全审计。

## 已实施

- API Key 只由宿主机模型适配器读取；容器不运行模型客户端，不继承宿主机环境。
- 唯一 bind mount 是导出的只读源码；不挂载 Docker Socket、HOME、SSH、Git 元数据或凭据目录。
- Docker 参数包含非 root UID/GID、network=none、read-only、cap-drop=ALL、
  no-new-privileges、pids-limit、memory、memory-swap、CPU 限制、nofile/core ulimit。
- 构建仅写入容器 tmpfs。命令超时删除整个容器，清理子进程；宿主机工具进程也有进程组清理。
- 模型不能发送任意 argv/shell，只能请求人审核清单中的固定验证动作。
- 文本工具拒绝路径穿越、链接、未跟踪文件、超出预算文件、测试/构建文件写入。
- 所有 Git 操作禁用 hooks/fsmonitor，diff 禁用外部 diff/textconv；清理任务 Worktree。
- HTTPS 模型请求拒绝重定向，不回显 HTTP 错误响应体或凭据。
- 基线构建失败、测试超时、预期退出码/标记不符、空补丁都不会产生 passed。

## 操作者负责审核

本地仓库 Git 配置、任务 YAML 和编译镜像属于受信任输入。Git checkout 仍可能使用仓库配置的
clean/smudge filter，因此不要直接使用第三方提供的 `.git` 目录或 config；应自行 clone 源码，
审核本地配置后运行。禁止将密钥提交进源码，导出器不会替你检测所有业务秘密。
命令白名单不等于 CMake 安全：CMake 配置会运行代码，因此它始终在容器里执行。

默认使用本地 Docker daemon，不继承 DOCKER_HOST/DOCKER_CONTEXT 等环境变量；
没有 daemon 时直接失败。当前不支持远程 daemon、Docker Desktop 路径转换、rootless daemon 配置
目录发现或 Windows 宿主机，后续需要专门验收。

## 现有局限

Docker 共享宿主机内核，不能保证抵御容器逃逸；敌对多租户任务应使用专用 worker/VM。
不允许自定义 seccomp 放宽，沿用 daemon 默认 seccomp/AppArmor；宿主机管理员仍可改变默认策略。
容器内不可信程序可能伪造输出或构造针对测试的补丁。独立工作区保护验收输入及构建隔离，
不能证明补丁语义普适正确；需要有覆盖面的固定回归和后续隐藏测试。
模型可读取整个选定 commit 中的文本，禁止在仓库内放置不愿发送给所选模型服务的内容。
事件/源码快照会持续占用磁盘，单次预算有上限，但跨运行保留策略暂未实现。

真实 Docker 安全断言已编入显式集成测试，在本次受限环境中未执行。
不要将 mock 参数测试或宿主机 C++ 测试报告宣称为真实容器隔离测试通过。

发现问题时请先本地复现并最小化；公开报告中不要包含密钥、敏感仓库内容或未处理凭据。
