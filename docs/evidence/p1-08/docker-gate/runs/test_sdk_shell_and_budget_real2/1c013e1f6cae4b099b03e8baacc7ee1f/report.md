# ReproPatch 1c013e1f6cae4b099b03e8baacc7ee1f

任务：negative-maximum
入口：run
结局：**BUDGET\_EXHAUSTED**
原因：TOOL\_BUDGET
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：80702d19a74dcffcfc0a2ec0a77e83c397cbb695
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：5.368 秒
模型步骤：1；准入工具：0
模型停止原因：TOOL\_BUDGET
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：43


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/e870d22bf6fc433f81c6863d3a9c3a85/cc684e5a81df4bdeb25f7778c163b5c0.xml |
| baseline | positive\_values | 通过 | evidence/e870d22bf6fc433f81c6863d3a9c3a85/fe3ea39a5ca24eaea9d9cdb1b045f024.xml |
| baseline | empty\_values | 通过 | evidence/e870d22bf6fc433f81c6863d3a9c3a85/bf97a4c089614f649e3429a043017c39.xml |
| baseline | mixed\_values | 通过 | evidence/e870d22bf6fc433f81c6863d3a9c3a85/e4b76ec5a9bc4ea59d5fa276ebbca209.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/f43deb56ed9a404d9af23d4ccad04ce3/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/f4873205ac3641918f9ce98eff82aac0/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/90d50f6c954c4525a81e682790ad7a48/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/d26609b4f7774a4c852cdc0fdfbb9ea2/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/fadc1a032b214837a8d500d983256243/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/e870d22bf6fc433f81c6863d3a9c3a85-cc684e5a81df4bdeb25f7778c163b5c0.xml --timeout 120.000000 | exited | 8 | logs/fd8e1dacc419448380f8cd1aca9e9422/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e870d22bf6fc433f81c6863d3a9c3a85-cc684e5a81df4bdeb25f7778c163b5c0.xml | exited | 0 | logs/2685dafeea1f4d48ab38cb79649b8c3d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/e870d22bf6fc433f81c6863d3a9c3a85-fe3ea39a5ca24eaea9d9cdb1b045f024.xml --timeout 120.000000 | exited | 0 | logs/61365f60f7c9475bbbfc4aca57730e64/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e870d22bf6fc433f81c6863d3a9c3a85-fe3ea39a5ca24eaea9d9cdb1b045f024.xml | exited | 0 | logs/5282960502a74405915f4a2f9accd2ff/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/e870d22bf6fc433f81c6863d3a9c3a85-bf97a4c089614f649e3429a043017c39.xml --timeout 120.000000 | exited | 0 | logs/1b10ecf73112442c9ec97624caf0baba/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e870d22bf6fc433f81c6863d3a9c3a85-bf97a4c089614f649e3429a043017c39.xml | exited | 0 | logs/3ba3c956f0ea411692f7e9ba51dc2eb1/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/e870d22bf6fc433f81c6863d3a9c3a85-e4b76ec5a9bc4ea59d5fa276ebbca209.xml --timeout 120.000000 | exited | 0 | logs/a6985b0ac8da42a5941233a7b47d97a0/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e870d22bf6fc433f81c6863d3a9c3a85-e4b76ec5a9bc4ea59d5fa276ebbca209.xml | exited | 0 | logs/65680d9579fa46bfbadd6669aeb8469a/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
