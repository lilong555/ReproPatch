# C++ 诊断反馈候选

五次固定12请求实验的公共Oracle结果为 **0/5**。生产核心保持
`6c13e9efed3f3c13206bf225c8aaed5413e438e27786af92f8adff98d63e7338`。
[逐次JSON](diagnostic-feedback-results.json)保存源码身份、请求、候选、内部与外部结局。

| 反馈候选 | 实例 | 请求 | 首次编辑轮次 | 自检轮次 | 内部拒绝原因 | 公共Oracle |
| --- | --- | ---: | ---: | --- | --- | --- |
| 搜索命中上下文 | fmtlib__fmt-4286 | 12 | 4 | 6, 10 | F2P_FAILED | 失败 |
| 搜索命中上下文（simdjson） | simdjson__simdjson-2178 | 10 | 4 | 5, 9 | F2P_FAILED | 失败 |
| 自检失败源码片段 | fmtlib__fmt-4286 | 12 | 8 | 10, 12 | CANDIDATE_BUILD_FAILED | 失败 |
| 基线及自检源码片段 | fmtlib__fmt-4286 | 12 | 5 | 8, 10 | F2P_FAILED | 失败 |
| 主错误优先源码片段 | fmtlib__fmt-4286 | 11 | 6 | 8, 10 | F2P_FAILED | 失败 |

搜索候选在命中处提供前后源码及可编辑状态；诊断候选从编译器与测试日志中的
`/src/文件:行`读取同一授权源码片段。后续候选将此视图用于基线，并按主错误、声明说明、
包含栈排序。读取继续经过现有权限检查，片段数量和字节数固定有界。
每次保留12请求、24工具、8192输出token、原生SDK和完整独立验收。

全部实例参与开发诊断。搜索候选的FMT首次编辑提前到第4轮，但候选仍在complex宽字符填充用例失败；
simdjson候选仍未完整处理JSON Pointer语法。新增源码片段也未提高本组修复数。
这些候选的代码、运行和失败结果均保留，当前生产源码采用已公布的固定核心。

本组共 **57** 次模型请求；其中24次已收入六题对照附件，本附件新增归档请求为 **33** 次，
CPA累计已归档 **520** 次。实际CPA账单未知，DeepSeek历史费用上界保持¥2.18923088 / ¥20。

原始证据：[ReproPatch-diagnostic-feedback-2026-10-23.tar.gz](https://github.com/lilong555/ReproPatch/releases/download/benchmark-diagnostic-feedback-2026-10-23/ReproPatch-diagnostic-feedback-2026-10-23.tar.gz)，SHA-256：
`013f1826e70fdfcc67eff9d4e5904447b4a0d8db1af04be102de0f2b4d6fc8a0`。
下载同名`.sha256`后运行`sha256sum -c`。解压后执行`python3 summarize-diagnostic-feedback.py`，
可从原始请求账本、源码快照、候选和外部评分重算结果。逐文件哈希和独立解压重算均通过。

[六题三框架结果](cross-framework-results.md)保存当前生产核心与mini、Codex的比较。
