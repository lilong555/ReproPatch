# ReproPatch 4d1391b7d15e44c8b81a7bba741387ce

任务：negative-maximum
入口：run
结局：**BUDGET\_EXHAUSTED**
原因：TOOL\_BUDGET
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：70a032786108d8624acac5330bd58732cdb7b00f
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：4.144 秒
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
| baseline | negative\_values | 失败 | evidence/f03665f9fcf84491b5d8aa05e03fd669/b56695a5c9e24c14821c01317676f4a5.xml |
| baseline | positive\_values | 通过 | evidence/f03665f9fcf84491b5d8aa05e03fd669/40c832c6dd6a4327a9ef220809e7dc4d.xml |
| baseline | empty\_values | 通过 | evidence/f03665f9fcf84491b5d8aa05e03fd669/d93059aa282847829be5569e74659c09.xml |
| baseline | mixed\_values | 通过 | evidence/f03665f9fcf84491b5d8aa05e03fd669/636d04a5457f49f48ef4d62b008150c8.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/48b95afef5f646bdb65c9ef88f9060e5/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/9b59f06e55d24e5290e1c53bc6ef586a/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/f774a55a009040e486bb7e3249d20d9c/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/f8094303975e4a0181f8370ba2564e98/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/ebffea808cb34a68b7269ce34204f77b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/f03665f9fcf84491b5d8aa05e03fd669-b56695a5c9e24c14821c01317676f4a5.xml --timeout 120.000000 | exited | 8 | logs/3de5eac422214c4ba3cbba1d9521d191/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f03665f9fcf84491b5d8aa05e03fd669-b56695a5c9e24c14821c01317676f4a5.xml | exited | 0 | logs/38cfbf3ec37c4b118857b0fa637d9d98/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/f03665f9fcf84491b5d8aa05e03fd669-40c832c6dd6a4327a9ef220809e7dc4d.xml --timeout 120.000000 | exited | 0 | logs/ae572bd4bbf94ea284cb4a8db1cbcc4e/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f03665f9fcf84491b5d8aa05e03fd669-40c832c6dd6a4327a9ef220809e7dc4d.xml | exited | 0 | logs/151e5749a41b44fb94042bbcfa4a1457/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/f03665f9fcf84491b5d8aa05e03fd669-d93059aa282847829be5569e74659c09.xml --timeout 120.000000 | exited | 0 | logs/b759a4d2cfff4b0f9fcd0a893637d4c6/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f03665f9fcf84491b5d8aa05e03fd669-d93059aa282847829be5569e74659c09.xml | exited | 0 | logs/02e9e2ec37dd4062aed1ddbb407f90e8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/f03665f9fcf84491b5d8aa05e03fd669-636d04a5457f49f48ef4d62b008150c8.xml --timeout 120.000000 | exited | 0 | logs/752b8d79d5ad4c13986669f84463b2be/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f03665f9fcf84491b5d8aa05e03fd669-636d04a5457f49f48ef4d62b008150c8.xml | exited | 0 | logs/7f99fb4a2ff14b4ea831b3ac74369c39/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
