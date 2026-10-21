# ReproPatch 28f1ad86b5eb47808a52645456d0e6a2

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：16.280 秒
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
| baseline | negative\_values | 失败 | evidence/51d21b7e852140b582708909d4023799/7cad1df3491447528cbae6f584a5a49d.xml |
| baseline | positive\_values | 通过 | evidence/51d21b7e852140b582708909d4023799/137c2fdeb4f54b318c957acf1e2b73f2.xml |
| baseline | empty\_values | 通过 | evidence/51d21b7e852140b582708909d4023799/d28e2af7363e4f7a911a65ccdb5c4531.xml |
| baseline | mixed\_values | 通过 | evidence/51d21b7e852140b582708909d4023799/1b2dba5918d54ce2b45d6781ed7d5305.xml |
| agent\_check | negative\_values | 通过 | evidence/7dad9c72b1cd4e17b97ba74c0ba73b23/7cbc0683aa374a899fc709b5c8086ef1.xml |
| agent\_check | positive\_values | 通过 | evidence/7dad9c72b1cd4e17b97ba74c0ba73b23/b32faeb889b3470f9fa7e9e22a732ed2.xml |
| agent\_check | empty\_values | 通过 | evidence/7dad9c72b1cd4e17b97ba74c0ba73b23/e9ee93be4e3b4fe2b9bbd79b480b9b68.xml |
| agent\_check | mixed\_values | 通过 | evidence/7dad9c72b1cd4e17b97ba74c0ba73b23/3751dc48c7a24557bb52f188cd921e8d.xml |
| independent | negative\_values | 通过 | evidence/31d22023f7434649bd3a910398b914a8/97b61645918b46cd96c23faa0b17cc44.xml |
| independent | positive\_values | 通过 | evidence/31d22023f7434649bd3a910398b914a8/9a67e37275ca4c7e824b59d571d7e48f.xml |
| independent | empty\_values | 通过 | evidence/31d22023f7434649bd3a910398b914a8/a1d51d3c2b6c4ba49d985412625cb684.xml |
| independent | mixed\_values | 通过 | evidence/31d22023f7434649bd3a910398b914a8/4011004fd9ae4ae3b975aaabccd5b14f.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/d3efc61915c64e57a01e694f15fe923b/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/b580f151c3d44106b3d051fa2537704b/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/2232e53b5186426e858f7710cd71d43c/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/309724c6143c406a9ce7661b80149a89/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/25a0b047dcda4adf96592b10bdcad14c/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/51d21b7e852140b582708909d4023799-7cad1df3491447528cbae6f584a5a49d.xml --timeout 120.000000 | exited | 8 | logs/4eb80250d73540b19407f080dda76f50/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/51d21b7e852140b582708909d4023799-7cad1df3491447528cbae6f584a5a49d.xml | exited | 0 | logs/d6c41be77dc948398d3cf459c2f295d0/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/51d21b7e852140b582708909d4023799-137c2fdeb4f54b318c957acf1e2b73f2.xml --timeout 120.000000 | exited | 0 | logs/a55cf4b7bf7745da9cc5286d7993106f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/51d21b7e852140b582708909d4023799-137c2fdeb4f54b318c957acf1e2b73f2.xml | exited | 0 | logs/5ddfb3c371cd4b1583ed4403dd256930/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/51d21b7e852140b582708909d4023799-d28e2af7363e4f7a911a65ccdb5c4531.xml --timeout 120.000000 | exited | 0 | logs/58732b77fb35413492fefc995520358d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/51d21b7e852140b582708909d4023799-d28e2af7363e4f7a911a65ccdb5c4531.xml | exited | 0 | logs/c90fbe20384c433d94f235829053dfbf/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/51d21b7e852140b582708909d4023799-1b2dba5918d54ce2b45d6781ed7d5305.xml --timeout 120.000000 | exited | 0 | logs/57814aa068ed4fc997d3daef6299c354/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/51d21b7e852140b582708909d4023799-1b2dba5918d54ce2b45d6781ed7d5305.xml | exited | 0 | logs/28cfbb8cb5744175ae69e5a534eb8beb/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/3f274ff7225b433ebaa14e45359d35f8/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/4558de715a7b47888d703de20b88dfe1/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/fe986ef07d6e4bf897b7c4ef8ab705c0/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/676a71f371ea494bac9436c66a5c9647/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/c54bc197239342e6b54c959e6cf7adfe/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/7dad9c72b1cd4e17b97ba74c0ba73b23-7cbc0683aa374a899fc709b5c8086ef1.xml --timeout 120.000000 | exited | 0 | logs/8a63f76cbc234a38b49f3f559378bb42/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7dad9c72b1cd4e17b97ba74c0ba73b23-7cbc0683aa374a899fc709b5c8086ef1.xml | exited | 0 | logs/c44ae14040274a6f8df0155965aa07ac/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/7dad9c72b1cd4e17b97ba74c0ba73b23-b32faeb889b3470f9fa7e9e22a732ed2.xml --timeout 120.000000 | exited | 0 | logs/d36dfb725ead4a17bf56d9962aceaad1/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7dad9c72b1cd4e17b97ba74c0ba73b23-b32faeb889b3470f9fa7e9e22a732ed2.xml | exited | 0 | logs/3cc3427b924c4270be4aa854622660fb/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/7dad9c72b1cd4e17b97ba74c0ba73b23-e9ee93be4e3b4fe2b9bbd79b480b9b68.xml --timeout 120.000000 | exited | 0 | logs/f97ef34ac9204f638d84af80e841ae5c/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7dad9c72b1cd4e17b97ba74c0ba73b23-e9ee93be4e3b4fe2b9bbd79b480b9b68.xml | exited | 0 | logs/4f99b34ea1dd48a7a966490c44a733d2/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/7dad9c72b1cd4e17b97ba74c0ba73b23-3751dc48c7a24557bb52f188cd921e8d.xml --timeout 120.000000 | exited | 0 | logs/fd06f57c2ae4491a851bce8328385da6/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7dad9c72b1cd4e17b97ba74c0ba73b23-3751dc48c7a24557bb52f188cd921e8d.xml | exited | 0 | logs/728814fcdb7c4a3a97cf3dcb3fef97bd/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/fcd5d6057345423c83d60dca60585ca5/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/7bcb9a15d0fe4b73b09d1f6af5b085a7/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/37c7211c490e4cd0bcc2dc3a69329e5f/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/3bdb22848d034c1a8b85679bb9e8c7c3/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/9224b6f08f6f49bb845b89220470dde7/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/31d22023f7434649bd3a910398b914a8-97b61645918b46cd96c23faa0b17cc44.xml --timeout 120.000000 | exited | 0 | logs/240ed357c9744ae6bc276beef53559db/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/31d22023f7434649bd3a910398b914a8-97b61645918b46cd96c23faa0b17cc44.xml | exited | 0 | logs/3ad07362643646c7bdc13b5239c7d7a8/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/31d22023f7434649bd3a910398b914a8-9a67e37275ca4c7e824b59d571d7e48f.xml --timeout 120.000000 | exited | 0 | logs/61cecda2cc1c40458570ba029c8bca7e/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/31d22023f7434649bd3a910398b914a8-9a67e37275ca4c7e824b59d571d7e48f.xml | exited | 0 | logs/cfff34f974da4c31a39ef9439e199b87/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/31d22023f7434649bd3a910398b914a8-a1d51d3c2b6c4ba49d985412625cb684.xml --timeout 120.000000 | exited | 0 | logs/0b3bfc7791e54653969aa3a38e2b9a05/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/31d22023f7434649bd3a910398b914a8-a1d51d3c2b6c4ba49d985412625cb684.xml | exited | 0 | logs/e60166e65a38451386fbd8aef2867667/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/31d22023f7434649bd3a910398b914a8-4011004fd9ae4ae3b975aaabccd5b14f.xml --timeout 120.000000 | exited | 0 | logs/43e2f3f9a8ae44fdb3c68ff1db0b2c97/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/31d22023f7434649bd3a910398b914a8-4011004fd9ae4ae3b975aaabccd5b14f.xml | exited | 0 | logs/1f59876425c44058958e78ccff4da011/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
