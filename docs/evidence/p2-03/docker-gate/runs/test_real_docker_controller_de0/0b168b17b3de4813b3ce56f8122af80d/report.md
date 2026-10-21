# ReproPatch 0b168b17b3de4813b3ce56f8122af80d

任务：negative-maximum
入口：run
结局：**RECOVERY\_FAILED**
原因：UNSUPPORTED\_RECOVERY\_PHASE
执行引擎：fake
模型：未知
Docker 隔离：未知
基线 commit：96d3b9c109826d0edf2daad1090fb28feaf4d765
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：1.146 秒
模型步骤：0；准入工具：0
模型停止原因：未知
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：14


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |

错误：UNSUPPORTED\_RECOVERY\_PHASE: 不重执行中断的阶段
诊断附件：recovery/1/unverified.patch
诊断附件：recovery/1/source-manifest.json

领域轨迹：events.jsonl

仅验收固定 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核；模型生成不保证正确。
未知副作用不重做；诊断补丁需以新的 verify-patch Run 独立验收。
