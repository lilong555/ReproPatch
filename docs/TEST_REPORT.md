# MVP 实际测试报告

测试日期：2026-10-19。版本：0.1.0。测试使用 Mock Model 和模拟 HTTP，未调用付费服务。

**结论：74 项通过，3 项真实 Docker 测试未运行。**
真实 C++ 编译、原始复现、修复、独立验证和错误补丁拒绝均已执行。
Docker 路径已经实现并经过参数/生命周期单测，但当前环境无法启动容器，隔离验收尚未完成。

## 环境

| 工具/条件 | 实际值 |
| --- | --- |
| Python | 3.12.14 |
| Git | 2.51.1 |
| g++ | 13.3.0，C++20 |
| CMake / CTest | 4.4.4，通过 Python 包安装 |
| pytest | 9.1.1 |
| coverage | 7.16.2，最终以 pure Python tracing 复核 |
| PyYAML | 6.0.3 |
| Docker CLI / daemon Socket | 均不存在 |
| Linux capabilities | 全为 0，NoNewPrivs=1 |

宿主机 fixture 使用的是项目内受信任源码，报告中的 `isolated=false`。
它不是生产执行后端，也不能证明 Docker 隔离参数在真实 daemon 上生效。

## 最终运行

```bash
ruff check src tests scripts
ruff format --check src tests scripts
coverage run --timid --source=src/repropatch -m pytest -q --junitxml=final-tests.xml
coverage json -o final-coverage.json
coverage report
```

- Ruff 检查与格式检查通过，21 个 Python 文件符合格式要求。
- Pytest 共收集 77 项：74 通过、3 跳过、0 失败、0 错误。
- 最终 XML 总耗时 8.279 秒；测试终端输出见原始日志。
- 语句覆盖率 **640 / 694 = 92.22%**。该数值包含 mocked Docker 代码执行，
  **不是容器安全性通过率**。不以覆盖率代替真实隔离测试。
- 本环境默认覆盖采集器曾将未执行的异常路径标为已覆盖，因此最终使用 `--timid`
  重新运行测试并采集以上数字；不采用较高的初始结果。

原始证据：[JUnit XML](evidence/final-tests.xml)、[测试输出](evidence/final-tests.log)、
[覆盖率 JSON](evidence/final-coverage.json)。开发环境路径和时间戳按原始输出保留。

## C++ 真实运行证据

运行 ID：`negative-maximum-ead30b400a42`。
基线 commit：`bdbeddbe6e9bf18cdd161d9698f2cb5dc66e6ad6`。
该 fixture 的 Git 历史另外保存在 `evidence/example-repo.bundle` 中。

通过固定脚本实际运行：

```bash
python scripts/init_example.py
python scripts/capture_fixture_evidence.py
```

| 阶段 | 配置退出码 | 编译退出码 | 复现退出码 | 完整回归退出码 |
| --- | ---: | ---: | ---: | ---: |
| 原始版本 | 0 | 0 | 8，出现 `expected -3, got 0` | 此阶段不执行 |
| Agent 自查 | 0 | 0 | 此自查运行完整回归 | 0 |
| 独立 Worktree | 0 | 0 | 0 | 0，4 个 CTest 用例通过 |

实际候选补丁仅把 `int best = 0;` 改为 `int best = samples.front();`，
保留空输入检查。回归包含全负数、INT_MIN、正数、空输入及正负混合输入。
Mock 共完成 5 次 turn、4 次工具调用，完整运行耗时 **3.385 秒**。
这是该机器上的一次小型 fixture 运行，不是性能基准或模型能力指标。

另一个真实编译集成测试把初值改为 `-1`，独立验证确实拒绝了该错误补丁。
空补丁和预算耗尽也不会被接受为通过。

原始产物：[运行报告](evidence/trusted-fixture/report.md)、
[结构化报告](evidence/trusted-fixture/report.json)、
[实际 diff](evidence/trusted-fixture/patch.diff)、
[事件轨迹](evidence/trusted-fixture/events.jsonl)。目录中同时提供 SQLite 和原始源码快照。

## Docker 验收状态

默认测试中的 3 项 Docker 测试具有显式开关，没有 daemon 时不会被算作通过。
另行显式尝试了一项真实端到端测试：

```bash
REPROPATCH_DOCKER_TESTS=1 pytest -q \
  tests/test_docker_integration.py::test_docker_cpp_end_to_end
```

结果是 **1 项失败，原因为 Docker 不可用**，Harness 返回：
`Docker is unavailable; no host fallback is permitted`。
CLI 的 `doctor` 返回 2，`run` 返回 1 并留下错误报告，没有执行宿主机降级路径。

证据：[doctor](evidence/doctor.json)、[Docker gate 日志](evidence/docker-gate.log)、
[gate XML](evidence/docker-gate.xml)、[CLI 错误报告](evidence/docker-unavailable-report.json)。

待在 Docker 主机执行的测试是：真实修复端到端、非 root/断网/只读/凭据边界、超时后删除容器。
`.github/workflows/ci.yml` 已配置独立 Docker job，但未推送或触发远程 CI，不能声称 CI 已通过。

## 开发里程碑与修复

| 里程碑 | 实际结果 | 发现及处理 |
| --- | --- | --- |
| 第一轮实现 | 55 通过，2 失败 | 真实集成找不到虚拟环境内 CMake；修正受信任测试执行器的工具定位 |
| 第二轮 | 66 通过，1 失败，3 跳过 | CTest 4 摘要文本变化；改为核对成功摘要和各用例名，避免绑死完整文本 |
| 第三轮 | 67 通过，3 跳过 | 完整正确补丁及错误补丁真实编译路径通过 |
| 审查补强 | 71 通过，3 跳过 | 增加异常/预算耗尽保留 diff、镜像漂移拒绝、错误清单拒绝 |
| 最终复核 | 74 通过，3 跳过 | CLI 退出码、模型费用开关、安装包验证；用独立 tracing 方式复核覆盖率 |

原始中间记录保留为 `evidence/milestone-1.xml` 至 `milestone-4.xml`。

## 安装与打包验证

`python -m build` 成功生成 sdist 和 wheel。在另一份全新虚拟环境中安装 wheel 后，
`repropatch --version` 输出 0.1.0，`python -m repropatch --help` 正常，
`repropatch validate-task` 对示例清单返回有效。
源码包包含 README、架构、验收、安全边界、后续计划、全部测试及示例。

## 尚未验证或尚未实现

真实 Docker 隔离、真实模型服务兼容性、真实开源 C++ bug 成功率尚未验证。
C++ 独立执行器、事件溯源恢复、Checkpoint 和轨迹重放尚未实现，均列入下一阶段。
当前审计日志正常结束时一致，突然崩溃后的 SQLite/JSONL 尾部一致性不作保证。
未创建 GitHub 仓库、未推送、未产生付费模型请求。
