# ReproPatch fadda040f5374c8386877846e9d3f862

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：9.361 秒
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
| baseline | negative\_values | 失败 | evidence/8c584f037b8e4ad5b55a2ad8b2c1d2da/db439c1b22604cc2812d49b5ce3a88cf.xml |
| baseline | positive\_values | 通过 | evidence/8c584f037b8e4ad5b55a2ad8b2c1d2da/3190fd08a1a44921bfc582c06c5977f9.xml |
| baseline | empty\_values | 通过 | evidence/8c584f037b8e4ad5b55a2ad8b2c1d2da/c01dfde91b7d49768c37406b7e8af4c4.xml |
| baseline | mixed\_values | 通过 | evidence/8c584f037b8e4ad5b55a2ad8b2c1d2da/2f6b68c315854f0eab94b9f90ecdad37.xml |
| independent | negative\_values | 通过 | evidence/80e0a4de35e84ae0a262a12ab0730651/6e7fbd6acdb64702b1f0adbf4304929f.xml |
| independent | positive\_values | 通过 | evidence/80e0a4de35e84ae0a262a12ab0730651/4676f011cb60425d9c99b396ae7acbfd.xml |
| independent | empty\_values | 通过 | evidence/80e0a4de35e84ae0a262a12ab0730651/ae95722a19a946a5baedf8cba39bb69f.xml |
| independent | mixed\_values | 通过 | evidence/80e0a4de35e84ae0a262a12ab0730651/b95f4f4a74a24115a700322e11da4419.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/941aae0d8e71416b9c96d4973b04555c/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/6b75166ba4b64af6ad6b041fa2075abf/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/3e5ffdcb09684992946df71e7eb1765e/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/c59315213454414593320a5a87d3a382/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/d5ff1d1934af405ab7db5515235d6b21/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/8c584f037b8e4ad5b55a2ad8b2c1d2da-db439c1b22604cc2812d49b5ce3a88cf.xml --timeout 120.000000 | exited | 8 | logs/2b0a0dc246d140f598d3a16e7ed72d56/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8c584f037b8e4ad5b55a2ad8b2c1d2da-db439c1b22604cc2812d49b5ce3a88cf.xml | exited | 0 | logs/0ae272c7b1b9415db179c2fda3bfeed8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/8c584f037b8e4ad5b55a2ad8b2c1d2da-3190fd08a1a44921bfc582c06c5977f9.xml --timeout 120.000000 | exited | 0 | logs/570444fe63ea4aa284f86441c725bf09/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8c584f037b8e4ad5b55a2ad8b2c1d2da-3190fd08a1a44921bfc582c06c5977f9.xml | exited | 0 | logs/a1dc8460456c4d2bb52dbdd955ef2aa7/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/8c584f037b8e4ad5b55a2ad8b2c1d2da-c01dfde91b7d49768c37406b7e8af4c4.xml --timeout 120.000000 | exited | 0 | logs/a0ed8327fc894acea68a960a2e61d67a/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8c584f037b8e4ad5b55a2ad8b2c1d2da-c01dfde91b7d49768c37406b7e8af4c4.xml | exited | 0 | logs/8a3d99f52124462fb5e96b7f30111886/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/8c584f037b8e4ad5b55a2ad8b2c1d2da-2f6b68c315854f0eab94b9f90ecdad37.xml --timeout 120.000000 | exited | 0 | logs/f4239560653a4807833e1dfe0807b5a9/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8c584f037b8e4ad5b55a2ad8b2c1d2da-2f6b68c315854f0eab94b9f90ecdad37.xml | exited | 0 | logs/e3356cf638764088b7695236e6e190d3/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/9623c096787441249e977ee4101ba997/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/efd8180494b64600915adddd932bf1bd/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/8ea774603e4b44b181cb6158b3553d96/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/579e0336011b4f6fbac1225bbffb9447/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/834de969ed2c49f9b7119257dbfeb60d/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/80e0a4de35e84ae0a262a12ab0730651-6e7fbd6acdb64702b1f0adbf4304929f.xml --timeout 120.000000 | exited | 0 | logs/26944d357df34e8aa7458a8582fb43cc/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/80e0a4de35e84ae0a262a12ab0730651-6e7fbd6acdb64702b1f0adbf4304929f.xml | exited | 0 | logs/03316058034947fd9ce46197c1456ddd/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/80e0a4de35e84ae0a262a12ab0730651-4676f011cb60425d9c99b396ae7acbfd.xml --timeout 120.000000 | exited | 0 | logs/e04043abfe534469980e1093b6891287/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/80e0a4de35e84ae0a262a12ab0730651-4676f011cb60425d9c99b396ae7acbfd.xml | exited | 0 | logs/4eb3c34be30e4cfd805553aa5ab31df7/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/80e0a4de35e84ae0a262a12ab0730651-ae95722a19a946a5baedf8cba39bb69f.xml --timeout 120.000000 | exited | 0 | logs/0a548796110240bf926eea835019db36/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/80e0a4de35e84ae0a262a12ab0730651-ae95722a19a946a5baedf8cba39bb69f.xml | exited | 0 | logs/f6961814462a456897359760019c801d/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/80e0a4de35e84ae0a262a12ab0730651-b95f4f4a74a24115a700322e11da4419.xml --timeout 120.000000 | exited | 0 | logs/86230b3948f345f9a41230bf3c61db07/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/80e0a4de35e84ae0a262a12ab0730651-b95f4f4a74a24115a700322e11da4419.xml | exited | 0 | logs/26ecc923bdbb40be8e0d453d58ab03ba/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
外部生成过程、预算和 trace 未受本次运行管理或验证。
