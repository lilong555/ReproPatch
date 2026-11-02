# 工程验收

交付验收覆盖从安装到结果复核的完整路径。确定性演示使用公开
`agents.testing.ScriptedModel`，源码编译、Docker 隔离、状态恢复与独立验收均执行真实代码。
真实模型的修复能力另由冻结实验衡量。

## 验收矩阵

| 编号 | 标准 | 验证入口 |
| --- | --- | --- |
| E1 | wheel/sdist 包含 CLI、实现与演示资源，项目目录外可调用 | CI 的 wheel 安装与 `--require-installed-wheel` 工程 gate |
| E2 | `doctor` 给出工具、Docker、镜像检查及后续动作；Task v2 校验严格 | [CLI 测试](../tests/test_engineering_cli.py)、[Task 测试](../tests/test_task.py) |
| E3 | 正常修复先复现缺陷，导出候选，再经全新工作树和冷构建获得 `ACCEPTED` | `demo --scenario repair` |
| E4 | 错误候选即使声明修复完成，也由独立测试裁决为 `REJECTED / F2P_FAILED` | `demo --scenario rejection` |
| E5 | 编辑后的安全 Checkpoint 可恢复同一 Run；基线、编辑各执行一次，预算与期限连续 | `demo --scenario recovery`、[恢复测试](../tests/test_resume.py) |
| E6 | `inspect`、`diagnose`、`replay`、`export-trace` 保持原 Run 全部文件字节不变 | 工程 gate 文件指纹比对、[诊断测试](../tests/test_diagnostics.py) |
| E7 | 证据缺失或摘要损坏可诊断，数据库已提交结局与证据状态分别呈现 | [报告测试](../tests/test_events_reports.py)、[轨迹测试](../tests/test_trace.py) |
| E8 | 模型用量保持已知、未知、合成三类语义；累计预算与整批工具准入可核验 | [SDK 契约](../tests/test_sdk_contract.py)、[运行时测试](../tests/test_agent_runtime.py) |
| E9 | 真实容器验证非 root、断网、只读权限、输出限额、超时与派生进程清理 | `scripts/check_docker_gate.py` |
| E10 | 基线与候选都核对固定测试身份；跳过、缺失和执行故障明确留证 | [独立验收测试](../tests/test_verification.py)、[原生测试](../tests/test_native_ctest_runtime.py) |
| E11 | 源码、补丁和执行环境有身份记录，核心查询与独立补丁验收只依赖核心安装 | [源码完整性](../tests/test_source_integrity.py)、[可选依赖测试](../tests/test_sdk_optional.py) |
| E12 | README、演示、架构、工程决策、路线和测试证据入口完整 | [工程说明](ENGINEERING.md)、[测试报告](TEST_REPORT.md) |

## 可重复执行

在 Python 3.12 环境安装固定依赖：

```bash
python -m pip install -c requirements/agent.txt -e '.[agent,semantic,dev]' cmake==4.4.4
ruff check src tests scripts
ruff format --check src tests scripts
pytest -m 'not docker and not sdk'
pytest -m 'sdk and not docker'
```

Docker gate 构建工具链镜像，并执行指定的真实容器用例。显式启用时，Docker 或镜像缺失会使验收失败。

```bash
python scripts/check_docker_gate.py --build \
  --output .repropatch/acceptance/docker
python -m build
python -m pip install --force-reinstall --no-deps dist/*.whl
python scripts/check_engineering_gate.py \
  --image repropatch-cpp:0.1 \
  --output .repropatch/acceptance/engineering \
  --require-installed-wheel
```

每次验收使用新的输出目录，保留原始结果。工程 gate 的 `summary.json` 记录安装身份、
实现 SHA-256、镜像 ID、三个场景的终态、原 Run 文件指纹及每条 CLI 命令的退出码。
`queries/` 保存命令标准输出、标准错误和导出的事件；`demo/` 保存独立 Run、基线、
候选、Checkpoint 与验收证据。

CI 执行相同入口，并上传 `python-cpp-evidence`、`sdk-contract-evidence`、
`docker-gate-evidence`、`engineering-evidence` 和 `context-native-evidence`。
当前执行结果与历史证据统一从[测试报告](TEST_REPORT.md)访问。
