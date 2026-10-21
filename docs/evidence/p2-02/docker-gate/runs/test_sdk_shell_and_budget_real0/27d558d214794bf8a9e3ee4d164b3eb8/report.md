# ReproPatch 27d558d214794bf8a9e3ee4d164b3eb8

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：3c14c45041da834f7e4536212148430d3052e1df
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：9.049 秒
模型步骤：3；准入工具：2
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：97


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/16608fcaa4bb4fd09bda615f0cb76dcb/30a6906339f445a5b25c6fa497aeeb3c.xml |
| baseline | positive\_values | 通过 | evidence/16608fcaa4bb4fd09bda615f0cb76dcb/d499b48562504051b6096ca883591570.xml |
| baseline | empty\_values | 通过 | evidence/16608fcaa4bb4fd09bda615f0cb76dcb/208bc1bd33844366a16b1824a61d6077.xml |
| baseline | mixed\_values | 通过 | evidence/16608fcaa4bb4fd09bda615f0cb76dcb/4be33610d7f44645bffdc33fd52b14db.xml |
| independent | negative\_values | 通过 | evidence/fad590da4985404fb651f2e626c0f65f/0801dc4014164000bc1a187d45f8cfa9.xml |
| independent | positive\_values | 通过 | evidence/fad590da4985404fb651f2e626c0f65f/93ff5ebc0d454607ae799c3d1f85d299.xml |
| independent | empty\_values | 通过 | evidence/fad590da4985404fb651f2e626c0f65f/7d7803dc3de64979b0d69153475d2122.xml |
| independent | mixed\_values | 通过 | evidence/fad590da4985404fb651f2e626c0f65f/4dcceb4b73fd470b888901f59f08dae1.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/4181c915710c4c15976a18d7cb633d8a/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/ad2e2d2b36fa48159af5dfb42778bf6b/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/266c31a8efa04fe39414d1d9f7d3522d/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/1754272857454b2186f9e064f8beccf3/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/ebea2a94f1474781a1e83829f771cfea/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/16608fcaa4bb4fd09bda615f0cb76dcb-30a6906339f445a5b25c6fa497aeeb3c.xml --timeout 120.000000 | exited | 8 | logs/68467cdf29d843208061ac55067916da/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/16608fcaa4bb4fd09bda615f0cb76dcb-30a6906339f445a5b25c6fa497aeeb3c.xml | exited | 0 | logs/83d403518d5b4a4e83c3a58c891f681f/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/16608fcaa4bb4fd09bda615f0cb76dcb-d499b48562504051b6096ca883591570.xml --timeout 120.000000 | exited | 0 | logs/6ccb4547e8234a39b36e657228d0983a/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/16608fcaa4bb4fd09bda615f0cb76dcb-d499b48562504051b6096ca883591570.xml | exited | 0 | logs/4c35b58ec7714478bdb43b4562e204c3/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/16608fcaa4bb4fd09bda615f0cb76dcb-208bc1bd33844366a16b1824a61d6077.xml --timeout 120.000000 | exited | 0 | logs/7923279cc80649f09f2259b3c4e985cf/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/16608fcaa4bb4fd09bda615f0cb76dcb-208bc1bd33844366a16b1824a61d6077.xml | exited | 0 | logs/7f6c8eae14d3497ca95a87fab07dab01/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/16608fcaa4bb4fd09bda615f0cb76dcb-4be33610d7f44645bffdc33fd52b14db.xml --timeout 120.000000 | exited | 0 | logs/bb5170659ab2487a8b77b41657a4f983/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/16608fcaa4bb4fd09bda615f0cb76dcb-4be33610d7f44645bffdc33fd52b14db.xml | exited | 0 | logs/6e99e7b8733240e49a619b1e79508c91/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/3506e3de1cd542d3ae3340e8a9723f34/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/dd3f003197a34d80a23578fee3dc1ae2/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/5b48b17921334efca964b46e12247916/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/91602a9e1a3542a58aac77f6114f9949/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/279f9e83b93c4667ba085b4acd34d664/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/fad590da4985404fb651f2e626c0f65f-0801dc4014164000bc1a187d45f8cfa9.xml --timeout 120.000000 | exited | 0 | logs/704bf7fbb1ec46b5b8263e9425e78965/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fad590da4985404fb651f2e626c0f65f-0801dc4014164000bc1a187d45f8cfa9.xml | exited | 0 | logs/92fa0e237c1741a0806ff8124b4ef809/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/fad590da4985404fb651f2e626c0f65f-93ff5ebc0d454607ae799c3d1f85d299.xml --timeout 120.000000 | exited | 0 | logs/e05b1f1a463d4fbab3b2754dbd059df6/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fad590da4985404fb651f2e626c0f65f-93ff5ebc0d454607ae799c3d1f85d299.xml | exited | 0 | logs/52208c48557349cea538bdd450e045ad/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/fad590da4985404fb651f2e626c0f65f-7d7803dc3de64979b0d69153475d2122.xml --timeout 120.000000 | exited | 0 | logs/bbc40710ce05468ca1c9121b4868bce2/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fad590da4985404fb651f2e626c0f65f-7d7803dc3de64979b0d69153475d2122.xml | exited | 0 | logs/519ffe2fcd0843d68c44ed1e0bf12e21/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/fad590da4985404fb651f2e626c0f65f-4dcceb4b73fd470b888901f59f08dae1.xml --timeout 120.000000 | exited | 0 | logs/0e0a3e5fd77549fab47aa717408155dd/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fad590da4985404fb651f2e626c0f65f-4dcceb4b73fd470b888901f59f08dae1.xml | exited | 0 | logs/01a6c07005b14379bcd47a5d00af3b55/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
