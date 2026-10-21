# ReproPatch f8b6b43a5a0b422c91886e9236e97d31

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：a3eb4322ddda60c6b4a7e8669e04d46a722d8622
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：9.153 秒
模型步骤：3；准入工具：2
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：94


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/11af900b2dcd401c94a428455467e071/70cf7242ef934a7cb37914170553f106.xml |
| baseline | positive\_values | 通过 | evidence/11af900b2dcd401c94a428455467e071/3567f6379eb04d7d9d3c079cd515c153.xml |
| baseline | empty\_values | 通过 | evidence/11af900b2dcd401c94a428455467e071/11ee48118e9a49fe97c2b641ac31739a.xml |
| baseline | mixed\_values | 通过 | evidence/11af900b2dcd401c94a428455467e071/bae4cc51d42c49bb936aa04f84a38ed5.xml |
| independent | negative\_values | 通过 | evidence/76fd05d83aa841edb6a9ac50e55925ad/a1ad072848a549f68d8090508c527569.xml |
| independent | positive\_values | 通过 | evidence/76fd05d83aa841edb6a9ac50e55925ad/3c143f7608f2485d9029af7c740d9e57.xml |
| independent | empty\_values | 通过 | evidence/76fd05d83aa841edb6a9ac50e55925ad/4273b571c8b948408f6d70de8e5889b2.xml |
| independent | mixed\_values | 通过 | evidence/76fd05d83aa841edb6a9ac50e55925ad/f747b7cca73149199132c87ba1130f2f.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/a94e512b9cc34b25b8c986ee99d03fd3/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/44e19cf5e2574c5ab67d641bbce29aba/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/d5f951356baf4d068d39a189fd04aeb5/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/c8f38b79a55d45208b8e552afba1351d/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/f8532d70d7e24abd804d11ab4ea34922/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/11af900b2dcd401c94a428455467e071-70cf7242ef934a7cb37914170553f106.xml --timeout 120.000000 | exited | 8 | logs/1b694fd61aab4bd4b74415a8423f8830/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/11af900b2dcd401c94a428455467e071-70cf7242ef934a7cb37914170553f106.xml | exited | 0 | logs/7abd3d2b7fb845d8a1037cc39a7cfd7f/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/11af900b2dcd401c94a428455467e071-3567f6379eb04d7d9d3c079cd515c153.xml --timeout 120.000000 | exited | 0 | logs/6aaa95e317754173a5741c3c8b1ffd52/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/11af900b2dcd401c94a428455467e071-3567f6379eb04d7d9d3c079cd515c153.xml | exited | 0 | logs/1203e627840a4bdd89bcc616d47aa461/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/11af900b2dcd401c94a428455467e071-11ee48118e9a49fe97c2b641ac31739a.xml --timeout 120.000000 | exited | 0 | logs/226fe9c8a8bb4b0ea5615befa58124c2/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/11af900b2dcd401c94a428455467e071-11ee48118e9a49fe97c2b641ac31739a.xml | exited | 0 | logs/3b66fff706fb431194b76c45bcbff151/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/11af900b2dcd401c94a428455467e071-bae4cc51d42c49bb936aa04f84a38ed5.xml --timeout 120.000000 | exited | 0 | logs/903628ad4c8d48d3879c175c26ee775e/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/11af900b2dcd401c94a428455467e071-bae4cc51d42c49bb936aa04f84a38ed5.xml | exited | 0 | logs/9ca9480c40534c37bf4b7b3a2c92ec3c/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/1bf46fb52fd94572b121c5cba6055166/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/5ce56515347148bea86cb2e560228945/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/ea4e8c6486af4995b5291a644c8d8ab7/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/4fb152eed6a0482f8fb8bf0fb64dbaa8/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/0e0359ad7a944486bf7185d2154f1cad/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/76fd05d83aa841edb6a9ac50e55925ad-a1ad072848a549f68d8090508c527569.xml --timeout 120.000000 | exited | 0 | logs/93428edfcdb94439b9d465cf4e7e7498/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/76fd05d83aa841edb6a9ac50e55925ad-a1ad072848a549f68d8090508c527569.xml | exited | 0 | logs/cc5f7329bbb74d1c99c2933f7f985bfe/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/76fd05d83aa841edb6a9ac50e55925ad-3c143f7608f2485d9029af7c740d9e57.xml --timeout 120.000000 | exited | 0 | logs/184278c1abf841cbbb90523a336ce456/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/76fd05d83aa841edb6a9ac50e55925ad-3c143f7608f2485d9029af7c740d9e57.xml | exited | 0 | logs/ffac14e1f3b74dd18734779109698e42/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/76fd05d83aa841edb6a9ac50e55925ad-4273b571c8b948408f6d70de8e5889b2.xml --timeout 120.000000 | exited | 0 | logs/2b2672c40fab41c0a9a125c73e063936/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/76fd05d83aa841edb6a9ac50e55925ad-4273b571c8b948408f6d70de8e5889b2.xml | exited | 0 | logs/df9f827db58e41fca983cd56b12a24c5/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/76fd05d83aa841edb6a9ac50e55925ad-f747b7cca73149199132c87ba1130f2f.xml --timeout 120.000000 | exited | 0 | logs/0c5cdd642fed40adb8fdf0cee1f68708/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/76fd05d83aa841edb6a9ac50e55925ad-f747b7cca73149199132c87ba1130f2f.xml | exited | 0 | logs/f7005af81cf64763a324d924604b4d05/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
