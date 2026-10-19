# 下一阶段开发计划

当前目标以 [Spec 2026-10-19.2](../specs/2026-10-19.2/SPEC.md) 为准。
本文件是实施顺序摘要；详细 DoD 由其 IMPLEMENTATION_PLAN 定义。
当前产品仍为 0.1.0，没有以文档替代 0.2.0 验收。

| 顺序 | Task | 工作与验收门槛 |
| --- | --- | --- |
| 当前 | P1-01 | 继续现有分支，保存新版规格；在真实 Linux Docker 主机验证正确/错误补丁、隔离和超时清理。当前环境阻塞。 |
| 1 | P1-02 | Task v2：固定完整 commit/image、readable/editable/protected、规范化任务哈希，更新真实 fixture 输入。 |
| 2 | P1-03 | 源码与补丁完整性、只读快照、资源/输出边界和清理确认，复用 Git/Docker CLI。 |
| 3 | P1-06 | 提取共享验证逻辑，交付不依赖模型的 verify-patch，固定结构化 F2P/P2P，拒绝缺失/skip/空跑。 |
| 4 | P1-04 | 安装经契约测试的可选 openai-agents extra，直接用公开 Runner/Responses 接口，替换手写 HTTP。 |
| 5 | P1-05 | 六个受控工具接 SDK，使用原生 Items/ScriptedModel；不自建第二套循环、消息协议或上下文裁剪器。 |
| 6 | P1-07、P1-08 | SQLite 单一事件权威、导出与查询；完成纯验证和自动修复两条路径的 Docker/安装验收。真实模型 smoke 另需费用确认。 |

只有 P1 的门槛实际通过，才进入后续阶段：

| 阶段 | 范围 | 保持不做的工作 |
| --- | --- | --- |
| P2 / 0.3.0 | 外层三表状态、安全 Checkpoint、受限 Resume、只读 Trace Replay | 不重做未知副作用，不复制通用会话引擎，不承诺 Exactly Once。 |
| P3 / 0.4.0 | 少量固定 C++ 任务；Harbor 作业与产物收集后本地验收；可重算指标 | 不建队列、worker 池、调度器或自定义轨迹方言。Execution Replay 只重新验收保存补丁。 |
| P4 / 按需 | 额外模型、上游 compaction、必要的 C++ 执行器与性能优化 | 没有明确需求或测量收益就不立项，不为了代码量增加组件。 |

当前旧 Mock、Loop、Model Protocol 和 urllib 在替代路径验证前保留；
新路径通过后删除相应旧生产逻辑，不维护两套长期实现。
自有 fixture 不是第三方历史 bug，也不能用于估计模型修复率。
所有实验只记录真实结果，模型费用未知时不填零；远程创建/推送和付费调用继续先确认。
