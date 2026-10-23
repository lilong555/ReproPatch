# JSON 整数访问任务

nlohmann/json-4525 已通过完整参考资格：基线复现 **2 F2P + 96 P2P**，
源码参考补丁在内部独立验收通过 **98/98**，完整上游参考在公共原生 Oracle 通过 **98/98**。
资格检查模型请求为 **0**。动态资格覆盖为 **8/129（6.20%）**、四个仓库。

缺陷涉及 JSON 存储为无符号整数时，`get_ptr<number_integer_t*>()` 和
`get_ref<number_integer_t&>()` 访问了联合体中的有符号成员。
目标测试为 `test-pointer_access_cpp11` 与 `test-reference_access_cpp11`。
原始 Issue、官方测试补丁、完整参考补丁与源码参考分别保存。
源码参考保留 `include/` 和 `single_include/` 的修复；完整参考还包含 API 文档更新。

| 身份 | 固定值 |
| --- | --- |
| 数据集 revision | `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d` |
| 原始 commit | `1b9a9d1f2122e73b69f5d62d0ce3ebda8cd41ff0` |
| prepared commit | `8df37183e76b41fe0edc963ce6ccda51d174c256` |
| 镜像 | `sha256:85df2a93b8024356d4f10a729382a9a0663f73b3c0adc312a36dadb962e86477` |
| 测试补丁 SHA-256 | `4b07295d171fcdb90235e957ab9e3e29c889386c0d1831cc851802e2d93e511a` |
| 完整参考 SHA-256 | `13398e723048065e86a9e6f411c409709006a5c79146b3d0db6a481782faaf9d` |
| evaluator commit | `4b96a678b136f87c8760fa475697f3c98d5f9e5e` |

本题为固定 nlohmann 数据文件第三条。第二条 json-4536 的参考补丁新增源码文件，保留适配审查状态。
json-4525 复用固定离线数据、2 CPU、4 GiB 内存、3 GiB 构建临时空间、GCC 13.3 和 CMake 3.28.3。
prepared 环境使用已有逐项 CTest 适配；公共 Oracle 从原始源码重新应用官方测试，
保留原生 CMake、Git FetchContent 与完整 98 项测试。

四组模型协议在模型执行前冻结：ReproPatch 原版、mini-SWE-agent、相关模板反馈候选、Codex CLI，
每组一次，单槽依次运行。同题共享 Issue、Task、镜像、编辑范围和公共 Oracle，
每次 12 请求、24 工具、8192 输出 token、256 KiB 输入边界和 90 秒请求超时。
相关模板候选核心为 `1f77a7d1421abe0a6fefe6e187fbfe464d72d0b850c3a0ac5ae5a40005ae76fd`，
原版为 `6c13e9efed3f3c13206bf225c8aaed5413e438e27786af92f8adff98d63e7338`。
模型成绩按各次原始候选评分，另行报告。

[资格证据](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-json4525-qualification-2026-10-23)
包含 prepared Git bundle、Task、原始记录、参考、内部 SQLite、98 项原生测试记录和冻结执行脚本。
附件 `ReproPatch-json4525-qualification-2026-10-23.tar.gz` 为 9,664,427 字节，含 1,467 个文件；
SHA-256：`a052b7b2407877934352a0d7450588d1ab1b23b0cd38e9709cfb7fc33b75ecbb`。
逐文件哈希、凭据哨兵、独立解压和 Git bundle 校验均通过。

工具链镜像、离线数据和原始源码 bundle 复用
[json-4537 资格附件](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-json4537-qualification-2026-10-23)，
依赖哈希与原始 commit 的祖先关系保存在本附件的 `json4525-qualification-dependencies.json`。
首次资格检查受 Docker 服务中断影响，原始失败已收入[修复复测附件](repair-followup-results.md)。
