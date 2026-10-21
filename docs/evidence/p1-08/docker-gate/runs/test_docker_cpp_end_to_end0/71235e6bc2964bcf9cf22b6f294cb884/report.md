# ReproPatch 71235e6bc2964bcf9cf22b6f294cb884

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：64b784927cec5725d23326a629810e91de6ce8cb
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：12.395 秒
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
| baseline | negative\_values | 失败 | evidence/b1a32b54723246d0ada838c8f71d009a/c8f95677fe344957be79437ccfd9aac7.xml |
| baseline | positive\_values | 通过 | evidence/b1a32b54723246d0ada838c8f71d009a/6c78cf0042b2400a93176a51626e37d6.xml |
| baseline | empty\_values | 通过 | evidence/b1a32b54723246d0ada838c8f71d009a/619106fa609841e795500d989bca0e5d.xml |
| baseline | mixed\_values | 通过 | evidence/b1a32b54723246d0ada838c8f71d009a/5b76fcdc32a448509ba27a7f26a036e3.xml |
| agent\_check | negative\_values | 通过 | evidence/598708e2bb7448bcb2591278bf22ebea/09a455bd946343258a3288e5a2c4d056.xml |
| agent\_check | positive\_values | 通过 | evidence/598708e2bb7448bcb2591278bf22ebea/28066676ff384a3a8516bf04296e38fe.xml |
| agent\_check | empty\_values | 通过 | evidence/598708e2bb7448bcb2591278bf22ebea/fb408a992c1d4dc491c388ea87174a14.xml |
| agent\_check | mixed\_values | 通过 | evidence/598708e2bb7448bcb2591278bf22ebea/6f85bd6626df4af2b266f213215162c6.xml |
| independent | negative\_values | 通过 | evidence/ee04aaf9869d4a848b35ea3d00ee009e/86eb39e04b5e4a69a7facb1f2de2ba75.xml |
| independent | positive\_values | 通过 | evidence/ee04aaf9869d4a848b35ea3d00ee009e/147fc4d18fc84c93b8591acdb59a124c.xml |
| independent | empty\_values | 通过 | evidence/ee04aaf9869d4a848b35ea3d00ee009e/fc526c38c0b1458f8f83ba997b8d4176.xml |
| independent | mixed\_values | 通过 | evidence/ee04aaf9869d4a848b35ea3d00ee009e/c1e147eebe3f4613a50604fdd992e3f4.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/3705e087527b4a8d9760ace3a3be823b/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/2f45521df82f49d5b8cff378dbfd2793/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/3e93245e564342ac8eda78e68e42415b/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/6dcf44cfdf7445df8d4f94618c254818/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/67584d8d2aba409abeeff34c55ff6bbc/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/b1a32b54723246d0ada838c8f71d009a-c8f95677fe344957be79437ccfd9aac7.xml --timeout 120.000000 | exited | 8 | logs/8ad0f4a798ba4f768d07f6167c0b3e7f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b1a32b54723246d0ada838c8f71d009a-c8f95677fe344957be79437ccfd9aac7.xml | exited | 0 | logs/3aa5140e6ac8490e980ae89809de5ac7/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/b1a32b54723246d0ada838c8f71d009a-6c78cf0042b2400a93176a51626e37d6.xml --timeout 120.000000 | exited | 0 | logs/de1a369748bd4263b601032ee2a20375/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b1a32b54723246d0ada838c8f71d009a-6c78cf0042b2400a93176a51626e37d6.xml | exited | 0 | logs/cf63763c46c143379a9940e9ceed793a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/b1a32b54723246d0ada838c8f71d009a-619106fa609841e795500d989bca0e5d.xml --timeout 120.000000 | exited | 0 | logs/a9e7e843603f472d8761f8cbcbacb470/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b1a32b54723246d0ada838c8f71d009a-619106fa609841e795500d989bca0e5d.xml | exited | 0 | logs/08c64260ff8c4536913a7006cab1d0d7/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/b1a32b54723246d0ada838c8f71d009a-5b76fcdc32a448509ba27a7f26a036e3.xml --timeout 120.000000 | exited | 0 | logs/3ae977f96867489ca4039edae47cd15d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b1a32b54723246d0ada838c8f71d009a-5b76fcdc32a448509ba27a7f26a036e3.xml | exited | 0 | logs/f22d92aa88814007b142aca830379734/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/32e434c3ea87423687f9f07dd89912c9/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/748fe6247c4d49009c293c21ff076293/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/dee9763eae5a4a3dacee09ff04b5ab6c/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/3212a39b2fe145e0b3d7090715c98612/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/5df83f42e9fc41ecb80fcd5277670af3/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/598708e2bb7448bcb2591278bf22ebea-09a455bd946343258a3288e5a2c4d056.xml --timeout 120.000000 | exited | 0 | logs/374d6e9dcee34db7bed1a58acc28927e/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/598708e2bb7448bcb2591278bf22ebea-09a455bd946343258a3288e5a2c4d056.xml | exited | 0 | logs/b04c2af62c2a4666b3f9acb6a0392b9b/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/598708e2bb7448bcb2591278bf22ebea-28066676ff384a3a8516bf04296e38fe.xml --timeout 120.000000 | exited | 0 | logs/b1740ad657b1471aa8e377848169f5dc/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/598708e2bb7448bcb2591278bf22ebea-28066676ff384a3a8516bf04296e38fe.xml | exited | 0 | logs/3947fae014ca412ca7e0748811f38a68/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/598708e2bb7448bcb2591278bf22ebea-fb408a992c1d4dc491c388ea87174a14.xml --timeout 120.000000 | exited | 0 | logs/200dd0f2d4c14413b524f0168fd90018/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/598708e2bb7448bcb2591278bf22ebea-fb408a992c1d4dc491c388ea87174a14.xml | exited | 0 | logs/f695506b5e3d48fcb03a1ecffce7a78f/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/598708e2bb7448bcb2591278bf22ebea-6f85bd6626df4af2b266f213215162c6.xml --timeout 120.000000 | exited | 0 | logs/e50d824802f94d6fb9cf6201971e24cc/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/598708e2bb7448bcb2591278bf22ebea-6f85bd6626df4af2b266f213215162c6.xml | exited | 0 | logs/5d329f8fba9f493fafac32ab44e7226f/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/74e269f1fcb9429eb14d24b079567ea4/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/2b0acbc251254bf6b589da29662bcc93/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/0b48f137774b414e94570e7b2ba70e93/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/e0e93f60695d4099a25da815762c19b4/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/7e86f76df4974107b42df76d8368bf8d/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/ee04aaf9869d4a848b35ea3d00ee009e-86eb39e04b5e4a69a7facb1f2de2ba75.xml --timeout 120.000000 | exited | 0 | logs/0ed4bbe8d0be4021b6ff1b764d317963/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ee04aaf9869d4a848b35ea3d00ee009e-86eb39e04b5e4a69a7facb1f2de2ba75.xml | exited | 0 | logs/84aa8b595e254aa6bdf45965e30f323b/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/ee04aaf9869d4a848b35ea3d00ee009e-147fc4d18fc84c93b8591acdb59a124c.xml --timeout 120.000000 | exited | 0 | logs/8a9bc0bf2ee8495a99ed3254383fced1/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ee04aaf9869d4a848b35ea3d00ee009e-147fc4d18fc84c93b8591acdb59a124c.xml | exited | 0 | logs/63914646c611466e87d58802041e005d/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/ee04aaf9869d4a848b35ea3d00ee009e-fc526c38c0b1458f8f83ba997b8d4176.xml --timeout 120.000000 | exited | 0 | logs/a09381ca766f42d3808a1d5381f0a318/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ee04aaf9869d4a848b35ea3d00ee009e-fc526c38c0b1458f8f83ba997b8d4176.xml | exited | 0 | logs/e2c87f7994224808939d618615df0e3f/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/ee04aaf9869d4a848b35ea3d00ee009e-c1e147eebe3f4613a50604fdd992e3f4.xml --timeout 120.000000 | exited | 0 | logs/b745a34eac8b4c2c8d5df9411a01b33e/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ee04aaf9869d4a848b35ea3d00ee009e-c1e147eebe3f4613a50604fdd992e3f4.xml | exited | 0 | logs/ca90b6702e1b44f58f889e55f2e68bec/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
