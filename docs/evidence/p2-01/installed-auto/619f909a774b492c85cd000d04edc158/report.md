# ReproPatch 619f909a774b492c85cd000d04edc158

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：12.764 秒
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
| baseline | negative\_values | 失败 | evidence/6189564ff5ec4150a92f78baf47e9776/f5d3c41a1bc348449469abb0fab66d98.xml |
| baseline | positive\_values | 通过 | evidence/6189564ff5ec4150a92f78baf47e9776/2c104692b1a446738d439d1baf0ceb2d.xml |
| baseline | empty\_values | 通过 | evidence/6189564ff5ec4150a92f78baf47e9776/5cc08f7c67e84648830d8458edfd6ade.xml |
| baseline | mixed\_values | 通过 | evidence/6189564ff5ec4150a92f78baf47e9776/b7b0398e75b5473d9c122d1fce1386b8.xml |
| agent\_check | negative\_values | 通过 | evidence/e68f70ca11cb452493c35f4d7a348787/ac3b8544cdec4c7b835249ff5da6145d.xml |
| agent\_check | positive\_values | 通过 | evidence/e68f70ca11cb452493c35f4d7a348787/3a86ce9ca30d424f813aa4d19ce96d5d.xml |
| agent\_check | empty\_values | 通过 | evidence/e68f70ca11cb452493c35f4d7a348787/15d33adb16fc46d99f5593719377e41c.xml |
| agent\_check | mixed\_values | 通过 | evidence/e68f70ca11cb452493c35f4d7a348787/a34dd53c4bf04409be7190bd87732cf1.xml |
| independent | negative\_values | 通过 | evidence/42a84989c5004666b22b7e18fcc5c20e/6d7cccbb4ce5489c91088e6f4cbd067f.xml |
| independent | positive\_values | 通过 | evidence/42a84989c5004666b22b7e18fcc5c20e/40cc04b157de409bacabad8aee5a083e.xml |
| independent | empty\_values | 通过 | evidence/42a84989c5004666b22b7e18fcc5c20e/6df457de9dee4987b234b9a4467cdf24.xml |
| independent | mixed\_values | 通过 | evidence/42a84989c5004666b22b7e18fcc5c20e/0962701fb3014b2498e99585656bc370.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/b7044eb3fcde4ea69cd7fce0ec4e2281/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/5ac0d6808c9e444f8976a8310dec0225/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/2c06a6c2bcbc4b05918fa4533c749779/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/f2fdee178d664c939b99a30c5d421f0e/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/88c95e1053a34ad7be7130e669d01d07/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/6189564ff5ec4150a92f78baf47e9776-f5d3c41a1bc348449469abb0fab66d98.xml --timeout 120.000000 | exited | 8 | logs/bc5d057631134c549b63aa521d2e0532/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/6189564ff5ec4150a92f78baf47e9776-f5d3c41a1bc348449469abb0fab66d98.xml | exited | 0 | logs/11da44fdd82f4144a0fab3007332fda3/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/6189564ff5ec4150a92f78baf47e9776-2c104692b1a446738d439d1baf0ceb2d.xml --timeout 120.000000 | exited | 0 | logs/4faca34a62284bd998a9b86824c168f5/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/6189564ff5ec4150a92f78baf47e9776-2c104692b1a446738d439d1baf0ceb2d.xml | exited | 0 | logs/583cdb6259654bc389e8bc4674625b1f/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/6189564ff5ec4150a92f78baf47e9776-5cc08f7c67e84648830d8458edfd6ade.xml --timeout 120.000000 | exited | 0 | logs/101302cbe5f049acaeba6cd6b808dfda/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/6189564ff5ec4150a92f78baf47e9776-5cc08f7c67e84648830d8458edfd6ade.xml | exited | 0 | logs/d9477491ff95497386a9fc16b5a85579/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/6189564ff5ec4150a92f78baf47e9776-b7b0398e75b5473d9c122d1fce1386b8.xml --timeout 120.000000 | exited | 0 | logs/9eee98f0c6e4492ebda2f60d651fe5db/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/6189564ff5ec4150a92f78baf47e9776-b7b0398e75b5473d9c122d1fce1386b8.xml | exited | 0 | logs/f76b5a4b174e4b5c950122bc6015f356/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/acf76d20d2f54afb87b2a700fdcba016/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/76987de326534a57aa06e1c41a8d22f3/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/18c21de2e4434f1d832bc1a265644638/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/95562bae255540368f17ca69d76dbc6e/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/2472da80a34a42799c9f4469dec51e86/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/e68f70ca11cb452493c35f4d7a348787-ac3b8544cdec4c7b835249ff5da6145d.xml --timeout 120.000000 | exited | 0 | logs/25b88283734240d78ad3ab242dca5924/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e68f70ca11cb452493c35f4d7a348787-ac3b8544cdec4c7b835249ff5da6145d.xml | exited | 0 | logs/1a0c78cc3e1a4cd5849798160c8480e1/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/e68f70ca11cb452493c35f4d7a348787-3a86ce9ca30d424f813aa4d19ce96d5d.xml --timeout 120.000000 | exited | 0 | logs/a05460899594452fbe9ef2f17091bef0/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e68f70ca11cb452493c35f4d7a348787-3a86ce9ca30d424f813aa4d19ce96d5d.xml | exited | 0 | logs/4f56dbaff2c342b7903eb1d8c5e38dee/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/e68f70ca11cb452493c35f4d7a348787-15d33adb16fc46d99f5593719377e41c.xml --timeout 120.000000 | exited | 0 | logs/b29e0e8d22584957834432d6d2d72ef9/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e68f70ca11cb452493c35f4d7a348787-15d33adb16fc46d99f5593719377e41c.xml | exited | 0 | logs/34a2b692e3674e24bf31664466b504b4/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/e68f70ca11cb452493c35f4d7a348787-a34dd53c4bf04409be7190bd87732cf1.xml --timeout 120.000000 | exited | 0 | logs/feb396c6e06a49ed8a35bef0485564e8/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e68f70ca11cb452493c35f4d7a348787-a34dd53c4bf04409be7190bd87732cf1.xml | exited | 0 | logs/e780d235e799434288ee0068a7be480b/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/ce860b5d66cd41a29c83eed3d6bddefe/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/1fec0c760ca54e27a9ff6e8a5760c876/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/8e292babc40545e39f2c5897301ff449/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/a831d2888ca34f9ba0e549b5beecfb44/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/9c2e6184fed24f0c82c2f44acfb19ff6/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/42a84989c5004666b22b7e18fcc5c20e-6d7cccbb4ce5489c91088e6f4cbd067f.xml --timeout 120.000000 | exited | 0 | logs/d879c22d27c5468aa1923830baa2cd34/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/42a84989c5004666b22b7e18fcc5c20e-6d7cccbb4ce5489c91088e6f4cbd067f.xml | exited | 0 | logs/c3876b74cb9a4cb7ae345e0d2e21c214/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/42a84989c5004666b22b7e18fcc5c20e-40cc04b157de409bacabad8aee5a083e.xml --timeout 120.000000 | exited | 0 | logs/c9d14235ad644750863af2b5977949cb/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/42a84989c5004666b22b7e18fcc5c20e-40cc04b157de409bacabad8aee5a083e.xml | exited | 0 | logs/b34c2152a90d47a49d40119408d22a7a/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/42a84989c5004666b22b7e18fcc5c20e-6df457de9dee4987b234b9a4467cdf24.xml --timeout 120.000000 | exited | 0 | logs/04b0d476649e4c22b373572c940be669/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/42a84989c5004666b22b7e18fcc5c20e-6df457de9dee4987b234b9a4467cdf24.xml | exited | 0 | logs/acaffa6c8793400c888b064214597405/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/42a84989c5004666b22b7e18fcc5c20e-0962701fb3014b2498e99585656bc370.xml --timeout 120.000000 | exited | 0 | logs/d5a60363bac24077982f8c4d8bae949f/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/42a84989c5004666b22b7e18fcc5c20e-0962701fb3014b2498e99585656bc370.xml | exited | 0 | logs/88e8902ee8c04fdfb5be9a6e4e131598/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
