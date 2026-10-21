# ReproPatch

面向 C++ 工程的可复现代码修复与独立验收 Harness。

当前开发版本为 **0.3.0.dev3，Task v2**。Phase 1、P2-01 至 P2-03 已完成。
`verify-patch` 无需模型、SDK 或 API key，使用固定基线和全新容器独立验收外部补丁。
自动修复与外部补丁共用结构化 CTest、固定测试身份、完整字节清单和候选往返检查。
**297 项核心测试、147 项 SDK 契约与 21 项真实 Docker 测试通过**。
Phase 1 的 0.2.0rc1 已完成 DeepSeek 真实自动修复和独立 Docker 验收，结局为 `ACCEPTED`。

自动 `run` 使用公开 Agents SDK Runner、六个受控异步工具和原生 Responses Items。
fake 引擎直接使用原生 ScriptedModel；SDK 引擎使用 AsyncOpenAI/OpenAIResponsesModel。
SQLite 的 runs/events/checkpoints 三表记录外层状态、累计预算和事件；提交失败不会释放模型或工具执行。
`inspect` 只读查询，`report` 核验证据并重建 JSONL / JSON / Markdown。
SDK 完整输入边界保存 Checkpoint，支持受控暂停与有限 Resume；Replay 和 Harbor 命令尚未提供。
下一任务为 P2-04。事务契约见 [P2-01](docs/P2-01.md)，Checkpoint 与暂停见 [P2-02](docs/P2-02.md)，有限恢复见 [P2-03](docs/P2-03.md)。
Phase 1 的真实模型证据见 [P1-08](docs/P1-08.md)。

[规格入口](SPEC.md) · [测试报告](docs/TEST_REPORT.md) · [实施计划](docs/IMPLEMENTATION_PLAN.md)

## 快速开始

需要 Linux amd64、Python 3.12+、Git、可用本地 Docker daemon 和已经准备的编译镜像。
WSL2 可使用启用 Ubuntu 集成的 Docker Desktop Linux 引擎。任务运行不自动构建或下载镜像。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]' cmake

# 没有本地镜像时，在可访问镜像源和软件源的环境中准备
# docker build -t repropatch-cpp:0.1 -f docker/Dockerfile docker

python scripts/init_example.py \
  --write-task examples/tasks/negative-maximum.v2.yaml --image repropatch-cpp:0.1
repropatch validate-task examples/tasks/negative-maximum.v2.yaml
repropatch doctor --image repropatch-cpp:0.1 --json
repropatch verify-patch examples/tasks/negative-maximum.v2.yaml \
  --patch examples/patches/negative-maximum.correct.patch --producer local --json

```

`init_example.py` 不重置已有仓库，也不改写未提交源码；输出实际完整 commit、本地 image ID、任务路径和
规范任务哈希。生成的 Task 保存实际 image ID，镜像 tag 仅用于准备和诊断。
自有 C++ fixture 用于验证 Harness，不代表第三方历史漏洞或模型修复率。

## Task v2

[可运行示例](examples/tasks/negative-maximum.v2.yaml) 使用当前机器记录的真实 commit/image。
跨机器使用前需要导入同一镜像，或重新生成任务；不能将本地 image ID 当作可拉取地址。
[完整字段契约](specs/2026-10-19.2/docs/TASK_FORMAT.md) 定义全部字段。

- `repository.path/commit` 固定本地仓库及直接指向 commit 的完整 OID；HEAD、tag、缩写均拒绝。
- `environment.image` 必须是 `sha256:<64hex>` 或 `name@sha256:<64hex>`；不允许仅 tag。
- `files.readable` 与 `tests.protected_paths` 可用以 `/` 结尾的目录展开固定 commit 文件；
  `files.editable` 只允许逐个列举 C/C++ 文件，必须属于 readable 且不与 protected 相交。
- CMakeLists.txt 和 `.cmake` 文件始终不可编辑。操作者仍须完整列入测试脚本与间接输入。
- F2P/P2P 必须给出不相交的固定测试名。复现与验证使用固定 CTest argv，选择表达式由 Harness 生成。
- 清单最多 128 KiB；拒绝重复键、未知字段、anchor/alias、自定义 tag、过深结构及无效类型。

`validate-task` 仅检查语法与字段，不访问 Docker、网络、模型或编译器，不创建 Run。
运行前会查询实际 commit/image、展开文件集合并冻结 `task.resolved.json`。
源 YAML 的 SHA-256 与规范执行契约的 `task_sha256` 分别记录；后者不包含本地绝对路径、
产物位置、保留策略、Run ID 和时间，集合排序不依赖进程 hash seed。

旧 `version: 1` 返回明确迁移错误。`run --image` 已取消，修改镜像必须修改 Task；
`--output-root` 只改变产物位置，不改变执行契约哈希。

## 外部补丁验收

`verify-patch TASK --patch FILE` 只接受本地普通文件，patch 最多 8 MiB。
可加 `--producer NAME`、`--producer-trace FILE`（最多 16 MiB）、`--output-root DIR`、`--json`；
拒绝模型、key、费用或暂停参数。原始补丁与 trace 保存为私有证据，trace 是未验证的外部附件。
外部生成的 token 用量与费用保持未知，Agent 计数为零。

候选越界、空输入、非法格式可在创建执行容器前拒绝；任何 `ACCEPTED` 都必须建立本次完整基线，
再从同一 commit 应用规范 patch 并独立重建。参考错误补丁
[negative-maximum.wrong.patch](examples/patches/negative-maximum.wrong.patch) 应得到 `REJECTED`。

CTest 使用 JSON v1 发现及逐项 JUnit，固定名字、完整 argv 与全部解释属性的身份哈希。
F2P 必须普通失败且退出码/原始字面签名符合，P2P 必须真实通过；最终所有测试身份一致且真实通过。
skip、disabled、测试缺失、错误计数、未知状态或缺失 XML 均不能通过。
具体契约见 [P1-06](docs/P1-06.md)。

## 当前执行边界

容器使用非 root、只读源码和根文件系统、断网、无 capabilities、有限 CPU/内存/PID 与构建 tmpfs。
验证执行使用 Task 的总 wall、验证预留、命令上限与最后十秒清理余量；每项 CTest 的 timeout 由阶段剩余时间限定。
SDK 在请求前检查上下文与阶段期限，模型开始即计 turn，响应中的工具调用整批准入、串行执行。
最后允许 turn 的合法工具仍执行；步骤、工具、上下文或 Agent 时限停止后，已有合法补丁仍可使用验证预留。
每个 Run 使用 0700 独占控制目录和工作区，运行期间持有文件锁；控制文件为 0600。
容器按 Run/操作标签记录实际 ID、固定 profile、镜像和用途，创建后先保存身份再启动。
超时、取消或原始输出达限时整体删除容器；十秒清理预算内再次 inspect，daemon 失联不算删除成功。

每命令分别保存原始 stdout/stderr，两流合计达到 **4 MiB** 即停止，不能用于成功验收。
模型双流预览合计最多 64 KiB，首尾取样并转义控制字符；失败签名只在完整原始流内匹配。
Run 非源码审计文件总预算 **256 MiB**，包含日志、事件、清单和补丁，并预留最终诊断空间。
源码快照位于所属工作区；普通成功诊断后释放，最多保留最近需要诊断的快照。
`workspace.retain` 支持 `none`、`on_failure`、`always`，保留工作树及快照时也不保留活跃容器。
具体契约见 [P1-03B](docs/P1-03B.md)。

结构化文件工具只读取 frozen readable 集合，修改仅限 editable。
编译容器会看到完整无 `.git` 源码快照，readable 不是仓库内容保密保证。
真实模型必须显式提供 `--allow-paid-model`；默认测试不调用付费模型。
0.2.0rc1 已认证 `https://api.deepseek.com` 的 `deepseek-flash`，使用显式环境代理；
0.3.0.dev3 通过离线 SDK 与真实容器回归，本任务没有重复调用付费模型。

## 源码与补丁契约

每次评估记录完整 `SourceManifest`：规范相对路径、原始字节 SHA-256、大小和 Git mode。
单源文件最多 16 MiB，整树最多 256 MiB；文件集合之外的新增、删除、链接、特殊文件、空目录和
权限变更均拒绝。Git 本地配置与提交属性先经审查，不运行外部 filter、hooks、diff 或 textconv。

文本编辑限定 UTF-8、无 NUL、单文件 1 MiB；文件预览为 64 KiB。BOM、CRLF 和末尾换行按原始
字节保留。候选仅允许已有 editable C/C++ 文本的内容修改，规范补丁最多 8 MiB。
独立工作树实际执行保存的 `git apply`，完整清单与再次导出的补丁逐字节一致后才进入独立编译。
宿主源码被外部改写、证据引用被破坏或 Git 往返改变字节时，运行不能通过。
当前契约与边界见 [P1-03A](docs/P1-03A.md)。

## 结果

`outputs.root` 默认为 YAML 相对的 `.repropatch/runs`；示例明确使用项目根目录下的专用根。
CLI 输出 Run ID、入口、最终 outcome/reason_code 和绝对产物目录。静态输入错误退出 2；
REJECTED/NOT_REPRODUCED/BUDGET_EXHAUSTED 退出 1，ERROR/INCONCLUSIVE 退出 3，取消退出 130，通过退出 0。

```text
<outputs.root>/<run-id>/
  task.original.yaml
  task.resolved.json
  run.json
  report.json / report.md
  patch.diff / candidate.manifest.json
  producer/
    input.patch
    trace.bin
  events.sqlite3 / events.jsonl
  baseline.manifest.json
  resources.json / .run.lock
  manifests/
  evidence/<evaluation-id>/evaluation.json / <test-id>.xml
  evidence/<command-id>.result.json / final-result.json
  logs/<command-id>/stdout.bin / stderr.bin
```

工作树与源码快照位于独立的 `workspace.root/<run-id>/`。新 Run 使用 SQLite schema v2，
外层状态、累计预算和事件在同一事务提交；JSONL 从已提交事件快照导出。
报告的 `isolated=true` 表示实际使用 Docker；受信任宿主 fixture 测试始终为 `false`。

```bash
repropatch inspect RUN_ID --root .repropatch/runs --json
repropatch report RUN_ID --root .repropatch/runs --format json
```

`RUN_ID` 使用完整 32 位小写十六进制值；输出根不同需显式指定 `--root`。
查询失败 Run 的报告仍退出 0；读取或导出失败退出 3。报告丢失可以重新导出，不执行模型或仓库代码。
模型请求前原子提交步骤扣减和 `segment_open=1`；模型输出与工具结果不关闭这个标记。
只有完整输入边界的 Checkpoint 事务会关闭修复片段；模型回复或工具日志本身不能证明可恢复。
结局在清理及证据检查后提交；之后导出失败只产生 `ARTIFACT_EXPORT_FAILED`，不改写已提交结局。
`inspect` 显示最后已提交阶段、结局及 `artifacts_complete`；未提交终态时结局保持 null。
证据缺失或 hash 不符显示不可核查；未知用量、HTTP 次数和费用保持未知。
`inspect` 分别展示 database_version 与 event_format，schema v2 仍使用原来的 v1 事件信封。
历史 kind / P1 审计按原版本查询，不自动改建数据库，不提供恢复能力。
报告契约见 [P1-07](docs/P1-07.md)，当前数据库与事务边界见 [P2-01](docs/P2-01.md)。

## 受控暂停与有限恢复

```bash
repropatch run examples/tasks/negative-maximum.v2.yaml \
  --engine fake --mock-script examples/models/fix-negative-maximum.json \
  --pause-after-step 3 --json
```

N 是全 Run 累计模型 turn，必须满足 `1 <= N < max_steps`；没有该参数时照常修复和验收。
只在 SDK 准备下一次完整输入、前轮工具及容器已清理后暂停。模型已正常结束时直接验收，不补发请求。
成功暂停退出 0，summary 给出 `paused=true`、`state=INTERRUPTED`、`outcome=null` 与 Checkpoint 引用。
暂停不表示补丁通过；SIGINT 仍为取消。

```bash
repropatch resume RUN_ID --root .repropatch/runs --json
# 再次暂停时 N 是累计 turn，必须 steps_used < N < max_steps
repropatch resume RUN_ID --root .repropatch/runs --pause-after-step 4 --json
```

恢复使用冻结 Task、模型、instructions、SDK 版本及原始期限，不接受新的模型或预算参数。
真实模型 key 从原 key_env 重新读取；fake 使用冻结脚本的剩余 steps，不重放已消费回复。
先持锁并核对、删除已登记的所属容器，再验证 Checkpoint；从 base＋patch 在新工作树重建完整字节。
原修复树如被第三方修改，返回 WORKSPACE_DIVERGED 并保留原内容；缺失的可丢弃工作区可重建。
未知请求返回 MODEL_RESULT_UNKNOWN，未闭合工具轮次返回 OPEN_AGENT_SEGMENT；均以 RECOVERY_FAILED 结束，
不重复调用模型或工具。停机时间消耗原预算；安全候选只在剩余验证时间允许时独立验收。
恢复失败保存的诊断补丁 verification_eligible=false，需要显式新建 verify-patch Run 才能判断。
终态 Run 和旧 P1 审计不能继续；数据库不可核查或不能提交时停止，recovery-error.json 不是状态权威。

Checkpoint 的输入、补丁、完整源码清单及 manifest 位于 Run 的 `checkpoints/<id>/`，
文件先持久化，再由同一 SQLite 事务提交引用、累计预算和关闭的执行片段。
首次边界 step=0 允许零字节补丁；未提交文件只是孤儿，不参与恢复点选择。
暂停保留修复源码及必需证据，原始绝对期限保持不变，不保留活跃容器或构建目录。
核心安装可查询和重新导出暂停报告，无需加载 SDK；损坏的 Checkpoint 明确不可核查。

## 开发验证

非 Docker 的真实 C++ 测试需要宿主 g++、CMake/CTest；虚拟环境中的 `cmake` 包提供后两者。

```bash
ruff check src tests scripts
ruff format --check src tests scripts
python -m pytest -m 'not docker and not sdk' -q
python scripts/check_docker_gate.py
```

可选 SDK 契约使用独立环境，不调用付费模型：

```bash
python3.12 -m venv .venv-agent
.venv-agent/bin/python -m pip install -c requirements/agent.txt -e '.[agent,dev]'
.venv-agent/bin/python scripts/check_sdk_contract.py
.venv-agent/bin/repropatch run examples/tasks/negative-maximum.v2.yaml \
  --engine fake --mock-script examples/models/fix-negative-maximum.json --json
```

`agent` 固定 `openai-agents==0.24.0`、`openai==3.35.1`，完整依赖约束在
[requirements/agent.txt](requirements/agent.txt) 与 `uv.lock`。公开 API、脚本格式、超时和凭据契约见
[P1-04](docs/P1-04.md) 与 [生产运行契约](docs/P1-05.md)。核心安装不需要这些依赖。
真实模型需 `--engine agents-sdk --model MODEL --allow-paid-model`，不得将 key 放入命令行；
模型密钥通过 `--key-env` 指定的环境变量供应。客户端默认直连；
`--use-env-proxy` 显式信任 HTTPX 的宿主代理及 TLS 环境配置，容器仍不继承这些配置。
`run` 默认使用 fake，必须提供 `--mock-script`；`sdk` 和 `--model-name` 分别是 engine 与 model 参数的别名。

经授权的真实自动修复示例：

```bash
repropatch run examples/tasks/negative-maximum.live.v2.yaml \
  --engine agents-sdk --model deepseek-flash --api-base https://api.deepseek.com \
  --key-env DEEPSEEK_API_KEY --use-env-proxy --allow-paid-model --json
```

0.2.0rc1 在 2026-10-20 的完整 [真实验收](docs/evidence/p1-08/live-deepseek/summary.json) 使用
DeepSeek-V4.1-Flash-1017 对应的 `deepseek-flash`，5 轮模型调用、5 次工具调用，
独立重建后的 F2P/P2P 全部通过。接口别名的版本对应关系以供应商当日文档为准；
单个自有 fixture 的成功不代表一般修复率。

Docker gate 显式启用十九项真实容器测试，保存源码指纹、镜像 ID、原始日志、JUnit 与运行报告。
证据默认位于新的 `.repropatch/docker-gates/<时间>-<标识>/`；`--output` 可指定尚不存在的目录。
`--build` 可先准备镜像；缺 Docker、构建失败、测试跳过或失败均不能获得通过结论。

许可：Apache-2.0。
