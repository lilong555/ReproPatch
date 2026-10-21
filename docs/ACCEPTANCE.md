# MVP 验收标准

下表是 0.1.0 基线检查，不等于已满足新版 Spec 的目标 MVP。
0.2.0 的完整验收以 [2026-10-19.2](../specs/2026-10-19.2/docs/TESTING_AND_EVALUATION.md) 为准。

| 编号 | 标准 | 验证途径 |
| --- | --- | --- |
| A1 | 可安装 CLI，解析严格 YAML，错误输入有明确退出码 | CLI/Task 单测、wheel 安装冒烟 |
| A2 | 支持读、搜、精确改源码、固定命令、有限 Agent Loop | 工具策略与 Harness 测试 |
| A3 | 每次独立 detached Worktree，输入仓库不被修改，退出清理 | Worktree 与真实 C++ 集成 |
| A4 | 生产路径只在受限 Docker 执行，不静默回退宿主机 | 参数单测、缺 Docker 错误路径及真实 Docker 容器边界测试通过 |
| A5 | 原始构建成功、指定测试确实失败并满足退出码/输出标记 | 真实 CMake/CTest 原始负数案例 |
| A6 | 正确补丁在新 Worktree/构建环境通过复现和回归 | 真实宿主 C++ 集成与 Docker 端到端测试通过 |
| A7 | 错误/空补丁、超时、编译失败、回归失败、超预算均不标记通过 | 单测和错误补丁真实编译集成 |
| A8 | Diff、事件、耗时、报告可查，正常 SQLite/JSONL 一致 | 事件逐条核对及固定案例证据 |
| A9 | 模型可替换，默认测试不调用收费 API | Mock、模拟 HTTP、显式付费开关 |
| A10 | README、架构、安全边界、实际测试报告与后续计划齐全 | 交付文件 |

Docker 完整验收必须执行：

```bash
docker build -t repropatch-cpp:0.1 -f docker/Dockerfile docker
REPROPATCH_DOCKER_TESTS=1 pytest -m docker -v
```

成功时应有 4 个真实 Docker 测试通过：完整修复、错误补丁拒绝、容器权限/网络/只读/凭据边界、
超时后容器删除。显式启用时不应跳过 Docker 缺失。
2026-10-20 的实际结果为 **4 项通过、0 项跳过**；对应运行报告的 `isolated=true`。
原始证据见 [Docker 验收摘要](evidence/p1-01-wsl/docker-gate/summary.json) 和
[测试报告](TEST_REPORT.md)。该结论适用于 0.1.0 的上述门槛。当前 Task v2、源码与生命周期、独立验证器、SDK 自动修复及权威报告查询已完成；0.2.0 的离线门槛与真实模型修复均通过，见 [P1-08](P1-08.md)。

当前 Task v2 的输入门槛与原始证据见 [P1-02](P1-02.md)；源码与生命周期契约见 [P1-03A](P1-03A.md)、[P1-03B](P1-03B.md)；当前测试结果见 [测试报告](TEST_REPORT.md)。
