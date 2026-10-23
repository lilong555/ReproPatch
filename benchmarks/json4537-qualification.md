# nlohmann/json-4537 任务资格

固定第四仓库 nlohmann/json 的首条数据记录，官方参考补丁通过完整原生 **98/98**，
ReproPatch Task v2 通过 **1 F2P + 97 P2P** 基线和独立终验。模型四组实验单独记录。

[完整资格证据与镜像](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-json4537-qualification-2026-10-23)

| 身份 | 固定值 |
| --- | --- |
| 数据 revision | `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d` |
| 实例 | `nlohmann__json-4537`，Issue #3915 |
| 上游 commit | `e6cafa573aac6ed9227f752a5371c0b3f436307d` |
| prepared commit | `4bc894bccc39dccb96a42e68abde806f4427687f` |
| 原生测试 | 98，含 JSON_DIAGNOSTICS、ABI、Unicode、CMake 集成 |
| F2P | `test-diagnostics_cpp11` |
| 镜像 | `sha256:85df2a93b8024356d4f10a729382a9a0663f73b3c0adc312a36dadb962e86477` |
| 固定数据 commit | `a1375cea09d27cc1c4cadb8d00470375b421ac37` |
| 编译条件 | GCC 13.3、CMake/CTest 3.28.3、`-O1`，assertions 开启 |
| 资源 | 2 CPU、4 GiB 内存、3 GiB 构建 tmpfs，非 root、断网 |

缺陷为对象范围 insert 后的父指针关系，引发启用 JSON_DIAGNOSTICS 的断言。
允许编辑 `include/` 与 `single_include/` 内已有 C++ 头文件，测试和构建脚本固定保护。
可读测试范围为 `tests/src/`，历史测试报告中的图片保留在源码清单中。

Task 的逐项验收适配保持全部 98 项测试：固定公开数据放入镜像，清除数据下载隐式 fixture；
CMake 构建节点显式配置其原生工程后再构建；prepared FetchContent 读取当前源码；
诊断节点执行同一原生二进制，断言终止经 CMake 传播为非零 CTest 退出。
外部 Oracle 使用原始 CMake、原生 fixture 和本地 Git 克隆，完整构建并测试。

公共参考验收的 98 项均通过，容器删除已确认。
内部基线观察到诊断用例真实失败、其余 97 项通过；参考补丁在新工作树和新容器中全部通过。
内部资格用时 687.852778 秒，模型请求数为 0。
预检中的补丁应用、文本读取、fixture、Git 目录信任及辅助组件失败保留在原始资格证据中。

[任务准备器](../scripts/prepare_json_task.py)和[原生 Oracle](../scripts/check_json_candidate.py)
复用现有 Task、Worktree 和固定上游 evaluator。

```bash
python scripts/prepare_json_task.py \
  --record nlohmann4537-record.json \
  --repository nlohmann-upstream \
  --output json4537-prepared

python scripts/check_json_candidate.py \
  --record nlohmann4537-record.json \
  --repository nlohmann-upstream \
  --candidate json4537-prepared/reference.patch \
  --task json4537-prepared/task.yaml \
  --evaluator-source fixed-multiswe-evaluator \
  --output json4537-reference-oracle \
  --reference-check
```

工具链镜像以 `ReproPatch-json4537-toolchain-2026-10-23.tar.gz` 归档，314,355,181 字节，SHA-256：
`0c7d2a777e46d0bd64082a76b3ed5515a7531f14feeee0557de8727b40f97a77`。
归档配置的 SHA-256 与运行镜像身份一致，镜像只含编译工具、Git 组件和固定公开测试数据。

资格证据包 `ReproPatch-json4537-qualification-2026-10-23.tar.gz` 为302,637,551字节，
包含2,267个文件、上游与prepared源码bundle、全部预检、内部和原生Oracle日志、固定测试数据、
镜像构建材料及逐文件清单。SHA-256：
`fbdbe39d870889cb10720d13ce1ccf7d307d63aa0681e3b67021b2730770f617`。
逐文件哈希、凭据哨兵和独立解压资格结果核验通过，模型请求数为0。
