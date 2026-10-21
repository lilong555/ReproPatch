# ReproPatch 35826a9cf2624003b203c40f51dd6719

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：101d5d6e4e632baa7ccc877d9ee75640ac99b7f1
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.307 秒
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
| baseline | negative\_values | 失败 | evidence/ac861f0b8ec14832b27df29d9274fccc/477ce5696c724ca2a56eea6f4c8be32f.xml |
| baseline | positive\_values | 通过 | evidence/ac861f0b8ec14832b27df29d9274fccc/a0dd6fe09f044955936ddbafc1b497bb.xml |
| baseline | empty\_values | 通过 | evidence/ac861f0b8ec14832b27df29d9274fccc/e42152dce32048fd91c101cc4fd87c4d.xml |
| baseline | mixed\_values | 通过 | evidence/ac861f0b8ec14832b27df29d9274fccc/2e18415be4214e17882d99cfefefdf57.xml |
| independent | negative\_values | 失败 | evidence/5dd8e563a5b1403aaaa5f7e647e6de71/3a1f1715610e429fa1f4c9f005c393ec.xml |
| independent | positive\_values | 通过 | evidence/5dd8e563a5b1403aaaa5f7e647e6de71/15a75019cc364df09a437831a999516c.xml |
| independent | empty\_values | 通过 | evidence/5dd8e563a5b1403aaaa5f7e647e6de71/3384802b3cde433cac756387adbce125.xml |
| independent | mixed\_values | 通过 | evidence/5dd8e563a5b1403aaaa5f7e647e6de71/03504297123b4056b6e8b7135a8eaf53.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/1af45fc12ea74fdb96be911fd59d3396/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/384225f0ac914f87891af92b97f22c95/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/4f357a50a2144dffb4f5e72293614fbb/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/46da66f4df8d42e69da8ed67c19e9247/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/ff278ba6ea6e4edbad047214d3a74cf7/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/ac861f0b8ec14832b27df29d9274fccc-477ce5696c724ca2a56eea6f4c8be32f.xml --timeout 120.000000 | exited | 8 | logs/8f8df973c9ff429b8f38aa8244528a2c/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ac861f0b8ec14832b27df29d9274fccc-477ce5696c724ca2a56eea6f4c8be32f.xml | exited | 0 | logs/87b20b0038c843c7816ef236884493b6/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/ac861f0b8ec14832b27df29d9274fccc-a0dd6fe09f044955936ddbafc1b497bb.xml --timeout 120.000000 | exited | 0 | logs/0e9eeefe34dc424aa563a16661f2f485/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ac861f0b8ec14832b27df29d9274fccc-a0dd6fe09f044955936ddbafc1b497bb.xml | exited | 0 | logs/b52e7ac4c7d540b9864cc1739bb1dd4b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/ac861f0b8ec14832b27df29d9274fccc-e42152dce32048fd91c101cc4fd87c4d.xml --timeout 120.000000 | exited | 0 | logs/8751056e8b4343298c0af99b91407fb5/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ac861f0b8ec14832b27df29d9274fccc-e42152dce32048fd91c101cc4fd87c4d.xml | exited | 0 | logs/f655db3b2d4745768bd0dc991ac7212b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/ac861f0b8ec14832b27df29d9274fccc-2e18415be4214e17882d99cfefefdf57.xml --timeout 120.000000 | exited | 0 | logs/e0c077b4964248aebe41de34e9fa399b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ac861f0b8ec14832b27df29d9274fccc-2e18415be4214e17882d99cfefefdf57.xml | exited | 0 | logs/912cd0fefa9a436e9ff27598037f2171/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/0525b273034347bea7188075f86e70c3/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/427bd9b1143444e3a623745fd42a696e/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/13a4cd6848c4488c841f50a8b806fb64/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/76ecad4c5f4346678c687ffad3fca164/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/91df00e2bfc84c6b988ba68fb98436e8/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/5dd8e563a5b1403aaaa5f7e647e6de71-3a1f1715610e429fa1f4c9f005c393ec.xml --timeout 120.000000 | exited | 8 | logs/f87bcf3331d249d398bd51f5c7485ae3/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5dd8e563a5b1403aaaa5f7e647e6de71-3a1f1715610e429fa1f4c9f005c393ec.xml | exited | 0 | logs/f906c56eda7b43a89e162e0a6f13c8f6/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/5dd8e563a5b1403aaaa5f7e647e6de71-15a75019cc364df09a437831a999516c.xml --timeout 120.000000 | exited | 0 | logs/e21fd28b5f6c433ca34f2ea0c36384e6/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5dd8e563a5b1403aaaa5f7e647e6de71-15a75019cc364df09a437831a999516c.xml | exited | 0 | logs/c931222b12ff41f19e1109c23177c164/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/5dd8e563a5b1403aaaa5f7e647e6de71-3384802b3cde433cac756387adbce125.xml --timeout 120.000000 | exited | 0 | logs/47dad6955c04488386d237a45b3a577e/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5dd8e563a5b1403aaaa5f7e647e6de71-3384802b3cde433cac756387adbce125.xml | exited | 0 | logs/a00dbac238284982930a8b37370bfc1c/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/5dd8e563a5b1403aaaa5f7e647e6de71-03504297123b4056b6e8b7135a8eaf53.xml --timeout 120.000000 | exited | 0 | logs/c97e195739144116aeed424d4f3a177f/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5dd8e563a5b1403aaaa5f7e647e6de71-03504297123b4056b6e8b7135a8eaf53.xml | exited | 0 | logs/076ea8e47f204abab3453d90447e7a4c/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
外部生成过程、预算和 trace 未受本次运行管理或验证。
