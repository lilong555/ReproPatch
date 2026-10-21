# ReproPatch 0ef140ac7d2e4a3dafcbbf77e64c3fa7

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：05f2b15331faabbfb21f7fd01bc46f58bb20b670
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.367 秒
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
| baseline | negative\_values | 失败 | evidence/0896982941644cec8330bf8a34ee0ba5/15e4149c0af64dceb0aaa7ad97e00283.xml |
| baseline | positive\_values | 通过 | evidence/0896982941644cec8330bf8a34ee0ba5/b1f0a8291aa84be8984a6eea03ead3b0.xml |
| baseline | empty\_values | 通过 | evidence/0896982941644cec8330bf8a34ee0ba5/13a66ac16efc45299fc3f3cebeec40ec.xml |
| baseline | mixed\_values | 通过 | evidence/0896982941644cec8330bf8a34ee0ba5/9e80e173b6274a9d95370a80da6fd9a4.xml |
| independent | negative\_values | 失败 | evidence/2147a5486e274b28a28f6fe0cfe62b4b/371ceea12bb542babeb6be59bd37ecf4.xml |
| independent | positive\_values | 通过 | evidence/2147a5486e274b28a28f6fe0cfe62b4b/0568f66b23bc488b8a3e9e18abeb77a8.xml |
| independent | empty\_values | 通过 | evidence/2147a5486e274b28a28f6fe0cfe62b4b/c02186ed72614498a5d9b154b8bebe6f.xml |
| independent | mixed\_values | 通过 | evidence/2147a5486e274b28a28f6fe0cfe62b4b/67f654ace8d54c1182d290070912ced3.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/0540da6878ab432a91cfe96a189d84cc/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/e4940eecbeaf407c81249158fdf6518a/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/6b8b0942c42a46129e3f9a7f983cde2a/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/b739af781b7c4b0896165e5d5162cf25/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/dac93fcf636b4e458c8080dca6e5596c/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/0896982941644cec8330bf8a34ee0ba5-15e4149c0af64dceb0aaa7ad97e00283.xml --timeout 120.000000 | exited | 8 | logs/ab89b25bf7164b16beed850fa4cfa6d1/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0896982941644cec8330bf8a34ee0ba5-15e4149c0af64dceb0aaa7ad97e00283.xml | exited | 0 | logs/24884d2ef488441e98e40d9bc7fff316/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/0896982941644cec8330bf8a34ee0ba5-b1f0a8291aa84be8984a6eea03ead3b0.xml --timeout 120.000000 | exited | 0 | logs/ebf86a0bdafe4d89a27a5ee33ec378b9/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0896982941644cec8330bf8a34ee0ba5-b1f0a8291aa84be8984a6eea03ead3b0.xml | exited | 0 | logs/ffffa64f4ed0463fade926fd6d7a9d25/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/0896982941644cec8330bf8a34ee0ba5-13a66ac16efc45299fc3f3cebeec40ec.xml --timeout 120.000000 | exited | 0 | logs/4ae37ef2c77947d6809db19396a9d9e5/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0896982941644cec8330bf8a34ee0ba5-13a66ac16efc45299fc3f3cebeec40ec.xml | exited | 0 | logs/df9b20568a6d459296741376dd85be58/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/0896982941644cec8330bf8a34ee0ba5-9e80e173b6274a9d95370a80da6fd9a4.xml --timeout 120.000000 | exited | 0 | logs/642a7796807642aaae078e26b4002958/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0896982941644cec8330bf8a34ee0ba5-9e80e173b6274a9d95370a80da6fd9a4.xml | exited | 0 | logs/a4437eb9bbcf4dd08b6b83d3848eedce/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/3d04022be7fc401b9f98221b2e95d18e/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/48e71462e987439a835a84ea3740cab6/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/bf99a25156d94f6290a5a886b2d37e69/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/0d7ad26018a1492d81b7d6b2770bb28c/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/3194d22b60654d36b367913e00759484/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/2147a5486e274b28a28f6fe0cfe62b4b-371ceea12bb542babeb6be59bd37ecf4.xml --timeout 120.000000 | exited | 8 | logs/a163d5b9023d421db6c23c839d9b98f4/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/2147a5486e274b28a28f6fe0cfe62b4b-371ceea12bb542babeb6be59bd37ecf4.xml | exited | 0 | logs/141791807a34417cbd6b27ba24216070/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/2147a5486e274b28a28f6fe0cfe62b4b-0568f66b23bc488b8a3e9e18abeb77a8.xml --timeout 120.000000 | exited | 0 | logs/5a5e4d6082c441f18da1bf3379c9cf04/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/2147a5486e274b28a28f6fe0cfe62b4b-0568f66b23bc488b8a3e9e18abeb77a8.xml | exited | 0 | logs/dfa83903d8d64b1da03ae1990ebca850/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/2147a5486e274b28a28f6fe0cfe62b4b-c02186ed72614498a5d9b154b8bebe6f.xml --timeout 120.000000 | exited | 0 | logs/d4e1121ec2004a22a827127f23087924/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/2147a5486e274b28a28f6fe0cfe62b4b-c02186ed72614498a5d9b154b8bebe6f.xml | exited | 0 | logs/286149b87eec46118ea065a1abad3b80/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/2147a5486e274b28a28f6fe0cfe62b4b-67f654ace8d54c1182d290070912ced3.xml --timeout 120.000000 | exited | 0 | logs/5b3a9ac15a5d47228f89431115dc9e74/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/2147a5486e274b28a28f6fe0cfe62b4b-67f654ace8d54c1182d290070912ced3.xml | exited | 0 | logs/cbb1754be43d4839bbaf2a88585c12b3/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
