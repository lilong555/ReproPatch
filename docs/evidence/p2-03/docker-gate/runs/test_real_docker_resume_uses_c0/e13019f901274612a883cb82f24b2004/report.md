# ReproPatch e13019f901274612a883cb82f24b2004

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：510738b06708c0593e43584bffb61625bec72f90
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：14.474 秒
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
| baseline | negative\_values | 失败 | evidence/6d92e671da5c4fa593d7309b2ec11aae/996873d897cd429dbb1b9af1bb1645ee.xml |
| baseline | positive\_values | 通过 | evidence/6d92e671da5c4fa593d7309b2ec11aae/56d97eb9c92942589eb3fd2346bae7fd.xml |
| baseline | empty\_values | 通过 | evidence/6d92e671da5c4fa593d7309b2ec11aae/c2de32be2f0342caa17342351bce4485.xml |
| baseline | mixed\_values | 通过 | evidence/6d92e671da5c4fa593d7309b2ec11aae/29366e89827449c7af8fe4f19f2290af.xml |
| agent\_check | negative\_values | 通过 | evidence/4ae68301ecbd4c26a76e6fb0bf7c566b/d873e3656c1b486d95fde2965734e167.xml |
| agent\_check | positive\_values | 通过 | evidence/4ae68301ecbd4c26a76e6fb0bf7c566b/6fee06bfed8d4c94bf3c61f441052113.xml |
| agent\_check | empty\_values | 通过 | evidence/4ae68301ecbd4c26a76e6fb0bf7c566b/3ad8a33e31e24ea49c495ad97aeabd88.xml |
| agent\_check | mixed\_values | 通过 | evidence/4ae68301ecbd4c26a76e6fb0bf7c566b/7a874d76c2a7464b99779a38281239d0.xml |
| independent | negative\_values | 通过 | evidence/dd72d531771e401a982fa33b781cb79b/b9ea0cafa51041cc9711dd69ad114d9c.xml |
| independent | positive\_values | 通过 | evidence/dd72d531771e401a982fa33b781cb79b/74d5e833ba0041a6a48f76a93663f28e.xml |
| independent | empty\_values | 通过 | evidence/dd72d531771e401a982fa33b781cb79b/a04baa3bb5bb44c896df8b8707bf33c3.xml |
| independent | mixed\_values | 通过 | evidence/dd72d531771e401a982fa33b781cb79b/91a8c3e00ff74fac903434c4f1803263.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/5f2f2e1125f74e4e8f0a7cadf5d8bd0f/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/fd6b76cd567c4624a28863e9d324592f/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/2204e2d0ee584d579a7dd60e551f394b/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/266418cd81334e6288197a41351dd065/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/b64d6996499c4d158475bca64f5c1889/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/6d92e671da5c4fa593d7309b2ec11aae-996873d897cd429dbb1b9af1bb1645ee.xml --timeout 120.000000 | exited | 8 | logs/1936c52ea7de45108403959b837c5d8d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/6d92e671da5c4fa593d7309b2ec11aae-996873d897cd429dbb1b9af1bb1645ee.xml | exited | 0 | logs/1c19ed063d964db89a7bdad80c59ffa5/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/6d92e671da5c4fa593d7309b2ec11aae-56d97eb9c92942589eb3fd2346bae7fd.xml --timeout 120.000000 | exited | 0 | logs/68eef85ba7a941a784d71a2b56aa2889/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/6d92e671da5c4fa593d7309b2ec11aae-56d97eb9c92942589eb3fd2346bae7fd.xml | exited | 0 | logs/5db48a8689764cfaa6572cb1febcc441/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/6d92e671da5c4fa593d7309b2ec11aae-c2de32be2f0342caa17342351bce4485.xml --timeout 120.000000 | exited | 0 | logs/1d5bf48a6ea94d019afdee0378da2d4c/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/6d92e671da5c4fa593d7309b2ec11aae-c2de32be2f0342caa17342351bce4485.xml | exited | 0 | logs/578d56d33df843a5a5cc3bc603fd70f8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/6d92e671da5c4fa593d7309b2ec11aae-29366e89827449c7af8fe4f19f2290af.xml --timeout 120.000000 | exited | 0 | logs/d6cf40f7eb1d48a186a975b92a26155f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/6d92e671da5c4fa593d7309b2ec11aae-29366e89827449c7af8fe4f19f2290af.xml | exited | 0 | logs/7e263a050a084b759fcab077cb452d6e/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/4bec1796289f4dc1968e9eabd25fad48/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/24853c7e75c44e2892b35ad1eb7b1aaf/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/6a3d00be3390461eb660870b7acc2dba/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/07327332b64d4f59b257df80d76f2739/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/0a0b1458ac8e41afae52da0897a413f0/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/4ae68301ecbd4c26a76e6fb0bf7c566b-d873e3656c1b486d95fde2965734e167.xml --timeout 120.000000 | exited | 0 | logs/8cc3893c57e94025ab5fda235090035f/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4ae68301ecbd4c26a76e6fb0bf7c566b-d873e3656c1b486d95fde2965734e167.xml | exited | 0 | logs/752ce400aa1f4fe59985e4f200b7bc3d/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/4ae68301ecbd4c26a76e6fb0bf7c566b-6fee06bfed8d4c94bf3c61f441052113.xml --timeout 120.000000 | exited | 0 | logs/6c72237ac23b4145acc0ce8416abc842/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4ae68301ecbd4c26a76e6fb0bf7c566b-6fee06bfed8d4c94bf3c61f441052113.xml | exited | 0 | logs/4cc0ec800123462dbdfce6cef36f7511/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/4ae68301ecbd4c26a76e6fb0bf7c566b-3ad8a33e31e24ea49c495ad97aeabd88.xml --timeout 120.000000 | exited | 0 | logs/ccc5e72cda164b76b3d919b054019a14/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4ae68301ecbd4c26a76e6fb0bf7c566b-3ad8a33e31e24ea49c495ad97aeabd88.xml | exited | 0 | logs/a74d140d2b8a46738e391488f62b7801/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/4ae68301ecbd4c26a76e6fb0bf7c566b-7a874d76c2a7464b99779a38281239d0.xml --timeout 120.000000 | exited | 0 | logs/285a15e140a04a09a78f81fe5c01d274/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4ae68301ecbd4c26a76e6fb0bf7c566b-7a874d76c2a7464b99779a38281239d0.xml | exited | 0 | logs/d41bcf989313497ead4ec2ef5a0a93e7/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/fe605d4c97ba49b7b4b8b60b1ac8bc5f/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/b81457aaa45b432692039cd9b69fb343/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/6123456b3d6b41828528b96537ec3229/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/ee4f45a23c5c41449044f91c1cd42f5f/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/415526c91ec843f7abda1e55d004490d/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/dd72d531771e401a982fa33b781cb79b-b9ea0cafa51041cc9711dd69ad114d9c.xml --timeout 120.000000 | exited | 0 | logs/118ab72c02234146b70c1e4e779891cd/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/dd72d531771e401a982fa33b781cb79b-b9ea0cafa51041cc9711dd69ad114d9c.xml | exited | 0 | logs/ca41fffee82045148e58149b4f1740aa/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/dd72d531771e401a982fa33b781cb79b-74d5e833ba0041a6a48f76a93663f28e.xml --timeout 120.000000 | exited | 0 | logs/2963754227ca4c6893101dd3925bf570/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/dd72d531771e401a982fa33b781cb79b-74d5e833ba0041a6a48f76a93663f28e.xml | exited | 0 | logs/7ce8d52379b24265bfa521a379f538b7/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/dd72d531771e401a982fa33b781cb79b-a04baa3bb5bb44c896df8b8707bf33c3.xml --timeout 120.000000 | exited | 0 | logs/b5607393465b428296033d0ea9d0ee59/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/dd72d531771e401a982fa33b781cb79b-a04baa3bb5bb44c896df8b8707bf33c3.xml | exited | 0 | logs/fdf68eabb4f24f5485cc162bf4fe8471/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/dd72d531771e401a982fa33b781cb79b-91a8c3e00ff74fac903434c4f1803263.xml --timeout 120.000000 | exited | 0 | logs/005d79553ee24a49bd3b25543f82973d/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/dd72d531771e401a982fa33b781cb79b-91a8c3e00ff74fac903434c4f1803263.xml | exited | 0 | logs/9371a4532728456b931fc0d7d5104662/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
