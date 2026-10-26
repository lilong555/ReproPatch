# ReproPatch Shell-first 修复规格

Shell-first 使用一个 `bash` 工具完成代码搜索、阅读、修改和可见测试。同一次修复阶段共享源码快照和构建目录，最终候选交由独立冷 Oracle 验收。入口为 `--tool-mode shell-only`；默认 `legacy` 保留六工具接口和历史实验行为。

当前交付包含持久修复环境、源码同步、预算接入、候选导出和暂停恢复。目标级增量验证与编译诊断摘要是后续两个独立任务。

## 实验依据

[Luna max 四臂实验](ACTIONS_FORMAL.md)的 19 道 fmt 任务中，Full 通过 7 题、产生 8 个空候选，关闭自检组通过 10 题。Full 的 `run_shell` 调用为 0，16 次自检累计 751.25 秒，每题上限为 12 次模型请求。

优先检验两个机制：较细的搜索与阅读操作消耗请求预算，使首次编辑延后；自检重复配置和构建占用纠错时间。Shell 的复合命令与持久 `/build` 分别针对这两个问题。修复成功率的变化由新实验测量。

两组共同通过 7 题，关闭自检组单独通过 3 题，共同失败 9 题；由这组配对计算的精确双侧 McNemar 检验为 `p=0.25`。历史结果用于确定开发方向，后续比较固定模型、任务和预算。

研究依据：

- [An Empirical Study of Harness Design for Coding Agents](https://arxiv.org/html/2609.20804v1)，2026-09-17。固定执行循环研究 176 组配置；Nemotron-3 550B 在 Shell-only 下的 SWE-bench 成功率增加 3.6 个百分点、成本降低 53%。论文同时观察到不同模型对工具接口的偏好差异。
- [Is Bash All You Need?](https://arxiv.org/html/2609.11999v1)，2026-09-10。在两个企业任务基准上比较五类接口，Bash 的任务得分和 Token 效率较好，为可组合操作提供辅助证据。C++ 修复的实际收益由本项目配对实验确认。

## 执行流程

```text
固定 Task、Commit、镜像
    -> 冷基线与初始失败反馈
    -> 持久修复容器中的 Bash 循环
    -> 停止修复容器，冻结合法 Candidate
    -> 全新 Worktree + 全新容器中的冷 Oracle
    -> 补丁、逐项 F2P/P2P、SQLite 与原始日志
```

修复容器在 Agent 阶段创建一次，普通命令结束后继续保留。每次命令启动独立的 `bash --noprofile --norc -c` 子进程。`/build` 和 `/tmp` 中的文件持续存在，当前目录和环境变量按每次调用重新设置。

`/src` 是固定提交的完整源码快照。宿主 Worktree、Git 元数据、模型凭据与控制目录保持隔离。源码根目录和测试、构建配置只读，`editable` 中已有文件通过单文件挂载原位写入。

容器沿用非 root、断网、只读根文件系统、无额外 capabilities，以及 Task 的 CPU、内存、PID 和 tmpfs 限额。命令结束后冻结容器并同步源码；下一次命令前恢复运行。后台进程应在当前命令内结束。

## Bash 接口

| 字段 | 规则 |
| --- | --- |
| `command` | 非空 Bash 命令，UTF-8 大小至多 16 KiB；支持管道、循环与复合操作 |
| `cwd` | `/src` 或 `/build`，默认 `/src` |
| `timeout_seconds` | 可选正整数，实际时限取请求值、Task 命令时限和阶段剩余时间的最小值 |

初始上下文提供任务描述、可编辑文件、固定构建与测试命令、基线失败和预算。每次结果包含退出码、stdout/stderr 预览、命令及容器身份、源码前后 SHA-256、变更文件和剩余预算。

源码编辑使用保留原路径与 inode 的方式，例如：

```bash
python3 - <<'PY'
from pathlib import Path
p = Path("/src/src/stats.cpp")
p.write_bytes(p.read_bytes().replace(
    b"int best = 0;", b"int best = samples.front();"
))
PY
```

临时脚本和日志放在 `/build` 或 `/tmp`，可执行产物放在 `/build`。已有文件的修改继续遵循 Task 的 UTF-8、大小、文件集合和受保护路径规则。

构建优先使用 Task 的 `commands.configure`、`commands.build` 与测试入口。第一阶段沿用任务选定的 CMake generator；Ninja 和 ccache 可由工具链提供。相同 `/build` 支持后续 `cmake --build /build` 复用已有构建状态。

`--compiler-cache` 提供 Run 内独占的 `/cache` 与 ccache 环境变量；Shell 命令通过 `-DCMAKE_CXX_COMPILER_LAUNCHER=ccache` 启用编译缓存。Shell-only 基线实验保持此选项关闭。

## 结果与预算

`max_steps` 约束模型请求，`max_tool_calls` 约束 Bash 调用。单次 Bash 内的复合操作共同受命令时间、输出和资源限额约束。SDK 继续采用整批准入与串行工具执行。

每命令原始双流输出合计上限为 4 MiB，模型收到至多 64 KiB 预览；Run 审计预算为 256 MiB。较长构建日志可由命令主动写入 `/build`，再按行或关键错误读取。

普通命令失败，包括退出码 125、126、127，作为反馈返回，模型可以继续修复。命令超时或输出达限会清理修复容器并结束 Agent 阶段；经审计的合法源码仍可进入最终验收。非法源码变化直接拒绝本次候选。

每次同步先核对完整源码清单，再接收授权文件的字节变化。最终补丁在原始提交的全新 Worktree 中真实应用，核对源码清单和补丁往返后进入独立容器。修复阶段的 `/build`、测试输出与 ccache 均不进入冷 Oracle。

`--candidate-only` 冻结并导出候选，由 Benchmark 的外部 Oracle 评分。Shell 源码审计以 `FORBIDDEN_PATCH` 或 `SOURCE_CHANGED` 结束时，诊断补丁仅用于分析，候选导出结果为空。

## 暂停与恢复

Checkpoint 保存已审计源码、原生 SDK 输入、模式对应的提示与工具指纹、累计预算和原期限。暂停时删除修复容器。

恢复后从 Checkpoint 重建源码与修复容器，`/build`、`/tmp` 和编译缓存重新开始；下一次模型输入明确说明该状态。已提交且闭合的输入边界支持继续执行；开放片段按既有恢复协议处理。

## 使用与云端验收

安装可选 Agent 依赖：

```bash
python -m pip install -c requirements/agent.txt -e '.[agent,dev]'
```

已有 C++ 镜像时，直接运行零模型费用示例：

```bash
python scripts/init_example.py \
  --write-task .repropatch/tasks/negative-maximum.shell.yaml \
  --image repropatch-cpp:0.1
repropatch run .repropatch/tasks/negative-maximum.shell.yaml \
  --engine fake \
  --mock-script examples/models/fix-negative-maximum.shell.json \
  --tool-mode shell-only --json
```

镜像构建与真实 Docker 验收默认交给现有 GitHub Actions。对已推送分支运行：

```bash
gh workflow run ci.yml --ref "$(git branch --show-current)"
gh run list --workflow ci.yml --branch "$(git branch --show-current)"
gh run watch RUN_ID --exit-status
```

`docker-integration` Job 从 `docker/Dockerfile` 构建镜像，执行 `scripts/check_docker_gate.py --build`，并上传 JUnit、源码清单、Run 报告和沙箱证据。CI 使用确定性 `ScriptedModel`，付费模型请求为 0。

本地已有合适镜像时也可直接运行：

```bash
python scripts/check_docker_gate.py --image repropatch-cpp:0.1
```

核心验收关注持久构建、合法源码导出、独立冷验收，以及正常结束和错误路径的资源清理。相关实现位于 `repair_sandbox.py`、`harness.py`、`agent_runtime.py`、`workspace.py` 和 `recovery.py`；旧版执行入口保持可用。

## Shell-only 全量实验

批次 `shell-only-full-20261026` 覆盖资格运行 `40194807297` 的全部 21 道 fmt 任务。配置位于 [`shell-only-full-protocol.json`](../benchmarks/shell-only-full-protocol.json)。

| 项目 | 配置 |
| --- | --- |
| 模型 | `gpt-6-luna`，`reasoning_effort=max` |
| 请求 | 每题至多 24 次，全批至多 504 次，自动重试为 0 |
| 工具 | 仅 `bash`，每题至多 48 次调用 |
| 执行时间 | Harness 7200 秒，含 1200 秒验收预留；单请求 180 秒 |
| 运行环境 | 固定 GHCR 镜像，持久修复容器，ccache 关闭 |
| 验收 | 冻结候选后执行独立冷 Oracle |
| Actions | 21 题矩阵，并行 2 题，每个 Job 上限 150 分钟 |
| 产物 | 逐题轨迹、请求账本、候选、冷评分及全量汇总，保留 14 天 |

工作流按授权额度选择批次：

```bash
gh workflow run formal-benchmark.yml \
  --ref feat/shell-first-agent \
  -f authorization=504
```

镜像直接从 GHCR 拉取，模型校准复用已冻结证据。本批按 24 请求配置单独报告，历史四臂按原有 12 请求配置保留。

## 下一步实施

### 目标级增量验证

在 Shell-only 上添加可由 Shell 调用的轻量验证入口。输入为预先确定的构建目标和可见测试选择，输出为真实退出状态、耗时与日志位置。首次配置生成持久构建目录，后续调用优先构建相关目标并运行定向测试。

CMake target 与测试的对应关系通过现有 Task 适配信息和 CMake/CTest 元数据确定。目标对应关系缺失时使用任务原有构建入口。记录配置、编译、测试的独立耗时，保持最终冷 Oracle 的执行方式。

验收使用相同源码与镜像比较重复完整构建和目标增量构建，核对测试结果并报告耗时；Agent 通过同一个 Bash 接口调用。

### 编译诊断反馈

在原始日志旁生成 GCC/Clang 诊断摘要，包含首要错误位置、相关模板实例化链、构建目标及失败测试。完整原始日志与摘要同时保留。解析失败时提供有界原文。

摘要开关单独实验，观察输入 Token、重复读取、修复成功与耗时。候选 Checkpoint 的自动选择排在这两个任务之后，选择依据为 Agent 可见反馈。

### 开发实验与独立验证

开发集为 fmt-1171、2292、3260、3272、3537、3734。先比较 Shell-only 与目标级增量验证，再单独加入诊断摘要。固定模型、提示主体、Task、Oracle 和预算；请求预算先在 24 至 30 次范围做时间预检，然后冻结执行配置。

历史 Full 7/19 用作诊断参考。独立验证选择 10 至 20 道尚未参与调参的任务，覆盖至少两个仓库，完成 Docker 资格后进行逐题配对比较。mini-SWE-agent 和 Codex 在机制稳定后使用同等条件加入。

主指标是 Oracle Pass@1；同时报告空候选率、首次有效编辑步骤、构建与测试耗时、Token、每成功任务成本和基础设施失败。首次编辑由工具结果中的源码哈希变化确定；纯 Shell 复合命令先记录总耗时，构建与测试细分由后续验证入口记录。

开发任务用于观察机制，独立任务用于评价效果。新的付费运行单独固定请求与费用上限，沿用显式模型授权。
