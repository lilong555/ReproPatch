# 零密钥工程演示

`repropatch demo` 使用公开 OpenAI Agents SDK 的 `ScriptedModel` 驱动真实 Harness、Git 工作树和 Docker，展示成功修复、错误候选拒绝、暂停恢复三个场景。演示保存真实构建、测试、状态和证据，模型步骤来自本地脚本，API 密钥和付费模型请求均为零。

实现：[demo.py](../src/repropatch/demo.py)、[harness.py](../src/repropatch/harness.py)、[models.py](../src/repropatch/models.py)。验证：[CLI 合同](../tests/test_engineering_cli.py)、[真实 Docker 流程](../tests/test_docker_integration.py)、[工程门禁](../scripts/check_engineering_gate.py)。

## 准备与运行

需要 Python 3.12+、Git 和 Linux amd64 Docker 引擎。WSL2 可使用启用发行版集成的 Docker Desktop Linux 引擎。项目与运行目录放在 Linux 文件系统中。

在项目根目录执行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[agent,semantic]'

docker build -t repropatch-cpp:0.1 -f docker/Dockerfile docker
repropatch doctor --image repropatch-cpp:0.1 --json
repropatch demo --output .repropatch/demo --image repropatch-cpp:0.1 --scenario all --json
```

默认镜像为 `repropatch-cpp:0.1`，默认场景为 `all`，默认输出目录为 `.repropatch/demo`。镜像提前构建；演示通过本地实际镜像身份固定运行环境。`--output` 使用新目录，重复运行可改为 `.repropatch/demo-2`。

实现：[cli.py](../src/repropatch/cli.py)、[Task 镜像解析](../src/repropatch/task.py)、[编译镜像](../docker/Dockerfile)。验证：[参数与预检合同](../tests/test_engineering_cli.py)、[镜像与容器身份](../tests/test_docker_integration.py)。

## 三个场景

| 场景 | 执行内容 | 预期证据 |
| --- | --- | --- |
| `repair` | 复现原始缺陷，经 SDK 工具修改实现，冻结候选并独立验收 | `ACCEPTED`，F2P/P2P 通过、候选与源码清单、容器清理确认 |
| `rejection` | 交付错误候选并执行同一验收链 | `REJECTED`，明确拒绝原因与原始失败证据 |
| `recovery` | 在完整 SDK 输入边界暂停，从已提交 Checkpoint 续跑并验收 | 暂停阶段、Checkpoint、同一 Run 的恢复记录和最终验收 |
| `all` | 顺序执行上述三个场景 | 各场景的 Run ID、结局和检查结果 |

场景可单独执行，输出目录分别保存：

```bash
repropatch demo --output .repropatch/demo-repair --image repropatch-cpp:0.1 --scenario repair --json
repropatch demo --output .repropatch/demo-rejection --image repropatch-cpp:0.1 --scenario rejection --json
repropatch demo --output .repropatch/demo-recovery --image repropatch-cpp:0.1 --scenario recovery --json
```

错误候选的拒绝证据是 `rejection` 的检查目标。各场景符合预期时，演示摘要 `status` 为 `passed`，CLI 返回 0；场景检查失败返回 3，准备或参数错误返回 2。每个 Run 的 `outcome/reason_code` 提供具体的修复结局。

实现：[demo.py](../src/repropatch/demo.py)、[cli.py](../src/repropatch/cli.py)、[verification.py](../src/repropatch/verification.py)。验证：[演示 CLI 退出码](../tests/test_engineering_cli.py)、[正确与错误候选判定](../tests/test_docker_integration.py)。

## 证据检查

从演示 JSON 获取 Run ID 和证据目录。以下 `PATH` 是包含各 Run 目录的根路径，`RUN_ID` 是该目录内的运行身份：

```bash
repropatch inspect RUN_ID --root PATH --json
repropatch diagnose RUN_ID --root PATH --json
repropatch replay RUN_ID --root PATH --mode trace --json
```

`inspect` 查看已提交的阶段、结局和完整性。`diagnose` 聚合阶段、证据、用量与恢复条件；其退出码按证据完整性判定。`replay` 按事件序号呈现轨迹与证据引用。这三个入口从只读 SQLite 快照查询原 Run。

实现：[reports.py](../src/repropatch/reports.py)、[diagnostics.py](../src/repropatch/diagnostics.py)、[trace.py](../src/repropatch/trace.py)。验证：[报告查询](../tests/test_events_reports.py)、[诊断 CLI](../tests/test_engineering_cli.py)、[只读轨迹](../tests/test_trace.py)。

需要外部 JSONL 轨迹时，提前准备目录并使用新文件：

```bash
mkdir -p .repropatch/exports
repropatch export-trace RUN_ID --root PATH --output .repropatch/exports/demo-trace.jsonl
```

派生报告可从已提交事实重建：

```bash
repropatch report RUN_ID --root PATH --format json
```

`report` 持有 Run 锁并重新导出报告、JSONL 与索引；原始事件和最终结局保留。轨迹导出发布到 Run 之外的新文件。

实现：[trace.py](../src/repropatch/trace.py)、[reports.py](../src/repropatch/reports.py)。验证：[轨迹发布](../tests/test_trace.py)、[报告重建](../tests/test_events_reports.py)。

### 重点产物

| 产物 | 检查内容 | 实现与验证 |
| --- | --- | --- |
| `task.resolved.json` | 实际 commit、镜像、权限、测试和预算 | [task.py](../src/repropatch/task.py) · [Task 测试](../tests/test_task.py) |
| `events.sqlite3` | 阶段、预算、工具批次、命令与 Checkpoint 事务 | [events.py](../src/repropatch/events.py) · [事务测试](../tests/test_recovery.py) |
| 候选 patch 与 SourceManifest | 实际修改、SHA-256、字节大小、Git mode 与往返核验 | [workspace.py](../src/repropatch/workspace.py) · [源码完整性](../tests/test_source_integrity.py) |
| 原始 stdout/stderr、JUnit 与 inventory | 基线失败、构建结果、F2P/P2P 实际执行和测试身份 | [verification.py](../src/repropatch/verification.py)、[process.py](../src/repropatch/process.py) · [验证器测试](../tests/test_verification.py) |
| `checkpoints/` 与 SDK 原生附件 | 下一完整输入、源码与配置指纹、恢复前后的模型和工具身份 | [recovery.py](../src/repropatch/recovery.py)、[agent_runtime.py](../src/repropatch/agent_runtime.py) · [暂停恢复](../tests/test_resume.py) |
| `report.json`、`report.md`、`run.json` | 已提交结局、用量、清理和派生产物完整性 | [reports.py](../src/repropatch/reports.py) · [报告测试](../tests/test_events_reports.py) |

演示用量标记为 `synthetic`，Docker 命令、CTest 和恢复事务保留实际执行证据。检查结果时同时阅读候选身份、验收结局、证据完整性与资源清理。

## 独立暂停与恢复

需要停留在暂停点检查产物时，先生成示例 Task，再执行本地脚本：

```bash
python scripts/init_example.py --write-task .repropatch/tasks/negative-maximum.yaml --image repropatch-cpp:0.1
repropatch run .repropatch/tasks/negative-maximum.yaml --engine fake --mock-script examples/models/fix-negative-maximum.json --output-root .repropatch/runs --pause-after-step 3 --json
```

脚本依次读取、搜索和编辑 `src/stats.cpp`，在累计第三步之后的完整输入边界提交 Checkpoint。返回的暂停摘要包含 `paused` 与 `checkpoint`。保持相同安装环境，使用 Run ID 继续：

```bash
repropatch diagnose RUN_ID --root .repropatch/runs --json
repropatch resume RUN_ID --root .repropatch/runs --json
repropatch inspect RUN_ID --root .repropatch/runs --json
```

恢复沿用同一 Run、已核验基线、累计预算和原始期限，核对完整源码后执行剩余脚本与独立验收。源码、配置或证据分歧保留为明确诊断。

实现：[recovery.py](../src/repropatch/recovery.py)、[示例脚本](../examples/models/fix-negative-maximum.json)。验证：[剩余步骤与预算连续性](../tests/test_resume.py)、[真实 Docker 恢复](../tests/test_docker_integration.py)。

## 工程门禁

工程门禁执行 `all` 三场景，核对场景结局、证据与 `inspect/diagnose/replay/export-trace` 对原 Run 的只读性。本地快捷入口直接核验当前安装环境，支持 editable 安装：

```bash
python scripts/check_engineering_gate.py --image repropatch-cpp:0.1 --output .repropatch/engineering-evidence
```

交付包验收先构建并安装 wheel，再通过 `--require-installed-wheel` 核验安装来源：

```bash
python -m pip install build
python -m build
python -m pip install --force-reinstall --no-deps dist/*.whl
python scripts/check_engineering_gate.py --image repropatch-cpp:0.1 --output .repropatch/engineering-wheel-evidence --require-installed-wheel
```

门禁输出使用新目录，保存安装身份、命令、场景与证据记录。CI 的 `docker-integration` 在 Docker 门禁后按上述顺序构建、安装和验收 wheel，并上传 `engineering-evidence` 与 `dist/`。输出 `summary.json` 保存检查结果，完整测试结果、场景结局与耗时见[测试报告](TEST_REPORT.md)。

入口：[check_engineering_gate.py](../scripts/check_engineering_gate.py)、[CI](../.github/workflows/ci.yml)。相关验证：[CLI 合同](../tests/test_engineering_cli.py)、[Docker 集成](../tests/test_docker_integration.py)。

更完整的配置、状态和优化指标见[工程指南](ENGINEERING.md)，真实仓库实验与原始记录见[评测索引](../benchmarks/README.md)。
