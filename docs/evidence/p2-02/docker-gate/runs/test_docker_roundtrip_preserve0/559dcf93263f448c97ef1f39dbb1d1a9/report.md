# ReproPatch 559dcf93263f448c97ef1f39dbb1d1a9

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：1b08e7368ee021433d376d76b925fa7801d6c45f
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：13.010 秒
模型步骤：5；准入工具：4
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：136


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/0ca0fd4560ff4f89ae04b127d0b1c17f/08f49999b6574011a1fbfc40aced3788.xml |
| baseline | positive\_values | 通过 | evidence/0ca0fd4560ff4f89ae04b127d0b1c17f/01aa19dedabf47c88b2882e8b9152a20.xml |
| baseline | empty\_values | 通过 | evidence/0ca0fd4560ff4f89ae04b127d0b1c17f/34c6580388c345829d22426350a3102d.xml |
| baseline | mixed\_values | 通过 | evidence/0ca0fd4560ff4f89ae04b127d0b1c17f/0dc031a91f24473f9c58638a5edcd712.xml |
| agent\_check | negative\_values | 通过 | evidence/0087f8e09e15445ba494ff7155ff8155/b086f24422fb43719bbcf6511765a103.xml |
| agent\_check | positive\_values | 通过 | evidence/0087f8e09e15445ba494ff7155ff8155/e59ae3e2802d440cb24d70d685eaaf66.xml |
| agent\_check | empty\_values | 通过 | evidence/0087f8e09e15445ba494ff7155ff8155/e18355f3457f4ab3b12ae05c1d300b39.xml |
| agent\_check | mixed\_values | 通过 | evidence/0087f8e09e15445ba494ff7155ff8155/ddc6fbe487394efaae88dd67e1240d5c.xml |
| independent | negative\_values | 通过 | evidence/88dbda57fc2149b39a648d5a046f1448/55a3e120e19340648034a45ab800dced.xml |
| independent | positive\_values | 通过 | evidence/88dbda57fc2149b39a648d5a046f1448/fa89fd920c7341bc9f7f9c64661b4a12.xml |
| independent | empty\_values | 通过 | evidence/88dbda57fc2149b39a648d5a046f1448/d9ec9ed2cb42401bb8454ce3581a7593.xml |
| independent | mixed\_values | 通过 | evidence/88dbda57fc2149b39a648d5a046f1448/bb812a3634754e2993bcef842aa5d6fb.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/aca68b4fcec84fecad080f6642dd6b6d/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/5d0c0cce051f4864bfb9e8b7802b74c2/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/36f91605eae04ad7ad44392a67a1c77f/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/15af7adca5d741739b7e2471b78a59cf/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/bfa0420f1aec48bb99cb5dbc2ca937f8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/0ca0fd4560ff4f89ae04b127d0b1c17f-08f49999b6574011a1fbfc40aced3788.xml --timeout 120.000000 | exited | 8 | logs/8f00a1bee8434a7abdfb86083af6139b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0ca0fd4560ff4f89ae04b127d0b1c17f-08f49999b6574011a1fbfc40aced3788.xml | exited | 0 | logs/c5a02b8bcb0e4beca32a8b88f1bfc1c9/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/0ca0fd4560ff4f89ae04b127d0b1c17f-01aa19dedabf47c88b2882e8b9152a20.xml --timeout 120.000000 | exited | 0 | logs/74b2621e6e8f45c28383eee7c23f13cc/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0ca0fd4560ff4f89ae04b127d0b1c17f-01aa19dedabf47c88b2882e8b9152a20.xml | exited | 0 | logs/7652a572367e4a37889149fe26756014/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/0ca0fd4560ff4f89ae04b127d0b1c17f-34c6580388c345829d22426350a3102d.xml --timeout 120.000000 | exited | 0 | logs/8e0dc92ba3d54cc79ef4cf1955d9ec45/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0ca0fd4560ff4f89ae04b127d0b1c17f-34c6580388c345829d22426350a3102d.xml | exited | 0 | logs/2462e89e67c14b8cbd9eb80f831aba6c/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/0ca0fd4560ff4f89ae04b127d0b1c17f-0dc031a91f24473f9c58638a5edcd712.xml --timeout 120.000000 | exited | 0 | logs/4d657bbbd6b54df2a05cb94f2a2efb09/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0ca0fd4560ff4f89ae04b127d0b1c17f-0dc031a91f24473f9c58638a5edcd712.xml | exited | 0 | logs/8d41034e4ec24e51a4d8cf21691aeb2c/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/8b8e4e2dadd64a2a938890e66f2262a4/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/7762d575241241358c2b5c431ccf87b1/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/a1999bde0f104eb8a982405275afb06d/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/540bced1766548e09756a65546f48d25/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/e1b4aa9f7ad745a9a78d199df2b02780/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/0087f8e09e15445ba494ff7155ff8155-b086f24422fb43719bbcf6511765a103.xml --timeout 120.000000 | exited | 0 | logs/14d789cd75214d36918855b1a0d8821c/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0087f8e09e15445ba494ff7155ff8155-b086f24422fb43719bbcf6511765a103.xml | exited | 0 | logs/2663b010d3c14b159d4179e98937f511/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/0087f8e09e15445ba494ff7155ff8155-e59ae3e2802d440cb24d70d685eaaf66.xml --timeout 120.000000 | exited | 0 | logs/da5f5b35457040dba88709ae549ef639/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0087f8e09e15445ba494ff7155ff8155-e59ae3e2802d440cb24d70d685eaaf66.xml | exited | 0 | logs/d72da9cd59c64343837bfcf7bfa6d672/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/0087f8e09e15445ba494ff7155ff8155-e18355f3457f4ab3b12ae05c1d300b39.xml --timeout 120.000000 | exited | 0 | logs/a2210a9e72024bf3a2a4c686bd74ea04/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0087f8e09e15445ba494ff7155ff8155-e18355f3457f4ab3b12ae05c1d300b39.xml | exited | 0 | logs/7bc3b25836434c159048eeade5f16edc/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/0087f8e09e15445ba494ff7155ff8155-ddc6fbe487394efaae88dd67e1240d5c.xml --timeout 120.000000 | exited | 0 | logs/b299bb2202e74b308a603a98ef2623bb/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0087f8e09e15445ba494ff7155ff8155-ddc6fbe487394efaae88dd67e1240d5c.xml | exited | 0 | logs/d7888bfaad784893b57f2c54325f9190/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/433869db3a8a4066ba37b51ff58f6de8/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/f6b69bc1a48b4128b7380a12083ad2fd/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/15def2614939423fb65387d6092b857c/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/355c154755844318ab50f3440cfccc73/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/1bd7c780462b4413909f04bf61802315/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/88dbda57fc2149b39a648d5a046f1448-55a3e120e19340648034a45ab800dced.xml --timeout 120.000000 | exited | 0 | logs/fa13bd6ae7d54a769a5681b8f93274be/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/88dbda57fc2149b39a648d5a046f1448-55a3e120e19340648034a45ab800dced.xml | exited | 0 | logs/25d7ab2e92e24c51b326f6313001d096/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/88dbda57fc2149b39a648d5a046f1448-fa89fd920c7341bc9f7f9c64661b4a12.xml --timeout 120.000000 | exited | 0 | logs/14c71db8f55244e2bdd0fce7c4e71097/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/88dbda57fc2149b39a648d5a046f1448-fa89fd920c7341bc9f7f9c64661b4a12.xml | exited | 0 | logs/017a42800c194ab3aca2314277d7d9da/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/88dbda57fc2149b39a648d5a046f1448-d9ec9ed2cb42401bb8454ce3581a7593.xml --timeout 120.000000 | exited | 0 | logs/874ed76645194bc18b50ebb9afdcdb1f/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/88dbda57fc2149b39a648d5a046f1448-d9ec9ed2cb42401bb8454ce3581a7593.xml | exited | 0 | logs/7922759f58ea46d7871987bcb1e1a6df/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/88dbda57fc2149b39a648d5a046f1448-bb812a3634754e2993bcef842aa5d6fb.xml --timeout 120.000000 | exited | 0 | logs/adfcd4b0311f4f6c85645072b6ade6fb/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/88dbda57fc2149b39a648d5a046f1448-bb812a3634754e2993bcef842aa5d6fb.xml | exited | 0 | logs/57ef77a65c2d496c8059ef261f3c2744/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
