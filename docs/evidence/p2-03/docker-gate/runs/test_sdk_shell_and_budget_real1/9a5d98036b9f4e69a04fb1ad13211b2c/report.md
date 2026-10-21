# ReproPatch 9a5d98036b9f4e69a04fb1ad13211b2c

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：034779dd222137ac4a6af3eff9e7de572e6e290a
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：10.492 秒
模型步骤：3；准入工具：2
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：97


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/30b2239aa84346de8226ed8063ee1d86/f560a741e719430391859f5d6217d629.xml |
| baseline | positive\_values | 通过 | evidence/30b2239aa84346de8226ed8063ee1d86/c3c00f713e944db18714541aa3bd4bc0.xml |
| baseline | empty\_values | 通过 | evidence/30b2239aa84346de8226ed8063ee1d86/237758c028c14c8babb675bbd8260afd.xml |
| baseline | mixed\_values | 通过 | evidence/30b2239aa84346de8226ed8063ee1d86/cdf13b74774848eb9af0afe9165abc1d.xml |
| independent | negative\_values | 通过 | evidence/1bfc0efe36734ee1a5cbc9c8a39c1500/6bd149f44ae24c9ca87b9b160cc98f09.xml |
| independent | positive\_values | 通过 | evidence/1bfc0efe36734ee1a5cbc9c8a39c1500/0a20ddeafefc4dcb8f641cdd2c5ce323.xml |
| independent | empty\_values | 通过 | evidence/1bfc0efe36734ee1a5cbc9c8a39c1500/35b2c99ab7844ae495936960e8fbfdfe.xml |
| independent | mixed\_values | 通过 | evidence/1bfc0efe36734ee1a5cbc9c8a39c1500/edd4582559984ae89ca2f4829bcb9c2a.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/9d8966eb3f1546269774b3f663275d8e/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/8d573e5c66ab42cfae2a57928704d1ba/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/724ffd7bc3be46b186359eba42668377/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/705eb6aed9134895bdd076c7c617f590/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/70475f4fab1845e8a654da6aab24bddb/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/30b2239aa84346de8226ed8063ee1d86-f560a741e719430391859f5d6217d629.xml --timeout 120.000000 | exited | 8 | logs/62c7d9ebebae4738898f3bf908343f3b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/30b2239aa84346de8226ed8063ee1d86-f560a741e719430391859f5d6217d629.xml | exited | 0 | logs/e19d8dd18b794c91bf2f330fb9cc4206/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/30b2239aa84346de8226ed8063ee1d86-c3c00f713e944db18714541aa3bd4bc0.xml --timeout 120.000000 | exited | 0 | logs/21fbb4d9c234419c8d12b1d1318f6d7c/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/30b2239aa84346de8226ed8063ee1d86-c3c00f713e944db18714541aa3bd4bc0.xml | exited | 0 | logs/bf585f80515d4b6196f1d07c8aba0617/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/30b2239aa84346de8226ed8063ee1d86-237758c028c14c8babb675bbd8260afd.xml --timeout 120.000000 | exited | 0 | logs/41e61da614504dd8b47822d4636fbb42/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/30b2239aa84346de8226ed8063ee1d86-237758c028c14c8babb675bbd8260afd.xml | exited | 0 | logs/f32bd5cda0dc487d8e701caf9e4becd6/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/30b2239aa84346de8226ed8063ee1d86-cdf13b74774848eb9af0afe9165abc1d.xml --timeout 120.000000 | exited | 0 | logs/8f9e77d2a7304eb5bfec47ff4ebe93ef/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/30b2239aa84346de8226ed8063ee1d86-cdf13b74774848eb9af0afe9165abc1d.xml | exited | 0 | logs/526f413fd8664314a43e2f0b8e049d1f/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/93bb42b12edd4d80bc08746727b431ff/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/9891b0cfec0b4ee5a23a0a318a985e9a/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/d74b4d0daaf4448dbde74c0c04940fa8/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/ea424ef7dfb44481a5dd0f46bb642c7e/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/39844cc1fef04c23a1e398be34e28392/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/1bfc0efe36734ee1a5cbc9c8a39c1500-6bd149f44ae24c9ca87b9b160cc98f09.xml --timeout 120.000000 | exited | 0 | logs/a596a550fa1b417a911223bccc20acb6/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/1bfc0efe36734ee1a5cbc9c8a39c1500-6bd149f44ae24c9ca87b9b160cc98f09.xml | exited | 0 | logs/0152e04bbd264d89bc608358bf2ca54e/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/1bfc0efe36734ee1a5cbc9c8a39c1500-0a20ddeafefc4dcb8f641cdd2c5ce323.xml --timeout 120.000000 | exited | 0 | logs/7d137b3b6fe54ea1ad3270bb52a10a72/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/1bfc0efe36734ee1a5cbc9c8a39c1500-0a20ddeafefc4dcb8f641cdd2c5ce323.xml | exited | 0 | logs/a6f0f5aa3d894660895f866ae4dfa0fa/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/1bfc0efe36734ee1a5cbc9c8a39c1500-35b2c99ab7844ae495936960e8fbfdfe.xml --timeout 120.000000 | exited | 0 | logs/547fbc88643b4737af8ca3cd2889be22/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/1bfc0efe36734ee1a5cbc9c8a39c1500-35b2c99ab7844ae495936960e8fbfdfe.xml | exited | 0 | logs/ab2b1f312c2f40d793cdd9ba5de6ea93/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/1bfc0efe36734ee1a5cbc9c8a39c1500-edd4582559984ae89ca2f4829bcb9c2a.xml --timeout 120.000000 | exited | 0 | logs/ddcd4fea4954415cad5a60e6eb1c92a1/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/1bfc0efe36734ee1a5cbc9c8a39c1500-edd4582559984ae89ca2f4829bcb9c2a.xml | exited | 0 | logs/4c26380ba9374b339c0317966e63148e/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
