# CLI、产物与错误约定

状态：**目标接口，Spec 2026-10-19.2。** 现有0.1.0只有旧版run/doctor/validate-task；以下新增接口尚未实现。Task见[TASK_FORMAT](TASK_FORMAT.md)，结果字段见[VERIFICATION](VERIFICATION.md)，状态见[STATE_AND_RECOVERY](STATE_AND_RECOVERY.md)。

## 1. 命令及阶段

| 命令 | 阶段 | 参数／默认 | 输出与副作用 |
|---|---|---|---|
| `repropatch --version` | P1保留 | 无 | 软件版本、支持Task版本 |
| `repropatch validate-task TASK` | P1升级 | YAML路径 | 仅静态校验，不调用模型／Docker／网络 |
| `repropatch doctor [--image IMAGE] [--json]` | P1升级 | 不给image只查宿主 | 诊断Linux／Git／Docker／固定镜像工具，不安装或pull |
| `repropatch run TASK` | P1升级 | engine等见下表 | 新Run：基线→SDK自动修复→独立验收 |
| `repropatch verify-patch TASK --patch FILE` | **P1新增** | 可加producer／trace／output-root／json | 新Run：固定补丁→基线→独立验收，不导入SDK或读取模型key |
| `repropatch inspect RUN_ID [--root DIR] [--json]` | P1 | root默认cwd的`.repropatch/runs` | 只读状态、证据完整性、最后事件，不恢复 |
| `repropatch report RUN_ID [--root DIR] [--format md或json]` | P1 | format默认md | stdout展示派生报告；失败Run也可正常读取 |
| `repropatch export-trace RUN_ID [--root DIR] [--output FILE]` | P2 | 默认stdout | 从SQLite一致性快照导出JSONL |
| `repropatch resume RUN_ID [--root DIR] [--pause-after-step N]` | P2 | 冻结engine／model／预算不变 | 仅恢复可核查安全Checkpoint，不重发未知操作 |
| `repropatch replay RUN_ID --mode trace [--root DIR]` | P2 | 默认人类可读，可`--json` | 只读时间线，不执行模型或工具 |
| `repropatch replay RUN_ID --mode execution [--root DIR]` | P3 | 可`--output-root DIR` | 新Run重新验证保存的补丁；不重放Shell或模型 |
| `repropatch export-harbor --suite FILE --output DIR` | P3 | 必须显式输出目录 | 生成固定Task映射、producer说明和Harbor集成配置，不启动job |
| `repropatch verify-harbor --job DIR --task-map FILE [--output-root DIR]` | P3 | 已结束本地job与可信映射必需；输出根默认cwd的`.repropatch/imports` | 新批次目录／index.json；有界导入本地patch，串行调用verify-patch；不启动producer或下载文件 |
| `repropatch eval --suite FILE --results DIR [--format md或json]` | P3 | DIR必须为含index.json的一个批次／实验目录；format默认md | 读取明确选择的样本与证据，重算并写eval.json／eval.md；不启动模型、不自建调度 |

完整RUN_ID为32位小写hex UUID；不做模糊前缀查找。CLI路径相对于cwd，YAML内路径相对于YAML所在目录。所有命令支持`--help`。inspect/report不扫描磁盘寻找Run，根不同就显式`--root`。

### 1.1 自动路径参数

| 参数 | 默认／规则 |
|---|---|
| `--engine fake或agents-sdk` | 默认fake；不会隐式产生付费请求 |
| `--mock-script FILE` | fake必需；采用SDK ScriptedModel输出项脚本；真实engine拒绝该参数 |
| `--model NAME` | agents-sdk必需；不写会变化的默认模型名 |
| `--api-base HTTPS_URL` | 默认官方SDK端点；显式其它端点不代表已认证兼容 |
| `--key-env NAME` | 默认OPENAI_API_KEY；存名称，不存value |
| `--allow-paid-model` | agents-sdk必需；授权本Run模型费用及Task源码／输出发送到该端点 |
| `--output-root DIR` | 覆盖outputs.root，位置不参与task执行hash |
| `--json` | stdout仅一条最终summary JSON；进度及诊断stderr |
| `--pause-after-step N` | P2；默认不暂停；N为累计turn数，必须大于当前已用数且小于max_steps |

fake与agents-sdk均通过同一SDK Runner；因此自动路径需要安装agent extra。纯验证用户只安装核心包。缺extra产生`ENGINE_DEPENDENCY_MISSING`与明确安装命令，不能自动改用旧手写Loop或联网安装。

不提供任意Docker参数、`--no-sandbox`、无限budget、自动push和兼容fallback开关。变更模型／预算／Task必须新建Run；resume只允许重新供应同名key_env的实际凭证，不改变来源指纹。

### 1.2 外部补丁参数

| 参数 | 默认／规则 |
|---|---|
| `--patch FILE` | 必需，普通文件，≤8MiB；复制到Run后冻结，不再次读取原文件 |
| `--producer NAME` | 可选来源标签，≤128字符；未提供为null，不作为可信身份认证 |
| `--producer-trace FILE` | 可选普通文件，≤16MiB；当作opaque数据保存，不执行、不解包、不解析为可信CommandResult |
| `--output-root DIR`、`--json` | 与run相同 |

verify-patch拒绝engine、model、key、paid、pause参数；没有Agent运行就不假装管理外部生成预算。非法／超范围patch可在PREPARING提前REJECTED，任何ACCEPTED必须具备本次原始基线与独立验证证据。报告字段producer.patch引用`producer/input.patch`，candidate.patch引用审核后的`patch.diff`；二者语法字节可不同，应用结果必须满足同一源码manifest。

### 1.3 Harbor批次与eval输入

verify-harbor的output-root是**导入批次根**，不能与run的单Run父目录混淆。每次生成新的32位hex UUID batch_id，写入`<output-root>/<batch_id>/index.json`，所有新验证Run位于该批次的`runs/<run_id>/`。命令打印batch_id、批次绝对目录和各结果计数；`inspect/report`读取子Run时使用`--root <batch-dir>/runs`。Task自身的outputs.root被此显式批次布局覆盖，不影响执行hash。

eval的results直接指向这一个批次目录，不指向Harbor原始job或多个批次的父目录，也不自动选择“最新／最好”批次。索引结构及少量手动SDK实验的同格式输入由[评测规范](TESTING_AND_EVALUATION.md#batch-index)定义。Harbor源目录仍从索引定位并核对；eval只能写该目录下派生的eval.json／eval.md，不能修改index、Run或原始trial。相同批次重复eval是只读重算加报告重导出，不是新实验。

## 2. 退出码与暂停

| 退出码 | 语义 |
|---:|---|
| 0 | run/verify-patch获得ACCEPTED且必需产物导出成功；或查询／导出／诊断成功；或明确请求的P2受控暂停已完成 |
| 1 | 执行结果REJECTED、NOT_REPRODUCED、BUDGET_EXHAUSTED；eval有完成但未验收的样本 |
| 2 | CLI／Task静态输入错误、doctor前置不满足、extra未安装、resume参数不合法；未形成可执行尝试 |
| 3 | ERROR、INCONCLUSIVE、RECOVERY_FAILED，读取／导出失败，eval含执行错误／结果不确定 |
| 130 | 用户取消；已尽力清理，记录CANCELLED与清理结果 |

只有显式`--pause-after-step`引起的成功暂停可以outcome=null且退出0；summary包含`paused=true`、`state=INTERRUPTED`和checkpoint引用。自动化不能只凭退出0声称补丁通过，应读取outcome。SIGINT是取消，不是假暂停；SDK正常结束优先走验收，可能根本没有触发指定暂停点。

SIGKILL退出状态由操作系统产生，可能没有最终报告。P1显示未完成；P2先核对安全Checkpoint和segment_open，无法安全续跑就RECOVERY_FAILED。终态Run不能resume。读取REJECTED报告时查询命令仍退出0，防止混淆读取成功与内容结论。

verify-harbor与eval采用相同聚合优先级：静态输入／未知schema／空样本集合为2；用户取消为130；存在基础设施故障、collection_failed、结果或启动状态未知、缺必需证据／未完成导入为3；其余已知但未验收的条目（含正常结束但无可用patch、not_started、REJECTED／NOT_REPRODUCED／BUDGET_EXHAUSTED）为1；非空目标集合全部完整ACCEPTED才为0。某一条的明确REJECTED不阻止继续验证后续条目；受控工作区／清理失败等使控制面不再安全时立即停止，剩余条目保留未处理。单条或批次的输出失败同样为3，不改已提交Run结局。

已提交outcome后的文件导出失败不改写原运行结局，CLI此次退出3／ARTIFACT_EXPORT_FAILED；inspect仍可读取权威事件并给`artifacts_complete=false`。

## 3. 产物目录

```text
<outputs.root>/<run_id>/
  task.original.yaml
  task.resolved.json
  run.json
  events.sqlite3
  events.jsonl
  report.json
  report.md
  patch.diff
  candidate.manifest.json
  producer/
    input.patch
    trace.bin
  native/
    input-s000001.json
    output-s000001.json
  logs/<command_id>/
    stdout.bin
    stderr.bin
  evidence/
  diagnostics/
  checkpoints/
  recovery/
```

这是角色布局，不强制每个Run都生成全部文件。producer目录仅外部输入，native仅自动路径，checkpoints/recovery仅P2。未到验证阶段就没有测试结果，未有候选就没有成功patch。日志用command_id关联；来源、path／hash／size遵守EvidenceRef。Worktree与快照位于单独workspace.root，控制元数据不挂入代码容器。

P1事件SQLite是审计权威，run.json是来源／所有权索引；P2再增加runs/checkpoints形成外层三表状态权威。不存在operations调度目录或另一套turn会话协议。SDK原生输入／输出是私有附件，不能把其中opaque reasoning内容直接放到公开报告。

JSONL只从DB导出，exported_through_seq与时间放在run.json的export_metadata，文件每行是一条Event。report JSON／Markdown从权威记录生成，临时文件+rename提交。报告丢失可重新导出；不以JSONL最后一行判断任务完成。

默认保留全部有界报告与证据，工作树按workspace.retain清理；受控暂停、未知资源和待恢复Run不能提前删。无自动GC或随意路径删除命令。分享产物前按安全文档检查任务源码、provider附件及日志；只关闭远程tracing不意味着本地产物适合直接公开。

## 4. 输出示例与诊断

以下仅示意输出结构，不是实际测试结果：

```json
{
  "run_id": "0123456789abcdef0123456789abcdef",
  "task_id": "negative-maximum",
  "input_mode": "verify-patch",
  "state": "FINISHED",
  "outcome": "REJECTED",
  "reason_code": "F2P_FAILED",
  "paused": false,
  "artifact_dir": "/absolute/project/.repropatch/runs/0123456789abcdef0123456789abcdef",
  "artifacts_complete": true,
  "command_error": null
}
```

reason_code属于Run；command_error属于这次CLI动作，不覆盖原reason。engine／producer／usage的完整定义引用VERIFICATION，不在此复制第二套报告schema。

可操作的错误信息示例：

```text
ENGINE_DEPENDENCY_MISSING: install the agent extra to use the SDK repair path.
TASK_VERSION_UNSUPPORTED: expected version 2; see docs/TASK_FORMAT.md.
IMAGE_NOT_FOUND: prepare the fixed local image before execution.
DOCKER_UNAVAILABLE: no reachable local Docker daemon; check doctor output.
FORBIDDEN_PATCH: candidate modifies protected file tests/check.cpp.
OPEN_AGENT_SEGMENT: preserve the candidate and start a new verify-patch run.
```

终端转义控制字符；不打印环境全集、鉴权头、SDK repr或不透明continuation。原始命令bytes只保存在受控文件，异常traceback在diagnostics，stderr给短错误及证据位置。

## 5. 目标使用流程

下面是**实现P1后**的操作顺序；本轮文档包不含可运行镜像或新版产品：

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
docker build -t repropatch-cpp:local -f docker/Dockerfile docker
python scripts/init_example.py --write-task examples/tasks/negative-maximum.v2.yaml --image repropatch-cpp:local
repropatch validate-task examples/tasks/negative-maximum.v2.yaml
repropatch doctor --image repropatch-cpp:local --json
repropatch verify-patch examples/tasks/negative-maximum.v2.yaml --patch candidate.patch --producer codex --json
```

candidate.patch由操作者使用已选工具生成；这里不启动Codex、不声称该外部生成过程受ReproPatch隔离。init脚本只管理受信任fixture，不重置用户仓库；doctor可接受tag诊断，但Task存实际ID/digest。输出根取生成Task中的实际路径，inspect/report在不同位置时需给`--root`。

自动路径在同一环境额外安装SDK：

```bash
python -m pip install -e '.[agent,dev]' -c requirements/constraints-py312-linux.txt
repropatch run examples/tasks/negative-maximum.v2.yaml --engine fake --mock-script examples/models/fix-negative-maximum.json --json
repropatch run examples/tasks/negative-maximum.v2.yaml --engine agents-sdk --model MODEL_NAME --allow-paid-model
```

MODEL_NAME是待替换参数；密钥通过本地key_env提供，不写进命令或Task。得到实际Run ID后可`inspect`、`report`；无模型凭证也能完成整个外部补丁验收路径。

P2可通过`run ... --pause-after-step 1`创建受控Checkpoint，再`resume RUN_ID --root DIR`；它不保证恢复每种故障。P3执行重放是`replay RUN_ID --mode execution`；P3的verify-harbor每次创建新导入索引，eval通过该索引和原始trial/collection manifest重算，缺项不重试；这不是第二个job runner。Harbor集成按[评测规范](TESTING_AND_EVALUATION.md)的固定版本pilot完成后才能使用export/eval命令，不把尚未实现的兼容性写成现状。
