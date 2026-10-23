# 六题 C++ 修复与 Codex 对照

固定 `gpt-6-luna` 模型别名，六个真实实例的首次修复结果为
ReproPatch Full **4/6**、mini-SWE-agent **3/6**、
Codex CLI **4/6**。第三仓库 simdjson 在核心源码冻结后选取，
其结果为 Full **0/1**、
mini **1/1**、Codex **0/1**。

[逐次数据](cross-framework-results.json) · [源码清单](cross-framework-source-manifest.json) ·
[完整原始证据](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-cross-framework-2026-10-23)

## 固定实例

| 实例 | ReproPatch Full | mini-SWE-agent | Codex CLI |
| --- | --- | --- | --- |
| catchorg__Catch2-2187 | 通过 | 失败 | 通过 |
| catchorg__Catch2-2723 | 通过 | 失败 | 通过 |
| fmtlib__fmt-4310 | 通过 | 通过 | 通过 |
| fmtlib__fmt-4286 | 失败 | 失败 | 失败 |
| fmtlib__fmt-4057 | 通过 | 通过 | 通过 |
| simdjson__simdjson-2178 | 失败 | 通过 | 传输中断 |

每个任务每组首次尝试均保留。Codex的simdjson首次请求传输中断、候选为空；
该尝试进入首次尝试分母。随后另起独立尝试，使用12次请求产生的候选仍未通过99项外部测试。
这条复测单列在JSON，首次成绩保持原记录。
Catch2 的历史重复结果单独保留：Full 6/6、mini 3/6、内部消融 3/6，
见[只读契约反馈实验](contract-results.md)。这些重复记录衡量两个已知实例上的稳定性。

| 六题首次结果 | 修复 / 尝试 | 模型请求 | 输入 token | 输出 token |
| --- | ---: | ---: | ---: | ---: |
| ReproPatch Full | 4/6 | 58 | 845,736 | 3,365 |
| mini-SWE-agent | 3/6 | 47 | 787,492 | 6,912 |
| Codex CLI | 4/6 | 60 | 1,506,752 | 6,408 |

## 相同 HTTPS 端点子集

三个 FMT 实例及 simdjson 均有 `https://cpa.liyinlong.me/v1` 记录。
FMT-4310、4286 的 Full 和 mini 使用已保存的后续控制运行；4057 和 simdjson 使用首次运行。
这组固定选择按端点和运行身份确定，保留其余全部尝试。

| 同端点四题 | 修复 / 尝试 | 模型请求 | 输入 token | 输出 token |
| --- | ---: | ---: | ---: | ---: |
| ReproPatch Full | 2/4 | 35 | 396,125 | 1,993 |
| mini-SWE-agent | 3/4 | 26 | 319,716 | 3,652 |
| Codex CLI | 2/4 | 37 | 714,197 | 3,863 |

4310、4286 的 Codex 复用了同任务历史领域输入；该输入与后续控制组的源码身份、任务、
预算、可编辑集合和镜像相同，基线日志、执行时间及证据引用随运行变化。
历史六题汇总中，前四题 Full/mini 经 localhost 调用，Codex 经 HTTPS 调用。
供应商后端实例身份保持未知，各请求的模型响应标识、采样设置和推理配置见 JSON 与原始 HTTP。

## 泛化任务与验收

固定数据 revision 为 `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d`，C++ 池共129条。
当前完成参考验收的六题覆盖 **6/129（4.65%）**、三个仓库。
完整[静态筛查](coverage.json)保留全部实例，动态适配状态见本报告与 readiness。

simdjson-2178 来自固定文件的首条记录。生产核心冻结后选题，模型执行前已保存协议、
参考补丁的外部99项测试通过记录，以及内部2 F2P + 97 P2P参考验收。
缺陷涉及 JSON Pointer 越过标量时的错误码，以及错误转义语法的区别。

离线依赖固定为 simdjson-data `a5b13babe65c1bba7186b41b43d4cbdc20a5c470` 和
cxxopts `794c975287355de48158d9a80ed502d26b20a472`。
测试环境把 quickstart 编译输出和大样本临时文件放入构建目录；prepared Task 清除指向
构建目标或源码文件的 CTest 排序属性，支持 Harness 逐项验收。
外部 Oracle 从原始提交重新应用官方测试补丁和相同输出路径适配，保留原生排序属性，
完整构建并执行99项测试。三组使用同一 Oracle，受保护测试及依赖均保持固定。
资格检查中的输出目录、临时空间和排序属性失败均为零模型请求，原始记录随附件保存。

Catch2 公共 Oracle 使用固定上游 Report，2187要求2 F2P +50 P2P，2723要求2 F2P +100 P2P。
FMT-4310、4286、4057为编译回归扩展，原始测试阶段为NONE；完整原生测试数分别为21、21、20。
参考补丁只用于资格检查。已发起尝试保留；空补丁记录NO_PATCH；达到模型限制后的候选照常评分。

## 输入与执行条件

Full核心 SHA-256：`6c13e9efed3f3c13206bf225c8aaed5413e438e27786af92f8adff98d63e7338`。
mini固定2.4.6、commit `04d809ceab9df28f9adaed044884180159172930`；
Codex CLI固定0.163.0，二进制与配套code-mode-host的哈希记录于每次结果。
公共 evaluator固定 `4b96a678b136f87c8760fa475697f3c98d5f9e5e`。

每次最多12个上游请求、24次原生工具调用、8192输出token；输入边界256KiB，请求超时90秒。
Full/mini保留原生非流式协议；Codex保留原生SSE，代理设置相同输出上限并逐请求计量。
Codex的推理配置为none；实际请求参数逐项保留。
各组保留自己的系统提示和工具协议。修复容器均非root、断网、固定CPU/内存、只开放允许源码的写入。
Codex通过模型专用Unix套接字连接宿主代理，容器中使用虚拟凭据。
源码读取在首个模型请求前以实际容器用户检查。simdjson的首次领域输入经哈希核验后供mini与Codex复用。

Full worker含基线、自检和独立验收；mini/Codex worker含原生Agent执行与工作区检查。
公共Oracle耗时单列。Codex Catch2与部分simdjson资格检查存在资源时间重叠，耗时按实际观察保存。

## 逐次结果

| 实例 | 框架 | 请求 / 工具 | 候选字节 | Agent停止原因 | 公共Oracle |
| --- | --- | ---: | ---: | --- | --- |
| catchorg__Catch2-2187 | ReproPatch Full | 11 / 10 | 657 | ACCEPTED | 通过 |
| catchorg__Catch2-2187 | mini-SWE-agent | 9 / 9 | 0 | Submitted | 失败 |
| catchorg__Catch2-2187 | Codex CLI | 12 / 12 | 777 | CLI退出 1 | 通过 |
| catchorg__Catch2-2723 | ReproPatch Full | 12 / 12 | 795 | ACCEPTED | 通过 |
| catchorg__Catch2-2723 | mini-SWE-agent | 12 / 12 | 834 | LimitsExceeded | 失败 |
| catchorg__Catch2-2723 | Codex CLI | 11 / 10 | 947 | CLI退出 1 | 通过 |
| fmtlib__fmt-4310 | ReproPatch Full | 5 / 4 | 478 | ACCEPTED | 通过 |
| fmtlib__fmt-4310 | mini-SWE-agent | 5 / 5 | 412 | Submitted | 通过 |
| fmtlib__fmt-4310 | Codex CLI | 12 / 12 | 473 | CLI退出 1 | 通过 |
| fmtlib__fmt-4286 | ReproPatch Full | 12 / 12 | 901 | REJECTED | 失败 |
| fmtlib__fmt-4286 | mini-SWE-agent | 6 / 6 | 845 | Submitted | 失败 |
| fmtlib__fmt-4286 | Codex CLI | 12 / 12 | 1596 | CLI退出 1 | 失败 |
| fmtlib__fmt-4057 | ReproPatch Full | 8 / 7 | 1028 | VERIFICATION_PASSED | 通过 |
| fmtlib__fmt-4057 | mini-SWE-agent | 5 / 5 | 962 | Submitted | 通过 |
| fmtlib__fmt-4057 | Codex CLI | 12 / 12 | 1186 | CLI退出 1 | 通过 |
| simdjson__simdjson-2178 | ReproPatch Full | 10 / 9 | 1405 | F2P_FAILED | 失败 |
| simdjson__simdjson-2178 | mini-SWE-agent | 10 / 10 | 1911 | Submitted | 通过 |
| simdjson__simdjson-2178 | Codex CLI | 1 / 0 | 0 | CLI退出 1 | 失败 |

Codex接入阶段另保留两条环境失败：CODEX_HOME目录缺失0请求、配套运行组件缺失4请求。
完成组件修正后的首次有效尝试进入评分；原始环境失败记录与用量持续保留。
三组在FMT-4286均有失败候选，外部测试暴露宽字符格式化回归。

已归档的两个诊断候选也保持失败记录：搜索上下文候选在第4轮开始编辑、第6轮首次自检，
其候选仍在complex宽字符填充用例失败；追加自检源码片段的候选未通过独立构建。
生产核心为报告中的固定SHA。完整的[五个诊断反馈候选](diagnostic-feedback-results.md)另批保存，
包含本附件截止后完成的基线片段、错误排序及simdjson候选。

## 用量与复核

本批Codex含接入阶段共 **63** 次上游请求，
simdjson三组共 **33** 次；新增未知用量 **2** 次。
本批已归档的诊断候选另有 **24** 次请求。
历史和本批已归档CPA累计 **487** 次；运行中的候选在JSON单列名称，后续结果另批保存。
CPA实际费用保持未知；DeepSeek历史费用上界维持 **¥2.18923088 / ¥20**。
既有批量工具调用试验保留六次运行及用量，候选配置未采用。

原始证据：[ReproPatch-cross-framework-2026-10-23.tar.gz](https://github.com/lilong555/ReproPatch/releases/download/benchmark-cross-framework-2026-10-23/ReproPatch-cross-framework-2026-10-23.tar.gz)，SHA-256：
`986b31c8f19ab29c1530d6b0bc20391eb6d2e09f7598ca2e9631df69e0c89549`。
同名 `.sha256` 支持 `sha256sum -c`。附件包含逐文件哈希、模型原始请求/响应、SQLite、
候选、评分、源码快照和simdjson prepared仓库bundle。
解压后执行 `python3 summarize-cross-framework.py` 可从证据重算本报告的JSON结果。
原始工具链镜像见[上一批工具链附件](https://github.com/lilong555/ReproPatch/releases/tag/benchmark-contract-comparison-2026-10-22)。
