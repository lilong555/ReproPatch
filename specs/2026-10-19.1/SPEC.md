# ReproPatch — 项目规格总纲

规格日期：2026-10-19。规格修订：`2026-10-19.1`。目标 Task 格式：`version: 2`。

**交付性质：可实施的设计规格，不是已实现功能清单。** 本轮只创建规格、示例和开发计划，不修改产品代码、不运行付费模型、不发布仓库。既有源码和历史证据的准确状态见[CURRENT_STATE](docs/CURRENT_STATE.md)。

## 1. 项目定位

ReproPatch 是面向 Linux、Docker、Git、CMake/CTest 的 C++ 代码修复 Agent Harness。它将固定版本的缺陷描述转为一次有预算的修复实验：先证明原始问题符合复现契约，让模型在受控环境中提出并修改源码，再将候选补丁带到原始 commit 的新工作区和空构建环境，独立验证，输出补丁、证据与轨迹。

目标用户是维护 C++ 项目的个人／小团队开发者，以及研究 Coding Agent 执行可靠性的工程师。第一批场景是可离线构建、具有明确失败测试的函数／库级缺陷。CI 失败日志可以作为 bug.description 的输入材料；自动抓取 GitHub Issue／CI、创建 PR 和替用户合并均不属于 MVP。

项目的展示价值是让权限、状态、预算、失败分类和验收证据彼此一致，而不是单纯展示一个能调用工具的聊天循环。现有框架已有沙箱、事件和评测能力；差异在于对固定 C++ 修复契约的集中实现与可核查实验，详见[决策与调研](docs/DECISIONS.md)。

## 2. 可复现性的准确含义

锁定源 commit、镜像内容、任务契约、补丁、工具链、预算和 Harness 版本，使他人能够重新运行相同条件并比较结果。它不保证再次调用远程模型得到逐字相同的响应，也不保证不同内核／CPU／系统时间下 stdout 或耗时逐位一致。

区分三个产物：Trace Replay 只重看历史；Execution Replay 重新执行已存动作／补丁；重新调用模型是新的实验。`ACCEPTED` 表示冻结的 F2P/P2P 验收契约全部通过，不能外推成所有输入都正确、完全防御恶意源码或可以自动合并。

## 3. 本轮现状与后续版本

当前规格目录初始为空；在先前工作目录发现既有 0.1.0 实现，因此本设计是**已有 MVP 的收敛与演进方案**。已有 Python 循环、Worktree、Docker 执行代码、Mock 和 C++ fixture；Docker 路径和真实模型尚无成功验收证据。源码有未提交修改，后续实现必须先保留并审查，不能覆盖或用旧测试记录证明它们已通过。

| 阶段 | 对应目标版本 | 必需结果 | 明确后置 |
|---|---|---|---|
| Phase 0 | 本规格 | 现状检查、MVP 冻结、核心契约、任务计划、规格一致性检查 | 不生成空框架或大量业务代码 |
| Phase 1 | 0.2.0 | Task v2、固定输入、Docker 端到端、基础工具、一个真实模型接口、F2P/P2P 独立验证、报告与审计 | Checkpoint、Resume、复杂事务恢复、正式评测 |
| Phase 2 | 0.3.0 | 状态事务、操作核对、Checkpoint、Resume、Trace Replay、针对性故障注入 | 分布式调度／Exactly Once |
| Phase 3 | 0.4.0 → 满足门槛后 1.0.0 | 固定小任务集、同条件对照、成本报告、Execution Replay、公开文档及发布门槛 | 无证据的大规模 benchmark／跨平台支持 |
| Phase 4 | 按需 | 经实测证明需要的 C++ 执行器、其它模型／上下文优化、Harbor 接入等 | 不是 1.0 的必做清单 |

版本是建议的目标标签，不能在阶段未验收时把其功能宣称可用。软件版本、Task version、数据库 schema_version、事件 schema_version 分开演进。

## 4. MVP 的准确范围

MVP 支持一个本地、Git 元数据由操作者信任的仓库，一个完整 commit，一个已在本机准备的固定镜像；Linux/amd64、Python 3.12、本地 Docker Engine；运行串行，无常驻服务。

任务必须构建成功，具有至少一个正常失败的 F2P 测试及至少一个基线通过的 P2P 测试。模型通过列表／读取／搜索／精确替换和隔离诊断工具工作。只支持允许列表内已有普通 UTF-8 C/C++ 文件的内容修改。最终补丁从全树变化检查中导出；不接受测试／构建注册变更，也不接受新增、删除、重命名、链接、二进制及权限位修改。

执行容器只得到不含 `.git` 的只读源码快照和临时构建区。源码编辑留在宿主的受控数据工具中；Shell 仅在容器内执行，不能获得 Docker socket、API key、宿主 home 或原仓库管理目录。

现有 SQLite 审计表保留，消除 JSONL 双写的权威歧义；Phase 1 内存状态＋报告不承诺崩溃恢复。Phase 2 再增加事务状态、操作 intent/result 和 checkpoint，不为了将来功能提前堆放未使用的恢复模块。

## 5. 非目标

本项目不做模型训练／微调、通用聊天、IDE、推理框架、多 Agent 协作、通用工作流、微服务、Kubernetes、分布式队列或企业权限平台。首版不兼容任意语言／构建系统、不支持联网构建、私有仓库认证、submodule/LFS、交互程序、任意不可信本地 `.git`，不自动发布补丁或发消息给他人。

不为了简历增加 C++ 代码量。Python 的 subprocess、Git/Docker CLI 已足以承担首版进程控制；只有性能数据或进程管理缺陷证明有收益，才启动独立 C++20 执行器。

## 6. 技术选型摘要

| 领域 | 选择 | 阶段与理由 |
|---|---|---|
| CLI／结构化数据 | argparse、dataclass、enum、typing | 保留现有实现；无须引入 Typer/Pydantic |
| Task | PyYAML＋一次边界校验 | YAML 是用户明确要求，标准库无解析器 |
| 模型通信 | 官方 openai Python SDK＋一个 Model Protocol | 替换自制 HTTP；不依赖整个 Agents Framework |
| 执行 | subprocess、Git CLI、Docker CLI | 复用成熟能力，Python 管流程，容器跑源码 |
| 验证 | CMake/CTest ≥3.26 | 固定测试身份、结构化结果、干净重建 |
| 状态／事件 | sqlite3；JSONL 仅导出 | P1 事件权威，P2 事务状态权威 |
| 测试／质量 | pytest、Ruff；setuptools/pip | 保留生态；覆盖关键行为，不以覆盖率数字驱动 |
| 未来执行器 | C++20 | Phase 4，必须先有测量证据 |

重要取舍完整记录在[DECISIONS](docs/DECISIONS.md)，避免散落在代码注释里。

## 7. 规范优先级与唯一权威

“必须”是阶段验收条件，“应”是默认实现选择，“可”表示非阻塞扩展。本规格内出现冲突时先按下表定位权威文件并修复其它引用，不能在实现中任选一种解释。

| 文档 | 唯一负责的内容 |
|---|---|
| [CURRENT_STATE](docs/CURRENT_STATE.md) | 既有代码、历史证据、未提交改动与迁移背景 |
| [REQUIREMENTS](docs/REQUIREMENTS.md) | FR/NFR、模块／任务／验收映射 |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | 模块依赖、数据流、接口所有者、执行时序 |
| [TASK_FORMAT](docs/TASK_FORMAT.md) | Task v2 字段、默认值、输入冻结和配置优先级 |
| [AGENT_RUNTIME](docs/AGENT_RUNTIME.md) | Model／工具／CommandResult、上下文、预算／停止规则 |
| [EXECUTION_AND_SECURITY](docs/EXECUTION_AND_SECURITY.md) | Git、路径、容器、进程、密钥及清理边界 |
| [VERIFICATION](docs/VERIFICATION.md) | 原始复现、补丁、独立验收与结局判定 |
| [STATE_AND_RECOVERY](docs/STATE_AND_RECOVERY.md) | 状态／结果枚举、身份、事件、SQL、恢复和重放 |
| [CLI](docs/CLI.md) | 命令阶段、参数、退出码、产物目录 |
| [TESTING_AND_EVALUATION](docs/TESTING_AND_EVALUATION.md) | 测试义务、评测分母、CI 与发布门槛 |
| [IMPLEMENTATION_PLAN](docs/IMPLEMENTATION_PLAN.md) | 可逐项实施任务、依赖、DoD 与阶段验收 |
| [DECISIONS](docs/DECISIONS.md) | 长期决策依据和官方资料调研 |
| [SPEC_REVIEW](docs/SPEC_REVIEW.md) | 本轮规格检查方法、结果、剩余实现门槛 |
| [task.example.yaml](examples/task.example.yaml) | Task v2 完整示例；镜像占位必须实际锁定 |

## 8. 必须兑现的工程原则

输入只在 YAML、模型响应、工具请求、文件／容器结果进入控制面的边界校验；内部函数信任已成立的不变量。工具参数错误反馈模型，基础设施错误向任务边界传播，意外异常保留诊断，不用“空列表／默认成功”掩盖。

抽象只有具体价值才保留：模型协议支持 Mock 与一个真实客户端；工作区对象负责资源所有权；事件存储负责事务。不要再叠加 Manager／Service／Repository，也不建通用容器后端／插件注册体系。

测试围绕错误验收、漏补丁、进程泄漏、状态丢失和主要用户路径；新增测试必须说明防哪种回归。保留现有有价值测试，不为对齐一个数量删除测试，也不为了提高覆盖率测第三方库内部。

开发采用一项任务一条可验证改动。改变公开字段／错误分类／权限时同步其权威规格及受影响的示例、测试和 README。完成任务需提供实际命令与结果；失败／跳过必须解释。只生成代码不构成完成。

## 9. 第一条实施入口

阅读 CURRENT_STATE → 本总纲 → IMPLEMENTATION_PLAN；首先执行 **P1-01：确认现有改动并建立真实 Docker 基线**，再做 P1-02 的 v2 迁移。不要从创建新项目骨架或重写全部模块开始。

后续 Coding Agent 必须先选一个 Task ID，读取对应权威文档、检查 Git 状态、仅实施该任务、运行其指定验证并记录结果。若实际证据推翻设计，修改最小相关 Spec 并说明原因；不要在本轮规格交付后自动进入实现。
