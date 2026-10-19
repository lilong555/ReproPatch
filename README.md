# ReproPatch

**面向 C++ 工程的可复现代码修复 Agent Harness。**

ReproPatch 从本地 Git 仓库的指定 commit 创建独立 Worktree，先确认缺陷确实存在，
再让模型使用少量受限工具修改源码，最后把补丁带到另一份干净 Worktree 和全新构建环境中验证。
每次运行生成补丁、命令输出、模型与工具轨迹、源码快照、SQLite/JSONL 日志和验证报告。

当前为 **0.1.0 MVP**。真实 C++ 编译、修复及错误补丁拒绝已在开发环境验证；
该环境没有 Docker，因此 **Docker 隔离端到端测试尚未在本次开发中执行**。
真实 Docker 测试已提供，必须在有 daemon 的 Linux 主机上运行后才能完成隔离验收。
具体测试数字与证据见 [测试报告](docs/TEST_REPORT.md)。未调用付费模型。

## 快速开始

需要 Linux、Python 3.12+、Git、可访问的本地 Docker Engine。
容器编译工具在镜像中安装，宿主机无需 CMake。运行命令不会自动拉取镜像。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python scripts/init_example.py
docker build -t repropatch-cpp:0.1 -f docker/Dockerfile docker
repropatch doctor
repropatch validate-task examples/tasks/negative-maximum.yaml
repropatch run examples/tasks/negative-maximum.yaml \
  --model mock --script examples/models/fix-negative-maximum.json
```

`init_example.py` 将已提供的源码初始化为独立 Git 仓库；已有 `.git` 时不会覆盖。
父项目仓库仍跟踪示例源码。源码下载包不需要携带嵌套 Git 元数据。
Mock Model 按 JSON 中预写的工具调用行动，验证 Harness 的完整流程，**不代表模型修复能力**。
没有 Docker 时 `run` 返回错误报告，不会自动改用宿主机执行任务。

### 查看结果

CLI 输出运行 ID、状态、耗时和产物目录。退出码：通过 `0`，未通过/运行错误 `1`，
参数/清单错误或 doctor 不满足条件 `2`。每次运行拥有唯一目录：

```text
.repropatch/runs/<task-id>-<run-id>/
  report.json       # 状态、基线 commit、任务、模型标识、镜像 ID、命令结果和耗时
  report.md         # 便于查看的验证摘要
  patch.diff        # 最终或未完成的候选补丁，失败时也保留
  events.jsonl      # 按序排列的模型/工具/命令审计日志
  events.sqlite3    # 同一审计事件的结构化记录
  snapshots/        # 各次评估实际使用的源码；不包含 .git
```

工作区和容器会清理，源码快照和日志保留。`report.json` 的 `isolated` 必须为 `true`
才表示确实使用了 Docker；开发测试的宿主机证据明确为 `false`。
日志可能包含项目源码和模型回复，请按项目自身的数据访问规则保管。

## 任务清单

完整示例见 [negative-maximum.yaml](examples/tasks/negative-maximum.yaml)。

```yaml
version: 1
id: negative-maximum
repository: ../cpp-bugs             # 相对于 YAML 文件
revision: HEAD                     # 开始运行时解析为不可变 commit
prompt: Fix maximum_sample for all-negative input.
editable_paths: [src/stats.cpp]     # 仅允许已有、被 Git 跟踪的 C/C++ 文件
commands:
  configure: [cmake, -S, /src, -B, /build, -DCMAKE_BUILD_TYPE=Debug]
  build: [cmake, --build, /build, --parallel, '2']
  reproduce: [ctest, --test-dir, /build, --output-on-failure, --no-tests=error, -R, '^negative_values$']
  verify: [ctest, --test-dir, /build, --output-on-failure, --no-tests=error]
failure_exit_code: 8
failure_contains: 'expected -3, got 0'
timeout_seconds: 60
max_steps: 12
```

任务清单由操作者审核，模型不能修改。命令是 argv，不通过宿主机 shell。
容器中的源码位于 `/src`，临时构建目录位于 `/build`。`configure`、`build` 必须先成功；
基线复现必须以指定非零退出码失败并满足输出标记，超时、截断输出、构建失败均不算复现。
验证时重新执行 configure、build、reproduce、verify，四条命令全部成功才标记通过。
请在 CTest 命令中保留 `--no-tests=error`，避免测试选择为空时误判。

目前只支持已有普通源码文件的精确替换，不支持新增/删除文件、修改测试、调整构建脚本、
Git submodule、symlink/LFS 或超过 32 MB 的源码快照。仓库工作目录的未提交改动不会进入任务。

## Agent 工具与模型

| 工具 | 权限和限制 |
| --- | --- |
| `read_file(path)` | 读取被 Git 跟踪的 UTF-8 文本，单文件最多 64 KB |
| `search_code(query)` | 字面量搜索被跟踪文本，最多 50 条匹配 |
| `edit_file(path, old, new)` | 仅清单内源码，old 必须精确匹配一次，禁止路径穿越及链接 |
| `run_command(name)` | 只能请求 `reproduce` 或 `verify`，每次从干净构建开始 |

默认预算最多 24 次模型完成请求，每次至多 8 个工具调用；示例为 12 次。
每条编译/测试命令具有独立超时，输出最多保留 64 KB。模型请求 60 秒超时、
最多 2048 个 completion tokens，累积请求上下文最多 1 MB，不自动重试付费请求。

提供可替换的 Python `Model` Protocol、确定性的 `MockModel`，以及使用标准工具调用格式的
`OpenAICompatibleModel`。后者适用于支持 Chat Completions 工具协议的 HTTPS 服务，
真实服务兼容性需要另行验证。API Key 只由宿主机模型客户端读取；不会写入任务或容器环境。

获得费用确认后，可由使用者自行执行：

```bash
export OPENAI_API_KEY='在本地设置，不要提交到 Git'
repropatch run examples/tasks/negative-maximum.yaml \
  --model openai-compatible --model-name YOUR_TOOL_CAPABLE_MODEL --allow-paid-model
```

可通过 `--api-base` 和 `--key-env` 替换端点及环境变量。
本次开发没有执行该命令，没有创建远程仓库或推送代码。

## 测试

宿主机测试需要 g++、CMake、CTest；也可 `pip install cmake`。所有测试使用 Mock 或模拟 HTTP，
不需要 API Key，不产生模型费用。

```bash
ruff check src tests scripts
ruff format --check src tests scripts
pytest --cov=repropatch --cov-report=term-missing

# 必须先构建镜像；显式启用后，Docker 缺失会导致测试失败
REPROPATCH_DOCKER_TESTS=1 pytest -m docker -v
```

没有 Docker 也可以跑固定内置案例并保存**真实宿主机编译证据**：

```bash
python scripts/init_example.py
python scripts/capture_fixture_evidence.py
```

这个开发脚本只接收输出路径，使用测试目录中的受信任执行器，不接受任意任务清单。
它不会证明 Docker 隔离可用，也不属于安装包中的生产执行后端。

## 工程结构

```text
src/repropatch/
  cli.py            # run / doctor / validate-task
  task.py           # 严格 YAML 解析与输入约束
  harness.py        # 复现、Agent Loop、独立验证、报告
  models.py         # 可替换模型协议和两个适配器
  tools.py          # 四个受限工具
  workspace.py      # Worktree、快照、补丁边界
  sandbox.py        # Docker 生命周期和隔离参数
  process.py        # 输出上限、超时、进程组清理
  events.py         # SQLite / JSONL 审计日志
tests/              # 单测、真实 C++ 集成、显式 Docker 集成
examples/           # C++20 缺陷仓库、任务 YAML、确定性脚本
docker/             # 编译镜像
scripts/            # 示例初始化及受信任案例取证
docs/               # 架构、验收、测试结果、后续计划
```

示例的缺陷是最大值计算错误地以 0 初始化，导致全负输入产生不存在的结果。
这是为验证 Harness 编写的真实可执行缺陷案例，不冒充来自第三方项目的历史漏洞。
回归测试覆盖负数、`INT_MIN`、正数、空输入、混合输入。

继续阅读：[架构](docs/ARCHITECTURE.md) · [安全边界](SECURITY.md) ·
[MVP 验收](docs/ACCEPTANCE.md) · [下一阶段](docs/ROADMAP.md)。

许可：Apache-2.0。
