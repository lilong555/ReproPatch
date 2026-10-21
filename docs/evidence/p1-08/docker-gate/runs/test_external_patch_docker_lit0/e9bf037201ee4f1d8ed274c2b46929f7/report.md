# ReproPatch e9bf037201ee4f1d8ed274c2b46929f7

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：cf6c6d8a2f2a524db6f3967f7922c13bb0b4220e
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：7.029 秒
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
| baseline | parse\[value\]+edge | 失败 | evidence/455920fb578e4877acc33ac2b60f4941/3d720e89fecd4da39825c1ac8a326a68.xml |
| baseline | positive\_values | 通过 | evidence/455920fb578e4877acc33ac2b60f4941/961ef4510e6441a4aa6886b1ee820a0d.xml |
| baseline | empty\_values | 通过 | evidence/455920fb578e4877acc33ac2b60f4941/bc150a7d682646809a07b47ca4a5995e.xml |
| baseline | mixed\_values | 通过 | evidence/455920fb578e4877acc33ac2b60f4941/7c73d5f1edd84c75a3b76d459b92300d.xml |
| independent | parse\[value\]+edge | 通过 | evidence/b5de64fb85be4da5869c91fe99354cdf/da15cc831bc0405e894506318b236e80.xml |
| independent | positive\_values | 通过 | evidence/b5de64fb85be4da5869c91fe99354cdf/05c2e8896570418493140c5dce2bef92.xml |
| independent | empty\_values | 通过 | evidence/b5de64fb85be4da5869c91fe99354cdf/a6efd7de5e04447cb88cb15c0bfe54cc.xml |
| independent | mixed\_values | 通过 | evidence/b5de64fb85be4da5869c91fe99354cdf/c135cdacd5b0424995ac22322109232e.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/824c50b1937244338ce0dd7bfc0e1658/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/fbf2bf747f69494b9a8b719827d0ea0c/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/2f5a1aff1bfc4045a4fd0dfd3ba5a861/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/def5e45ed6b04024a7380e4eaac4dc4e/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/326c844c40c84c79b85fea2865c226df/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\\\[value\\\]\\+edge$ --output-junit /build/.repropatch-results/455920fb578e4877acc33ac2b60f4941-3d720e89fecd4da39825c1ac8a326a68.xml --timeout 120.000000 | exited | 8 | logs/0515c122701c47ce8c8cd36d82dc216b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/455920fb578e4877acc33ac2b60f4941-3d720e89fecd4da39825c1ac8a326a68.xml | exited | 0 | logs/7bee0b43163b49408684b25a36f9f12c/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/455920fb578e4877acc33ac2b60f4941-961ef4510e6441a4aa6886b1ee820a0d.xml --timeout 120.000000 | exited | 0 | logs/2cf69faf9d304bf6964cb01b05d8dabd/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/455920fb578e4877acc33ac2b60f4941-961ef4510e6441a4aa6886b1ee820a0d.xml | exited | 0 | logs/dfc265b2f90245b4818260d67a06e29c/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/455920fb578e4877acc33ac2b60f4941-bc150a7d682646809a07b47ca4a5995e.xml --timeout 120.000000 | exited | 0 | logs/14b2e4c154bf4c4095e0594ed31a1a60/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/455920fb578e4877acc33ac2b60f4941-bc150a7d682646809a07b47ca4a5995e.xml | exited | 0 | logs/fe2409dad1654725a2681dbc332527a4/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/455920fb578e4877acc33ac2b60f4941-7c73d5f1edd84c75a3b76d459b92300d.xml --timeout 120.000000 | exited | 0 | logs/a57f84865b7747d3b99241a5d988947e/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/455920fb578e4877acc33ac2b60f4941-7c73d5f1edd84c75a3b76d459b92300d.xml | exited | 0 | logs/1b64b93b58d341c18bbb4bef996c181b/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/3099e7a33218412ea1521f19e550ca2c/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/f4b05e217ea64d939d8678cf479948f2/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/6a522c7a885943a4b636b7a760178d4e/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/986b8f07f41a43de81ee77a858789335/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/768a41d2017d4b7ea800ab87c0ff0f6e/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\\\[value\\\]\\+edge$ --output-junit /build/.repropatch-results/b5de64fb85be4da5869c91fe99354cdf-da15cc831bc0405e894506318b236e80.xml --timeout 120.000000 | exited | 0 | logs/66868a0c38bf4a6d93de4ae34cbd1b01/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b5de64fb85be4da5869c91fe99354cdf-da15cc831bc0405e894506318b236e80.xml | exited | 0 | logs/1cc46b743c524308bb22c0349ac62aee/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/b5de64fb85be4da5869c91fe99354cdf-05c2e8896570418493140c5dce2bef92.xml --timeout 120.000000 | exited | 0 | logs/121c1cc9e7f64fd39439be5752de00aa/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b5de64fb85be4da5869c91fe99354cdf-05c2e8896570418493140c5dce2bef92.xml | exited | 0 | logs/4569b8f461bd42d682a78f1f9fba2f5d/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/b5de64fb85be4da5869c91fe99354cdf-a6efd7de5e04447cb88cb15c0bfe54cc.xml --timeout 120.000000 | exited | 0 | logs/a005bd78f181421ab59d690211d33067/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b5de64fb85be4da5869c91fe99354cdf-a6efd7de5e04447cb88cb15c0bfe54cc.xml | exited | 0 | logs/08d6efa2f1f64430ae77a28decbd6855/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/b5de64fb85be4da5869c91fe99354cdf-c135cdacd5b0424995ac22322109232e.xml --timeout 120.000000 | exited | 0 | logs/8f2cf229439c45609472efd386c88048/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b5de64fb85be4da5869c91fe99354cdf-c135cdacd5b0424995ac22322109232e.xml | exited | 0 | logs/88cf134381214c41928eda93a51a3187/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
