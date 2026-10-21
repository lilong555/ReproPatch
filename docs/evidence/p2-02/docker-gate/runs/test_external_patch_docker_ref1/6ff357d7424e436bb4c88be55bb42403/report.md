# ReproPatch 6ff357d7424e436bb4c88be55bb42403

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：REQUIRED\_TEST\_NOT\_RUN
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：20792468c424903809245e5b304db8773a3a4ae6
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：6.412 秒
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
| baseline | negative\_values | 失败 | evidence/0af82ac411c3435baa3b4b601540b632/dd1ad8ef872f409b885867fe75f835f2.xml |
| baseline | positive\_values | 通过 | evidence/0af82ac411c3435baa3b4b601540b632/99d89d00878f4ca28035a8c987ca2b72.xml |
| baseline | empty\_values | 通过 | evidence/0af82ac411c3435baa3b4b601540b632/a82157289e2143afb81fa716f177762d.xml |
| baseline | mixed\_values | 通过 | evidence/0af82ac411c3435baa3b4b601540b632/cdce8f3f2122421994fc36eabb57d67a.xml |
| independent | negative\_values | 未运行 | 未知 |
| independent | positive\_values | 未运行 | 未知 |
| independent | empty\_values | 未运行 | 未知 |
| independent | mixed\_values | 未运行 | 未知 |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/5a4549fb8365451193b0be94deb484ff/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/af4dc73662744429a64607b9319743f9/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/fed0b70818f94d1da5bfe716b208235d/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/6b533414d39e496c9efb2b3ffdcbdfae/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/cbc49285f5ce48b2ba96259fb1a34e3a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/0af82ac411c3435baa3b4b601540b632-dd1ad8ef872f409b885867fe75f835f2.xml --timeout 120.000000 | exited | 8 | logs/e0e3cea11dc241348a336d923c25cd1d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0af82ac411c3435baa3b4b601540b632-dd1ad8ef872f409b885867fe75f835f2.xml | exited | 0 | logs/f49468c8dfd940928734ce37d26a3761/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/0af82ac411c3435baa3b4b601540b632-99d89d00878f4ca28035a8c987ca2b72.xml --timeout 120.000000 | exited | 0 | logs/c3dcc9ab3d734dd388db222f490ce58e/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0af82ac411c3435baa3b4b601540b632-99d89d00878f4ca28035a8c987ca2b72.xml | exited | 0 | logs/ef38f8ea07a840dbae0d8ac1683cdc11/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/0af82ac411c3435baa3b4b601540b632-a82157289e2143afb81fa716f177762d.xml --timeout 120.000000 | exited | 0 | logs/96e827b0cdf7477e9207d2611886f8ba/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0af82ac411c3435baa3b4b601540b632-a82157289e2143afb81fa716f177762d.xml | exited | 0 | logs/d4e8928738204446af1f4935b1c6f1e2/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/0af82ac411c3435baa3b4b601540b632-cdce8f3f2122421994fc36eabb57d67a.xml --timeout 120.000000 | exited | 0 | logs/adbfbf7ab7d44a0a9a146bc013cea37f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0af82ac411c3435baa3b4b601540b632-cdce8f3f2122421994fc36eabb57d67a.xml | exited | 0 | logs/a335dc96df324c6888d981908eccb5d8/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/29ab5c9281e549a9ab992a9861bb41a1/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/86f55c4c7cd045e4826e3fa02e11a12d/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/ce5c1cafee3c4fc783852dbf598f0362/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/f0efcf599c584f9c9e9d3b0167422d1a/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
