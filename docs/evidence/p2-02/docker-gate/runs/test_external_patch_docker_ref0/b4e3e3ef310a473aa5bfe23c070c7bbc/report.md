# ReproPatch b4e3e3ef310a473aa5bfe23c070c7bbc

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：REQUIRED\_TEST\_NOT\_RUN
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：f4da2d1f5a7e662e4e970ecf21423e29476c622c
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.178 秒
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
| baseline | negative\_values | 失败 | evidence/a8e6cce166994e0d8e74766c7d71dd1e/474070f6491b43ef896bc1e8169136f4.xml |
| baseline | positive\_values | 通过 | evidence/a8e6cce166994e0d8e74766c7d71dd1e/2e261aa31a564c45a10c3a0fbcd4a527.xml |
| baseline | empty\_values | 通过 | evidence/a8e6cce166994e0d8e74766c7d71dd1e/d722240434724e4c9faf58938f9064a2.xml |
| baseline | mixed\_values | 通过 | evidence/a8e6cce166994e0d8e74766c7d71dd1e/9f94baf8ba834489be1ee8ded0115ece.xml |
| independent | negative\_values | 跳过 | evidence/0e31a19fb8f6447a990ef8c7a06af65a/f6c7a5b337124c1ca51e6b3532674640.xml |
| independent | positive\_values | 通过 | evidence/0e31a19fb8f6447a990ef8c7a06af65a/f137bcc1818c45d1973dbc59cfbd6aa2.xml |
| independent | empty\_values | 通过 | evidence/0e31a19fb8f6447a990ef8c7a06af65a/08ad5de3fd944c67ac69c821011c312b.xml |
| independent | mixed\_values | 失败 | evidence/0e31a19fb8f6447a990ef8c7a06af65a/f81abd6aa62b4118bf314ae330444b20.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/1898dd987c114f08aef0008f2b647f81/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/28b5b3c1790646a88dbf56916cadbf89/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/4cad3b54a6144419bb78ecedec61ff0f/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/9e02f9b0890948419826cea894e2bae2/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/6e162d2f73404ee98bd675e69559aee5/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/a8e6cce166994e0d8e74766c7d71dd1e-474070f6491b43ef896bc1e8169136f4.xml --timeout 120.000000 | exited | 8 | logs/971d21001311408982a6a78d16d11627/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a8e6cce166994e0d8e74766c7d71dd1e-474070f6491b43ef896bc1e8169136f4.xml | exited | 0 | logs/6b619bf8c94d497d91ec4a5351bb1829/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/a8e6cce166994e0d8e74766c7d71dd1e-2e261aa31a564c45a10c3a0fbcd4a527.xml --timeout 120.000000 | exited | 0 | logs/418e88e0b2f445ef80c2ec0e3b570dfa/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a8e6cce166994e0d8e74766c7d71dd1e-2e261aa31a564c45a10c3a0fbcd4a527.xml | exited | 0 | logs/be9baea7d9c042f7b2291f2d8428fb18/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/a8e6cce166994e0d8e74766c7d71dd1e-d722240434724e4c9faf58938f9064a2.xml --timeout 120.000000 | exited | 0 | logs/91ce60a8634a4f7c94556fbb33040392/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a8e6cce166994e0d8e74766c7d71dd1e-d722240434724e4c9faf58938f9064a2.xml | exited | 0 | logs/32ebab3296ca415bba6e6578d0bfd741/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/a8e6cce166994e0d8e74766c7d71dd1e-9f94baf8ba834489be1ee8ded0115ece.xml --timeout 120.000000 | exited | 0 | logs/0d72890fb3894c41b8edf61d24a064e6/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a8e6cce166994e0d8e74766c7d71dd1e-9f94baf8ba834489be1ee8ded0115ece.xml | exited | 0 | logs/86bc579f4e46405aa43cc525bcb3635a/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/02e9f7a3c8c349c5bed95a5f2329c6f9/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/606112274e874e79b68f9224f3ccc0da/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/6d31d1ba2d38446f89107c191d4fa7b6/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/c9522de51017496b89a2c47d7a80fe39/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/9ae9283957fc470693c0b80ababf28f7/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/0e31a19fb8f6447a990ef8c7a06af65a-f6c7a5b337124c1ca51e6b3532674640.xml --timeout 120.000000 | exited | 0 | logs/87dcbc57730e4c21b34295cc5742934c/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0e31a19fb8f6447a990ef8c7a06af65a-f6c7a5b337124c1ca51e6b3532674640.xml | exited | 0 | logs/69067505775c40a4bfca68ab81d06662/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/0e31a19fb8f6447a990ef8c7a06af65a-f137bcc1818c45d1973dbc59cfbd6aa2.xml --timeout 120.000000 | exited | 0 | logs/89cae23d92794cde98869b571a114fba/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0e31a19fb8f6447a990ef8c7a06af65a-f137bcc1818c45d1973dbc59cfbd6aa2.xml | exited | 0 | logs/27de3cc197e74709b7b06f6c1fff2b37/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/0e31a19fb8f6447a990ef8c7a06af65a-08ad5de3fd944c67ac69c821011c312b.xml --timeout 120.000000 | exited | 0 | logs/a8b770095a594be7b84dca8fbfc5af0a/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0e31a19fb8f6447a990ef8c7a06af65a-08ad5de3fd944c67ac69c821011c312b.xml | exited | 0 | logs/00529d05b398444583613090affddbc1/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/0e31a19fb8f6447a990ef8c7a06af65a-f81abd6aa62b4118bf314ae330444b20.xml --timeout 120.000000 | exited | 8 | logs/f6021f0721584cb2aa4679245612a180/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0e31a19fb8f6447a990ef8c7a06af65a-f81abd6aa62b4118bf314ae330444b20.xml | exited | 0 | logs/25caab133a594934acb2f59890965931/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
