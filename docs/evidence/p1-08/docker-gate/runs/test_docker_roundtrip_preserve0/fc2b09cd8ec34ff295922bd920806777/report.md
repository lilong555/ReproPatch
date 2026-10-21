# ReproPatch fc2b09cd8ec34ff295922bd920806777

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：4342e119bd30791c284122bd8a54986c2ad01b05
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：12.123 秒
模型步骤：5；准入工具：4
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：131


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/4d47b37fb95444c48ee6b173646301d3/dfa4c1d7228a454db710bb13be25b983.xml |
| baseline | positive\_values | 通过 | evidence/4d47b37fb95444c48ee6b173646301d3/1e1fad0f76ab49cba31a2cbdc94bed4e.xml |
| baseline | empty\_values | 通过 | evidence/4d47b37fb95444c48ee6b173646301d3/19fd35474b9448b89e34baa85f985970.xml |
| baseline | mixed\_values | 通过 | evidence/4d47b37fb95444c48ee6b173646301d3/4104d814a9ee4658a9f587e3e5c4f5df.xml |
| agent\_check | negative\_values | 通过 | evidence/3eb1b59a3e0049b699a6eecabf142644/5cb84d39c4b54e7788ce4e7dab931c74.xml |
| agent\_check | positive\_values | 通过 | evidence/3eb1b59a3e0049b699a6eecabf142644/e56eeecdb6c04f84bab12541a30d6231.xml |
| agent\_check | empty\_values | 通过 | evidence/3eb1b59a3e0049b699a6eecabf142644/d56d5b40bd6b416db1b8e7f6c06e5fcb.xml |
| agent\_check | mixed\_values | 通过 | evidence/3eb1b59a3e0049b699a6eecabf142644/5a18300c6bc3494aabf9b53b9e2ca99a.xml |
| independent | negative\_values | 通过 | evidence/8dafdc5f25944859a284e7c27e985f50/d0418b9324904f24a268826275130ee8.xml |
| independent | positive\_values | 通过 | evidence/8dafdc5f25944859a284e7c27e985f50/cc5eb5164d2e45c199e3dd8357605291.xml |
| independent | empty\_values | 通过 | evidence/8dafdc5f25944859a284e7c27e985f50/e6c54916ee2949e5bd0302ea6448edab.xml |
| independent | mixed\_values | 通过 | evidence/8dafdc5f25944859a284e7c27e985f50/172b70b5c06d48c3a7e617424b74a984.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/7cdefbc7a2184e4bac54cec4791e3062/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/0f6583ecf6464bec8e10b96403db16a6/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/f936593356b64240944721d8921fcddf/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/fb44483ab5c145828b4eb58291af8c57/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/4f16a359e52242faa0818b688e406b2e/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/4d47b37fb95444c48ee6b173646301d3-dfa4c1d7228a454db710bb13be25b983.xml --timeout 120.000000 | exited | 8 | logs/e86ed206b70546fe99cd2ca8acb69b68/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4d47b37fb95444c48ee6b173646301d3-dfa4c1d7228a454db710bb13be25b983.xml | exited | 0 | logs/e4465a70d50445c5806c76b8f220177f/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/4d47b37fb95444c48ee6b173646301d3-1e1fad0f76ab49cba31a2cbdc94bed4e.xml --timeout 120.000000 | exited | 0 | logs/c11839fa8ead42aeae383f7e72dd2e95/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4d47b37fb95444c48ee6b173646301d3-1e1fad0f76ab49cba31a2cbdc94bed4e.xml | exited | 0 | logs/a043669ca6b74c7db689672cdfd03b73/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/4d47b37fb95444c48ee6b173646301d3-19fd35474b9448b89e34baa85f985970.xml --timeout 120.000000 | exited | 0 | logs/104530be6b7d4679acdda5b2adf72a2c/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4d47b37fb95444c48ee6b173646301d3-19fd35474b9448b89e34baa85f985970.xml | exited | 0 | logs/e976f9c691554e9a9e13c773916819b8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/4d47b37fb95444c48ee6b173646301d3-4104d814a9ee4658a9f587e3e5c4f5df.xml --timeout 120.000000 | exited | 0 | logs/f8daaa405ad34fda828c93adf82e5ca4/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4d47b37fb95444c48ee6b173646301d3-4104d814a9ee4658a9f587e3e5c4f5df.xml | exited | 0 | logs/f5f32c6ec3034df0866bd85717d05764/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/0707d22d3c194f198a6c1617001bd93f/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/2d67c0a8a5c94132bb942d7e4cd3c4d2/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/73c216de16e745c08c0622b5aa2cce0e/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/1773563128124413bf87ef4b6b36635f/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/1ce87ce03fc545fc8788d1d7a58d39ae/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/3eb1b59a3e0049b699a6eecabf142644-5cb84d39c4b54e7788ce4e7dab931c74.xml --timeout 120.000000 | exited | 0 | logs/1b795d4afd03488aa7c2115e411ee1a3/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3eb1b59a3e0049b699a6eecabf142644-5cb84d39c4b54e7788ce4e7dab931c74.xml | exited | 0 | logs/cfbcdd5d1340467f956dfedfe8d1e671/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/3eb1b59a3e0049b699a6eecabf142644-e56eeecdb6c04f84bab12541a30d6231.xml --timeout 120.000000 | exited | 0 | logs/163f0f371dbf4a99a4a924eb72c90302/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3eb1b59a3e0049b699a6eecabf142644-e56eeecdb6c04f84bab12541a30d6231.xml | exited | 0 | logs/d5f1e6080a2e455c81d35e39f2e30256/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/3eb1b59a3e0049b699a6eecabf142644-d56d5b40bd6b416db1b8e7f6c06e5fcb.xml --timeout 120.000000 | exited | 0 | logs/6240161c7806435f80e283b1794f184a/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3eb1b59a3e0049b699a6eecabf142644-d56d5b40bd6b416db1b8e7f6c06e5fcb.xml | exited | 0 | logs/56991366b5ae401aaf8e4050c751f3dc/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/3eb1b59a3e0049b699a6eecabf142644-5a18300c6bc3494aabf9b53b9e2ca99a.xml --timeout 120.000000 | exited | 0 | logs/a9f22527de3c425c82e729e07829d260/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3eb1b59a3e0049b699a6eecabf142644-5a18300c6bc3494aabf9b53b9e2ca99a.xml | exited | 0 | logs/597200ef242a4990aa5de3baa1e5b99a/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/8338b2142fde4713b7ddc4a1a55196b7/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/329c54cb7f7d4eefab1babdb28641d69/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/08e5656cf763443dad257d1123fc1f19/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/d905771df31a4cf09545cc80c5a6390b/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/671377f4770d44488bf33567adaa2b63/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/8dafdc5f25944859a284e7c27e985f50-d0418b9324904f24a268826275130ee8.xml --timeout 120.000000 | exited | 0 | logs/70e5ae52403a4cbb8bed8aba1758e9c6/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8dafdc5f25944859a284e7c27e985f50-d0418b9324904f24a268826275130ee8.xml | exited | 0 | logs/5ed29de03733432f812fb9acba3b4151/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/8dafdc5f25944859a284e7c27e985f50-cc5eb5164d2e45c199e3dd8357605291.xml --timeout 120.000000 | exited | 0 | logs/c49ae23b154640269890f45267162234/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8dafdc5f25944859a284e7c27e985f50-cc5eb5164d2e45c199e3dd8357605291.xml | exited | 0 | logs/047abb73936f493993f933a04f1a67af/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/8dafdc5f25944859a284e7c27e985f50-e6c54916ee2949e5bd0302ea6448edab.xml --timeout 120.000000 | exited | 0 | logs/dabbe483ac42434384cb59bf999c5ddb/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8dafdc5f25944859a284e7c27e985f50-e6c54916ee2949e5bd0302ea6448edab.xml | exited | 0 | logs/f68a5d7be1374ce385421a7600734cba/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/8dafdc5f25944859a284e7c27e985f50-172b70b5c06d48c3a7e617424b74a984.xml --timeout 120.000000 | exited | 0 | logs/a2a5a61b31b64a5ca8ed3c88e757dc8a/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8dafdc5f25944859a284e7c27e985f50-172b70b5c06d48c3a7e617424b74a984.xml | exited | 0 | logs/08a0ba6ad2c34abfb89252cb57b85848/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
