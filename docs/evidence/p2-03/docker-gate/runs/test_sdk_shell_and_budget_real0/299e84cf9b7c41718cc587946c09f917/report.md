# ReproPatch 299e84cf9b7c41718cc587946c09f917

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：073a98de838a46a36a6d6fd2647419c3de65e8b4
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：9.005 秒
模型步骤：3；准入工具：2
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：97


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/0a711b77257b489fb1c0e3874091c2e6/7cf1b61d369a427ab16f84a71627c67c.xml |
| baseline | positive\_values | 通过 | evidence/0a711b77257b489fb1c0e3874091c2e6/83ca29f9b65e4c2190c71a97589fa78d.xml |
| baseline | empty\_values | 通过 | evidence/0a711b77257b489fb1c0e3874091c2e6/f3992c35c1324153814291a103a1b9c2.xml |
| baseline | mixed\_values | 通过 | evidence/0a711b77257b489fb1c0e3874091c2e6/b3ac8172b8494546974fcb65aed0d6d2.xml |
| independent | negative\_values | 通过 | evidence/329cb392409b46c5bdef069fb90c5557/170611720e4d4072b5fb2b9d61237650.xml |
| independent | positive\_values | 通过 | evidence/329cb392409b46c5bdef069fb90c5557/85fa5291a7f846bc85106127adae56ab.xml |
| independent | empty\_values | 通过 | evidence/329cb392409b46c5bdef069fb90c5557/dae631dedf894828a805683619c04711.xml |
| independent | mixed\_values | 通过 | evidence/329cb392409b46c5bdef069fb90c5557/1585e1963c334e28bcb663ba56b96d67.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/9358c2c73dfb4a329d3035970d9285f8/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/1ad8b6c31bcb4695b012dd54a39e1b83/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/c86f10a5e3ad4adba8f887248f4ca37e/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/b0b140d4dac9401a90580eadc211235b/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/0257b1cdc5624c7ebe21a5ac4279f1e1/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/0a711b77257b489fb1c0e3874091c2e6-7cf1b61d369a427ab16f84a71627c67c.xml --timeout 120.000000 | exited | 8 | logs/970b18670d674cc883a847c34bafceec/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0a711b77257b489fb1c0e3874091c2e6-7cf1b61d369a427ab16f84a71627c67c.xml | exited | 0 | logs/09e16bf0cc7b4b6e9376383bfc550725/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/0a711b77257b489fb1c0e3874091c2e6-83ca29f9b65e4c2190c71a97589fa78d.xml --timeout 120.000000 | exited | 0 | logs/0688e766c4c84133bd85cc3e93077e69/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0a711b77257b489fb1c0e3874091c2e6-83ca29f9b65e4c2190c71a97589fa78d.xml | exited | 0 | logs/4517b4f7d3a9437f889084e4ff1e14dd/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/0a711b77257b489fb1c0e3874091c2e6-f3992c35c1324153814291a103a1b9c2.xml --timeout 120.000000 | exited | 0 | logs/f4a95f74ae26489eb68ef2fb348ac742/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0a711b77257b489fb1c0e3874091c2e6-f3992c35c1324153814291a103a1b9c2.xml | exited | 0 | logs/2f072dd9674d4363a6635a8ea0535d27/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/0a711b77257b489fb1c0e3874091c2e6-b3ac8172b8494546974fcb65aed0d6d2.xml --timeout 120.000000 | exited | 0 | logs/a6480a4084ba469a8eacf8bf6f541220/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0a711b77257b489fb1c0e3874091c2e6-b3ac8172b8494546974fcb65aed0d6d2.xml | exited | 0 | logs/db16451f37144f85ad2fe22cb19913d9/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/8cdb1ab3257c4ae99aec6c6103e208ab/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/cc8029f5fb9247338be82d3b5c320a35/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/846fb4986d504a10a95757ef330d2c69/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/1d0652b62dd8419689a8e091fc785ec2/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/19d35ca2f8064d3a82460284cb6ee469/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/329cb392409b46c5bdef069fb90c5557-170611720e4d4072b5fb2b9d61237650.xml --timeout 120.000000 | exited | 0 | logs/f563af5cc26c41e685502cb53204f740/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/329cb392409b46c5bdef069fb90c5557-170611720e4d4072b5fb2b9d61237650.xml | exited | 0 | logs/fb1df999941746eda6015c45f21ee094/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/329cb392409b46c5bdef069fb90c5557-85fa5291a7f846bc85106127adae56ab.xml --timeout 120.000000 | exited | 0 | logs/80a2581587ca428eab62b488687a83c4/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/329cb392409b46c5bdef069fb90c5557-85fa5291a7f846bc85106127adae56ab.xml | exited | 0 | logs/1282016829b942f5a4e855c03b5c5f5a/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/329cb392409b46c5bdef069fb90c5557-dae631dedf894828a805683619c04711.xml --timeout 120.000000 | exited | 0 | logs/b43abbed53494077ae16490443b59549/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/329cb392409b46c5bdef069fb90c5557-dae631dedf894828a805683619c04711.xml | exited | 0 | logs/d56f3c8d82204ce0b2ae4def59749591/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/329cb392409b46c5bdef069fb90c5557-1585e1963c334e28bcb663ba56b96d67.xml --timeout 120.000000 | exited | 0 | logs/5305c56743074e23ba7267b29469a690/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/329cb392409b46c5bdef069fb90c5557-1585e1963c334e28bcb663ba56b96d67.xml | exited | 0 | logs/ff8a9261ec464ddc83c91925ec7bc81b/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
