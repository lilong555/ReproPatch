# ReproPatch 4193faeebbd74fd88b3b7659d96bf780

任务：negative-maximum
入口：run
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：cc821f769170d31c1c14e1cb6ea99c9eb400f299
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：9.129 秒
模型步骤：2；准入工具：1
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：83


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/8fc26b802cf847d4839bce9d77c73e63/afc1a32d9446466daa51efb08ec3944c.xml |
| baseline | positive\_values | 通过 | evidence/8fc26b802cf847d4839bce9d77c73e63/2470559823c14282a1498435aae27fb2.xml |
| baseline | empty\_values | 通过 | evidence/8fc26b802cf847d4839bce9d77c73e63/3fbd16915a5e4bc499119f38daf96507.xml |
| baseline | mixed\_values | 通过 | evidence/8fc26b802cf847d4839bce9d77c73e63/38e25891745c4b589c12f87ee0f72dab.xml |
| independent | negative\_values | 失败 | evidence/9e17fadb362b45b98a44443345c2a95e/82f9911ad782482a894f2fd335d30ad4.xml |
| independent | positive\_values | 通过 | evidence/9e17fadb362b45b98a44443345c2a95e/44a7b38eabb54472b770911a4e4a790e.xml |
| independent | empty\_values | 通过 | evidence/9e17fadb362b45b98a44443345c2a95e/aa0f0a5705654912897f81bbf8a9e405.xml |
| independent | mixed\_values | 通过 | evidence/9e17fadb362b45b98a44443345c2a95e/0e86da6e7a614c15819104e8a7fad185.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/c66325a09e204b0aa0cfb56f8734fbb3/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/23c4ec672d154f03ac0f79c88fb3978b/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/af241a561b0e4393aba7e81f58f59885/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/d5c8726deeec4797849637179de5173d/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/9e2884570b1446f7890b4dc582628207/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/8fc26b802cf847d4839bce9d77c73e63-afc1a32d9446466daa51efb08ec3944c.xml --timeout 120.000000 | exited | 8 | logs/e538b372f7a74ff6b46340bd79aa6f5e/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8fc26b802cf847d4839bce9d77c73e63-afc1a32d9446466daa51efb08ec3944c.xml | exited | 0 | logs/ec7ec9142f894fa3a104b1d52a339a97/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/8fc26b802cf847d4839bce9d77c73e63-2470559823c14282a1498435aae27fb2.xml --timeout 120.000000 | exited | 0 | logs/0c6f9db07891466a8ea733bf1f56d397/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8fc26b802cf847d4839bce9d77c73e63-2470559823c14282a1498435aae27fb2.xml | exited | 0 | logs/c45712d57977422591a8a56287500111/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/8fc26b802cf847d4839bce9d77c73e63-3fbd16915a5e4bc499119f38daf96507.xml --timeout 120.000000 | exited | 0 | logs/90814327969b40808101904030d0db0b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8fc26b802cf847d4839bce9d77c73e63-3fbd16915a5e4bc499119f38daf96507.xml | exited | 0 | logs/29dcc68e46a74a84bc5e8effd3863e16/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/8fc26b802cf847d4839bce9d77c73e63-38e25891745c4b589c12f87ee0f72dab.xml --timeout 120.000000 | exited | 0 | logs/9a96f54769e34053a0e413fd40dd52e2/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8fc26b802cf847d4839bce9d77c73e63-38e25891745c4b589c12f87ee0f72dab.xml | exited | 0 | logs/fa8c5d8d2cd1496c99240d8eae4b54f0/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/7b0c3ceaf95c46dca06562763fea9396/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/e5118395b16b474fa9c54b2b509def95/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/37c2414222ab4383b849c76b99ff1730/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/bf8d528dd3374b4ab33a0e79cdeba343/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/5ce1ecd3468747598209a117bf332947/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/9e17fadb362b45b98a44443345c2a95e-82f9911ad782482a894f2fd335d30ad4.xml --timeout 120.000000 | exited | 8 | logs/bfd8f265b2164aa9a3482055a9c75557/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/9e17fadb362b45b98a44443345c2a95e-82f9911ad782482a894f2fd335d30ad4.xml | exited | 0 | logs/ff1cfb7414804078b33c9ff6c22afcdc/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/9e17fadb362b45b98a44443345c2a95e-44a7b38eabb54472b770911a4e4a790e.xml --timeout 120.000000 | exited | 0 | logs/af13785483974de198743b7a9fcbf0c0/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/9e17fadb362b45b98a44443345c2a95e-44a7b38eabb54472b770911a4e4a790e.xml | exited | 0 | logs/dbb2614b94644a47921b3f35898e87cc/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/9e17fadb362b45b98a44443345c2a95e-aa0f0a5705654912897f81bbf8a9e405.xml --timeout 120.000000 | exited | 0 | logs/62a214ba61ef4b68b10588563e11d321/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/9e17fadb362b45b98a44443345c2a95e-aa0f0a5705654912897f81bbf8a9e405.xml | exited | 0 | logs/6612530dea054650a7eeaefa9e3c71d3/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/9e17fadb362b45b98a44443345c2a95e-0e86da6e7a614c15819104e8a7fad185.xml --timeout 120.000000 | exited | 0 | logs/4eb5816b00af4dd587f207b389c0e6cd/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/9e17fadb362b45b98a44443345c2a95e-0e86da6e7a614c15819104e8a7fad185.xml | exited | 0 | logs/0bce04c1c4bf4101a79aa943917b000e/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
