# mini-SWE-agent 原生环境

固定上游 commit `04d809ceab9df28f9adaed044884180159172930`，版本 2.4.6。
使用上游 `DefaultAgent` 与 `DockerEnvironment`，不复制或替换 Agent 循环。
模型客户端在宿主运行；修复命令在容器中运行。

```bash
python scripts/prepare_mini_environment.py \
  --task .repropatch/multiswe-prepared-adapted/catchorg__Catch2-2723/task.yaml \
  --mini-source .repropatch/mini-swe-agent \
  --output .repropatch/mini-catch2723-aligned --check-scripted
```

需要 Python 3.12、ReproPatch 核心依赖，以及上游原生类需要的 Jinja2、Pydantic、Rich、
python-dotenv、platformdirs。收费模型依赖与固定 Agents SDK 分开安装。
输出目录必须不存在；准备过程不拉镜像、不访问模型，也不加载用户的 mini 全局 `.env`。
`environment.json` 可由上游 `get_environment` 直接加载；`issue.txt` 保留原 Task 描述。

源码从固定 prepared commit 导出，逐个核对 Git Blob；新建仅含基线的 Git 仓库，
不复制宿主仓库配置、远程地址或原工程历史。prepared 测试源码对两组可见。
整个源码目录只读，再逐个挂载允许的现有文件为可写，禁止修改测试、CMake、Git 元数据，
也不能新增、删除或通过临时文件原子替换源码；Bash 编辑需使用原位写入。
宿主在 Agent 结束后导出 diff，候选必须交统一的官方 Oracle 判定。

| 资源与权限 | Catch2-2723 配置 |
| --- | --- |
| 镜像 | 与 ReproPatch 相同的固定 sanitized v0.2 image ID |
| 用户与网络 | 65534:65534，network=none，模型密钥不转发进容器 |
| CPU / 内存 / 进程数 | 2 / 2048 MiB，无额外 swap / 128 |
| 根目录与权限 | 只读、cap-drop=ALL、no-new-privileges、ipc=none |
| 临时空间 | /tmp 64 MiB；/build 1024 MiB，可执行构建产物 |
| 编辑范围 | Task 中全部允许的现有 C/C++ 文件 |

无模型检查通过原生 `DeterministicModel` 驱动两轮：读取并原位写回允许文件，
确认测试、CMake、根文件系统与 Git 配置的写入被拒绝，再提交结束。
实际 Docker inspect 记录资源限制；原生异步 cleanup 返回后，外层删除并确认容器已不存在。
这证明环境链路，不表示解决了任务，也不参与 Resolved@1。

仍须公开的接口差异：mini 使用 Bash 和持久容器；ReproPatch 的 Shell 源码只读，
由文件工具编辑，Shell 每次使用新容器。mini Bash 可读完整 prepared 源码，
ReproPatch 文件工具按 readable 过滤。这些差异不能描述为完全相同的工具权限。
当前还需冻结同模型协议、统一初始基线诊断、执行请求前预算预留并接入 Harbor 产物链路，
因此 `strict_same_model_comparison_ready` 保持 false。

实测摘要见 [mini-environment.json](mini-environment.json)，完整原始轨迹通过 Release Assets 提供。
