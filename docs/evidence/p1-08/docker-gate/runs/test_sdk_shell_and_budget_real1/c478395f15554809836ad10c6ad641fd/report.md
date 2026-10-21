# ReproPatch c478395f15554809836ad10c6ad641fd

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：dc025cad200e79ece4d146448bcbfb1e635b99cf
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：12.457 秒
模型步骤：3；准入工具：2
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：94


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/15a1152260ac4debb913be26fe1700f9/aaf9e9903f6f4b8ca324bb33cd7e6e88.xml |
| baseline | positive\_values | 通过 | evidence/15a1152260ac4debb913be26fe1700f9/69d2d686576e45e898f9d43e61e69a2c.xml |
| baseline | empty\_values | 通过 | evidence/15a1152260ac4debb913be26fe1700f9/a70a84b99c7c4417923b31b08ed6f74b.xml |
| baseline | mixed\_values | 通过 | evidence/15a1152260ac4debb913be26fe1700f9/457b124d34ee4a44bd500a9194b47d8d.xml |
| independent | negative\_values | 通过 | evidence/dd2a0d8ec67c41b39b9c05696d41c38f/b8ca2fb6f14042a1b61265cbd2d068ea.xml |
| independent | positive\_values | 通过 | evidence/dd2a0d8ec67c41b39b9c05696d41c38f/de29b80c23ff4b5fb83a983eb637fe7a.xml |
| independent | empty\_values | 通过 | evidence/dd2a0d8ec67c41b39b9c05696d41c38f/b42e5ced291a43caa8b2e12288d57a19.xml |
| independent | mixed\_values | 通过 | evidence/dd2a0d8ec67c41b39b9c05696d41c38f/05e4b420357747b4ae4da31f5d5b4297.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/3b80f60cc84b45b6b2c54f09856f46b4/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/a4d53c8dc73f4f06a58581e89e38bdde/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/83a3ac49f406436d9e55cfeb13dea475/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/a4b38c29ad22452c9815efafb73804d4/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/ef6913f1e5c642a6897dacbb1e589a5f/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/15a1152260ac4debb913be26fe1700f9-aaf9e9903f6f4b8ca324bb33cd7e6e88.xml --timeout 120.000000 | exited | 8 | logs/a5d3f469996a4b379ea5aa2ee85094ea/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/15a1152260ac4debb913be26fe1700f9-aaf9e9903f6f4b8ca324bb33cd7e6e88.xml | exited | 0 | logs/db9774a1ecb94f81849d19f60f59dc5a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/15a1152260ac4debb913be26fe1700f9-69d2d686576e45e898f9d43e61e69a2c.xml --timeout 120.000000 | exited | 0 | logs/0ecdd57726b440f08316928834ecfe37/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/15a1152260ac4debb913be26fe1700f9-69d2d686576e45e898f9d43e61e69a2c.xml | exited | 0 | logs/306f9aefda5d419a88c19cc4b9f4c5f5/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/15a1152260ac4debb913be26fe1700f9-a70a84b99c7c4417923b31b08ed6f74b.xml --timeout 120.000000 | exited | 0 | logs/d07629d9e5154aef9e435a8a24ef0fff/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/15a1152260ac4debb913be26fe1700f9-a70a84b99c7c4417923b31b08ed6f74b.xml | exited | 0 | logs/255034d6059745e1a55ab053eb57fa19/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/15a1152260ac4debb913be26fe1700f9-457b124d34ee4a44bd500a9194b47d8d.xml --timeout 120.000000 | exited | 0 | logs/34bdd96f0c7e4b56a0f14f974499e754/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/15a1152260ac4debb913be26fe1700f9-457b124d34ee4a44bd500a9194b47d8d.xml | exited | 0 | logs/d1555ad5c3644a3fab3e35c35732bc0c/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/15688528011749d3ae10eba634dad864/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/2d6beb90c4524db5b913713239bd8340/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/5e84a8e46a42477cba4e830b0c290172/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/6233e96f262e4339be0531061568a39c/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/42870812a2964cfba9f9a7540a5a9f00/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/dd2a0d8ec67c41b39b9c05696d41c38f-b8ca2fb6f14042a1b61265cbd2d068ea.xml --timeout 120.000000 | exited | 0 | logs/25e4482bd00b41149f2bdb281fe184c5/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/dd2a0d8ec67c41b39b9c05696d41c38f-b8ca2fb6f14042a1b61265cbd2d068ea.xml | exited | 0 | logs/a8709c6be0fc4db194f6adebf9aeee7a/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/dd2a0d8ec67c41b39b9c05696d41c38f-de29b80c23ff4b5fb83a983eb637fe7a.xml --timeout 120.000000 | exited | 0 | logs/fa786d9c96a14d3e9c44edabe9d1f155/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/dd2a0d8ec67c41b39b9c05696d41c38f-de29b80c23ff4b5fb83a983eb637fe7a.xml | exited | 0 | logs/eba7cabeb6a94ff0a8bb27b832c9ee91/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/dd2a0d8ec67c41b39b9c05696d41c38f-b42e5ced291a43caa8b2e12288d57a19.xml --timeout 120.000000 | exited | 0 | logs/c84654c4c3074389b9e5e47aed1cfd58/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/dd2a0d8ec67c41b39b9c05696d41c38f-b42e5ced291a43caa8b2e12288d57a19.xml | exited | 0 | logs/c20962e373014e0c9e64dea2164917e1/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/dd2a0d8ec67c41b39b9c05696d41c38f-05e4b420357747b4ae4da31f5d5b4297.xml --timeout 120.000000 | exited | 0 | logs/86310c25f7ee4dc0ba62ad458ebb5c3a/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/dd2a0d8ec67c41b39b9c05696d41c38f-05e4b420357747b4ae4da31f5d5b4297.xml | exited | 0 | logs/a60a2f2ecd0b4b43b668dd25a7266648/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
