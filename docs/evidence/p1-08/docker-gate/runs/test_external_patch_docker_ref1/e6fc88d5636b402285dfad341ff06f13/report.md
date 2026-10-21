# ReproPatch e6fc88d5636b402285dfad341ff06f13

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：REQUIRED\_TEST\_NOT\_RUN
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：6216d673e77da3fdb3f883c58f243cf28a8c5ee1
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：6.051 秒
模型步骤：0；准入工具：0
模型停止原因：未知
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：否；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：55


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/ef811715ad904624b6f25ab76fbfbd68/b07d9019f0444896afe4d3e65d9e2037.xml |
| baseline | positive\_values | 通过 | evidence/ef811715ad904624b6f25ab76fbfbd68/e42cd034f6da423bb815b9e304bc5e28.xml |
| baseline | empty\_values | 通过 | evidence/ef811715ad904624b6f25ab76fbfbd68/35ef57459d694f8f912ba49a2836fc93.xml |
| baseline | mixed\_values | 通过 | evidence/ef811715ad904624b6f25ab76fbfbd68/1b7ed53f6a404478836574463e2e0e6e.xml |
| independent | negative\_values | 未运行 | 未知 |
| independent | positive\_values | 未运行 | 未知 |
| independent | empty\_values | 未运行 | 未知 |
| independent | mixed\_values | 未运行 | 未知 |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/0eaaa579b9a8457e8d1ddafeb833ea86/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/866ea625c54f4f519c96f3aaa8378fd0/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/e328c4c552b2490a8a8416204c25197a/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/65d7bc23eb6644e99a118ff97fb0ad67/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/9525c05733c54f5695de9ee5ec0d2d24/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/ef811715ad904624b6f25ab76fbfbd68-b07d9019f0444896afe4d3e65d9e2037.xml --timeout 120.000000 | exited | 8 | logs/4561b5b6effa4fa891d489bc8ffa4a28/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ef811715ad904624b6f25ab76fbfbd68-b07d9019f0444896afe4d3e65d9e2037.xml | exited | 0 | logs/f5471d3bf8124621b728a7884c494f2c/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/ef811715ad904624b6f25ab76fbfbd68-e42cd034f6da423bb815b9e304bc5e28.xml --timeout 120.000000 | exited | 0 | logs/80867a3bfe7a4aab859058924fb27dab/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ef811715ad904624b6f25ab76fbfbd68-e42cd034f6da423bb815b9e304bc5e28.xml | exited | 0 | logs/588a5f784f9a4ce7b310a76e51fdfa85/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/ef811715ad904624b6f25ab76fbfbd68-35ef57459d694f8f912ba49a2836fc93.xml --timeout 120.000000 | exited | 0 | logs/20427dbfd682475abe40406c269460f3/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ef811715ad904624b6f25ab76fbfbd68-35ef57459d694f8f912ba49a2836fc93.xml | exited | 0 | logs/dea3ecb1b7e44b6e9cbde50c5a8be3e7/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/ef811715ad904624b6f25ab76fbfbd68-1b7ed53f6a404478836574463e2e0e6e.xml --timeout 120.000000 | exited | 0 | logs/93a4123cef2d432dbfd555f2528c63a0/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ef811715ad904624b6f25ab76fbfbd68-1b7ed53f6a404478836574463e2e0e6e.xml | exited | 0 | logs/4e96b806a67b49e89279d233701a2321/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/6451eea2e2c643fa91dd77d4e50cdbbb/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/34fc348a2a494fa6a02766c408ad3097/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/09e500523a1449b9b3b5c3bd2e9b8aa6/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/0997191ebc094c1f965c0e53be2661d0/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
