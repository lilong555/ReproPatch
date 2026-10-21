# ReproPatch 6a8b77db81174034a18fa5970479ad68

任务：negative-maximum
入口：run
结局：**BUDGET\_EXHAUSTED**
原因：TOOL\_BUDGET
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：626e819a43d4f286af557511d29da1746fa55668
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：4.424 秒
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
| baseline | negative\_values | 失败 | evidence/1907baa754f14ddf89164a567d12b966/e2f8e4e17d7b4ec2bcf49d6b45d88076.xml |
| baseline | positive\_values | 通过 | evidence/1907baa754f14ddf89164a567d12b966/ea7e69489fa241ac8ac9b5be0bbfc662.xml |
| baseline | empty\_values | 通过 | evidence/1907baa754f14ddf89164a567d12b966/823bcd7b5fa7461f9aca8921c01dcb0c.xml |
| baseline | mixed\_values | 通过 | evidence/1907baa754f14ddf89164a567d12b966/d277d8f48fa7431e958dac255ddd0462.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/292d45b3203446259dcd12fa8b53a680/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/1af05d35013d41bd929c8345263d27bb/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/06a1cdd60dcf4124b0c6bdc49eddfd68/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/ac6edb80810b4c19acef32a24838fbe9/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/7682c2afd46e41349fc3670384774881/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/1907baa754f14ddf89164a567d12b966-e2f8e4e17d7b4ec2bcf49d6b45d88076.xml --timeout 120.000000 | exited | 8 | logs/80ed65d808e748f0b8b8f7c44efa7f42/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/1907baa754f14ddf89164a567d12b966-e2f8e4e17d7b4ec2bcf49d6b45d88076.xml | exited | 0 | logs/cdd23da341f24421b0d4e82fe5dbb8e4/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/1907baa754f14ddf89164a567d12b966-ea7e69489fa241ac8ac9b5be0bbfc662.xml --timeout 120.000000 | exited | 0 | logs/142468cbd6e645f3916d67dc91f86c96/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/1907baa754f14ddf89164a567d12b966-ea7e69489fa241ac8ac9b5be0bbfc662.xml | exited | 0 | logs/cba745c1fec94b968c6d5ed771ba205a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/1907baa754f14ddf89164a567d12b966-823bcd7b5fa7461f9aca8921c01dcb0c.xml --timeout 120.000000 | exited | 0 | logs/d588a1aa52254699b3efe1bb2fa5189f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/1907baa754f14ddf89164a567d12b966-823bcd7b5fa7461f9aca8921c01dcb0c.xml | exited | 0 | logs/a75bf079e33e40ac91be867ce0ead4fe/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/1907baa754f14ddf89164a567d12b966-d277d8f48fa7431e958dac255ddd0462.xml --timeout 120.000000 | exited | 0 | logs/bc96bc6778c64b61ab936d7953c9ad88/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/1907baa754f14ddf89164a567d12b966-d277d8f48fa7431e958dac255ddd0462.xml | exited | 0 | logs/bd01873b0ac240aca8a4665e8f3f8c41/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
