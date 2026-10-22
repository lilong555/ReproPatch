# 搜索上下文候选：两题同模型对照

2026-10-22，固定 Catch2-2723、Catch2-2187，每组每题各一次。
候选在预算反馈基础上增加搜索上下文、可编辑状态和完整构建验证说明。
实现 SHA-256：`14b94bf9fc2934b55a8f4ecc2b81ed5cf5849381ed8b65636ff1d1764f4c949c`。
完整结构化结果见 [JSON](cpp-navigation-results.json)。

| 实例 | 框架 | 请求 / 工具 | 停止原因 | 候选 / Oracle | 费用上界（元） |
| --- | --- | --- | --- | --- | --- |
| 2723 | ReproPatch | 12 / 20 | STEP_BUDGET | NO_PATCH | 0.17726176 |
| 2723 | mini | 12 / 18 | LimitsExceeded | NO_PATCH | 0.12808648 |
| 2187 | ReproPatch | 9 / 23 | TOOL_BUDGET | NO_PATCH | 0.21179848 |
| 2187 | mini | 12 / 12 | LimitsExceeded | NO_PATCH | 0.09544544 |

本轮两组均 **0/2**，四次均未编辑源码。Oracle 入口记录 NO_PATCH，原生测试执行数为零。
45 次请求费用上界 **¥0.61259216**，未知用量 0 次；所属容器删除均已确认。
连同此前三个批次累计 **185 次请求、¥2.18923088**，剩余额度约 ¥17.81。
实际账单扣费未知，费用按冻结高峰价格和原始缓存用量计算。

## 协议与观察

沿用[评测协议](README.md)：同一 DeepSeek `deepseek-flash`、相同 prepared commit、
固定生成镜像、初始领域 JSON、可编辑范围及容器资源。每次最多 12 请求、24 工具、
8192 输出 token、90 秒请求超时和 256 KiB 输入边界。每题先 RP 后 mini，各自保留原生提示与工具协议。
mini 时间额度为 815 / 851 秒。任务、源码、实际请求参数和初始输入核验均保存在 JSON 与原始附件。

RP 在 2723 上使用 138.231 秒，最大完整原生输入为 190,762 字节；
2187 使用 112.201 秒，最大输入为 217,947 字节。两次均未触发上下文限制。
mini worker 分别为 74.092 / 36.135 秒。RP 时间包含基线和清理，mini 时间范围为原生执行和清理。

本轮没有观察到搜索上下文候选的分数收益。默认实现保留
[预算反馈候选](repair-cycle-results.md)，其独立批次为 RP 1/2、mini 0/2。
两个候选的首次结果分别公开；当前两题均已用于开发诊断，稳定性与泛化通过后续独立任务检验。

## 新的编译复现材料

FMT-4310 固定在上游 `01914f0389ef6ff151c289670f6910e059d5063f`。
使用官方测试补丁、官方参考补丁及固定 GCC 镜像执行语法编译探针，结果为：

| 源码状态 | 编译退出码 |
| --- | --- |
| 原始基线 | 0 |
| 基线 + 官方测试补丁 | 1，`args()` 成员缺失 |
| 测试补丁 + 官方参考修复 | 0 |

这是零模型请求的编译复现材料。Task v2 的固定测试映射与公共 Oracle 适配待完成。
其原始数据集 `test_patch_result` 保留 NONE，新增观察单独保存；该实例尚未计入修复成绩或已验证 Coverage。
三条编译命令、日志、补丁和复现脚本包含在本批附件中。

## 下载与复核

[原始证据与 SHA-256](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-cpp-navigation-pilot-2026-10-22)
保存本轮原生轨迹、HTTP 请求体/响应体、Task、累计账本、Oracle 决策和执行源码。
执行身份见 [Source Manifest](cpp-navigation-source-manifest.json)。

```bash
sha256sum -c ReproPatch-cpp-navigation-pilot-2026-10-22.tar.gz.sha256
tar -xzf ReproPatch-cpp-navigation-pilot-2026-10-22.tar.gz
python3 cpp-navigation-pilot/summarize.py
```

编译探针可在解压目录执行 `prepare-probe.py` 恢复固定源码，再执行 `compile-probe.py`。
它依赖附件记录的本地固定镜像，完整命令保存在 `fmt4310-probe/compile-probe.json`。
