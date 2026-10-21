# ReproPatch 31103e6878b043c9aa138704fadc3642

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：7c244ab02641719ac6911867979386e42b52da15
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：7.970 秒
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
| baseline | negative\_values | 失败 | evidence/7f1337fbd2234e658c485e75dd18a6b6/0c9471094ec347678989a9997e44f3ab.xml |
| baseline | positive\_values | 通过 | evidence/7f1337fbd2234e658c485e75dd18a6b6/2458fb6cfe7a4510bac29e8a5eb54885.xml |
| baseline | empty\_values | 通过 | evidence/7f1337fbd2234e658c485e75dd18a6b6/84d3ed7544894aa4913b07159015840a.xml |
| baseline | mixed\_values | 通过 | evidence/7f1337fbd2234e658c485e75dd18a6b6/ce5e456e867c4b608c9ee5dbe974a471.xml |
| independent | negative\_values | 通过 | evidence/017b5a4e47f0491f8d63bfab15076b7f/b57f323ceff64d2da11d0b68484e19fa.xml |
| independent | positive\_values | 通过 | evidence/017b5a4e47f0491f8d63bfab15076b7f/e3ac84f7791d477bbb7f90f0c540f707.xml |
| independent | empty\_values | 通过 | evidence/017b5a4e47f0491f8d63bfab15076b7f/1d7578656308401f940494d6ca7a0936.xml |
| independent | mixed\_values | 通过 | evidence/017b5a4e47f0491f8d63bfab15076b7f/66a6799c19f1457993b329bfef238dcd.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/525f9c1477634e81a4986803ef61fb17/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/906d22e0996d46919df9882e90e9b37a/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/547f24a7347542d1a6ed164c4b4a1b56/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/c41fbb4a53434c5cb2100c8efcd433e8/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/b9503290711346daa5ff883b2d1d65f6/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/7f1337fbd2234e658c485e75dd18a6b6-0c9471094ec347678989a9997e44f3ab.xml --timeout 120.000000 | exited | 8 | logs/e776b96edd8148fe9be1266f8783e278/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7f1337fbd2234e658c485e75dd18a6b6-0c9471094ec347678989a9997e44f3ab.xml | exited | 0 | logs/c3f54aa5bae24a24a9b65f83f010b5b9/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/7f1337fbd2234e658c485e75dd18a6b6-2458fb6cfe7a4510bac29e8a5eb54885.xml --timeout 120.000000 | exited | 0 | logs/5bd7d717360440c8aed82555e10a1e84/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7f1337fbd2234e658c485e75dd18a6b6-2458fb6cfe7a4510bac29e8a5eb54885.xml | exited | 0 | logs/4c84c4a809bf4386aed48c663a74b793/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/7f1337fbd2234e658c485e75dd18a6b6-84d3ed7544894aa4913b07159015840a.xml --timeout 120.000000 | exited | 0 | logs/80cbae42834f4ea9b42a90f1febff6d4/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7f1337fbd2234e658c485e75dd18a6b6-84d3ed7544894aa4913b07159015840a.xml | exited | 0 | logs/e943d6b7dedd4e2cae8dd2aff79a7272/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/7f1337fbd2234e658c485e75dd18a6b6-ce5e456e867c4b608c9ee5dbe974a471.xml --timeout 120.000000 | exited | 0 | logs/bfd15f9dc51848d289c1c9153e7e0bf5/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7f1337fbd2234e658c485e75dd18a6b6-ce5e456e867c4b608c9ee5dbe974a471.xml | exited | 0 | logs/c7521842d35c4a388fb90de943cf4c41/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/249ee2cb90f34741806d70aafdb7578a/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/37b84b9e619b4960b696027e23c8960f/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/3bf4f21a520a41d19fdd7ec30a98f7ee/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/02c20051527846dbafbbaa86a879052d/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/8b2965d41fdb4116be70b014812afd4a/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/017b5a4e47f0491f8d63bfab15076b7f-b57f323ceff64d2da11d0b68484e19fa.xml --timeout 120.000000 | exited | 0 | logs/e4c76b05f7774e07a967891834a15947/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/017b5a4e47f0491f8d63bfab15076b7f-b57f323ceff64d2da11d0b68484e19fa.xml | exited | 0 | logs/99783221a85e4adb84392a840a9c4b20/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/017b5a4e47f0491f8d63bfab15076b7f-e3ac84f7791d477bbb7f90f0c540f707.xml --timeout 120.000000 | exited | 0 | logs/2c3e93221fef48bba14872e5a42eb4d4/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/017b5a4e47f0491f8d63bfab15076b7f-e3ac84f7791d477bbb7f90f0c540f707.xml | exited | 0 | logs/64c470ddb75c4bf39e0a46513ca6eb60/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/017b5a4e47f0491f8d63bfab15076b7f-1d7578656308401f940494d6ca7a0936.xml --timeout 120.000000 | exited | 0 | logs/b642382db0cb48fb91b3a1bbc7cad21f/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/017b5a4e47f0491f8d63bfab15076b7f-1d7578656308401f940494d6ca7a0936.xml | exited | 0 | logs/71c1e64b5ae3461db2d9bd20a12d0006/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/017b5a4e47f0491f8d63bfab15076b7f-66a6799c19f1457993b329bfef238dcd.xml --timeout 120.000000 | exited | 0 | logs/d684b4b217644010b485a195231656b7/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/017b5a4e47f0491f8d63bfab15076b7f-66a6799c19f1457993b329bfef238dcd.xml | exited | 0 | logs/8b1f8fa2a19f4061a9ab005ca8fa84f5/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
