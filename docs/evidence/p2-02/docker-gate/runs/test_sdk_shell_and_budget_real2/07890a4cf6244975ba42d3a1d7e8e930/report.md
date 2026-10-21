# ReproPatch 07890a4cf6244975ba42d3a1d7e8e930

任务：negative-maximum
入口：run
结局：**BUDGET\_EXHAUSTED**
原因：TOOL\_BUDGET
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：0203072bcea492a22355b56af4f49ef6b8f0f7e8
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：3.831 秒
模型步骤：1；准入工具：0
模型停止原因：TOOL\_BUDGET
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：44


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/4023e4c4f69d4abba1aa1d10efd72b1f/11da9b82e52f47a2b518900263d1df7f.xml |
| baseline | positive\_values | 通过 | evidence/4023e4c4f69d4abba1aa1d10efd72b1f/08531edb1f1146e483c069991f7725b8.xml |
| baseline | empty\_values | 通过 | evidence/4023e4c4f69d4abba1aa1d10efd72b1f/6964b6bbceaf4b72a5e30c1490d5ee05.xml |
| baseline | mixed\_values | 通过 | evidence/4023e4c4f69d4abba1aa1d10efd72b1f/2a1b8b1dab11447f8c6e535ed4002556.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/37f649eab4494e1d88d73c66187504d8/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/6c06c18167634fb095f3b0d08bd8a969/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/16abc3ebc85e481c9396c715f4492707/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/5abdfdb13b0947a989efa69211bab7d4/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/ef39e558806346ec94813836f4d062a7/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/4023e4c4f69d4abba1aa1d10efd72b1f-11da9b82e52f47a2b518900263d1df7f.xml --timeout 120.000000 | exited | 8 | logs/d4c22f33802c4ae38cf1d5111f08d139/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4023e4c4f69d4abba1aa1d10efd72b1f-11da9b82e52f47a2b518900263d1df7f.xml | exited | 0 | logs/52a4f3216fd94629b0e6e7fff66391a3/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/4023e4c4f69d4abba1aa1d10efd72b1f-08531edb1f1146e483c069991f7725b8.xml --timeout 120.000000 | exited | 0 | logs/45c16ad4d3df4803991adca0f5ca56c7/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4023e4c4f69d4abba1aa1d10efd72b1f-08531edb1f1146e483c069991f7725b8.xml | exited | 0 | logs/43bab81bab8a4c8cbef0503062c4cd2b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/4023e4c4f69d4abba1aa1d10efd72b1f-6964b6bbceaf4b72a5e30c1490d5ee05.xml --timeout 120.000000 | exited | 0 | logs/1a37fb8e009047fe8571488c545d4de7/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4023e4c4f69d4abba1aa1d10efd72b1f-6964b6bbceaf4b72a5e30c1490d5ee05.xml | exited | 0 | logs/5e507c620c6046c6b569eb4e8fa199b0/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/4023e4c4f69d4abba1aa1d10efd72b1f-2a1b8b1dab11447f8c6e535ed4002556.xml --timeout 120.000000 | exited | 0 | logs/6c441e2b661143b88597c95d3d405dc3/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4023e4c4f69d4abba1aa1d10efd72b1f-2a1b8b1dab11447f8c6e535ed4002556.xml | exited | 0 | logs/5e69c1adb2444f658aa0a6763ab0b824/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
