# v0.4.0 四分钟工程演示

ReproPatch 是可恢复的 C++ 修复与验证系统。演示依次呈现正确候选接受、错误候选拒绝、编辑后暂停并恢复接受，展示固定输入、独立冷验收和运行证据。

示例缺陷是 `maximum_sample` 对非空全负输入返回 0。可修改文件为 `src/stats.cpp`，`negative_values` 为 F2P，`positive_values`、`empty_values`、`mixed_values` 为 P2P；CMake 与测试文件受保护。

模型使用公开 Agents SDK 的 `agents.testing.ScriptedModel`，CLI 引擎身份为 `fake`，演示摘要身份为 `scripted`。模型步骤来自本地 JSON 脚本，付费模型请求为 0；用量标记 `synthetic`，Token 数为未知。Git、C++ 编译、Docker、CTest 与恢复事务实际执行。

## 演示前准备

需要 Python 3.12+、Git 和本地 Linux amd64 Docker 引擎。WSL2 可使用启用发行版集成的 Docker Desktop Linux 引擎，源码与运行目录放在 Linux 文件系统中。依赖安装、镜像构建在现场计时前完成。

```bash
git clone https://github.com/lilong555/ReproPatch.git
cd ReproPatch
git switch --detach v0.4.0

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements/agent.txt \
  'repropatch[agent] @ https://github.com/lilong555/ReproPatch/releases/download/v0.4.0/repropatch-0.4.0-py3-none-any.whl'
python -I -m repropatch --version

docker build -t repropatch-cpp:0.1 -f docker/Dockerfile docker
repropatch doctor --image repropatch-cpp:0.1 --json
```

发布包、源码身份、镜像和原始验收记录见 [v0.4.0 证据摘要](evidence/v0.4.0/summary.json)；长期原件见 [ReproPatch-engineering-v0.4.0.zip](https://github.com/lilong555/ReproPatch/releases/download/v0.4.0/ReproPatch-engineering-v0.4.0.zip)。本地交付目录为 `/home/li/code/repropatch/deliverables/v0.4.0`。

## 四分钟主流程

| 时间 | 展示对象 | 讲解重点 |
| --- | --- | --- |
| 0:00–0:40 | 示例 Task、固定 commit、镜像 ID、授权文件与 F2P/P2P | 修复输入与完成标准组成可执行合同 |
| 0:40–1:30 | `doctor`、`demo --scenario all` 与 `summary.md` | 三种结局使用确定性模型步骤，执行链保存真实证据 |
| 1:30–2:20 | `patch.diff`、`candidate.manifest.json`、独立测试观察 | 候选从固定基线应用到新工作树，冷构建后逐项验收 |
| 2:20–3:10 | recovery 的暂停记录、Checkpoint、Run ID、计数与期限 | 同一 Run 续跑，基线与编辑各一次，预算和事件前缀连续 |
| 3:10–4:00 | rejection 的 `diagnose`、JUnit 与原始日志 | `F2P_FAILED` 可以追到声明测试的实际失败 |

现场执行：

```bash
DEMO=.repropatch/demo-v0.4.0-01
repropatch doctor --image repropatch-cpp:0.1 --json
repropatch demo --output "$DEMO" --image repropatch-cpp:0.1 --scenario all --json
sed -n '1,55p' "$DEMO/summary.md"
```

`--output` 使用新目录，重复演示将 `DEMO` 改为 `.repropatch/demo-v0.4.0-02`。`repair`、`rejection`、`recovery` 可作为 `--scenario` 的单独取值。

| 场景 | 预期结局 | 检查对象 |
| --- | --- | --- |
| `repair` | `ACCEPTED / VERIFICATION_PASSED` | F2P/P2P、补丁往返、候选清单、冷验收与清理 |
| `rejection` | `REJECTED / F2P_FAILED` | 错误候选的独立失败证据 |
| `recovery` | `ACCEPTED / VERIFICATION_PASSED` | 暂停与恢复 Run ID 相同，基线与编辑各一次，步骤 3→5、工具 3→4、原期限与事件前缀保留 |

三场景符合预期时，摘要 `status` 为 `passed`，`demo` 退出码为 0。场景检查失败返回 3，准备或参数错误返回 2。`rejection` 的预期拒绝属于演示通过条件。

## 追到失败证据

从摘要自动取拒绝场景的 Run ID；`--root` 指向该场景下所有 Run 的父目录：

```bash
ROOT="$DEMO/runs/rejection"
RUN_ID=$(python -c 'import json,sys; s=json.load(sys.stdin); print(next(r["run_id"] for r in s["runs"] if r["scenario"] == "rejection"))' < "$DEMO/summary.json")
repropatch inspect "$RUN_ID" --root "$ROOT" --json
repropatch diagnose "$RUN_ID" --root "$ROOT" --json
repropatch replay "$RUN_ID" --root "$ROOT" --mode trace --json
```

阅读 `"$ROOT/$RUN_ID/report.json"` 中的 `independent.tests`。`negative_values` 的 `observed_status` 为 `failed`，其 `result.path` 指向原始 JUnit；命令中的 `stdout_log.path`、`stderr_log.path` 指向原始双流日志。所有证据相对路径以 Run 的 `artifact_directory` 为根解析。

| 产物 | 展示内容 |
| --- | --- |
| `task.resolved.json` | commit、镜像、权限、测试、资源与预算 |
| `patch.diff`、`candidate.manifest.json` | 修改内容、完整源码 SHA-256、字节大小、Git mode |
| `events.sqlite3` | 已提交事件、阶段、累计用量与 Checkpoint 引用 |
| `checkpoints/` | 下一完整 SDK 输入、源码、补丁、工具及实现指纹 |
| recovery 的 `paused-report.json`、`paused-events.jsonl` | 暂停状态和恢复前事件前缀；位置由演示摘要中的证据引用给出 |
| 原始 stdout/stderr、inventory、JUnit | 基线签名、测试身份、实际执行与拒绝原因 |
| `report.json`、`report.md`、`run.json` | 结局、清理状态和派生索引 |

`inspect`、`diagnose`、`replay` 从只读 SQLite 快照查询。`export-trace` 将轨迹发布到 Run 之外的新文件；`report` 持有 Run 锁，从已提交事实重建派生报告、JSONL 和索引。

```bash
mkdir -p .repropatch/exports
repropatch export-trace "$RUN_ID" --root "$ROOT" \
  --output .repropatch/exports/v0.4.0-rejection-01.jsonl
repropatch report "$RUN_ID" --root "$ROOT" --format json
```

## 独立补丁入口

`verify-patch` 使用核心依赖完成基线复现与独立验收。人工、外部 Agent 或已有脚本生成的补丁都可进入同一流程。在上述 v0.4.0 源码目录中执行：

```bash
python scripts/init_example.py \
  --write-task .repropatch/tasks/negative-maximum.yaml --image repropatch-cpp:0.1
repropatch validate-task .repropatch/tasks/negative-maximum.yaml
repropatch verify-patch .repropatch/tasks/negative-maximum.yaml \
  --patch examples/patches/negative-maximum.correct.patch \
  --producer local --output-root .repropatch/external-patches --json
repropatch verify-patch .repropatch/tasks/negative-maximum.yaml \
  --patch examples/patches/negative-maximum.wrong.patch \
  --producer local --output-root .repropatch/external-patches --json
```

正确补丁预期退出 0，结局为 `ACCEPTED`；错误补丁预期退出 1，结局为 `REJECTED / F2P_FAILED`。核心安装的独立正反例记录由 [v0.4.0 证据摘要](evidence/v0.4.0/summary.json)提供。

## 独立暂停与恢复

需要停留在暂停点讲解时，使用同一示例 Task 和固定脚本：

```bash
repropatch run .repropatch/tasks/negative-maximum.yaml \
  --engine fake --mock-script examples/models/fix-negative-maximum.json \
  --output-root .repropatch/interview-resume --pause-after-step 3 --json
```

脚本依次读取、搜索和编辑 `src/stats.cpp`，在累计第三步后的完整输入边界提交 Checkpoint。将返回的 `run_id` 代入以下命令，保持相同安装环境与原运行期限：

```bash
repropatch diagnose RUN_ID --root .repropatch/interview-resume --json
repropatch resume RUN_ID --root .repropatch/interview-resume --json
repropatch inspect RUN_ID --root .repropatch/interview-resume --json
```

恢复重建已核验源码并执行剩余步骤，沿用已存基线、累计预算和原始 deadline。暂停期间计入原 wall deadline；持久 Shell 恢复重建源码，`/build`、`/tmp` 与编译缓存重新开始。

## 源码与验证入口

[verify_candidate](../src/repropatch/verification.py) 与 [apply_candidate](../src/repropatch/workspace.py)解释候选与独立验收；[save_checkpoint](../src/repropatch/recovery.py) 与 [EventLog](../src/repropatch/events.py)解释持久化顺序；[进程执行](../src/repropatch/process.py)、[DockerSandbox](../src/repropatch/sandbox.py)和[持久修复容器](../src/repropatch/repair_sandbox.py)解释退出与资源归属。

[工程门禁](../scripts/check_engineering_gate.py)通过安装后的 CLI 核对三场景、恢复计数和只读文件指纹，`--require-installed-wheel` 核验安装身份。[日常 CI](../.github/workflows/ci.yml)包含 Core、SDK、真实 Docker 与安装包三个工程作业；原生上下文检查通过手动参数 `native_context=true` 启用。

深入设计问答与简历表达见[面试材料](INTERVIEW.md)，配置见[工程指南](ENGINEERING.md)，历史真实仓库轨迹见[评测索引](../benchmarks/README.md)。
