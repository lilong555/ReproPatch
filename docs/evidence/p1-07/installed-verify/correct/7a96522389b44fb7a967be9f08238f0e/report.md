# ReproPatch 7a96522389b44fb7a967be9f08238f0e

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.478 秒
模型步骤：0；准入工具：0
模型停止原因：未知
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：否；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：73

外部来源标签（未认证）：fixture

| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/c8ace9c22d724fdbb9fcc0bd6a0d4a16/9909be99c7a94fd893ece00ec63885c6.xml |
| baseline | positive\_values | 通过 | evidence/c8ace9c22d724fdbb9fcc0bd6a0d4a16/7dfa0c26336e488cb3d669c6980701cd.xml |
| baseline | empty\_values | 通过 | evidence/c8ace9c22d724fdbb9fcc0bd6a0d4a16/416cc3ed522342cf8decacee76ed976f.xml |
| baseline | mixed\_values | 通过 | evidence/c8ace9c22d724fdbb9fcc0bd6a0d4a16/b5da441652eb42209fc51df62a1dc1c1.xml |
| independent | negative\_values | 通过 | evidence/a432fd254216470091b69c640f6660b3/120ee2194c7445ea9d6dc6dacb4b9c27.xml |
| independent | positive\_values | 通过 | evidence/a432fd254216470091b69c640f6660b3/f0a1ea4b3bdc469593a84e5f32f589c6.xml |
| independent | empty\_values | 通过 | evidence/a432fd254216470091b69c640f6660b3/622895b735954c0dad4cb9e1c03de34e.xml |
| independent | mixed\_values | 通过 | evidence/a432fd254216470091b69c640f6660b3/fc1519e22653451c8dfcbdf670e5fcc8.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/b30b74f206d74d1fa2176a7ebbd59a4b/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/080f01c948994ad2b90c5cb036aa0e5f/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/650f60693c3144c893af3f59670c17f5/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/26b5e328ba3b46ae803940abb458e75b/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/9404caad12a741d295ef5cdc4501a066/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/c8ace9c22d724fdbb9fcc0bd6a0d4a16-9909be99c7a94fd893ece00ec63885c6.xml --timeout 120.000000 | exited | 8 | logs/5f5e3686a18d448e9cb23f94e963e4fd/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c8ace9c22d724fdbb9fcc0bd6a0d4a16-9909be99c7a94fd893ece00ec63885c6.xml | exited | 0 | logs/2e4b8d1d1c3f40978f8185f17d8ad015/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/c8ace9c22d724fdbb9fcc0bd6a0d4a16-7dfa0c26336e488cb3d669c6980701cd.xml --timeout 120.000000 | exited | 0 | logs/07ec43e6c453407ebde45ed45825970d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c8ace9c22d724fdbb9fcc0bd6a0d4a16-7dfa0c26336e488cb3d669c6980701cd.xml | exited | 0 | logs/9c8afd2b1bc84c02a4d822ff87ca894a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/c8ace9c22d724fdbb9fcc0bd6a0d4a16-416cc3ed522342cf8decacee76ed976f.xml --timeout 120.000000 | exited | 0 | logs/4d4c1f5e970d48379202a98bfaa62363/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c8ace9c22d724fdbb9fcc0bd6a0d4a16-416cc3ed522342cf8decacee76ed976f.xml | exited | 0 | logs/ac8eaa3b7067473199f4b16471afdc3f/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/c8ace9c22d724fdbb9fcc0bd6a0d4a16-b5da441652eb42209fc51df62a1dc1c1.xml --timeout 120.000000 | exited | 0 | logs/455ae02015dc4e20b9d38ec5c6b3359b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c8ace9c22d724fdbb9fcc0bd6a0d4a16-b5da441652eb42209fc51df62a1dc1c1.xml | exited | 0 | logs/a667fd3e92b94600afa581a67a184d34/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/20c44689b02d4fd689fd96f6990c72d1/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/b4f10e35dd1945a3ae61881adcc98b0b/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/22153a167f3245c6be8fbcf32d5b25d7/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/62de191600464bb39661712a89ec6aab/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/dfda4384ab2c4197bc33394e764226cf/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/a432fd254216470091b69c640f6660b3-120ee2194c7445ea9d6dc6dacb4b9c27.xml --timeout 120.000000 | exited | 0 | logs/29c55ac7aaa9482d9b281b58a9685593/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a432fd254216470091b69c640f6660b3-120ee2194c7445ea9d6dc6dacb4b9c27.xml | exited | 0 | logs/8c25c646d85b42edb5233dd565f490b0/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/a432fd254216470091b69c640f6660b3-f0a1ea4b3bdc469593a84e5f32f589c6.xml --timeout 120.000000 | exited | 0 | logs/b69983877c004e45b68d39abe4cf03a2/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a432fd254216470091b69c640f6660b3-f0a1ea4b3bdc469593a84e5f32f589c6.xml | exited | 0 | logs/e2b15c8a33a547a48ef6484c28ad339a/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/a432fd254216470091b69c640f6660b3-622895b735954c0dad4cb9e1c03de34e.xml --timeout 120.000000 | exited | 0 | logs/54be6eaf5d4943c092e5e69d1dd77397/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a432fd254216470091b69c640f6660b3-622895b735954c0dad4cb9e1c03de34e.xml | exited | 0 | logs/d4a42147d346470cb99c1b9f65400524/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/a432fd254216470091b69c640f6660b3-fc1519e22653451c8dfcbdf670e5fcc8.xml --timeout 120.000000 | exited | 0 | logs/96702be29e8e4bb1b8118b4f8fcc0e1a/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a432fd254216470091b69c640f6660b3-fc1519e22653451c8dfcbdf670e5fcc8.xml | exited | 0 | logs/6e17a5e1004549c99162a16aa3b6ccfb/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
