# Spec 2026-10-19.2 接入记录

本次只推进 **P1-01**。当前仍是 0.1.0、Task v1，真实 Docker gate 阻塞，
未将规格归档或 CI 配置更新当作目标 0.2.0 已实现。

## 输入和既有代码

用户提供 `repropatch-spec-2026-10-19-1.zip`，内部声明修订为 `2026-10-19.2`。
16 个原始文件保持原字节存入 `specs/2026-10-19.2/`，旧修订作为历史保留。
接入前分支为 `work/spec-p1-01`，HEAD 为 `ab6e4c4bbc7fea4778a993257fef1245e26543ed`，
工作树干净，无 remote。已提交的清理修复完整保留，没有重建或覆盖产品代码。
来源及产品源码哈希见 [intake.json](evidence/spec-2026-10-19.2/intake.json)。

## 已同步的决定

| 领域 | 本次接入后的方向 | 当前是否已实现 |
| --- | --- | --- |
| 自动修复 | 直接采用 OpenAI Agents SDK Runner/Responses 原生 Items，不再扩展自制循环 | 否；现有 Loop 是旧基线 |
| 补丁来源 | verify-patch 为一等入口，可接人工或外部 Agent 的补丁 | 否；CLI 不假装支持 |
| 验证优先级 | P1-02 → P1-03 → P1-06，先交付不依赖模型的固定 F2P/P2P 验收 | 尚未进入 P1-02 |
| 模型与测试 | 在 SDK 接入阶段使用公开接口及 ScriptedModel，通过后删除旧生产路径 | 未安装可选 SDK extra、未调用真实模型 |
| 审计和恢复 | P1 SQLite 单写导出；P2 仅外层三表和安全边界恢复 | 待对应阶段实施 |
| 评测 | P3 使用 Harbor 作业与产物收集，再本地验收补丁 | 未接入；不另建调度器 |
| C++ 执行器 | 仅在测量证明必要时立项 | 未实现，也不是 MVP 必做项 |

已更新根规格入口、README、架构说明、P1-01 和 ROADMAP，
避免旧路线误导后续开发。上传包内的审计快照与规格原文没有改写。

## 本轮实际检查

- 再查 Docker CLI 和常见 daemon Socket，均不可用；`repropatch doctor` 返回 2。
- 当前进程 capabilities 全为 0，NoNewPrivs=1；尝试用户命名空间映射返回
  `write failed /proc/self/uid_map: Operation not permitted`。不能把 root 身份当作 Docker 能力。
- 相关进程和清理回归：11 项通过，见 [日志](evidence/spec-2026-10-19.2/process-tests.log) 与
  [JUnit](evidence/spec-2026-10-19.2/process-tests.xml)。
- 显式 Docker gate 实际运行：4 失败、76 未选中，原因是 Docker 不可用；
  见 [日志](evidence/spec-2026-10-19.2/docker-tests.log) 与
  [JUnit](evidence/spec-2026-10-19.2/docker-tests.xml)。这些不计为 Docker 验收通过。
- 产品源码未变，本轮不重复运行整套历史测试。此前 76 通过/4 跳过仍为历史结果，
  不能转述为本轮或新版 Spec 的完整验收。
- Ruff 检查与格式检查通过；workflow YAML 结构检查通过；218 处相对文档链接全部有效。
  检查结果及“未运行远程 CI/真实模型”标记见
  [static-checks.json](evidence/spec-2026-10-19.2/static-checks.json)。

## 让下一次 Linux 验收可核查

现有 GitHub Actions 保持两个 job，没有增加自建运行器或调度层。
移除任意的覆盖率百分比门槛，改为按测试行为判定。
Python job 保存 JUnit；Docker job 保存源码 commit、Docker 版本、image ID、
固定 pytest 目录中的运行产物和 JUnit，失败时仍尝试上传产物。
这只是 workflow 配置准备，没有创建远程仓库、推送代码或执行远程 CI。

## 尚未解除的前置条件

需要一个支持本地 Docker Engine 的 Linux/amd64 执行环境。该环境准备好后运行：

```bash
docker build -t repropatch-cpp:0.1 -f docker/Dockerfile docker
REPROPATCH_DOCKER_TESTS=1 pytest -m docker -v
```

只有正确补丁、错误补丁拒绝、权限边界及超时清理真实运行后才关闭 P1-01。
之后按新版顺序进入 Task v2 和独立验收路径。
本轮没有调用付费模型，没有以宿主执行任意 Task 来补 Docker 的缺口。
