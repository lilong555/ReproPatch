# ReproPatch d788419df1bb4c809aae803a8b3cd040

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：REQUIRED\_TEST\_NOT\_RUN
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：d2635e85de55fcd101f9a872e535368a6e2dc0d2
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.222 秒
模型步骤：0；准入工具：0
模型停止原因：未知
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：否；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：73


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/2bd9a29cb00c44b9a315796d2b1136c9/f518e49b737c4169b546aa147ca85fd5.xml |
| baseline | positive\_values | 通过 | evidence/2bd9a29cb00c44b9a315796d2b1136c9/8b1c8dc1b7bf470290add78cd49a55eb.xml |
| baseline | empty\_values | 通过 | evidence/2bd9a29cb00c44b9a315796d2b1136c9/3c3c9f88075746b08ec3735b5a7f0d3f.xml |
| baseline | mixed\_values | 通过 | evidence/2bd9a29cb00c44b9a315796d2b1136c9/378a73bf06704c11a5d13131f2bdab01.xml |
| independent | negative\_values | 跳过 | evidence/d4c1f1a4f4214c8cb30dc983b9a6c1aa/2f2f6b2388c141d28f16ebe700c66cfb.xml |
| independent | positive\_values | 通过 | evidence/d4c1f1a4f4214c8cb30dc983b9a6c1aa/8d658f2d941b4f209b7362dcf12aeb42.xml |
| independent | empty\_values | 通过 | evidence/d4c1f1a4f4214c8cb30dc983b9a6c1aa/6f20c9cd28df4e4eb9694fb1c6fb96ec.xml |
| independent | mixed\_values | 失败 | evidence/d4c1f1a4f4214c8cb30dc983b9a6c1aa/31b9537b157b4d129c8f7abf349f4691.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/96f52cf06dea4b51982aca2121864b0c/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/3b711efb7d9a4978969d01e66a3151d8/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/75e8ea8251144f8ca3ebbfa9f5d41083/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/096ae721de50429ab8ca49f2bc61a59e/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/f02af85e79584deb9af83cd3ba42e079/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/2bd9a29cb00c44b9a315796d2b1136c9-f518e49b737c4169b546aa147ca85fd5.xml --timeout 120.000000 | exited | 8 | logs/fa05f088207642c5af4b62ccb1cc9766/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/2bd9a29cb00c44b9a315796d2b1136c9-f518e49b737c4169b546aa147ca85fd5.xml | exited | 0 | logs/184328271edd47b29788a6f8dc1b4c13/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/2bd9a29cb00c44b9a315796d2b1136c9-8b1c8dc1b7bf470290add78cd49a55eb.xml --timeout 120.000000 | exited | 0 | logs/45b8432642db4c8b8ababba76b6b9ca1/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/2bd9a29cb00c44b9a315796d2b1136c9-8b1c8dc1b7bf470290add78cd49a55eb.xml | exited | 0 | logs/55ba95967a4e4124bdcefb68b98ebb86/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/2bd9a29cb00c44b9a315796d2b1136c9-3c3c9f88075746b08ec3735b5a7f0d3f.xml --timeout 120.000000 | exited | 0 | logs/59da257bb99549d6b772ae00c4c764a2/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/2bd9a29cb00c44b9a315796d2b1136c9-3c3c9f88075746b08ec3735b5a7f0d3f.xml | exited | 0 | logs/03d06e1d057f49149704a9414f781c21/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/2bd9a29cb00c44b9a315796d2b1136c9-378a73bf06704c11a5d13131f2bdab01.xml --timeout 120.000000 | exited | 0 | logs/a3346d2aa1c94056bcd1718b6763675f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/2bd9a29cb00c44b9a315796d2b1136c9-378a73bf06704c11a5d13131f2bdab01.xml | exited | 0 | logs/e163f2a16dda4d22a5e622b5bd24c93f/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/607110a19986422fb019779bc75c42cd/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/8dacd71e009a4e52a2bbdfabde76dbe6/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/057598ae64cc4920894a185315e84996/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/d1b61e1c05e64fb68fb11e6c2c68221d/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/8f57c989fd0f40e781fa6712385367ef/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/d4c1f1a4f4214c8cb30dc983b9a6c1aa-2f2f6b2388c141d28f16ebe700c66cfb.xml --timeout 120.000000 | exited | 0 | logs/022c27bf61a34fe791e6025de109114e/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d4c1f1a4f4214c8cb30dc983b9a6c1aa-2f2f6b2388c141d28f16ebe700c66cfb.xml | exited | 0 | logs/4f891f9fc12a4b2cb67e641bedbf6e69/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/d4c1f1a4f4214c8cb30dc983b9a6c1aa-8d658f2d941b4f209b7362dcf12aeb42.xml --timeout 120.000000 | exited | 0 | logs/8ab067709ebd483b8e7fc4a1bb9d0901/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d4c1f1a4f4214c8cb30dc983b9a6c1aa-8d658f2d941b4f209b7362dcf12aeb42.xml | exited | 0 | logs/a8fca3c2916b4554ab6b44db0ceb1028/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/d4c1f1a4f4214c8cb30dc983b9a6c1aa-6f20c9cd28df4e4eb9694fb1c6fb96ec.xml --timeout 120.000000 | exited | 0 | logs/cb117ffedb9a4f068c8f1c4d4221d8d7/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d4c1f1a4f4214c8cb30dc983b9a6c1aa-6f20c9cd28df4e4eb9694fb1c6fb96ec.xml | exited | 0 | logs/74d9827294674e14b8772b1fc909eb05/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/d4c1f1a4f4214c8cb30dc983b9a6c1aa-31b9537b157b4d129c8f7abf349f4691.xml --timeout 120.000000 | exited | 8 | logs/06abb4d6b668488e8fed4d9b3b626929/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d4c1f1a4f4214c8cb30dc983b9a6c1aa-31b9537b157b4d129c8f7abf349f4691.xml | exited | 0 | logs/ba8b9c09f30a47d493f6a3bd7211bf85/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
