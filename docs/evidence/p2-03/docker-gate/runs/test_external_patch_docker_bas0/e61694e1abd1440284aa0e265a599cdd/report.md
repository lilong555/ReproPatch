# ReproPatch e61694e1abd1440284aa0e265a599cdd

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：78e2a6b3fc9494eda54a9d34b87888c28d906d4f
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.226 秒
模型步骤：0；准入工具：0
模型停止原因：未知
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：否；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：73

外部来源标签（未认证）：fixture
外部轨迹：未验证的 opaque 附件，不作为测试或用量证据。

| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/49e258d551d54f73a94c53379367e5a5/68869085baf6420e929e535b78c2eeed.xml |
| baseline | positive\_values | 通过 | evidence/49e258d551d54f73a94c53379367e5a5/29e1ce8a65c644c49d9689a9eee88b29.xml |
| baseline | empty\_values | 通过 | evidence/49e258d551d54f73a94c53379367e5a5/9d44ade802c24ab99db5818190b7748a.xml |
| baseline | mixed\_values | 通过 | evidence/49e258d551d54f73a94c53379367e5a5/320b9d7a05634937bf9488a64f09fb2f.xml |
| independent | negative\_values | 通过 | evidence/94490c6333c24b3dae323dba50ebe63e/c9616be46df74ef2890e1a8555d4de83.xml |
| independent | positive\_values | 通过 | evidence/94490c6333c24b3dae323dba50ebe63e/469f8c532dc04d05bb7d71de68d4c20f.xml |
| independent | empty\_values | 通过 | evidence/94490c6333c24b3dae323dba50ebe63e/60dc7fc669044df0a6574d3135311638.xml |
| independent | mixed\_values | 通过 | evidence/94490c6333c24b3dae323dba50ebe63e/9eb26120913645228f893f66a8af1bca.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/29644effafdc4565b1d81102dd2435e5/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/751229c6b9c743469c8082ee0dcb686a/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/2076c295ee4b4d2cb2d9681c811d640e/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/a462644a0a244f6fa8b727b47f823a18/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/411de83d7f1148ce9bbe25f6472549f3/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/49e258d551d54f73a94c53379367e5a5-68869085baf6420e929e535b78c2eeed.xml --timeout 120.000000 | exited | 8 | logs/d53ec88e9d17402ea21a1b8a68e00e25/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/49e258d551d54f73a94c53379367e5a5-68869085baf6420e929e535b78c2eeed.xml | exited | 0 | logs/d78596abcf0e42b7840f6d049d5c2ca2/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/49e258d551d54f73a94c53379367e5a5-29e1ce8a65c644c49d9689a9eee88b29.xml --timeout 120.000000 | exited | 0 | logs/9464130b26404c1f9f2c1039622719be/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/49e258d551d54f73a94c53379367e5a5-29e1ce8a65c644c49d9689a9eee88b29.xml | exited | 0 | logs/6dffbb35a0e2495882ebdcb208d4b54d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/49e258d551d54f73a94c53379367e5a5-9d44ade802c24ab99db5818190b7748a.xml --timeout 120.000000 | exited | 0 | logs/6acdf7b35e144e62a9b00e3e340cdf5d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/49e258d551d54f73a94c53379367e5a5-9d44ade802c24ab99db5818190b7748a.xml | exited | 0 | logs/c9a9011b55b44596a8b4ec12038ea932/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/49e258d551d54f73a94c53379367e5a5-320b9d7a05634937bf9488a64f09fb2f.xml --timeout 120.000000 | exited | 0 | logs/d24fe059cf8440cb8532b912cddd5456/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/49e258d551d54f73a94c53379367e5a5-320b9d7a05634937bf9488a64f09fb2f.xml | exited | 0 | logs/4833377a11df4b8db018e947dec81cf4/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/2d7a8afed2d548019b5eb95370fb57bb/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/39c79e4100414c7e802f07fad78f7553/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/3b21ad7b22404d76b722665192cf0e6f/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/5d97cd7079644e6fae2d4b289e65df10/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/33b09612eb014fa78ea02cb5d479dcf6/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/94490c6333c24b3dae323dba50ebe63e-c9616be46df74ef2890e1a8555d4de83.xml --timeout 120.000000 | exited | 0 | logs/1580190f7b2a41a7a565abf3e2d6beb1/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/94490c6333c24b3dae323dba50ebe63e-c9616be46df74ef2890e1a8555d4de83.xml | exited | 0 | logs/b5029b224b2f44d4aa5738c2eeb6ab0b/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/94490c6333c24b3dae323dba50ebe63e-469f8c532dc04d05bb7d71de68d4c20f.xml --timeout 120.000000 | exited | 0 | logs/243bf80cc911433e82d4eea1f9ed61e5/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/94490c6333c24b3dae323dba50ebe63e-469f8c532dc04d05bb7d71de68d4c20f.xml | exited | 0 | logs/8ece3c3404fb45d1a2c5436351c31cc4/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/94490c6333c24b3dae323dba50ebe63e-60dc7fc669044df0a6574d3135311638.xml --timeout 120.000000 | exited | 0 | logs/41694ab9c4474aebb02e986ede9c5cf6/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/94490c6333c24b3dae323dba50ebe63e-60dc7fc669044df0a6574d3135311638.xml | exited | 0 | logs/d4834759701846f0ac95978ba03118e5/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/94490c6333c24b3dae323dba50ebe63e-9eb26120913645228f893f66a8af1bca.xml --timeout 120.000000 | exited | 0 | logs/a4639b7b0f544082bc0f25abae5ce182/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/94490c6333c24b3dae323dba50ebe63e-9eb26120913645228f893f66a8af1bca.xml | exited | 0 | logs/af8b7a9696864ec9a881f77f439106d1/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
外部生成过程、预算和 trace 未受本次运行管理或验证。
