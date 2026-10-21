# ReproPatch 1988c5e301674e529ac24cbdb43f0137

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：1a9a36bd8e92fea9a6db0fb0da890a220645f54c
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.063 秒
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
| baseline | negative\_values | 失败 | evidence/f189e11946944819831b33b99ac8b548/0c2a84a36e9344b5a926c8655c0bee1a.xml |
| baseline | positive\_values | 通过 | evidence/f189e11946944819831b33b99ac8b548/766ef915a1484c4ab001b0b82df3abc7.xml |
| baseline | empty\_values | 通过 | evidence/f189e11946944819831b33b99ac8b548/9162d99df7e54431972eb95a8e75e947.xml |
| baseline | mixed\_values | 通过 | evidence/f189e11946944819831b33b99ac8b548/d020024a44a647d5968470b4e5d80b09.xml |
| independent | negative\_values | 通过 | evidence/c7a3f4046b2948e18b7437c0e3cfbff7/e57d9002ece24edf951bd8e01929fd5d.xml |
| independent | positive\_values | 通过 | evidence/c7a3f4046b2948e18b7437c0e3cfbff7/926cef6163b34b098c1021e5f6c07bcc.xml |
| independent | empty\_values | 通过 | evidence/c7a3f4046b2948e18b7437c0e3cfbff7/2184df00cba4412e93626ebe511156e7.xml |
| independent | mixed\_values | 通过 | evidence/c7a3f4046b2948e18b7437c0e3cfbff7/ffefc7c05f8940ee918676a37be10a14.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/23f7b3abc1514fe6bb4ee091d8f2d8cb/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/9b03b4cad1024d2996975724520f6e4b/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/cdaef33e054d4657a861e9f653e4a0ee/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/1406b96cd6bd48f19d170f28ef0552eb/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/68dec8c40855489b86f60dbd37c8a108/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/f189e11946944819831b33b99ac8b548-0c2a84a36e9344b5a926c8655c0bee1a.xml --timeout 120.000000 | exited | 8 | logs/f6f5f0015cf5497881aa7a6f9e13e57b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f189e11946944819831b33b99ac8b548-0c2a84a36e9344b5a926c8655c0bee1a.xml | exited | 0 | logs/17f781615c3d4eb8b1eb10a3839bcbc8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/f189e11946944819831b33b99ac8b548-766ef915a1484c4ab001b0b82df3abc7.xml --timeout 120.000000 | exited | 0 | logs/0efb9128ebe0468598a3d9c9e8d70c52/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f189e11946944819831b33b99ac8b548-766ef915a1484c4ab001b0b82df3abc7.xml | exited | 0 | logs/01fa82179f3740ba92741b82f9117e52/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/f189e11946944819831b33b99ac8b548-9162d99df7e54431972eb95a8e75e947.xml --timeout 120.000000 | exited | 0 | logs/3a940268db2b422795ff5f3b909d5598/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f189e11946944819831b33b99ac8b548-9162d99df7e54431972eb95a8e75e947.xml | exited | 0 | logs/33b6d7157891474e87553ae3df61ff0d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/f189e11946944819831b33b99ac8b548-d020024a44a647d5968470b4e5d80b09.xml --timeout 120.000000 | exited | 0 | logs/7c0d8836a316446e9d74deb88c4f4aaa/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f189e11946944819831b33b99ac8b548-d020024a44a647d5968470b4e5d80b09.xml | exited | 0 | logs/679c1fcbc1cf42eeb52f83c97cf54317/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/e7fe45f93cac4249a45aad545906e17f/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/5776248ae19044c8a776d122b1ac27b7/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/7d645cae53be43f39020de5155af2b63/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/c85d16bddfca45a29684016caa64197a/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/c346d5a3dff04d3a973d4834fa79b227/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/c7a3f4046b2948e18b7437c0e3cfbff7-e57d9002ece24edf951bd8e01929fd5d.xml --timeout 120.000000 | exited | 0 | logs/d9484d8605344fc7b1f1bba96b93c915/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c7a3f4046b2948e18b7437c0e3cfbff7-e57d9002ece24edf951bd8e01929fd5d.xml | exited | 0 | logs/70cc6713195d47dea2ef8128e0e7ffe9/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/c7a3f4046b2948e18b7437c0e3cfbff7-926cef6163b34b098c1021e5f6c07bcc.xml --timeout 120.000000 | exited | 0 | logs/7712db7834f24158b2db899c39cf25e2/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c7a3f4046b2948e18b7437c0e3cfbff7-926cef6163b34b098c1021e5f6c07bcc.xml | exited | 0 | logs/d769b663efe84d29a64a68aa312249f6/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/c7a3f4046b2948e18b7437c0e3cfbff7-2184df00cba4412e93626ebe511156e7.xml --timeout 120.000000 | exited | 0 | logs/df791c20d269409e96998bd3e81c537d/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c7a3f4046b2948e18b7437c0e3cfbff7-2184df00cba4412e93626ebe511156e7.xml | exited | 0 | logs/645079c92fd142a785cbec325d741e5c/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/c7a3f4046b2948e18b7437c0e3cfbff7-ffefc7c05f8940ee918676a37be10a14.xml --timeout 120.000000 | exited | 0 | logs/8882303511b94fce9da3aee692e5b6bc/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c7a3f4046b2948e18b7437c0e3cfbff7-ffefc7c05f8940ee918676a37be10a14.xml | exited | 0 | logs/777be69e7e8a4c84b04640b70802f29b/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
