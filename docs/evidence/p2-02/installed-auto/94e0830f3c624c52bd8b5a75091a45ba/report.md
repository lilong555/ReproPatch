# ReproPatch 94e0830f3c624c52bd8b5a75091a45ba

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：10.574 秒
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
| baseline | negative\_values | 失败 | evidence/17397db43b304485a5e0a0ff6f3d87b4/31dbc2db45dd4853ae06b1f1219e2bc8.xml |
| baseline | positive\_values | 通过 | evidence/17397db43b304485a5e0a0ff6f3d87b4/35e2f2f44ff947aeae25e07e0a3c36c8.xml |
| baseline | empty\_values | 通过 | evidence/17397db43b304485a5e0a0ff6f3d87b4/50e50d056dee4126b4aa8f8bc3c2b7de.xml |
| baseline | mixed\_values | 通过 | evidence/17397db43b304485a5e0a0ff6f3d87b4/5aa44a8ba8364c00a46bf59a6e9eaaf5.xml |
| agent\_check | negative\_values | 通过 | evidence/7b45709087a54d77a9cca1b9a28c810b/699a8045e87c42b681228170df965146.xml |
| agent\_check | positive\_values | 通过 | evidence/7b45709087a54d77a9cca1b9a28c810b/87122393918746bfaee9c1b92ea7e22a.xml |
| agent\_check | empty\_values | 通过 | evidence/7b45709087a54d77a9cca1b9a28c810b/a856164ab9344b6580e507c67b8f7e96.xml |
| agent\_check | mixed\_values | 通过 | evidence/7b45709087a54d77a9cca1b9a28c810b/c508e0ab929d41e693776ef5ba297703.xml |
| independent | negative\_values | 通过 | evidence/a1472706c3324b4a8617823e53740ddd/580207beedd042cbb0ca2244c985bba3.xml |
| independent | positive\_values | 通过 | evidence/a1472706c3324b4a8617823e53740ddd/e2a6fedb8ee3497791ca888463c23e2c.xml |
| independent | empty\_values | 通过 | evidence/a1472706c3324b4a8617823e53740ddd/720028f963204ef7bfd18214d8394717.xml |
| independent | mixed\_values | 通过 | evidence/a1472706c3324b4a8617823e53740ddd/2922db0536524ffdacd4d611a49c8676.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/2e333f88110e4f2bbd212de657e92831/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/e48f3e99b1d042af8b5a85572c61aa60/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/81d6f36253ed4d2ea80f932e3949e112/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/7c9656093e8548f8a310a807ed6e6068/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/71d6c843122145cda800ddcfd4531805/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/17397db43b304485a5e0a0ff6f3d87b4-31dbc2db45dd4853ae06b1f1219e2bc8.xml --timeout 120.000000 | exited | 8 | logs/e1e37d7278954c0298b25d5789090c1c/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/17397db43b304485a5e0a0ff6f3d87b4-31dbc2db45dd4853ae06b1f1219e2bc8.xml | exited | 0 | logs/2129f54bf9e443e38d3c8a33d9b5ad48/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/17397db43b304485a5e0a0ff6f3d87b4-35e2f2f44ff947aeae25e07e0a3c36c8.xml --timeout 120.000000 | exited | 0 | logs/fd2cf1a21eb44dbb8f654373d0a9fb55/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/17397db43b304485a5e0a0ff6f3d87b4-35e2f2f44ff947aeae25e07e0a3c36c8.xml | exited | 0 | logs/25fd5bcb20074260a4c526fa3fbfd8f5/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/17397db43b304485a5e0a0ff6f3d87b4-50e50d056dee4126b4aa8f8bc3c2b7de.xml --timeout 120.000000 | exited | 0 | logs/c0c5954924c840a3bbfc0ca0a6ebfb82/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/17397db43b304485a5e0a0ff6f3d87b4-50e50d056dee4126b4aa8f8bc3c2b7de.xml | exited | 0 | logs/5800f77abc24444e832607e5e95d293b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/17397db43b304485a5e0a0ff6f3d87b4-5aa44a8ba8364c00a46bf59a6e9eaaf5.xml --timeout 120.000000 | exited | 0 | logs/4cccc98da3f841409873168baddca3c4/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/17397db43b304485a5e0a0ff6f3d87b4-5aa44a8ba8364c00a46bf59a6e9eaaf5.xml | exited | 0 | logs/b8b1c7e2ad884d5a91637457d857bf36/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/cc2434ddb2054109bd5c55ebfea04e81/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/89718a6f4ed04dce85953325790305e8/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/72797049399c45009e21e99300fff92a/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/a40ff9a81de647ce964860ef6662f95a/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/8a230d94540f44d28950f64b774d499b/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/7b45709087a54d77a9cca1b9a28c810b-699a8045e87c42b681228170df965146.xml --timeout 120.000000 | exited | 0 | logs/f0ab04f267bb47f5841ce9d649e4a8b9/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7b45709087a54d77a9cca1b9a28c810b-699a8045e87c42b681228170df965146.xml | exited | 0 | logs/655eeeaf2ccf4980ad41236ff8555bf1/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/7b45709087a54d77a9cca1b9a28c810b-87122393918746bfaee9c1b92ea7e22a.xml --timeout 120.000000 | exited | 0 | logs/49577236138f41879a0eea7204880cc4/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7b45709087a54d77a9cca1b9a28c810b-87122393918746bfaee9c1b92ea7e22a.xml | exited | 0 | logs/c32938ab9076417a83e843ce5cb74a31/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/7b45709087a54d77a9cca1b9a28c810b-a856164ab9344b6580e507c67b8f7e96.xml --timeout 120.000000 | exited | 0 | logs/1c47c27ed8b8424388302f9ed3ed759e/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7b45709087a54d77a9cca1b9a28c810b-a856164ab9344b6580e507c67b8f7e96.xml | exited | 0 | logs/5a9386b9f843416f9e9e5ac9ce25f2e2/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/7b45709087a54d77a9cca1b9a28c810b-c508e0ab929d41e693776ef5ba297703.xml --timeout 120.000000 | exited | 0 | logs/579ac75c2a704e9ab9fa90ed4a01ee7b/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7b45709087a54d77a9cca1b9a28c810b-c508e0ab929d41e693776ef5ba297703.xml | exited | 0 | logs/a2ad09180a1e48a08b7a59f83beb8bc7/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/fb3b8ac8823448cb8afa0924516d717e/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/b1befa731ecf4fbf93d3ea900b6da2c2/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/2a828e295cf949a7ba0f4feb1c237626/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/479794afeb264bcebcf5f5ba2ec3fdfc/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/59f287bb4d7042bea164c6a8e852aed4/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/a1472706c3324b4a8617823e53740ddd-580207beedd042cbb0ca2244c985bba3.xml --timeout 120.000000 | exited | 0 | logs/5abd1649e5a64152b3da4d9a25da65a0/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a1472706c3324b4a8617823e53740ddd-580207beedd042cbb0ca2244c985bba3.xml | exited | 0 | logs/221e86809ef944f1948b310321144d64/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/a1472706c3324b4a8617823e53740ddd-e2a6fedb8ee3497791ca888463c23e2c.xml --timeout 120.000000 | exited | 0 | logs/d9e5a511a25d4e59b0d380b563b8f3a2/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a1472706c3324b4a8617823e53740ddd-e2a6fedb8ee3497791ca888463c23e2c.xml | exited | 0 | logs/66a8e42ddd3e4725a1731b52b2d5397b/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/a1472706c3324b4a8617823e53740ddd-720028f963204ef7bfd18214d8394717.xml --timeout 120.000000 | exited | 0 | logs/d8e24483e6f54a9aa9dcb31aefcc06cf/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a1472706c3324b4a8617823e53740ddd-720028f963204ef7bfd18214d8394717.xml | exited | 0 | logs/2d7c304b03bb45d59ecb7b43074456a7/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/a1472706c3324b4a8617823e53740ddd-2922db0536524ffdacd4d611a49c8676.xml --timeout 120.000000 | exited | 0 | logs/212dba8a179948f28e7e610f805bb9b7/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a1472706c3324b4a8617823e53740ddd-2922db0536524ffdacd4d611a49c8676.xml | exited | 0 | logs/658ccc84ae7e46f082e9496bcebe5a75/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
