# ReproPatch 6e806b0a87174f6eaea94db6f3bd8255

任务：negative-maximum-live
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：agents-sdk
模型：deepseek-flash
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：21.088 秒
模型步骤：5；准入工具：5
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：未知
Token 输入 / 输出 / 合计：81507 / 632 / 82139
合成用量：否；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：133


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/820acf30b53a4fa3b21434c0db49a346/5baa4afc20ab48e9a613f0b1af3f1963.xml |
| baseline | positive\_values | 通过 | evidence/820acf30b53a4fa3b21434c0db49a346/9d22546da8b648b0ab27e2fdc1cc5a70.xml |
| baseline | empty\_values | 通过 | evidence/820acf30b53a4fa3b21434c0db49a346/53ea1cacefc7451b8daab4cd5aebb19f.xml |
| baseline | mixed\_values | 通过 | evidence/820acf30b53a4fa3b21434c0db49a346/19feb97bd30746049f859ccc41fc231b.xml |
| agent\_check | negative\_values | 通过 | evidence/f86e96c47fa742b8ae9d054ec366b6ba/bac7e43f7d6743d3ac3c26919bf2d33a.xml |
| agent\_check | positive\_values | 通过 | evidence/f86e96c47fa742b8ae9d054ec366b6ba/bd15a795436b4eefa66dc0a8b0b66ebc.xml |
| agent\_check | empty\_values | 通过 | evidence/f86e96c47fa742b8ae9d054ec366b6ba/a398b931cd8a41f2b3db4ecc2fa7f8bb.xml |
| agent\_check | mixed\_values | 通过 | evidence/f86e96c47fa742b8ae9d054ec366b6ba/942a19932a97417692fa86fbc4ec59f4.xml |
| independent | negative\_values | 通过 | evidence/b8e762d952864aa898517397e46a9327/c1765636ae284c1ea9c417ef5f1752ca.xml |
| independent | positive\_values | 通过 | evidence/b8e762d952864aa898517397e46a9327/42b1c08fc4f341ba816769529867d6c7.xml |
| independent | empty\_values | 通过 | evidence/b8e762d952864aa898517397e46a9327/01850c246ec54a2cb5307e4e5a8a003f.xml |
| independent | mixed\_values | 通过 | evidence/b8e762d952864aa898517397e46a9327/bea0132d18ec4dbdb85acabdaadaba49.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/5d2631d69add4c9d922f9dddf7bf1198/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/e31b3d70a2bc4f219da5aec235e2fbe3/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/41f32eb004b34791becf26a5d26a8bcc/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/aa84628a02254f62a92fbe7a3ee68974/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/68b59bd11cf94174921b9d5cd4e62203/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/820acf30b53a4fa3b21434c0db49a346-5baa4afc20ab48e9a613f0b1af3f1963.xml --timeout 60.000000 | exited | 8 | logs/4aa6da6203d94249a63794035372e0c7/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/820acf30b53a4fa3b21434c0db49a346-5baa4afc20ab48e9a613f0b1af3f1963.xml | exited | 0 | logs/f15376d10a60410e9fdd82d823f63b8b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/820acf30b53a4fa3b21434c0db49a346-9d22546da8b648b0ab27e2fdc1cc5a70.xml --timeout 60.000000 | exited | 0 | logs/a064dbe510dc4dde9e2858053e16690c/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/820acf30b53a4fa3b21434c0db49a346-9d22546da8b648b0ab27e2fdc1cc5a70.xml | exited | 0 | logs/d4b4ba0b108841b882211371e3d603de/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/820acf30b53a4fa3b21434c0db49a346-53ea1cacefc7451b8daab4cd5aebb19f.xml --timeout 60.000000 | exited | 0 | logs/c0c15bdf0e88466b8c32ee694c044b67/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/820acf30b53a4fa3b21434c0db49a346-53ea1cacefc7451b8daab4cd5aebb19f.xml | exited | 0 | logs/054b4d3014f54f12a3143caf2aa3222d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/820acf30b53a4fa3b21434c0db49a346-19feb97bd30746049f859ccc41fc231b.xml --timeout 60.000000 | exited | 0 | logs/af35dce1a08e46bea7d599de545d513a/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/820acf30b53a4fa3b21434c0db49a346-19feb97bd30746049f859ccc41fc231b.xml | exited | 0 | logs/42ccde28cd4b4c509263f15032968989/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/ce93490dd1e94398a0b705167e8fcd3a/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/31e8a86248054147880d5a13678b1949/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/9bae23ccd7b84e24be6f1ef64f240452/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/03a6869d41cb4c12a861d2bf139c05cb/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/7252d1445bd244a6a5ce858a3f2c92cf/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/f86e96c47fa742b8ae9d054ec366b6ba-bac7e43f7d6743d3ac3c26919bf2d33a.xml --timeout 60.000000 | exited | 0 | logs/858405c35e6742cfb55506754680e6ad/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f86e96c47fa742b8ae9d054ec366b6ba-bac7e43f7d6743d3ac3c26919bf2d33a.xml | exited | 0 | logs/7f14fadd460748f094fd02dcdb62483c/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/f86e96c47fa742b8ae9d054ec366b6ba-bd15a795436b4eefa66dc0a8b0b66ebc.xml --timeout 60.000000 | exited | 0 | logs/20d78938b323499cbecf364edaccef7c/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f86e96c47fa742b8ae9d054ec366b6ba-bd15a795436b4eefa66dc0a8b0b66ebc.xml | exited | 0 | logs/8b59ac0d36124749963f7b253ec99fa3/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/f86e96c47fa742b8ae9d054ec366b6ba-a398b931cd8a41f2b3db4ecc2fa7f8bb.xml --timeout 60.000000 | exited | 0 | logs/d97a87e81c1643529c33e6adc25eaebb/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f86e96c47fa742b8ae9d054ec366b6ba-a398b931cd8a41f2b3db4ecc2fa7f8bb.xml | exited | 0 | logs/cc2b71b81a6e4304ac5a0709ffb57d70/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/f86e96c47fa742b8ae9d054ec366b6ba-942a19932a97417692fa86fbc4ec59f4.xml --timeout 60.000000 | exited | 0 | logs/b96393cf913d4f7a80459475c1a0918b/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f86e96c47fa742b8ae9d054ec366b6ba-942a19932a97417692fa86fbc4ec59f4.xml | exited | 0 | logs/5a209591b9a14e27a9eafc6c7223a642/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/ffb36a6eabda45fd980aec4ec0f912a1/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/d44751880db241da9e8b0d79e313109f/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/770da60c4dae4dd7a76a458b1689b444/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/f47adb04096d49d9b44bb53a31800043/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/a143e87e11c64bc3a9fd88b17411f68a/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/b8e762d952864aa898517397e46a9327-c1765636ae284c1ea9c417ef5f1752ca.xml --timeout 60.000000 | exited | 0 | logs/fa175cb5f7ca4446b9266266325aeed6/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b8e762d952864aa898517397e46a9327-c1765636ae284c1ea9c417ef5f1752ca.xml | exited | 0 | logs/f0e43bf1d2014d52b1b1cd2b5cb22542/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/b8e762d952864aa898517397e46a9327-42b1c08fc4f341ba816769529867d6c7.xml --timeout 60.000000 | exited | 0 | logs/73ab125b59844f3dac7b04d1ffa573b1/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b8e762d952864aa898517397e46a9327-42b1c08fc4f341ba816769529867d6c7.xml | exited | 0 | logs/98be2fcfea7f4097bba3fa67e41f00dd/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/b8e762d952864aa898517397e46a9327-01850c246ec54a2cb5307e4e5a8a003f.xml --timeout 60.000000 | exited | 0 | logs/e214ac146d4e48f0844480330386ee86/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b8e762d952864aa898517397e46a9327-01850c246ec54a2cb5307e4e5a8a003f.xml | exited | 0 | logs/14e7b4edc65242c1a80b97e182719ff0/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/b8e762d952864aa898517397e46a9327-bea0132d18ec4dbdb85acabdaadaba49.xml --timeout 60.000000 | exited | 0 | logs/affbe3b8d12b46c4a32b095b6a6d702d/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b8e762d952864aa898517397e46a9327-bea0132d18ec4dbdb85acabdaadaba49.xml | exited | 0 | logs/c64bb9da17f244cd9f5440c1b4880987/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
