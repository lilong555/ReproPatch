# ReproPatch e840631096864ada9274f738c72aa4dd

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：b980ddc2e419d17524178cf59619b50e148d1d27
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：7.665 秒
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
| baseline | negative\_values | 失败 | evidence/c8c42712d2e945f88e4b2d626b415287/1eae1e42f9ee433b97d9a42189aa423a.xml |
| baseline | positive\_values | 通过 | evidence/c8c42712d2e945f88e4b2d626b415287/e00c4d272c864d7783a6865fa9c35521.xml |
| baseline | empty\_values | 通过 | evidence/c8c42712d2e945f88e4b2d626b415287/59746533614d48758c603ba00a28c676.xml |
| baseline | mixed\_values | 通过 | evidence/c8c42712d2e945f88e4b2d626b415287/eead7c514f104bc3ab8dbc47b20cdcee.xml |
| independent | negative\_values | 失败 | evidence/7fee18cd5b274bb7826a706510d7b36e/66200a7c1cde4c23acf114eb6313c9c0.xml |
| independent | positive\_values | 通过 | evidence/7fee18cd5b274bb7826a706510d7b36e/446e03c9a9744475b99e39909bbfdf86.xml |
| independent | empty\_values | 通过 | evidence/7fee18cd5b274bb7826a706510d7b36e/5971c96d3c324c3cb1064ca38611d20e.xml |
| independent | mixed\_values | 通过 | evidence/7fee18cd5b274bb7826a706510d7b36e/055f229169a24ef6b8e67d46392f5e8c.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/24a405d40bb14695b2cef36caae2d47e/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/f9d8e92754e84485b4662a2ac41750da/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/a15f043c8c614817b26f32ca2de17ae8/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/570af4ef47314650931f681dab39bd23/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/f1039295777e4fefa15ac950b6d007ac/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/c8c42712d2e945f88e4b2d626b415287-1eae1e42f9ee433b97d9a42189aa423a.xml --timeout 120.000000 | exited | 8 | logs/e6265fc3395c41a5b0f083fd55947b50/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c8c42712d2e945f88e4b2d626b415287-1eae1e42f9ee433b97d9a42189aa423a.xml | exited | 0 | logs/fb0b52a1e3f84f2f99ad02a8c25d4e30/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/c8c42712d2e945f88e4b2d626b415287-e00c4d272c864d7783a6865fa9c35521.xml --timeout 120.000000 | exited | 0 | logs/d9693db12df7475db80d4960106a9de4/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c8c42712d2e945f88e4b2d626b415287-e00c4d272c864d7783a6865fa9c35521.xml | exited | 0 | logs/795fc6442129446aa02b8367d4b769cf/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/c8c42712d2e945f88e4b2d626b415287-59746533614d48758c603ba00a28c676.xml --timeout 120.000000 | exited | 0 | logs/525dcc63e876405b9972f16614a5dbff/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c8c42712d2e945f88e4b2d626b415287-59746533614d48758c603ba00a28c676.xml | exited | 0 | logs/3968b78ba3a64abbbe0a228c0d6a7963/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/c8c42712d2e945f88e4b2d626b415287-eead7c514f104bc3ab8dbc47b20cdcee.xml --timeout 120.000000 | exited | 0 | logs/c2b064eedbb94fd9a6b8f3fef7b1999a/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c8c42712d2e945f88e4b2d626b415287-eead7c514f104bc3ab8dbc47b20cdcee.xml | exited | 0 | logs/d399db222d434c39b40d49f9db2ada6e/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/f2eb6402ce37491bb5af4c5ab64516cd/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/326d6dca60f74d5fa6fa1233e24e90f8/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/cdefde314bf244a6af943e556efaed47/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/a344a158798748d3a72878643765ed1d/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/1b84634e562142faae82bb64f29e90d3/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/7fee18cd5b274bb7826a706510d7b36e-66200a7c1cde4c23acf114eb6313c9c0.xml --timeout 120.000000 | exited | 8 | logs/834aba83d0084626893f0781a0b875c0/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7fee18cd5b274bb7826a706510d7b36e-66200a7c1cde4c23acf114eb6313c9c0.xml | exited | 0 | logs/347dd028592345adad8629a8583f545f/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/7fee18cd5b274bb7826a706510d7b36e-446e03c9a9744475b99e39909bbfdf86.xml --timeout 120.000000 | exited | 0 | logs/e22b48bc87354be6a6e600e3f9f7a349/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7fee18cd5b274bb7826a706510d7b36e-446e03c9a9744475b99e39909bbfdf86.xml | exited | 0 | logs/8aa4e8af23754112bd7f02053d80e311/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/7fee18cd5b274bb7826a706510d7b36e-5971c96d3c324c3cb1064ca38611d20e.xml --timeout 120.000000 | exited | 0 | logs/beff67b7d8a6440eb0bb083a746e0868/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7fee18cd5b274bb7826a706510d7b36e-5971c96d3c324c3cb1064ca38611d20e.xml | exited | 0 | logs/a26b43c0ae224cb3971ec1faa204a163/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/7fee18cd5b274bb7826a706510d7b36e-055f229169a24ef6b8e67d46392f5e8c.xml --timeout 120.000000 | exited | 0 | logs/100ef79403af478f94103576920028b8/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7fee18cd5b274bb7826a706510d7b36e-055f229169a24ef6b8e67d46392f5e8c.xml | exited | 0 | logs/433c23f9d7e0438d8acfc2ff6c396397/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
