# CLI、产物与错误约定

状态：**目标接口规格。** 旧实现当前仅有 run/doctor/validate-task；inspect/report及后续命令须按阶段实现，不应把下列示例当作当前软件已支持的功能。字段契约见[TASK_FORMAT](TASK_FORMAT.md)，状态／outcome见[STATE](STATE_AND_RECOVERY.md)。

## 1. 命令表

| 命令 | 阶段 | 参数与默认 | 输出／副作用 |
|---|---|---|---|
| `repropatch --version` | 已有，P1保留 | 无 | 软件和Task版本能力，stdout纯文本 |
| `repropatch validate-task TASK` | P1升级 | YAML路径 | 只做静态校验；不联网／模型／编译；合法打印task id和version |
| `repropatch doctor --image IMAGE [--json]` | P1升级 | image可省略，此时只查宿主能力 | Linux/Python/Git/Docker daemon、相关隔离参数、固定镜像与工具版本；不自动安装／pull |
| `repropatch run TASK` | P1升级 | 下表模型参数，`--json` | 创建新Run并执行；不复用同ID历史结果 |
| `repropatch inspect RUN_ID [--root DIR] [--json]` | P1新增 | root默认cwd的`.repropatch/runs` | 只读状态、阶段、预算、最后事件与产物；不恢复 |
| `repropatch report RUN_ID [--root DIR] [--format md\|json]` | P1新增 | format默认md | 向stdout展示报告；不因补丁失败让读取命令失败 |
| `repropatch export-trace RUN_ID [--root DIR]` | P2 | 可加`--output FILE`，默认stdout | 从SQLite一致性视图导出JSONL；不执行工具 |
| `repropatch resume RUN_ID [--root DIR]` | P2 | 使用原冻结模型配置；凭证仍由本地key_env读取 | 原Run恢复；不能给新Task、budget、model或image；终态拒绝 |
| `repropatch replay RUN_ID --mode trace [--root DIR]` | P2 | 默认text，可`--json` | 只读时间线；不创建执行Run |
| `repropatch replay RUN_ID --mode execution [--root DIR]` | P3 | 新输出根可`--output-root DIR` | 新Run，复用已存动作，不调用模型；原Run不变 |
| `repropatch eval --suite FILE --strategy baseline\|enhanced` | P3 | `--repeats 3`，模型参数同run | 串行独立Run和结构化汇总；两种strategy须各自执行 |

`RUN_ID` 是完整32位小写hex UUID，不支持模糊前缀匹配，避免误选目录。任意命令均可 `--help`。所有路径型CLI参数相对于调用者cwd解析，与YAML路径规则不同。`inspect/report` 若根目录不同必须显式给 `--root`；不扫描整个硬盘找Run。

### 1.1 Run模型与输出参数

| 参数 | 默认／规则 |
|---|---|
| `--model mock\|openai-compatible` | 默认mock；不自动选择付费接口 |
| `--script FILE` | mock必须；真实模型时拒绝该参数 |
| `--model-name NAME` | 真实模型必须；无默认会过时的模型名 |
| `--api-base HTTPS_URL` | 默认SDK官方端点；允许显式兼容端点，约束见Runtime |
| `--key-env NAME` | 默认`OPENAI_API_KEY`；只存名称，不存value |
| `--allow-paid-model` | 真实模型必须；一次运行授权模型请求和任务源码／日志发往选定服务，不逐次询问 |
| `--output-root DIR` | 覆盖outputs.root，只影响位置，不变task执行hash |
| `--json` | stdout最终只输出一个summary JSON；进度与诊断在stderr |

不提供 `--no-sandbox`、`--allow-any-path`、任意Docker参数、无限budget、自动联网安装或自动push选项。Task可信并不意味着可以绕过固定隔离参数。用户取消用SIGINT，不需要另建 daemon control API。

## 2. 退出码

| 退出码 | 含义 |
|---:|---|
| 0 | run的outcome为ACCEPTED且必需产物导出成功；或inspect/report/doctor等操作成功 |
| 1 | run为REJECTED、NOT_REPRODUCED、BUDGET_EXHAUSTED；eval有已评估未验收任务 |
| 2 | 命令／参数／静态Task错误，或doctor未满足前置条件；尚未形成可执行Run |
| 3 | run为ERROR、INCONCLUSIVE、RECOVERY_FAILED；查询／导出失败（ARTIFACT_EXPORT_FAILED）；eval有基础设施或不确定结果 |
| 130 | 用户取消，已尽力清理；报告CANCELLED及清理结果 |

SIGKILL 无法由应用改写退出码，也不能保证形成终态报告；P1读取时显示未完成，P2按恢复文档处理。inspect/report 读取一个REJECTED Run仍退出0，避免把数据内容与读取动作混淆。eval优先级：静态输入错误2；用户取消130；存在基础设施／不确定结果3；否则有未验收1；全部验收0。 已提交最终 outcome 后的产物导出错误不改写运行结局，但本次操作退出3；这也适用于已记录CANCELLED后的导出失败。inspect可成功读取最终事件却发现报告缺失，此时退出0并明确 artifacts_complete=false。

## 3. 产物目录

```text
<outputs.root>/<run_id>/
  task.original.yaml          原始输入，不含key
  task.resolved.json          不可变有效配置与内容身份
  run.json                    Run身份、模型标识、时间和资源所有权索引
  events.sqlite3              P1审计权威；P2再增加状态/操作/checkpoint表
  events.jsonl                从SQLite导出，记录exported_through_seq
  report.json                 最终结构化结论；未完成时可能不存在
  report.md                   面向人的派生摘要
  patch.diff                  冻结候选；没有补丁时不创建空成功产物
  candidate.manifest.json     全树字节与mode证明
  logs/                       各命令原始有界输出、模型公开消息
  evidence/                   测试发现、JUnit、基线与独立验证记录
  diagnostics/                脱敏错误与traceback
  operations/                 仅P2，大型操作请求／结果的不可变引用
  turns/                      仅P2，已完成工具组与对话引用
  checkpoints/                仅P2，完整组边界的不可变文件
  recovery/                   仅P2，恢复时保留的观察候选与诊断
```

这是允许的目录角色，不要求每次Run都生成每个文件。未进入模型阶段不生成模型日志；失败前无候选就不生成patch；没有验证时不得生成伪造“未通过测试”记录。临时Worktree／快照位于 `<workspace.root>/<run_id>/`，不在上述目录混入任意源仓库管理文件。

命令日志按operation ID命名，文件引用相对于Run根。`events.jsonl` 的导出截止序号和导出时间置于 `run.json` 的 export_metadata；JSONL每行仍只是一条Event，不插入伪Event头。最终报告保存task/image/patch哈希与证据引用；具体结果字段由[验证报告契约](VERIFICATION.md)规定。

Phase 1 `run.json` 是资源／来源索引，不是恢复权威；同意保留并不构成“支持resume”。Phase 2状态以DB为准，report／run索引落后可重建。导出结束后写临时文件再rename；不能用“最后一行JSONL”判断任务是否已完成。

默认保留全部报告、补丁、事件和有界诊断；工作区按retain处理。第一版不提供自动GC和任意路径删除命令；用户可在确认无需复核后删除整个已完成Run产物目录。未确认清理资源或待恢复Run不自动按保留策略丢弃证据。

## 4. 输出与错误样式

示意，不是本轮实际运行结果：

```json
{
  "run_id": "0123456789abcdef0123456789abcdef",
  "task_id": "negative-maximum",
  "state": "FINISHED",
  "outcome": "REJECTED",
  "reason_code": "F2P_FAILED",
  "artifact_dir": "/absolute/project/.repropatch/runs/0123456789abcdef0123456789abcdef",
  "artifacts_complete": true,
  "command_error": null
}
```

summary 中 reason_code 属于 Run 结论；command_error 为 null 或 `{code,message}`，表示这次 CLI 操作的失败，不能用 ARTIFACT_EXPORT_FAILED 覆盖已提交的运行 reason_code。artifacts_complete 只有必需导出存在且相应引用可核对时为 true；inspect 保留这一差别。

stderr错误包含稳定code、简明解释和下一步可操作信息，例如：

```text
TASK_VERSION_UNSUPPORTED: expected version 2; see docs/TASK_FORMAT.md v1 migration.
IMAGE_NOT_FOUND: fixed image is not available locally; prepare it before run.
DOCKER_UNAVAILABLE: no reachable local Docker daemon; source code was not executed on host.
MODEL_RESULT_UNKNOWN: a model request may have been billed; this run cannot be resumed safely.
```

最后一项是P2恢复错误。不要输出整个环境、鉴权头、SDK客户端repr或将日志中的控制字符原样写进终端；终端文本进行控制字符转义，原始bytes仅存受控文件。

## 5. 典型使用流程

下面命令是**目标P1验收流程**；已有v1实现应先按计划迁移。镜像创建是用户显式准备动作，不在 `run` 中触发。

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
docker build -t repropatch-cpp:local -f docker/Dockerfile docker
python scripts/init_example.py --write-task examples/tasks/negative-maximum.v2.yaml --image repropatch-cpp:local
repropatch validate-task examples/tasks/negative-maximum.v2.yaml
repropatch doctor --image repropatch-cpp:local --json
repropatch run examples/tasks/negative-maximum.v2.yaml --model mock --script examples/models/fix-negative-maximum.json --json
```

init脚本只管理已有受信任fixture，在目标repo已初始化时不重置用户数据；输出实际commit和image ID。doctor允许检查tag作为诊断便利，但Task必须存固定引用。取得CLI打印的Run ID后：

```bash
repropatch inspect RUN_ID --root .repropatch/runs --json
repropatch report RUN_ID --root .repropatch/runs --format md
```

`RUN_ID` 为待替换参数，不是假定示例UUID真实存在。真实模型使用者通过本机环境配置密钥，然后显式运行：

```bash
repropatch run examples/tasks/negative-maximum.v2.yaml --model openai-compatible --model-name MODEL_NAME --allow-paid-model
```

不把密钥赋值示例写成可误提交的字面量。目标P2恢复示例：`repropatch resume RUN_ID --root .repropatch/runs`；已FINISHED的Run须以 `run` 创建新尝试，不能“resume后改模型”。
