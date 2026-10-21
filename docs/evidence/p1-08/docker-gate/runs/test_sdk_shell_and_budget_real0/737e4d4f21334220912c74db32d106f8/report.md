# ReproPatch 737e4d4f21334220912c74db32d106f8

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：1effd1a194c185344be997ba2a044dbb86d32c5e
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：9.162 秒
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
| baseline | negative\_values | 失败 | evidence/e378b4b8cd5d46b4adc004140c403d2f/2a70a1c5ef324380bd14cd7135ed6445.xml |
| baseline | positive\_values | 通过 | evidence/e378b4b8cd5d46b4adc004140c403d2f/d2ab42c2ce274332b55cf81ab0531e65.xml |
| baseline | empty\_values | 通过 | evidence/e378b4b8cd5d46b4adc004140c403d2f/0d0991b6ba7f49fa800cd5fd408035fb.xml |
| baseline | mixed\_values | 通过 | evidence/e378b4b8cd5d46b4adc004140c403d2f/e7737340219546ada4e9e9e73f92be19.xml |
| independent | negative\_values | 通过 | evidence/a9be1b7aa80c4721901fb5a1e88ff94d/431e62cf8f76450188949151bc2b5533.xml |
| independent | positive\_values | 通过 | evidence/a9be1b7aa80c4721901fb5a1e88ff94d/c1b7cb0dea604417bd31054747a7984b.xml |
| independent | empty\_values | 通过 | evidence/a9be1b7aa80c4721901fb5a1e88ff94d/7b1922ca0e154dce9a07fe943a8a0cee.xml |
| independent | mixed\_values | 通过 | evidence/a9be1b7aa80c4721901fb5a1e88ff94d/f2fc4dca150b4c1b81b8a65ca41d709a.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/45263b99c2d54e6fa64c0a42052c2b58/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/8db946a8cc8044f9a64ca1a3bab0478d/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/532ad2476bb34339865906e8f10ba846/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/09bc78ef147e4132a384854d46c4fbcb/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/2afde90f4bc34938802acbfa8f4bfeb6/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/e378b4b8cd5d46b4adc004140c403d2f-2a70a1c5ef324380bd14cd7135ed6445.xml --timeout 120.000000 | exited | 8 | logs/ec5faee52f5d4229beaa4ec4a55c83a2/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e378b4b8cd5d46b4adc004140c403d2f-2a70a1c5ef324380bd14cd7135ed6445.xml | exited | 0 | logs/75f57640b5b0440b9c14b01c97e1e9db/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/e378b4b8cd5d46b4adc004140c403d2f-d2ab42c2ce274332b55cf81ab0531e65.xml --timeout 120.000000 | exited | 0 | logs/4b6a03f142bc460287c1732ec692cc4f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e378b4b8cd5d46b4adc004140c403d2f-d2ab42c2ce274332b55cf81ab0531e65.xml | exited | 0 | logs/77b6d63067f04930a028f8e768c1b72d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/e378b4b8cd5d46b4adc004140c403d2f-0d0991b6ba7f49fa800cd5fd408035fb.xml --timeout 120.000000 | exited | 0 | logs/515abe9d65a64ea4a2296b2804408020/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e378b4b8cd5d46b4adc004140c403d2f-0d0991b6ba7f49fa800cd5fd408035fb.xml | exited | 0 | logs/292df94768b2443cbafa9678d389dd71/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/e378b4b8cd5d46b4adc004140c403d2f-e7737340219546ada4e9e9e73f92be19.xml --timeout 120.000000 | exited | 0 | logs/8fe3f5eace7e4159b4312e5aee7339e7/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e378b4b8cd5d46b4adc004140c403d2f-e7737340219546ada4e9e9e73f92be19.xml | exited | 0 | logs/21f2d4977fad44318c7a6e0233d94f4a/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/379b77bb592f4548ac542886c95ed012/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/38ddf8b10d7a4fceb71395775afb18c0/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/a468a117bb3f4658915aea536007d98b/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/8222d9782c604f1aba3e1848ab4c971d/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/182e5829dfb64f629c91ef80d7e945c5/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/a9be1b7aa80c4721901fb5a1e88ff94d-431e62cf8f76450188949151bc2b5533.xml --timeout 120.000000 | exited | 0 | logs/3c9afe64089645e286ab6b1cf256c015/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a9be1b7aa80c4721901fb5a1e88ff94d-431e62cf8f76450188949151bc2b5533.xml | exited | 0 | logs/8477687076af4cd68bd8b29bf04b4396/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/a9be1b7aa80c4721901fb5a1e88ff94d-c1b7cb0dea604417bd31054747a7984b.xml --timeout 120.000000 | exited | 0 | logs/573c12a00b6f4706966dd64ac19246ef/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a9be1b7aa80c4721901fb5a1e88ff94d-c1b7cb0dea604417bd31054747a7984b.xml | exited | 0 | logs/dc59bd09453f4f728d74551abfdfab92/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/a9be1b7aa80c4721901fb5a1e88ff94d-7b1922ca0e154dce9a07fe943a8a0cee.xml --timeout 120.000000 | exited | 0 | logs/9220ca1009c44432abc6c4e908d05aee/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a9be1b7aa80c4721901fb5a1e88ff94d-7b1922ca0e154dce9a07fe943a8a0cee.xml | exited | 0 | logs/c71aefbec5af4e1b93f5e1f8f605fe70/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/a9be1b7aa80c4721901fb5a1e88ff94d-f2fc4dca150b4c1b81b8a65ca41d709a.xml --timeout 120.000000 | exited | 0 | logs/a81b5818e3164b23b1d5d0662caa557d/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a9be1b7aa80c4721901fb5a1e88ff94d-f2fc4dca150b4c1b81b8a65ca41d709a.xml | exited | 0 | logs/14df46cfc6014a599423b2a842f6b336/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
