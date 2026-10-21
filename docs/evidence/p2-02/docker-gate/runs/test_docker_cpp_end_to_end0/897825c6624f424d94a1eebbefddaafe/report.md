# ReproPatch 897825c6624f424d94a1eebbefddaafe

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：14840e10930baadc8367a6a44ebf2f29a97574cc
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：13.311 秒
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
| baseline | negative\_values | 失败 | evidence/6ecd1a58e2f84e7d8054b463e25b6334/4a2e653a0850444985e73cabbceb1d73.xml |
| baseline | positive\_values | 通过 | evidence/6ecd1a58e2f84e7d8054b463e25b6334/2fcd59451f42436e91a10e67fa254c00.xml |
| baseline | empty\_values | 通过 | evidence/6ecd1a58e2f84e7d8054b463e25b6334/87a5d43dbec4467391a2351058154dea.xml |
| baseline | mixed\_values | 通过 | evidence/6ecd1a58e2f84e7d8054b463e25b6334/60c39a411ae044f09f81c5b4719023ed.xml |
| agent\_check | negative\_values | 通过 | evidence/9a3ddcf87f9849e8b2096ec4e3dcf4ed/45d8a8cfa21742b8a6d43fbef0d4cdbc.xml |
| agent\_check | positive\_values | 通过 | evidence/9a3ddcf87f9849e8b2096ec4e3dcf4ed/2436b1b2f22043929c9ff5b1a46006ef.xml |
| agent\_check | empty\_values | 通过 | evidence/9a3ddcf87f9849e8b2096ec4e3dcf4ed/492e0140af8b425dadef2f2bdbb18e9f.xml |
| agent\_check | mixed\_values | 通过 | evidence/9a3ddcf87f9849e8b2096ec4e3dcf4ed/45968733b16249ad83bbfb9dd0ae7ece.xml |
| independent | negative\_values | 通过 | evidence/c2624768b14e45259e27ed80bfa539e4/cdb12471a5524bccb288bce4c2a97baf.xml |
| independent | positive\_values | 通过 | evidence/c2624768b14e45259e27ed80bfa539e4/5aa348a08e114d2ba6ba6171ae937e16.xml |
| independent | empty\_values | 通过 | evidence/c2624768b14e45259e27ed80bfa539e4/63cb5024660c46f1822019f67e6aa797.xml |
| independent | mixed\_values | 通过 | evidence/c2624768b14e45259e27ed80bfa539e4/4dd9d39b9c1646cc83cf08df19a7f6dd.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/c40cda5d88da4c2392ff33d17fec21b0/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/1044fe94ccd349c59adb3de098e4420b/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/bce4235433834941bc263c33e0890d82/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/28f24e09cf9d4fcfb61c72d998f380ab/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/ffb295593b974f8ebb6b993042049950/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/6ecd1a58e2f84e7d8054b463e25b6334-4a2e653a0850444985e73cabbceb1d73.xml --timeout 120.000000 | exited | 8 | logs/efda589186d44a09a67ee79f347533c9/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/6ecd1a58e2f84e7d8054b463e25b6334-4a2e653a0850444985e73cabbceb1d73.xml | exited | 0 | logs/2dc6acb5a11849499741ed83ad636f98/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/6ecd1a58e2f84e7d8054b463e25b6334-2fcd59451f42436e91a10e67fa254c00.xml --timeout 120.000000 | exited | 0 | logs/2fdcef1d2dea4c3580f24b06e624b262/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/6ecd1a58e2f84e7d8054b463e25b6334-2fcd59451f42436e91a10e67fa254c00.xml | exited | 0 | logs/85c06ea4ee664b8bad6e7252ccf1a3b5/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/6ecd1a58e2f84e7d8054b463e25b6334-87a5d43dbec4467391a2351058154dea.xml --timeout 120.000000 | exited | 0 | logs/e9b73582ddda4ea3acd99f8ae18128b6/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/6ecd1a58e2f84e7d8054b463e25b6334-87a5d43dbec4467391a2351058154dea.xml | exited | 0 | logs/f4c56376619c4cd284d1f6ef74df3821/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/6ecd1a58e2f84e7d8054b463e25b6334-60c39a411ae044f09f81c5b4719023ed.xml --timeout 120.000000 | exited | 0 | logs/022455f7995e485194e9f4f76f344370/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/6ecd1a58e2f84e7d8054b463e25b6334-60c39a411ae044f09f81c5b4719023ed.xml | exited | 0 | logs/474cd47bf6ce4f019b67c1539e8744d4/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/b4f6a00a0f244424a2af13d6abb4b65a/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/0b74b3ac3aab414ca6f242eeaafc8692/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/dfd48b7efb76446295b5c04a9f08f978/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/2564c61b3b4e4db89054ed1d281db24c/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/702556b552334969a121489a89f068ea/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/9a3ddcf87f9849e8b2096ec4e3dcf4ed-45d8a8cfa21742b8a6d43fbef0d4cdbc.xml --timeout 120.000000 | exited | 0 | logs/10dff7db1b4e4a4b85d99d913b51fc5c/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/9a3ddcf87f9849e8b2096ec4e3dcf4ed-45d8a8cfa21742b8a6d43fbef0d4cdbc.xml | exited | 0 | logs/359ce1d470ba418082eb0a2f7bcc597e/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/9a3ddcf87f9849e8b2096ec4e3dcf4ed-2436b1b2f22043929c9ff5b1a46006ef.xml --timeout 120.000000 | exited | 0 | logs/4ee38a662eca462c81a732bf373feaa9/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/9a3ddcf87f9849e8b2096ec4e3dcf4ed-2436b1b2f22043929c9ff5b1a46006ef.xml | exited | 0 | logs/f5f5aa41f8a44ac7b63140eae6a95b0a/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/9a3ddcf87f9849e8b2096ec4e3dcf4ed-492e0140af8b425dadef2f2bdbb18e9f.xml --timeout 120.000000 | exited | 0 | logs/a4b1ae0a422f4fb8a16e050791fc8538/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/9a3ddcf87f9849e8b2096ec4e3dcf4ed-492e0140af8b425dadef2f2bdbb18e9f.xml | exited | 0 | logs/07d463ff60bd411ab7f925f2b171374a/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/9a3ddcf87f9849e8b2096ec4e3dcf4ed-45968733b16249ad83bbfb9dd0ae7ece.xml --timeout 120.000000 | exited | 0 | logs/3095d7c58711406aa88d42d33b05371a/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/9a3ddcf87f9849e8b2096ec4e3dcf4ed-45968733b16249ad83bbfb9dd0ae7ece.xml | exited | 0 | logs/f86ff55c19f84dff9450327f93281c62/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/0d6031213b5d43f49f36f0956ec017de/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/a72ec10c8ae74794bf0e350bab72f861/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/3e0686f3ca2549a4976da3403bba30bb/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/5db4c8954a55470b87efa4daa8c8db36/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/4b4b2c87b89b48db84ba682521ca08ce/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/c2624768b14e45259e27ed80bfa539e4-cdb12471a5524bccb288bce4c2a97baf.xml --timeout 120.000000 | exited | 0 | logs/1b33cda4281d495b99f6c706d37b5345/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c2624768b14e45259e27ed80bfa539e4-cdb12471a5524bccb288bce4c2a97baf.xml | exited | 0 | logs/fec0fb66ae1242e79a84ab9dcf744b41/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/c2624768b14e45259e27ed80bfa539e4-5aa348a08e114d2ba6ba6171ae937e16.xml --timeout 120.000000 | exited | 0 | logs/a29ab7f54bbe4b80b6cff33bacbb3f8c/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c2624768b14e45259e27ed80bfa539e4-5aa348a08e114d2ba6ba6171ae937e16.xml | exited | 0 | logs/81da16bdf104474585c421b8370cee70/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/c2624768b14e45259e27ed80bfa539e4-63cb5024660c46f1822019f67e6aa797.xml --timeout 120.000000 | exited | 0 | logs/3031d6cdbf9e426fb3514f3a8d1e9b15/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c2624768b14e45259e27ed80bfa539e4-63cb5024660c46f1822019f67e6aa797.xml | exited | 0 | logs/875709156c3345039701513874607579/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/c2624768b14e45259e27ed80bfa539e4-4dd9d39b9c1646cc83cf08df19a7f6dd.xml --timeout 120.000000 | exited | 0 | logs/acc9f6dd3d4942d8bbfa8ec03db7514e/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c2624768b14e45259e27ed80bfa539e4-4dd9d39b9c1646cc83cf08df19a7f6dd.xml | exited | 0 | logs/f763a83530964a8894587bef682a6e47/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
