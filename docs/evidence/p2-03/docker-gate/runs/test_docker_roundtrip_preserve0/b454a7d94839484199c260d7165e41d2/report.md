# ReproPatch b454a7d94839484199c260d7165e41d2

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：9a01a6e9b1a0eba4f887b24b35e2273080c05ab5
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：13.816 秒
模型步骤：5；准入工具：4
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：136


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/514ffe0d6dd840fdb39b6f4ea63ddcc5/9961dbe1a1a24dec943e5ad83f31ca7b.xml |
| baseline | positive\_values | 通过 | evidence/514ffe0d6dd840fdb39b6f4ea63ddcc5/a6eac3638c03475d802b30b4b55bf945.xml |
| baseline | empty\_values | 通过 | evidence/514ffe0d6dd840fdb39b6f4ea63ddcc5/ad9a19e21a2144418f03524e54842135.xml |
| baseline | mixed\_values | 通过 | evidence/514ffe0d6dd840fdb39b6f4ea63ddcc5/e2e6084ddbad48078e6207eb5a0207ea.xml |
| agent\_check | negative\_values | 通过 | evidence/7a514789d4a24edc8b4a1125092df154/21f8c71a2bf7470e99a847f773ff3b00.xml |
| agent\_check | positive\_values | 通过 | evidence/7a514789d4a24edc8b4a1125092df154/21db813cc9804a8ebce462127ce97e1f.xml |
| agent\_check | empty\_values | 通过 | evidence/7a514789d4a24edc8b4a1125092df154/69086552915d470085e4b41bb76ccf60.xml |
| agent\_check | mixed\_values | 通过 | evidence/7a514789d4a24edc8b4a1125092df154/80f28bacbcf94964bd424144682c9a99.xml |
| independent | negative\_values | 通过 | evidence/d11a3b705d95473688de5e699fe967cc/8433a9d159e049ec8c4d7fcc6cd6c907.xml |
| independent | positive\_values | 通过 | evidence/d11a3b705d95473688de5e699fe967cc/7d2eb6116b1845a8880340d29a815268.xml |
| independent | empty\_values | 通过 | evidence/d11a3b705d95473688de5e699fe967cc/711b09483faf43ae898f6e17f0b6769a.xml |
| independent | mixed\_values | 通过 | evidence/d11a3b705d95473688de5e699fe967cc/b7020c4c4d2f4e9bb07254689e43c3ff.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/38a3110490504ed5ac18f3c4f82b988b/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/86a280bed1674994a7dfbc58163aa8f6/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/b1f40c27136d4f3da59b25833e2b6eac/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/f03278be45ea4071b24186693a9033fa/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/61e670b40bbc458cb9721cde36d21ed1/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/514ffe0d6dd840fdb39b6f4ea63ddcc5-9961dbe1a1a24dec943e5ad83f31ca7b.xml --timeout 120.000000 | exited | 8 | logs/bdb9d44c211448338afe9062506398a2/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/514ffe0d6dd840fdb39b6f4ea63ddcc5-9961dbe1a1a24dec943e5ad83f31ca7b.xml | exited | 0 | logs/f8f3a3a3abd646d9895e32ea7e71d073/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/514ffe0d6dd840fdb39b6f4ea63ddcc5-a6eac3638c03475d802b30b4b55bf945.xml --timeout 120.000000 | exited | 0 | logs/61300014fd6340948875b568e9c9a612/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/514ffe0d6dd840fdb39b6f4ea63ddcc5-a6eac3638c03475d802b30b4b55bf945.xml | exited | 0 | logs/d9de685807f84bfbb6efbd66ecd424b8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/514ffe0d6dd840fdb39b6f4ea63ddcc5-ad9a19e21a2144418f03524e54842135.xml --timeout 120.000000 | exited | 0 | logs/9a696c6bce1e4f89b9bb9ef343eabe14/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/514ffe0d6dd840fdb39b6f4ea63ddcc5-ad9a19e21a2144418f03524e54842135.xml | exited | 0 | logs/fbfe9d9dfdd444608016e7fb22a5ed5e/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/514ffe0d6dd840fdb39b6f4ea63ddcc5-e2e6084ddbad48078e6207eb5a0207ea.xml --timeout 120.000000 | exited | 0 | logs/8153dab489f34de0a17e5a9b3caffcd8/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/514ffe0d6dd840fdb39b6f4ea63ddcc5-e2e6084ddbad48078e6207eb5a0207ea.xml | exited | 0 | logs/605ad6ac11e14b86a6212677c6790ec4/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/479d1edfc4c04c12b0cee3f36cb30e6a/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/d4e90b3ce7364e02b02798ea51764f12/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/56ae8e02020443ff8bec23867d7e119a/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/984e95bdc1ac42f6a2f982e5b99db66f/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/228ea6921b5b4768a9acd63a83ab1c73/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/7a514789d4a24edc8b4a1125092df154-21f8c71a2bf7470e99a847f773ff3b00.xml --timeout 120.000000 | exited | 0 | logs/73008d281be041c4b9f24d86432a1066/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7a514789d4a24edc8b4a1125092df154-21f8c71a2bf7470e99a847f773ff3b00.xml | exited | 0 | logs/442c2e1e8364491597e67a74778b5f77/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/7a514789d4a24edc8b4a1125092df154-21db813cc9804a8ebce462127ce97e1f.xml --timeout 120.000000 | exited | 0 | logs/55be3d5578f14d58aa44a41cfa1af720/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7a514789d4a24edc8b4a1125092df154-21db813cc9804a8ebce462127ce97e1f.xml | exited | 0 | logs/dcd751a64ae54e08aaed14e94f946f75/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/7a514789d4a24edc8b4a1125092df154-69086552915d470085e4b41bb76ccf60.xml --timeout 120.000000 | exited | 0 | logs/e221b5a2f89343b687e76b75b83246c4/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7a514789d4a24edc8b4a1125092df154-69086552915d470085e4b41bb76ccf60.xml | exited | 0 | logs/62790dfd61044841bd349b355f20c8ac/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/7a514789d4a24edc8b4a1125092df154-80f28bacbcf94964bd424144682c9a99.xml --timeout 120.000000 | exited | 0 | logs/f5e372bcbd7b4edd8dc3d7360440c673/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7a514789d4a24edc8b4a1125092df154-80f28bacbcf94964bd424144682c9a99.xml | exited | 0 | logs/c707ca06c94c4c48bb3ce01fd1ce5498/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/ae63911f699d4450ba5b0de7d46b84f9/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/a5b2dbca57ee444d91e0464d0ae30c0f/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/18f3626259ee49c2a81cd716c1a3773f/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/c2c8a6408b034518bde7b73e7c48a782/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/d1bf8470b289477f8a345f11b8e85ec6/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/d11a3b705d95473688de5e699fe967cc-8433a9d159e049ec8c4d7fcc6cd6c907.xml --timeout 120.000000 | exited | 0 | logs/c057ca9806c1481ca9c0568e1a0a7847/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d11a3b705d95473688de5e699fe967cc-8433a9d159e049ec8c4d7fcc6cd6c907.xml | exited | 0 | logs/9dcc6f92ad5d4d07861c2ce3e2f8ddcd/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/d11a3b705d95473688de5e699fe967cc-7d2eb6116b1845a8880340d29a815268.xml --timeout 120.000000 | exited | 0 | logs/03bff1460dba4bed80cd60660d699105/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d11a3b705d95473688de5e699fe967cc-7d2eb6116b1845a8880340d29a815268.xml | exited | 0 | logs/4e8701c58ec34808ac8f85e4d3720686/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/d11a3b705d95473688de5e699fe967cc-711b09483faf43ae898f6e17f0b6769a.xml --timeout 120.000000 | exited | 0 | logs/5c7f051ccd8147a883351eafe2845364/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d11a3b705d95473688de5e699fe967cc-711b09483faf43ae898f6e17f0b6769a.xml | exited | 0 | logs/848f375cca56491fa1eba97d1af84762/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/d11a3b705d95473688de5e699fe967cc-b7020c4c4d2f4e9bb07254689e43c3ff.xml --timeout 120.000000 | exited | 0 | logs/b9061e8006a5495fbc19adced7737ab3/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d11a3b705d95473688de5e699fe967cc-b7020c4c4d2f4e9bb07254689e43c3ff.xml | exited | 0 | logs/a20a7aa07f6545318eb5c23d726b1d4a/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
