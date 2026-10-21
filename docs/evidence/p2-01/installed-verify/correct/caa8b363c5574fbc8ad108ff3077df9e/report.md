# ReproPatch caa8b363c5574fbc8ad108ff3077df9e

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.327 秒
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
| baseline | negative\_values | 失败 | evidence/b6aa5b88e0e540729d3b5500f759b261/f678f5e40a9b4d7f880f97e4db390b20.xml |
| baseline | positive\_values | 通过 | evidence/b6aa5b88e0e540729d3b5500f759b261/1724ba18fe474c4c9c0a12e7103a8521.xml |
| baseline | empty\_values | 通过 | evidence/b6aa5b88e0e540729d3b5500f759b261/36a3e767287a43d98582494f34aee073.xml |
| baseline | mixed\_values | 通过 | evidence/b6aa5b88e0e540729d3b5500f759b261/3c73cd7e2f98461286c40e7a26668440.xml |
| independent | negative\_values | 通过 | evidence/3256c344ae034700a598c63ec7b8d92b/563859215ab2484cb75bd76ac53456d6.xml |
| independent | positive\_values | 通过 | evidence/3256c344ae034700a598c63ec7b8d92b/0af63897df7446189f15a10f6e417949.xml |
| independent | empty\_values | 通过 | evidence/3256c344ae034700a598c63ec7b8d92b/58e4bb4606814f8fbc47be9caea98efb.xml |
| independent | mixed\_values | 通过 | evidence/3256c344ae034700a598c63ec7b8d92b/99f69fdebbaa47ef85ab6d2d2edc3896.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/1cac60252aa34f7897a65b7d8d7d8f51/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/6ce13e003582490a9211aa3db201eae8/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/40ae1fb3c08f4a1888942246813dc9c4/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/6fa027de7ae54cb1a9690ab9a70d47b6/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/d969b311a4114b64a850f23ebeca9e00/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/b6aa5b88e0e540729d3b5500f759b261-f678f5e40a9b4d7f880f97e4db390b20.xml --timeout 120.000000 | exited | 8 | logs/37a27c9851f34a10ba52173abc044c46/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b6aa5b88e0e540729d3b5500f759b261-f678f5e40a9b4d7f880f97e4db390b20.xml | exited | 0 | logs/bcb11f4da5a54ff285a2af57d33f6c4a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/b6aa5b88e0e540729d3b5500f759b261-1724ba18fe474c4c9c0a12e7103a8521.xml --timeout 120.000000 | exited | 0 | logs/d3e62bb773ea455db51dd55a4c62a3c8/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b6aa5b88e0e540729d3b5500f759b261-1724ba18fe474c4c9c0a12e7103a8521.xml | exited | 0 | logs/7f1d421a0b9c41ce813a3a038b3d776d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/b6aa5b88e0e540729d3b5500f759b261-36a3e767287a43d98582494f34aee073.xml --timeout 120.000000 | exited | 0 | logs/31eee7d80bf94afbaa32d671d7c9077a/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b6aa5b88e0e540729d3b5500f759b261-36a3e767287a43d98582494f34aee073.xml | exited | 0 | logs/c008d454ff5844b5931a86cdca58d60c/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/b6aa5b88e0e540729d3b5500f759b261-3c73cd7e2f98461286c40e7a26668440.xml --timeout 120.000000 | exited | 0 | logs/50114d59d9a74578a3979347bd32e479/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b6aa5b88e0e540729d3b5500f759b261-3c73cd7e2f98461286c40e7a26668440.xml | exited | 0 | logs/61051013df7c4088bfe1aea26f865e7d/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/430543a052314ee0a577b4e50bdf8340/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/e0d9325367a041f496f23d31198f33f2/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/ea2d218f674c4c5798849d4b7824dc40/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/2b2bd5acc12b4a77a97ba0c1b24c06b9/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/3a418b179f344ef5b7f0ed26f3733dbd/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/3256c344ae034700a598c63ec7b8d92b-563859215ab2484cb75bd76ac53456d6.xml --timeout 120.000000 | exited | 0 | logs/d28b7c6a899445c1bb7c81cbae38d48c/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3256c344ae034700a598c63ec7b8d92b-563859215ab2484cb75bd76ac53456d6.xml | exited | 0 | logs/fc66f0ac8d184d74a595e17153edf154/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/3256c344ae034700a598c63ec7b8d92b-0af63897df7446189f15a10f6e417949.xml --timeout 120.000000 | exited | 0 | logs/8a63001b101d4a6bb7d3a87375a0b0bf/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3256c344ae034700a598c63ec7b8d92b-0af63897df7446189f15a10f6e417949.xml | exited | 0 | logs/c32f9bceef1e4bd7aee605b5e1dc8ac9/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/3256c344ae034700a598c63ec7b8d92b-58e4bb4606814f8fbc47be9caea98efb.xml --timeout 120.000000 | exited | 0 | logs/f9aa9f485eea412d8578991b486bbe86/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3256c344ae034700a598c63ec7b8d92b-58e4bb4606814f8fbc47be9caea98efb.xml | exited | 0 | logs/f56f3c92ef3c4197ac028b14bd04d437/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/3256c344ae034700a598c63ec7b8d92b-99f69fdebbaa47ef85ab6d2d2edc3896.xml --timeout 120.000000 | exited | 0 | logs/4708f854478f45e7a6eb0350b260c866/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3256c344ae034700a598c63ec7b8d92b-99f69fdebbaa47ef85ab6d2d2edc3896.xml | exited | 0 | logs/bf0194d01e2d437f91c306d23131a4f9/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
