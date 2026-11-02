# 工程路线

ReproPatch 围绕一条完整的 C++ 修复工作流组织：任务契约、模型与工具执行、隔离环境、
状态持久化、故障恢复、独立验收和交付证据。项目展示以可运行的工程能力为主，
实验为设计选择和性能优化提供后台验证。

## 交付能力

| 能力 | 工程实现 | 验证入口 |
| --- | --- | --- |
| 任务建模 | Task v2 固定源码提交、镜像、文件权限、测试身份与预算 | `validate-task`、[任务测试](../tests/test_task.py) |
| Agent 编排 | 公开 SDK Runner、原生工具调用、六工具与持久 Shell 两种模式 | [运行时测试](../tests/test_agent_runtime.py)、[Shell 契约](SHELL_FIRST.md) |
| C++ 上下文 | Tree-sitter 定义、语法引用与包含关系；修复状态和历史证据按需查询 | [结构证据状态](SEMANTIC_STATE.md)、[专项测试](../tests/test_semantic_state.py) |
| 执行控制 | Docker 非 root、断网、只读根文件系统、资源限额与归属清理 | [沙箱测试](../tests/test_process_sandbox.py)、[真实 Docker 测试](../tests/test_docker_integration.py) |
| 可恢复运行 | SQLite 事务、完整输入 Checkpoint、累计预算、原始期限和有限恢复 | [恢复测试](../tests/test_resume.py)、[恢复演示](DEMO.md) |
| 可信验收 | 基线复现、补丁往返、全新工作树与冷构建、逐项 F2P/P2P 验收 | [验收实现](../src/repropatch/verification.py)、[验收标准](ACCEPTANCE.md) |
| 运行诊断 | 阶段时间线、命令失败、用量和预算、证据完整性、恢复条件 | `diagnose`、[诊断测试](../tests/test_diagnostics.py) |
| 安装交付 | wheel 内置演示资源；CLI 修复、拒绝、恢复三场景 | `demo`、[工程验收脚本](../scripts/check_engineering_gate.py) |
| 持续集成 | 核心、SDK、真实 Docker、固定原生上下文与安装包验收 | [CI 配置](../.github/workflows/ci.yml)、[测试报告](TEST_REPORT.md) |

## 优化闭环

每项优化从运行证据中定位问题，保留基线并明确测量口径。结果同时观察独立验收、
请求与已知 Token、未知用量、分阶段耗时及资源清理。

| 已有机制 | 解决的问题 | 测量与检查 |
| --- | --- | --- |
| 持久 Shell 与 Run 内 ccache | 重复配置、编译和环境启动开销 | 自检命令耗时、缓存命中；独立验收保持冷构建 |
| C++ 结构检索与证据索引 | 大仓库定位成本、长日志重复进入上下文 | 查询结果的源码 SHA、截断与分页、模型输入大小 |
| 原生上下文压缩与稳定状态 | 长任务历史增长、恢复后信息连续性 | 压缩前后工具关联、状态摘要、预算与未知用量 |
| 失败测试优先的自检 | 在有限时间内获得高价值编译与测试反馈 | F2P/P2P 观察、自检耗时、独立验收结局 |
| 整批工具准入与预算预留 | 执行中途耗尽额度、验收缺少时间 | 累计计数、最后允许 turn、验收与清理预留 |

## 后续优先级

| 顺序 | 工作 | 完成标准 |
| --- | --- | --- |
| 1 | 目标级增量验证 | 根据 CMake target 选择相关构建与可见测试，记录选择依据、覆盖范围和分阶段耗时 |
| 2 | 编译诊断结构化 | GCC/Clang 错误位置、类别、摘要与完整日志引用一致，覆盖多行错误和输出截断 |
| 3 | 跨 Run 运维汇总 | 按任务与实现身份聚合失败原因、延迟和用量，保留未知值及每条原始证据链接 |
| 4 | 长期证据复核 | 从归档重算摘要、候选身份、用量和冷验收，给出可重复执行的核验结果 |

## 后台实验

模型对照使用独立冻结的任务、模型配置、预算、执行源码和镜像身份。首跑、恢复、
复评分和基础设施故障分别保存；工程 CI 和确定性演示的付费模型请求为零。

实验入口：[结构证据状态](SEMANTIC_STATE.md)、
[跨仓库资格](BENCHMARK_QUALIFICATION.md)、
[统一上下文对照](../benchmarks/unified-context/final-results.md)、
[云端实验](ACTIONS_RESULTS.md)。
历史发布与测试证据见[测试报告](TEST_REPORT.md)。
