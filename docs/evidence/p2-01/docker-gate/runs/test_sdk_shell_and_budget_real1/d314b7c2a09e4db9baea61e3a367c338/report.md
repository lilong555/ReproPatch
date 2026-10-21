# ReproPatch d314b7c2a09e4db9baea61e3a367c338

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：f24710a09e2da15ddf490cd90e2b99fc689ba2ed
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：10.245 秒
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
| baseline | negative\_values | 失败 | evidence/07daccd88c6f417cac60a71563307d29/7cafef4e8bfc443d9c9f9d7d1589033f.xml |
| baseline | positive\_values | 通过 | evidence/07daccd88c6f417cac60a71563307d29/bd6d97d43db3483180cedd1666a370b6.xml |
| baseline | empty\_values | 通过 | evidence/07daccd88c6f417cac60a71563307d29/db7443bd18484ccf93f98ffc1edd92be.xml |
| baseline | mixed\_values | 通过 | evidence/07daccd88c6f417cac60a71563307d29/46571233d8c54391a53aa9dde543cbc0.xml |
| independent | negative\_values | 通过 | evidence/5638fae0ec774ee3b26184fd17932545/c0993dc9f96241c5be66b8c6b458b044.xml |
| independent | positive\_values | 通过 | evidence/5638fae0ec774ee3b26184fd17932545/3648639cfc7d438b966c2c1db1395c29.xml |
| independent | empty\_values | 通过 | evidence/5638fae0ec774ee3b26184fd17932545/d55788d9cc7149c1adb51b17504a5515.xml |
| independent | mixed\_values | 通过 | evidence/5638fae0ec774ee3b26184fd17932545/3398eebce3d64c78a94865c7018bcec9.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/4bbd67acdd1d437599639ca64ff05c2b/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/1ddb4304542e4dd99ac9d96436c46812/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/b3492946d1bd4db495b53cf7964175ed/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/ffe5b713468f43779630bee6e94cb141/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/368dd17ff2244d418774c22a676650a3/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/07daccd88c6f417cac60a71563307d29-7cafef4e8bfc443d9c9f9d7d1589033f.xml --timeout 120.000000 | exited | 8 | logs/6b7ec1658d404f1ca80b9e177f75a973/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/07daccd88c6f417cac60a71563307d29-7cafef4e8bfc443d9c9f9d7d1589033f.xml | exited | 0 | logs/74e19eeda06445498ee653d849129dbd/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/07daccd88c6f417cac60a71563307d29-bd6d97d43db3483180cedd1666a370b6.xml --timeout 120.000000 | exited | 0 | logs/d7511662ca1b470ea95336ba235c245e/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/07daccd88c6f417cac60a71563307d29-bd6d97d43db3483180cedd1666a370b6.xml | exited | 0 | logs/c4f150e8b1dc408e937f573f8299c079/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/07daccd88c6f417cac60a71563307d29-db7443bd18484ccf93f98ffc1edd92be.xml --timeout 120.000000 | exited | 0 | logs/c97fd661775242918ca0007b9575e3f4/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/07daccd88c6f417cac60a71563307d29-db7443bd18484ccf93f98ffc1edd92be.xml | exited | 0 | logs/c9ac750494f840f38a2d621276a5690b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/07daccd88c6f417cac60a71563307d29-46571233d8c54391a53aa9dde543cbc0.xml --timeout 120.000000 | exited | 0 | logs/fe0a094b8e784290b8162466f18d3332/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/07daccd88c6f417cac60a71563307d29-46571233d8c54391a53aa9dde543cbc0.xml | exited | 0 | logs/1abd39c7f6bf455495a8ded891e3ebb4/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/50c868ea9b4e42b39e0342bca1cc8f95/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/7d199fedacec4daf8cf2609c363e055e/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/9fa7c36dc5f645aba5ba0e08e503c817/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/328c275543184f44969211e8b8223049/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/ab4b481b6e0542efb256161224554c53/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/5638fae0ec774ee3b26184fd17932545-c0993dc9f96241c5be66b8c6b458b044.xml --timeout 120.000000 | exited | 0 | logs/cbf62da10c2b4e8a9d3866322a3ee7ef/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5638fae0ec774ee3b26184fd17932545-c0993dc9f96241c5be66b8c6b458b044.xml | exited | 0 | logs/177226afcef74493b867fbda38a25a0f/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/5638fae0ec774ee3b26184fd17932545-3648639cfc7d438b966c2c1db1395c29.xml --timeout 120.000000 | exited | 0 | logs/8d606726b78c48d4948fa8e61ff6b87a/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5638fae0ec774ee3b26184fd17932545-3648639cfc7d438b966c2c1db1395c29.xml | exited | 0 | logs/05f3bd477e954fa6849fa3095bce34be/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/5638fae0ec774ee3b26184fd17932545-d55788d9cc7149c1adb51b17504a5515.xml --timeout 120.000000 | exited | 0 | logs/1e836ab473a54f2092162697d644b62e/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5638fae0ec774ee3b26184fd17932545-d55788d9cc7149c1adb51b17504a5515.xml | exited | 0 | logs/ac11dff4f3584c6ab878c6a21318f5b0/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/5638fae0ec774ee3b26184fd17932545-3398eebce3d64c78a94865c7018bcec9.xml --timeout 120.000000 | exited | 0 | logs/64d0da51ba4f43ab97314619c054a2e1/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5638fae0ec774ee3b26184fd17932545-3398eebce3d64c78a94865c7018bcec9.xml | exited | 0 | logs/b23de252bf2e401e9976ed861f220066/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
