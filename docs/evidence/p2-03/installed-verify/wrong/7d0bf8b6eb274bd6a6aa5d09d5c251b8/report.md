# ReproPatch 7d0bf8b6eb274bd6a6aa5d09d5c251b8

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：10.783 秒
模型步骤：0；准入工具：0
模型停止原因：未知
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：否；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：73

外部来源标签（未认证）：fixture

| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/fe7bccb9250446a387c5e2c548085099/d6001962cbf349afb15e528b3f68e580.xml |
| baseline | positive\_values | 通过 | evidence/fe7bccb9250446a387c5e2c548085099/d6756ee9f4c143a181439d8ac7a5f656.xml |
| baseline | empty\_values | 通过 | evidence/fe7bccb9250446a387c5e2c548085099/17df7a34128d4f5a818419261354dfc9.xml |
| baseline | mixed\_values | 通过 | evidence/fe7bccb9250446a387c5e2c548085099/6b17434eab3d4a9a9e2bd3367bf4ec5f.xml |
| independent | negative\_values | 失败 | evidence/a7d449e63e024f0ba9f70844ab2bfb11/7786bdc7cbc2457f87db89d31594cb9f.xml |
| independent | positive\_values | 通过 | evidence/a7d449e63e024f0ba9f70844ab2bfb11/b3556d1b8f564012b7ea8d2b93abfd65.xml |
| independent | empty\_values | 通过 | evidence/a7d449e63e024f0ba9f70844ab2bfb11/702c229d07a445a1b67672b90165a044.xml |
| independent | mixed\_values | 通过 | evidence/a7d449e63e024f0ba9f70844ab2bfb11/314a4c0810954004825b63c13d99ec29.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/185454a28d6e4817a00ed45ab345b913/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/2af88916582545b89c3210bbf3edec17/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/fae2d48ce50f4bddbfbc44a70b772a4a/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/0e5fd49ab9f8438c8bc5275a3dc32810/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/f928eb802c544738b9c221d946012dea/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/fe7bccb9250446a387c5e2c548085099-d6001962cbf349afb15e528b3f68e580.xml --timeout 120.000000 | exited | 8 | logs/e87c717b22404166a67785b10e1519fa/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fe7bccb9250446a387c5e2c548085099-d6001962cbf349afb15e528b3f68e580.xml | exited | 0 | logs/8984f070851f4e7da6cb14bb6860be2a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/fe7bccb9250446a387c5e2c548085099-d6756ee9f4c143a181439d8ac7a5f656.xml --timeout 120.000000 | exited | 0 | logs/2354ac60eee34957a7093f74ce36224e/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fe7bccb9250446a387c5e2c548085099-d6756ee9f4c143a181439d8ac7a5f656.xml | exited | 0 | logs/6070860cfe17466c996fe3af2c759082/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/fe7bccb9250446a387c5e2c548085099-17df7a34128d4f5a818419261354dfc9.xml --timeout 120.000000 | exited | 0 | logs/70db9a9961cd43c088b0f3205acdb2fe/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fe7bccb9250446a387c5e2c548085099-17df7a34128d4f5a818419261354dfc9.xml | exited | 0 | logs/26365e76ee364575a1ca9278e136cf8b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/fe7bccb9250446a387c5e2c548085099-6b17434eab3d4a9a9e2bd3367bf4ec5f.xml --timeout 120.000000 | exited | 0 | logs/7c1dfe4ac8bd43a8b2a7571c1b805081/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fe7bccb9250446a387c5e2c548085099-6b17434eab3d4a9a9e2bd3367bf4ec5f.xml | exited | 0 | logs/9cf048d83d0c44249e56b81bbac990bf/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/ad9956c5f0094203a3582ac1881efc09/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/7acf8ae7a92c4e258ccd2dadb45f2bb2/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/87ac21c4600042a5a0cc10f44d8b8b66/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/276bdaa9b55c4ed4b0be46a4c08e21ed/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/f9fcad4d3e394acdb60d386e02b681a7/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/a7d449e63e024f0ba9f70844ab2bfb11-7786bdc7cbc2457f87db89d31594cb9f.xml --timeout 120.000000 | exited | 8 | logs/8b63d333ec264bf3b8fb1f43310a31f7/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a7d449e63e024f0ba9f70844ab2bfb11-7786bdc7cbc2457f87db89d31594cb9f.xml | exited | 0 | logs/cd4a0efc09f04cce870c161a5cbeb9dd/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/a7d449e63e024f0ba9f70844ab2bfb11-b3556d1b8f564012b7ea8d2b93abfd65.xml --timeout 120.000000 | exited | 0 | logs/07090416fa5c4450899f9d89347bf169/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a7d449e63e024f0ba9f70844ab2bfb11-b3556d1b8f564012b7ea8d2b93abfd65.xml | exited | 0 | logs/59c628bf3cf7454baf4a7d501a9c82a0/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/a7d449e63e024f0ba9f70844ab2bfb11-702c229d07a445a1b67672b90165a044.xml --timeout 120.000000 | exited | 0 | logs/26ec2593131f496abf46019fbe446dbf/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a7d449e63e024f0ba9f70844ab2bfb11-702c229d07a445a1b67672b90165a044.xml | exited | 0 | logs/0b221def554c47d6b0cddffae99e55d8/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/a7d449e63e024f0ba9f70844ab2bfb11-314a4c0810954004825b63c13d99ec29.xml --timeout 120.000000 | exited | 0 | logs/b4214a2dc5a94936abcdfe91f00b1979/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a7d449e63e024f0ba9f70844ab2bfb11-314a4c0810954004825b63c13d99ec29.xml | exited | 0 | logs/ac8e14ca906741109cb562aa669963cf/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
外部生成过程、预算和 trace 未受本次运行管理或验证。
