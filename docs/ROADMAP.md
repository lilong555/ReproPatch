# 下一阶段开发计划

当前目标以 [Spec 2026-10-19.2](../specs/2026-10-19.2/SPEC.md) 为准。
本文件是实施顺序摘要；详细 DoD 见 [当前实施计划](IMPLEMENTATION_PLAN.md) 与原始规格。
当前开发版本为 0.3.0.dev3、Task v2，Phase 1、P2-01 至 P2-03 已完成；公开仓库为 [lilong555/ReproPatch](https://github.com/lilong555/ReproPatch)。

| 顺序 | Task | 工作与验收门槛 |
| --- | --- | --- |
| 已完成 | P1-01 | 规格归档完整；76 项非 Docker 测试、4 项真实 Docker 测试通过，正确/错误补丁、隔离及超时清理均有原始证据。 |
| 已完成 | P1-02 | Task v2 静态解析与冻结、真实 commit/image、文件集合和稳定任务 hash；115 项普通测试、4 项真实 Docker 通过。 |
| 已完成 | P1-03A | 完整字节清单、Git 元数据审查、受控文本编辑、候选引用、真实补丁应用与独立清单/补丁往返；151 项普通测试、5 项真实 Docker 通过。 |
| 已完成 | P1-03B | Run 所有权和锁、原始双流日志、4 MiB 命令及 256 MiB 审计预算、容器删除确认和 retain；180 项普通测试、10 项真实 Docker 通过。父任务 P1-03 完成。 |
| 已完成 | P1-06 | 提取共享验证逻辑，交付不依赖模型的 verify-patch，固定结构化 F2P/P2P，拒绝缺失/skip/空跑；238 项普通测试、15 项真实 Docker 通过。 |
| 已完成 | P1-04 | 可选 SDK 固定依赖、公开 Runner/Responses 与 ScriptedModel；39 项离线契约通过。 |
| 已完成 | P1-05 | 六个受控工具接 SDK，使用原生 Items/ScriptedModel；不自建第二套循环、消息协议或上下文裁剪器。 |
| 已完成 | P1-07 | SQLite 单一事件权威、统一信封、原子导出、inspect/report；导出失败保持结局，证据损坏明确不可核查。 |
| 已完成 | P1-08 | MVP 门槛、干净安装、DeepSeek 真实修复及独立 Docker 验收通过。 |
| 已完成 | P2-01 | runs/events/checkpoints 三表、状态与预算同事务、执行片段不确定性；旧审计可读不可恢复。 |
| 已完成 | P2-02 | 公开完整输入边界的 Checkpoint、durable 文件及原子提交、受控暂停；不重做工具。 |
| 已完成 | P2-03 | 核对指纹、资源与关闭片段，从安全 Checkpoint 有限 Resume；未知模型/工具结果停止，不重发。 |
| 下一任务 | P2-04 | 只读 Trace Replay、export-trace 与恢复门槛；不执行模型或历史工具。 |

只有 P1 的门槛实际通过，才进入后续阶段：

| 阶段 | 范围 | 保持不做的工作 |
| --- | --- | --- |
| P2 / 0.3.0 | 外层三表状态、安全 Checkpoint、受限 Resume、只读 Trace Replay | 不重做未知副作用，不复制通用会话引擎，不承诺 Exactly Once。 |
| P3 / 0.4.0 | 少量固定 C++ 任务；Harbor 作业与产物收集后本地验收；可重算指标 | 不建队列、worker 池、调度器或自定义轨迹方言。Execution Replay 只重新验收保存补丁。 |
| P4 / 按需 | 额外模型、上游 compaction、必要的 C++ 执行器与性能优化 | 没有明确需求或测量收益就不立项，不为了代码量增加组件。 |

自动路径只使用公开 SDK Runner；不维护第二套模型协议、手写 HTTP 或模型 worker。
自有 fixture 不是第三方历史 bug，也不能用于估计模型修复率。
所有实验只记录真实结果，模型费用未知时不填零；远程创建/推送与付费调用按操作者的显式授权执行。
