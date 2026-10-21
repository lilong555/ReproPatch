# ReproPatch d934718188954783b21446beb1f07387

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：d97de3436080131a00daebc28453e34549783caa
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.075 秒
模型步骤：0；准入工具：0
模型停止原因：未知
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：否；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：73


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | parse\[value\]+edge | 失败 | evidence/1a163e96f75743c5a57b45f6497f0ec4/f9445ac256734eaaa9e84529806ed8ed.xml |
| baseline | positive\_values | 通过 | evidence/1a163e96f75743c5a57b45f6497f0ec4/d2eb3d9e57ee483e97b684fae64056c2.xml |
| baseline | empty\_values | 通过 | evidence/1a163e96f75743c5a57b45f6497f0ec4/9774b59d14e24ee68f00061fb25adaaf.xml |
| baseline | mixed\_values | 通过 | evidence/1a163e96f75743c5a57b45f6497f0ec4/72cb2193b7d14393924be08e462f8024.xml |
| independent | parse\[value\]+edge | 通过 | evidence/725a698a231b49dd866fe6f650ef1b57/9c5386934dc444eab892375aea7fc1fd.xml |
| independent | positive\_values | 通过 | evidence/725a698a231b49dd866fe6f650ef1b57/359b997fd4be46aea50ccce8bf6bb979.xml |
| independent | empty\_values | 通过 | evidence/725a698a231b49dd866fe6f650ef1b57/e187651b3bf642b4aed5fef648af3add.xml |
| independent | mixed\_values | 通过 | evidence/725a698a231b49dd866fe6f650ef1b57/bf3736f01e6c4f86b37f45ea52c753b1.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/d1d9e4330fca4dda99abd227084795c9/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/91eeef7c2e894f3b9d8617d7ca579736/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/ec71e21b0e5f48b4a1ee8c1aff6a1e0d/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/b2d875ade2a448608f7a222ba22be6cd/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/33bd5aeba6a5467899d2c8c51baa81cb/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\\\[value\\\]\\+edge$ --output-junit /build/.repropatch-results/1a163e96f75743c5a57b45f6497f0ec4-f9445ac256734eaaa9e84529806ed8ed.xml --timeout 120.000000 | exited | 8 | logs/94794448e2ff4a0cbf5dd4251dfd4cd3/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/1a163e96f75743c5a57b45f6497f0ec4-f9445ac256734eaaa9e84529806ed8ed.xml | exited | 0 | logs/51b05faf9b9a449180c82b4a0d296c60/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/1a163e96f75743c5a57b45f6497f0ec4-d2eb3d9e57ee483e97b684fae64056c2.xml --timeout 120.000000 | exited | 0 | logs/92a271912ea44937ac9486a57f83ee89/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/1a163e96f75743c5a57b45f6497f0ec4-d2eb3d9e57ee483e97b684fae64056c2.xml | exited | 0 | logs/b4fd9d6e18a843e5a64335aa95bcf86c/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/1a163e96f75743c5a57b45f6497f0ec4-9774b59d14e24ee68f00061fb25adaaf.xml --timeout 120.000000 | exited | 0 | logs/0a4948d6a3a646cd8fca3f6290dd7122/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/1a163e96f75743c5a57b45f6497f0ec4-9774b59d14e24ee68f00061fb25adaaf.xml | exited | 0 | logs/fe63706d9f6447719394a977ffcd424b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/1a163e96f75743c5a57b45f6497f0ec4-72cb2193b7d14393924be08e462f8024.xml --timeout 120.000000 | exited | 0 | logs/69a8bc17c5864fb382cfc515f42a1a36/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/1a163e96f75743c5a57b45f6497f0ec4-72cb2193b7d14393924be08e462f8024.xml | exited | 0 | logs/73c83b29e6fa405faea9dd733590c78f/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/3b564d8115fb484b8e6267b27b373233/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/18fc654f601a443e85253f9b83387cb3/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/ec21385b46a64e26834f0a1c1a410b8a/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/be983b80d7b74db3bd0bd2ccb5522b76/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/bd8baa6c3460475fa84137126766f206/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\\\[value\\\]\\+edge$ --output-junit /build/.repropatch-results/725a698a231b49dd866fe6f650ef1b57-9c5386934dc444eab892375aea7fc1fd.xml --timeout 120.000000 | exited | 0 | logs/6f54ebf0788b4f07833b59dd6941dd40/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/725a698a231b49dd866fe6f650ef1b57-9c5386934dc444eab892375aea7fc1fd.xml | exited | 0 | logs/901a62c1dc0d48c098e0bc281a8712da/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/725a698a231b49dd866fe6f650ef1b57-359b997fd4be46aea50ccce8bf6bb979.xml --timeout 120.000000 | exited | 0 | logs/73be6449b0e64f469fb5961a72f63c85/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/725a698a231b49dd866fe6f650ef1b57-359b997fd4be46aea50ccce8bf6bb979.xml | exited | 0 | logs/f649201d59154d4a9128a489aef15fda/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/725a698a231b49dd866fe6f650ef1b57-e187651b3bf642b4aed5fef648af3add.xml --timeout 120.000000 | exited | 0 | logs/2d1f1d2c79e5455896b22836c8a6d862/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/725a698a231b49dd866fe6f650ef1b57-e187651b3bf642b4aed5fef648af3add.xml | exited | 0 | logs/2016662b211d427bb761dd19caa9771b/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/725a698a231b49dd866fe6f650ef1b57-bf3736f01e6c4f86b37f45ea52c753b1.xml --timeout 120.000000 | exited | 0 | logs/785bcf3ea1f5408eb96a8c15562011fa/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/725a698a231b49dd866fe6f650ef1b57-bf3736f01e6c4f86b37f45ea52c753b1.xml | exited | 0 | logs/b42f2005b4404377831de788d6482efb/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
外部生成过程、预算和 trace 未受本次运行管理或验证。
