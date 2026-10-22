# 预算反馈候选：两题同模型对照

2026-10-22，固定 Catch2-2723、Catch2-2187，ReproPatch 与 mini-SWE-agent 2.4.6
各执行一次。ReproPatch 使用实时预算反馈和短修复循环策略；实现 SHA-256 为
`3ec6fe96fe7fb9385d767922cac0131bd1f0a0c6045776fa95c2ea1bde2b3285`。
详细原始引用与指标见 [JSON](repair-cycle-results.json)。

| 实例 | 框架 | 请求 / 工具 | 首次编辑轮次 | 官方 Oracle | 费用上界（元） |
| --- | --- | --- | --- | --- | --- |
| Catch2-2723 | ReproPatch | 12 / 19 | 8 | F2P 失败，P2P 通过 | 0.14740528 |
| Catch2-2723 | mini | 12 / 19 | — | NO_PATCH | 0.12536464 |
| Catch2-2187 | ReproPatch | 12 / 20 | 9 | 通过 | 0.11128392 |
| Catch2-2187 | mini | 12 / 12 | — | NO_PATCH | 0.12437272 |

本轮 **ReproPatch 1/2，mini 0/2**。2187 的候选通过 ReproPatch 独立验收及
官方 Oracle 的 **2 F2P + 50 P2P**。2723 的候选经两套验收均判定未修复，
官方两个 F2P 仍失败、100 个 P2P 通过。两组所属容器删除均已确认。

48 次模型 HTTP 请求费用上界 **¥0.50842656**，未知用量 0 次。
连同 rc2 与 rc3 历史批次累计 **140 次请求、¥1.57663872**，共用 ¥20 累计硬上限。
账本继承已有消费，历史账本原件保持原样。费用为冻结高峰价格及实际缓存用量的上界，账单扣费未知。

## 固定条件与观察

两组使用同一官方 DeepSeek `deepseek-flash`、相同任务、prepared commit、固定生成镜像、
初始领域 JSON、可编辑范围、2 CPU、2 GiB、非 root 和断网环境。每次最多 12 个请求、
24 个工具、8192 输出 token、90 秒请求超时，256 KiB 输入边界。每题先 RP、后 mini。
mini 时间额度扣除实际基线与预留后为 816 / 852 秒。原生系统提示、工具协议和容器生命周期分别保留。
源码、任务、输入核验及采样参数记录见 JSON；固定数据集与 Oracle 来源沿用 [评测协议](README.md)。

| 实例 | RP worker 秒 | mini worker 秒 | RP 最大完整输入字节 |
| --- | --- | --- | --- |
| 2723 | 256.838 | 70.099 | 186,029 |
| 2187 | 175.144 | 38.544 | 127,161 |

RP worker 包含基线、自检、候选导出和独立验收；mini worker 包含原生生成与工作区命令。
公共 Oracle 另外执行。RP 两次均经 Shell 构建测试，固定 `run_command` 调用数为零；
JSON 中 `first_check_model_step` 专指固定验证工具，Shell 命令保存在原生轨迹中。
模型曾尝试复用一次性容器的 `/build`，并重复组织配置、编译和测试命令。

与[上一轮 rc3](rc3-rerun.md)相比，本轮 RP 从 0/2 变为 1/2，mini 保持 0/2。
这两题已用于开发诊断，当前分数描述本批首次尝试；重复实验与未参与调优的 C++ 任务
用于后续检验稳定性及泛化。当前继续改进搜索上下文和构建工具说明，状态见 [readiness.json](readiness.json)。

## 原始证据

[下载证据与 SHA-256](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-repair-cycle-pilot-2026-10-22)
包含 Task、候选、原生轨迹、HTTP 请求体/响应体、Oracle 日志、累计费用账本与执行源码。
[Source Manifest](repair-cycle-source-manifest.json) 定位实际执行字节。

```bash
sha256sum -c ReproPatch-repair-cycle-pilot-2026-10-22.tar.gz.sha256
tar -xzf ReproPatch-repair-cycle-pilot-2026-10-22.tar.gz
python3 repair-cycle-pilot/summarize.py
```
