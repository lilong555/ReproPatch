# ReproPatch 15a77ef051394785804ba7c81099f2ff

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：REQUIRED\_TEST\_NOT\_RUN
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：b3a8233d2401a38dae6320970897c4a51fdf6592
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.917 秒
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
| baseline | negative\_values | 失败 | evidence/f1b7a86766274d1ba8167739f2ed2514/f108a5525c734619949e9c2cf5b06334.xml |
| baseline | positive\_values | 通过 | evidence/f1b7a86766274d1ba8167739f2ed2514/eb4912bb5cc049cb9929af538225c7d9.xml |
| baseline | empty\_values | 通过 | evidence/f1b7a86766274d1ba8167739f2ed2514/c83002226cc04d1697cbc2bdd2c335f3.xml |
| baseline | mixed\_values | 通过 | evidence/f1b7a86766274d1ba8167739f2ed2514/63f1a966b64045bd9253562bd102f4c3.xml |
| independent | negative\_values | 跳过 | evidence/e05494e405124679a39e79c15262a6b3/d8b2529fad7741bfa0ec4d2a0ccec4e9.xml |
| independent | positive\_values | 通过 | evidence/e05494e405124679a39e79c15262a6b3/5002cb224cbd4170809c7cf5808d4122.xml |
| independent | empty\_values | 通过 | evidence/e05494e405124679a39e79c15262a6b3/2bb3e9b045ec4814aebc97e421d7ebd0.xml |
| independent | mixed\_values | 失败 | evidence/e05494e405124679a39e79c15262a6b3/162f1ca474064a26ab85dc0e0e6bdf89.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/f6e4ee58b1fd40f8917a987ec111be82/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/975885bf4c5944c58fa65b418fd6b76a/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/213c8bb90108442f87a143875c0e2896/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/a183b9724acf4bd993c80d55aa3e090f/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/2e3ec4d032b4433d969f06ee449c3fcc/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/f1b7a86766274d1ba8167739f2ed2514-f108a5525c734619949e9c2cf5b06334.xml --timeout 120.000000 | exited | 8 | logs/72a4edb5ee814e2d845adb5ff87dd265/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f1b7a86766274d1ba8167739f2ed2514-f108a5525c734619949e9c2cf5b06334.xml | exited | 0 | logs/1101cb984dfa4158a658e514622920e1/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/f1b7a86766274d1ba8167739f2ed2514-eb4912bb5cc049cb9929af538225c7d9.xml --timeout 120.000000 | exited | 0 | logs/43ef1d084bbb45fdad7255648ad46be6/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f1b7a86766274d1ba8167739f2ed2514-eb4912bb5cc049cb9929af538225c7d9.xml | exited | 0 | logs/0c1057c343b7413fa0d76d8e1ac5465c/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/f1b7a86766274d1ba8167739f2ed2514-c83002226cc04d1697cbc2bdd2c335f3.xml --timeout 120.000000 | exited | 0 | logs/8b3225553c8940588172a688bde8f490/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f1b7a86766274d1ba8167739f2ed2514-c83002226cc04d1697cbc2bdd2c335f3.xml | exited | 0 | logs/1a7891f04ccd456eb51fc89f8bdb4233/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/f1b7a86766274d1ba8167739f2ed2514-63f1a966b64045bd9253562bd102f4c3.xml --timeout 120.000000 | exited | 0 | logs/6871a1c8d07244e0a1d04bbb71bb8cef/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f1b7a86766274d1ba8167739f2ed2514-63f1a966b64045bd9253562bd102f4c3.xml | exited | 0 | logs/af7d2f0df80541b295846352f6f9b65d/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/cc0150c04928415b84b607d174384e73/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/82393e64d6f14aa4883ed7b412e322e3/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/3c466087213f4afbabb35cd6e3bafd48/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/6dc24131e02949f186e97a7e238e0ef0/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/148537db4b8b495999f343e1c53766e7/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/e05494e405124679a39e79c15262a6b3-d8b2529fad7741bfa0ec4d2a0ccec4e9.xml --timeout 120.000000 | exited | 0 | logs/70b5857e14b24a458847cf430787305b/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e05494e405124679a39e79c15262a6b3-d8b2529fad7741bfa0ec4d2a0ccec4e9.xml | exited | 0 | logs/e1924da4896946b2a1d5473b0d224dcb/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/e05494e405124679a39e79c15262a6b3-5002cb224cbd4170809c7cf5808d4122.xml --timeout 120.000000 | exited | 0 | logs/2b33ae74e1884fc88d1faa0637cf531b/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e05494e405124679a39e79c15262a6b3-5002cb224cbd4170809c7cf5808d4122.xml | exited | 0 | logs/7854754d6c424dadac76850b71c0ac03/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/e05494e405124679a39e79c15262a6b3-2bb3e9b045ec4814aebc97e421d7ebd0.xml --timeout 120.000000 | exited | 0 | logs/e4853b1f687b4eb894f6480c557e2d06/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e05494e405124679a39e79c15262a6b3-2bb3e9b045ec4814aebc97e421d7ebd0.xml | exited | 0 | logs/55503515794d4722b40afdb57246933d/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/e05494e405124679a39e79c15262a6b3-162f1ca474064a26ab85dc0e0e6bdf89.xml --timeout 120.000000 | exited | 8 | logs/6a52ef7ed52449cfa19c42c394375cd0/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e05494e405124679a39e79c15262a6b3-162f1ca474064a26ab85dc0e0e6bdf89.xml | exited | 0 | logs/5c9a2d8e708d4756be81b4d2dbe7ef3e/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
