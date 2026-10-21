# ReproPatch d599df38fb7c46559dd863381f8d0254

任务：negative-maximum
入口：run
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：82792f9d7c492e4f3e265ecd14eeb882ec38dbc8
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.775 秒
模型步骤：2；准入工具：1
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：85


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/f7a8f29f0dbf46a0b4ea61baf2dafe7c/00cf3f56194e40758d70dff25df0b933.xml |
| baseline | positive\_values | 通过 | evidence/f7a8f29f0dbf46a0b4ea61baf2dafe7c/483509d056ec4e7cae6e07df69b473f7.xml |
| baseline | empty\_values | 通过 | evidence/f7a8f29f0dbf46a0b4ea61baf2dafe7c/a159e869815048d09a5770e5809e3e7b.xml |
| baseline | mixed\_values | 通过 | evidence/f7a8f29f0dbf46a0b4ea61baf2dafe7c/a67ab18143584017be7b799ce8e68c0c.xml |
| independent | negative\_values | 失败 | evidence/fa647d919c8b4de09edab02b10c7777b/e729028cd2d84193944f2ca8f719b420.xml |
| independent | positive\_values | 通过 | evidence/fa647d919c8b4de09edab02b10c7777b/7080dc14babc43cab7611364a39d7e7d.xml |
| independent | empty\_values | 通过 | evidence/fa647d919c8b4de09edab02b10c7777b/374d5c55b2a646ad86e8690c4343b379.xml |
| independent | mixed\_values | 通过 | evidence/fa647d919c8b4de09edab02b10c7777b/9dbd4bff28c24c419f89d02cf966a98b.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/54e84d1130bb4d04b608003ff5d36b74/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/cc171ad46e604d588135278d4261267e/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/2f372cd42c114433bcf6e37d26f7b993/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/f10388ad10f44d2e8a6c8d78f4ac2efa/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/49559f990b6a4bfbb43ae171ef32c4c4/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/f7a8f29f0dbf46a0b4ea61baf2dafe7c-00cf3f56194e40758d70dff25df0b933.xml --timeout 120.000000 | exited | 8 | logs/e408b8ea8f6546c9b2ede1201adf1c4b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f7a8f29f0dbf46a0b4ea61baf2dafe7c-00cf3f56194e40758d70dff25df0b933.xml | exited | 0 | logs/3e0783d2f8a94c729629ad3c47de72c8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/f7a8f29f0dbf46a0b4ea61baf2dafe7c-483509d056ec4e7cae6e07df69b473f7.xml --timeout 120.000000 | exited | 0 | logs/4f858216788644fab6c600b6d121d5e6/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f7a8f29f0dbf46a0b4ea61baf2dafe7c-483509d056ec4e7cae6e07df69b473f7.xml | exited | 0 | logs/9145381ffc624b11a2c31b0e4aab8763/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/f7a8f29f0dbf46a0b4ea61baf2dafe7c-a159e869815048d09a5770e5809e3e7b.xml --timeout 120.000000 | exited | 0 | logs/882104e25619486b9c6b82f651616df5/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f7a8f29f0dbf46a0b4ea61baf2dafe7c-a159e869815048d09a5770e5809e3e7b.xml | exited | 0 | logs/f4ed4d98043e461cb3a7a35453e4d23f/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/f7a8f29f0dbf46a0b4ea61baf2dafe7c-a67ab18143584017be7b799ce8e68c0c.xml --timeout 120.000000 | exited | 0 | logs/e8b64432ca324f70af3174c462ab5aa2/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f7a8f29f0dbf46a0b4ea61baf2dafe7c-a67ab18143584017be7b799ce8e68c0c.xml | exited | 0 | logs/4eb3b36f308a42c9873e7a24c8d33f0e/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/a4d3c7754b2940049c28804be94ec1d2/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/adea4455e27147d1abb2a521830978e8/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/f181ac4b5b38447a8bd52365b2e3318c/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/5fface2819f74cb68158b696d701d4e0/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/4396c25cbbf54ca28d87c8ea1f7b7d33/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/fa647d919c8b4de09edab02b10c7777b-e729028cd2d84193944f2ca8f719b420.xml --timeout 120.000000 | exited | 8 | logs/2a435f86242348e7ad7287a4b7ed2c39/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fa647d919c8b4de09edab02b10c7777b-e729028cd2d84193944f2ca8f719b420.xml | exited | 0 | logs/a41583183f68498a86a5ec3e62e19520/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/fa647d919c8b4de09edab02b10c7777b-7080dc14babc43cab7611364a39d7e7d.xml --timeout 120.000000 | exited | 0 | logs/0e883a0ad65140ceba8470eee788a03b/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fa647d919c8b4de09edab02b10c7777b-7080dc14babc43cab7611364a39d7e7d.xml | exited | 0 | logs/9c72c64cfdeb43579127c190bad3e0ce/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/fa647d919c8b4de09edab02b10c7777b-374d5c55b2a646ad86e8690c4343b379.xml --timeout 120.000000 | exited | 0 | logs/0754255c76d84901a433dff8a3bc01a0/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fa647d919c8b4de09edab02b10c7777b-374d5c55b2a646ad86e8690c4343b379.xml | exited | 0 | logs/145206363fd3445ab34a784034ede070/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/fa647d919c8b4de09edab02b10c7777b-9dbd4bff28c24c419f89d02cf966a98b.xml --timeout 120.000000 | exited | 0 | logs/e4b3179b0957419799d0e57105d9e7e4/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fa647d919c8b4de09edab02b10c7777b-9dbd4bff28c24c419f89d02cf966a98b.xml | exited | 0 | logs/54c5bcc912a94d38accfe38836f88298/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
