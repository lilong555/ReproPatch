# ReproPatch 302e7e68c3b4447bb156b8551025ffee

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：03f9210d8bcb353490d35c0b19c2936a339f9eaa
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：13.717 秒
模型步骤：5；准入工具：4
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：131


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/4fd569108cba43c7b585b60744ec7644/eeee90ffe22b4972aa6e6aaac8954e1a.xml |
| baseline | positive\_values | 通过 | evidence/4fd569108cba43c7b585b60744ec7644/72c70781f2d14a3090e487efd8200198.xml |
| baseline | empty\_values | 通过 | evidence/4fd569108cba43c7b585b60744ec7644/8eede1dade5c4d7994fd3b57f06eac88.xml |
| baseline | mixed\_values | 通过 | evidence/4fd569108cba43c7b585b60744ec7644/6044bb14dc8f4e9a838eb4b3f2d9e816.xml |
| agent\_check | negative\_values | 通过 | evidence/e59b27e4a4ec44a6be91a63be1189ddc/a0d6b11da2c84771a59cc51e482511c6.xml |
| agent\_check | positive\_values | 通过 | evidence/e59b27e4a4ec44a6be91a63be1189ddc/5cb88c883b6248868873104fbb65c361.xml |
| agent\_check | empty\_values | 通过 | evidence/e59b27e4a4ec44a6be91a63be1189ddc/9870a7c80f5a4d8983e44693e8535bd6.xml |
| agent\_check | mixed\_values | 通过 | evidence/e59b27e4a4ec44a6be91a63be1189ddc/e9e0a7e946b74355ada3e6365840b1f3.xml |
| independent | negative\_values | 通过 | evidence/5b74195ba785407ba878c84200d96cdc/d4645f5a67e447808e8353778c8ab0cc.xml |
| independent | positive\_values | 通过 | evidence/5b74195ba785407ba878c84200d96cdc/fdede718fe7044c69c4d2d6004eb128f.xml |
| independent | empty\_values | 通过 | evidence/5b74195ba785407ba878c84200d96cdc/5eb63cbfc782441a9b9258a43f56fc9c.xml |
| independent | mixed\_values | 通过 | evidence/5b74195ba785407ba878c84200d96cdc/bea7c90360c44cf19d1e061a3f40ec26.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/1bfcd2ade23d4ca9913dd69fde62b4d4/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/5e5c11a434fd4b3fb39d7974c5106a31/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/588804cc57ca4c1d86b8015c4fbe8e93/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/9c9217b7d2874fa1b4cc44a85230c713/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/be3fc5fedad24c78804f6bc8942c5b00/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/4fd569108cba43c7b585b60744ec7644-eeee90ffe22b4972aa6e6aaac8954e1a.xml --timeout 120.000000 | exited | 8 | logs/e6d8e9d68210450e8c51806d7ce98b7b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4fd569108cba43c7b585b60744ec7644-eeee90ffe22b4972aa6e6aaac8954e1a.xml | exited | 0 | logs/a87101fe3b344484ba85a814b8bf1c53/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/4fd569108cba43c7b585b60744ec7644-72c70781f2d14a3090e487efd8200198.xml --timeout 120.000000 | exited | 0 | logs/38d1b3bbb7d64db482ba03bd0170cbd3/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4fd569108cba43c7b585b60744ec7644-72c70781f2d14a3090e487efd8200198.xml | exited | 0 | logs/7ec67be1d6b94caf8926f674c8aa7c07/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/4fd569108cba43c7b585b60744ec7644-8eede1dade5c4d7994fd3b57f06eac88.xml --timeout 120.000000 | exited | 0 | logs/384fcc09f22d402f9819db88e6118453/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4fd569108cba43c7b585b60744ec7644-8eede1dade5c4d7994fd3b57f06eac88.xml | exited | 0 | logs/8082ff2828df40c8821bd7dac9ad7e98/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/4fd569108cba43c7b585b60744ec7644-6044bb14dc8f4e9a838eb4b3f2d9e816.xml --timeout 120.000000 | exited | 0 | logs/12c8c7e4748a486986a9a0186b1c2a35/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4fd569108cba43c7b585b60744ec7644-6044bb14dc8f4e9a838eb4b3f2d9e816.xml | exited | 0 | logs/5aaefac619004f3ca358263c6245d10f/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/593bce7dc07a430f81caf995dbaa5a24/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/0524d1ef886b4aebbbd19b2e050e8dba/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/5d360d78e7eb4f00a58efe6a688a9e04/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/5c47627900a840ba9e95f3e16e31def7/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/c1376d8684aa40b4b42b059b60a0e475/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/e59b27e4a4ec44a6be91a63be1189ddc-a0d6b11da2c84771a59cc51e482511c6.xml --timeout 120.000000 | exited | 0 | logs/13afe6f4ff4c4b85a6c65235eaf13abf/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e59b27e4a4ec44a6be91a63be1189ddc-a0d6b11da2c84771a59cc51e482511c6.xml | exited | 0 | logs/6c1b9de6b337439a8573ce3804abb088/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/e59b27e4a4ec44a6be91a63be1189ddc-5cb88c883b6248868873104fbb65c361.xml --timeout 120.000000 | exited | 0 | logs/6f0ab4a948074b5c88660009c7927f8f/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e59b27e4a4ec44a6be91a63be1189ddc-5cb88c883b6248868873104fbb65c361.xml | exited | 0 | logs/b74ae82aa1cd4de088cb60d7e587dc35/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/e59b27e4a4ec44a6be91a63be1189ddc-9870a7c80f5a4d8983e44693e8535bd6.xml --timeout 120.000000 | exited | 0 | logs/0ed3ea6c029a4a9eab4f01c083aeb76a/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e59b27e4a4ec44a6be91a63be1189ddc-9870a7c80f5a4d8983e44693e8535bd6.xml | exited | 0 | logs/53ae1e95beb34667b9506bd86c38a90f/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/e59b27e4a4ec44a6be91a63be1189ddc-e9e0a7e946b74355ada3e6365840b1f3.xml --timeout 120.000000 | exited | 0 | logs/747222978e5041e9b9fda153a5a3eb76/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e59b27e4a4ec44a6be91a63be1189ddc-e9e0a7e946b74355ada3e6365840b1f3.xml | exited | 0 | logs/0ce67164c9df43d48efca9d63d4a9e60/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/e3e03404d3d94d5c96462196b81b7322/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/583cbd8788554b639247739904485f3d/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/3ea9db047a174c5284f33cbb36eda78b/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/4a4530bac5a64aa7981f1b8196296075/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/826e9902a403464aad3f116ebd3e9879/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/5b74195ba785407ba878c84200d96cdc-d4645f5a67e447808e8353778c8ab0cc.xml --timeout 120.000000 | exited | 0 | logs/1053e2de7e80499ba4035cc83cacf450/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5b74195ba785407ba878c84200d96cdc-d4645f5a67e447808e8353778c8ab0cc.xml | exited | 0 | logs/e017603c04694ed88c42ddfae8f74bc7/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/5b74195ba785407ba878c84200d96cdc-fdede718fe7044c69c4d2d6004eb128f.xml --timeout 120.000000 | exited | 0 | logs/7bd70cb2145d4406875d84eeb7ea810f/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5b74195ba785407ba878c84200d96cdc-fdede718fe7044c69c4d2d6004eb128f.xml | exited | 0 | logs/5a573c6abda94fbab910a33b4f2c1a8a/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/5b74195ba785407ba878c84200d96cdc-5eb63cbfc782441a9b9258a43f56fc9c.xml --timeout 120.000000 | exited | 0 | logs/ac035dacd7d84aebbbae3057b0f6e255/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5b74195ba785407ba878c84200d96cdc-5eb63cbfc782441a9b9258a43f56fc9c.xml | exited | 0 | logs/c366027a069a40439d4c7598f2dc6322/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/5b74195ba785407ba878c84200d96cdc-bea7c90360c44cf19d1e061a3f40ec26.xml --timeout 120.000000 | exited | 0 | logs/9f554bdcc2f5424aa3a4b0d1f58e769e/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5b74195ba785407ba878c84200d96cdc-bea7c90360c44cf19d1e061a3f40ec26.xml | exited | 0 | logs/356d2ccc6e624ae58a4bfd5099f2fa97/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
