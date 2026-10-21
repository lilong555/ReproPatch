# ReproPatch 74ac60042b8b4a8faa0b420cbe71e1e7

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：14.173 秒
模型步骤：5；准入工具：4
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：145


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/f7340ffb932c4e5f8c09b4a27f51fb00/d79cd139aeb14f2998a2144f4450d53d.xml |
| baseline | positive\_values | 通过 | evidence/f7340ffb932c4e5f8c09b4a27f51fb00/f8c090bd3d8940669f28db7a9a1ffa23.xml |
| baseline | empty\_values | 通过 | evidence/f7340ffb932c4e5f8c09b4a27f51fb00/a160926bb91742ef8dc7a3a8435ff214.xml |
| baseline | mixed\_values | 通过 | evidence/f7340ffb932c4e5f8c09b4a27f51fb00/1126dd6acd7b4a49b811462f4c3d1aac.xml |
| agent\_check | negative\_values | 通过 | evidence/ba99ca26a2684d9e8435d5af4fea9467/acd2ddeedc6a431e8644975f182db74c.xml |
| agent\_check | positive\_values | 通过 | evidence/ba99ca26a2684d9e8435d5af4fea9467/51b5fdcc501b424aa3b2e4829d0cefdc.xml |
| agent\_check | empty\_values | 通过 | evidence/ba99ca26a2684d9e8435d5af4fea9467/10095e19c0cd4da5b97c2f61b507bacb.xml |
| agent\_check | mixed\_values | 通过 | evidence/ba99ca26a2684d9e8435d5af4fea9467/9bc74114de1e4f70a85b95d222ee1fd2.xml |
| independent | negative\_values | 通过 | evidence/fefb0e77ddcd455aba25ff90bdf98e9b/a687960286734b9fa9f05d305e35678f.xml |
| independent | positive\_values | 通过 | evidence/fefb0e77ddcd455aba25ff90bdf98e9b/735a3b3a0c3941f4818246d208c2e52a.xml |
| independent | empty\_values | 通过 | evidence/fefb0e77ddcd455aba25ff90bdf98e9b/0ff9ce4a421447f1bbb25bf54cd272fa.xml |
| independent | mixed\_values | 通过 | evidence/fefb0e77ddcd455aba25ff90bdf98e9b/92ef452b867d45ae9a483b8768de1f11.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/8656419af9c9458783c7ae28f875d9bf/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/904a5c370cc04e17ac30fc41a9071a6b/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/ec0d693ceb2440daa1153de23271c605/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/de1b8d22db9f4a28a59054ea96ca0c8f/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/9af64dad33314214bfe65bb8a6d2266a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/f7340ffb932c4e5f8c09b4a27f51fb00-d79cd139aeb14f2998a2144f4450d53d.xml --timeout 120.000000 | exited | 8 | logs/b477fdb4c5df42168e46a0df2c6a4ac8/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f7340ffb932c4e5f8c09b4a27f51fb00-d79cd139aeb14f2998a2144f4450d53d.xml | exited | 0 | logs/42cb3f4fd2144c6cbafba51b9b59d821/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/f7340ffb932c4e5f8c09b4a27f51fb00-f8c090bd3d8940669f28db7a9a1ffa23.xml --timeout 120.000000 | exited | 0 | logs/f8046cb892a346a69e3ccb42372edbe9/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f7340ffb932c4e5f8c09b4a27f51fb00-f8c090bd3d8940669f28db7a9a1ffa23.xml | exited | 0 | logs/ca6f3da3546048adabb7b22e19dafe50/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/f7340ffb932c4e5f8c09b4a27f51fb00-a160926bb91742ef8dc7a3a8435ff214.xml --timeout 120.000000 | exited | 0 | logs/8cd91a84287f4c68b165795dd3ec5ef4/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f7340ffb932c4e5f8c09b4a27f51fb00-a160926bb91742ef8dc7a3a8435ff214.xml | exited | 0 | logs/5158e204eaac4c65be465714dd8ddb1e/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/f7340ffb932c4e5f8c09b4a27f51fb00-1126dd6acd7b4a49b811462f4c3d1aac.xml --timeout 120.000000 | exited | 0 | logs/30ee58c9589448268b666c500f3d56ce/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f7340ffb932c4e5f8c09b4a27f51fb00-1126dd6acd7b4a49b811462f4c3d1aac.xml | exited | 0 | logs/2d91988ae7e2488a929d1ebc476c451a/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/cb08ed0fd896472d93e0f0c87b771f4c/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/1b55764b40444a21b8e17f10bad8b675/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/44c6af6da60e47e6a68e168d1fec7176/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/514fbfaa2d6d4be990944f5a26f9e945/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/0844f048adf44696aa4f9e450533d274/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/ba99ca26a2684d9e8435d5af4fea9467-acd2ddeedc6a431e8644975f182db74c.xml --timeout 120.000000 | exited | 0 | logs/e3fc8f292bbc4b63a6fd888ef14553f0/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ba99ca26a2684d9e8435d5af4fea9467-acd2ddeedc6a431e8644975f182db74c.xml | exited | 0 | logs/cc341f11d9b44ab29dc7bb93b225cfe8/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/ba99ca26a2684d9e8435d5af4fea9467-51b5fdcc501b424aa3b2e4829d0cefdc.xml --timeout 120.000000 | exited | 0 | logs/b1d542655961403f8b2257635a76fd91/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ba99ca26a2684d9e8435d5af4fea9467-51b5fdcc501b424aa3b2e4829d0cefdc.xml | exited | 0 | logs/3c177047588b443c894177f3744eab1b/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/ba99ca26a2684d9e8435d5af4fea9467-10095e19c0cd4da5b97c2f61b507bacb.xml --timeout 120.000000 | exited | 0 | logs/f66a04cab43d44a9a2206b199e69bba3/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ba99ca26a2684d9e8435d5af4fea9467-10095e19c0cd4da5b97c2f61b507bacb.xml | exited | 0 | logs/e52b8e7ad3d14d3f92ad6680fc40f491/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/ba99ca26a2684d9e8435d5af4fea9467-9bc74114de1e4f70a85b95d222ee1fd2.xml --timeout 120.000000 | exited | 0 | logs/03c52f73a0b846158c48868ad6589d83/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ba99ca26a2684d9e8435d5af4fea9467-9bc74114de1e4f70a85b95d222ee1fd2.xml | exited | 0 | logs/8b594887ada84c21a61ef5fa36142b3f/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/992085af43d2441eb8d9720ff9e0f120/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/49eaa37e31ec40acaac50538328b4ff6/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/3c326834fefe40f1b8fffcd241102063/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/b104624bcbf248faaac550cf32cfcbba/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/8bc437b2581049c8b472b8bf07bbc91a/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/fefb0e77ddcd455aba25ff90bdf98e9b-a687960286734b9fa9f05d305e35678f.xml --timeout 120.000000 | exited | 0 | logs/7c98a5aa534447e584a66d5ecc29867c/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fefb0e77ddcd455aba25ff90bdf98e9b-a687960286734b9fa9f05d305e35678f.xml | exited | 0 | logs/c8f8b83d8a9a48ceaf473cb65dfc1ecd/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/fefb0e77ddcd455aba25ff90bdf98e9b-735a3b3a0c3941f4818246d208c2e52a.xml --timeout 120.000000 | exited | 0 | logs/8a1fe4296c6741e6bcb701f7d249723c/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fefb0e77ddcd455aba25ff90bdf98e9b-735a3b3a0c3941f4818246d208c2e52a.xml | exited | 0 | logs/1334746b310d45c5a143198041e1149d/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/fefb0e77ddcd455aba25ff90bdf98e9b-0ff9ce4a421447f1bbb25bf54cd272fa.xml --timeout 120.000000 | exited | 0 | logs/f0846b93f13e4a92acbadd8730ca5160/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fefb0e77ddcd455aba25ff90bdf98e9b-0ff9ce4a421447f1bbb25bf54cd272fa.xml | exited | 0 | logs/5becc6d284cc490e8eaad1296486bda1/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/fefb0e77ddcd455aba25ff90bdf98e9b-92ef452b867d45ae9a483b8768de1f11.xml --timeout 120.000000 | exited | 0 | logs/09c684ee49594eb399f303af560a64b2/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fefb0e77ddcd455aba25ff90bdf98e9b-92ef452b867d45ae9a483b8768de1f11.xml | exited | 0 | logs/ed14108119ee498fb415f03f4eb689c1/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
