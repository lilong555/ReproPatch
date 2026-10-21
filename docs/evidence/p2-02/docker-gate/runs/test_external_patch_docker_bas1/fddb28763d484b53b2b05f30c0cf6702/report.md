# ReproPatch fddb28763d484b53b2b05f30c0cf6702

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：b7504720fab0c8e7374d31f447e0292ebc9a42f6
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：7.964 秒
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
| baseline | negative\_values | 失败 | evidence/f60fe32042624e5b868bb597bab03646/7283928b0eee473cbc12b9c978fc2454.xml |
| baseline | positive\_values | 通过 | evidence/f60fe32042624e5b868bb597bab03646/0ecc4c14a08e44c0aef425fafc807cca.xml |
| baseline | empty\_values | 通过 | evidence/f60fe32042624e5b868bb597bab03646/4376e7aba17f40b595ebb981285be8c9.xml |
| baseline | mixed\_values | 通过 | evidence/f60fe32042624e5b868bb597bab03646/00936d8bafa4410e9cd5df6b449bde5c.xml |
| independent | negative\_values | 失败 | evidence/18b45850395b4fef83114c6a4187d779/3a66bf2217f540f1ad8891f1695e891c.xml |
| independent | positive\_values | 通过 | evidence/18b45850395b4fef83114c6a4187d779/9aa1aea5903f4cc88aedadc560fd87fb.xml |
| independent | empty\_values | 通过 | evidence/18b45850395b4fef83114c6a4187d779/b549a0a7b96d45dc8283e294413cf4e7.xml |
| independent | mixed\_values | 通过 | evidence/18b45850395b4fef83114c6a4187d779/f9322fa54faf4d3ab18798c52fda99d2.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/aa9235ce934a4551842674bb3f6d8d6e/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/9fd5fc83daac47478c53527aaeed4240/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/f0b721fc8cdb4554a3e12c084c03d6c1/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/227b86be1b5b496fa08fc9167e266935/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/911c69ed94c74feca3dc73a4dc79952e/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/f60fe32042624e5b868bb597bab03646-7283928b0eee473cbc12b9c978fc2454.xml --timeout 120.000000 | exited | 8 | logs/fe4b07b1039d4bcaa573e32e47b45e27/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f60fe32042624e5b868bb597bab03646-7283928b0eee473cbc12b9c978fc2454.xml | exited | 0 | logs/132f54973cd8420ab95ebdbf8509468a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/f60fe32042624e5b868bb597bab03646-0ecc4c14a08e44c0aef425fafc807cca.xml --timeout 120.000000 | exited | 0 | logs/acf7a4fc81434a2c8d21347ff39d2d80/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f60fe32042624e5b868bb597bab03646-0ecc4c14a08e44c0aef425fafc807cca.xml | exited | 0 | logs/f801f97539304bc6a5170bbd6a4b1b9a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/f60fe32042624e5b868bb597bab03646-4376e7aba17f40b595ebb981285be8c9.xml --timeout 120.000000 | exited | 0 | logs/b96b7819a3194651aafaf9590a64845e/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f60fe32042624e5b868bb597bab03646-4376e7aba17f40b595ebb981285be8c9.xml | exited | 0 | logs/001e810be869495da4607b6112ab75bc/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/f60fe32042624e5b868bb597bab03646-00936d8bafa4410e9cd5df6b449bde5c.xml --timeout 120.000000 | exited | 0 | logs/9669c1f0383e425c88b62d8587e8d74f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f60fe32042624e5b868bb597bab03646-00936d8bafa4410e9cd5df6b449bde5c.xml | exited | 0 | logs/a0ed9f708ba6471d81cf653a3caca23e/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/08954c5966c14b87a1ede6d7b4b7de6b/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/019c8466409541c9ac980b89933b7d2e/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/813bc1e0001246aa90f5588e5f8d3c09/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/70b71c16240940df8e389be2b1c9744e/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/cb714e47c1d0480ca140f8d932b93e75/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/18b45850395b4fef83114c6a4187d779-3a66bf2217f540f1ad8891f1695e891c.xml --timeout 120.000000 | exited | 8 | logs/847bbaf7a0534272a23899bcc00fb552/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/18b45850395b4fef83114c6a4187d779-3a66bf2217f540f1ad8891f1695e891c.xml | exited | 0 | logs/5286631775364a9bb5324c482038a0b7/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/18b45850395b4fef83114c6a4187d779-9aa1aea5903f4cc88aedadc560fd87fb.xml --timeout 120.000000 | exited | 0 | logs/bcf8105d65344c47b50e6065a61747ce/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/18b45850395b4fef83114c6a4187d779-9aa1aea5903f4cc88aedadc560fd87fb.xml | exited | 0 | logs/07db792da8ab47e1a6f099133b00a7a5/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/18b45850395b4fef83114c6a4187d779-b549a0a7b96d45dc8283e294413cf4e7.xml --timeout 120.000000 | exited | 0 | logs/564d245de2df4e7c910e959b5e842fdb/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/18b45850395b4fef83114c6a4187d779-b549a0a7b96d45dc8283e294413cf4e7.xml | exited | 0 | logs/255622d04eb94b21bc20b3c1e5f2f36c/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/18b45850395b4fef83114c6a4187d779-f9322fa54faf4d3ab18798c52fda99d2.xml --timeout 120.000000 | exited | 0 | logs/56bbc9ab3f0b4fcb9b849e10a4d599a0/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/18b45850395b4fef83114c6a4187d779-f9322fa54faf4d3ab18798c52fda99d2.xml | exited | 0 | logs/33a425147c9b48ac9e86492b5ded6335/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
