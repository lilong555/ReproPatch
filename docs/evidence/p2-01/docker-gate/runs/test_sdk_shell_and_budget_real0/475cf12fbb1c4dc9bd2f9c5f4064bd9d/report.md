# ReproPatch 475cf12fbb1c4dc9bd2f9c5f4064bd9d

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：3231aa5a2fea32da2ad575f4708ba2f2d03b54f7
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：9.227 秒
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
| baseline | negative\_values | 失败 | evidence/ef58eb6a73884e89af20c2db64ca067d/9f045c0ae2a146c38db1b6fde3e47f41.xml |
| baseline | positive\_values | 通过 | evidence/ef58eb6a73884e89af20c2db64ca067d/20f7113bc72d4976a5ab76208c166ad2.xml |
| baseline | empty\_values | 通过 | evidence/ef58eb6a73884e89af20c2db64ca067d/a2c14c9d316b46fca31dbaa8fe8b5a20.xml |
| baseline | mixed\_values | 通过 | evidence/ef58eb6a73884e89af20c2db64ca067d/8ce593029c434b218da0d99a3696a3ee.xml |
| independent | negative\_values | 通过 | evidence/81a06b84a22f44e2b4c30473ff2306ec/6e2216a72e994f73bb378170c151c4c3.xml |
| independent | positive\_values | 通过 | evidence/81a06b84a22f44e2b4c30473ff2306ec/5cb5f31fe0864fc3bcc873ba6b77a26c.xml |
| independent | empty\_values | 通过 | evidence/81a06b84a22f44e2b4c30473ff2306ec/2880667c606d4a4e91b9edbcf5cd61bc.xml |
| independent | mixed\_values | 通过 | evidence/81a06b84a22f44e2b4c30473ff2306ec/7ec40674654940f8805c407afc92cd2e.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/a2aaefd098ef41788636185806aa8f53/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/9ff5c8426fae42d595cc7b453412da9f/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/b9798530e316489b911ef73bac27d0a8/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/b796d240cf254e4a993581ba8c8e9ded/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/03696db67c754ee2bbf6ffcb45cb6af3/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/ef58eb6a73884e89af20c2db64ca067d-9f045c0ae2a146c38db1b6fde3e47f41.xml --timeout 120.000000 | exited | 8 | logs/7a1c949059894640a432caa4ce4cc594/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ef58eb6a73884e89af20c2db64ca067d-9f045c0ae2a146c38db1b6fde3e47f41.xml | exited | 0 | logs/dd0d512a862b4e27b805202ae6c06624/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/ef58eb6a73884e89af20c2db64ca067d-20f7113bc72d4976a5ab76208c166ad2.xml --timeout 120.000000 | exited | 0 | logs/b67e31d441424875971ebc23bba26d17/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ef58eb6a73884e89af20c2db64ca067d-20f7113bc72d4976a5ab76208c166ad2.xml | exited | 0 | logs/f1e2f28beac246708bf8622818d17ded/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/ef58eb6a73884e89af20c2db64ca067d-a2c14c9d316b46fca31dbaa8fe8b5a20.xml --timeout 120.000000 | exited | 0 | logs/673f4a4709f94747a04d03a31626d8d1/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ef58eb6a73884e89af20c2db64ca067d-a2c14c9d316b46fca31dbaa8fe8b5a20.xml | exited | 0 | logs/21ab67ae9fb04e76a3ed33d699e96165/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/ef58eb6a73884e89af20c2db64ca067d-8ce593029c434b218da0d99a3696a3ee.xml --timeout 120.000000 | exited | 0 | logs/9f93f1cece704630875da376dd8c69b8/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ef58eb6a73884e89af20c2db64ca067d-8ce593029c434b218da0d99a3696a3ee.xml | exited | 0 | logs/4f84d223b0cd46d8b4ba54bed2747ba7/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/c0c5a68696bc48ee9b8f6a843b93c381/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/b817f4edc604475e99bb92ce4683f312/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/6bbad20ac06d41f1a52af39778fdf0e0/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/48201f74a19d4534b80c0a97f44800d0/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/735b103905bc4a8588d2811149ffe13f/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/81a06b84a22f44e2b4c30473ff2306ec-6e2216a72e994f73bb378170c151c4c3.xml --timeout 120.000000 | exited | 0 | logs/b71325a9e6b0470aa636c88f9a6f6a49/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/81a06b84a22f44e2b4c30473ff2306ec-6e2216a72e994f73bb378170c151c4c3.xml | exited | 0 | logs/7aa665c862f248c79206a145b143bc26/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/81a06b84a22f44e2b4c30473ff2306ec-5cb5f31fe0864fc3bcc873ba6b77a26c.xml --timeout 120.000000 | exited | 0 | logs/6e8bee38c60f4fc1baa577518b9c3174/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/81a06b84a22f44e2b4c30473ff2306ec-5cb5f31fe0864fc3bcc873ba6b77a26c.xml | exited | 0 | logs/14862308f38e4ac89415ff55dff59452/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/81a06b84a22f44e2b4c30473ff2306ec-2880667c606d4a4e91b9edbcf5cd61bc.xml --timeout 120.000000 | exited | 0 | logs/4e4aed893d8a4c989b50b8dd57c93170/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/81a06b84a22f44e2b4c30473ff2306ec-2880667c606d4a4e91b9edbcf5cd61bc.xml | exited | 0 | logs/b5517587dc41495bb03e376462ee3ec5/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/81a06b84a22f44e2b4c30473ff2306ec-7ec40674654940f8805c407afc92cd2e.xml --timeout 120.000000 | exited | 0 | logs/0b61cc69aacb44b5a826254015701c5c/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/81a06b84a22f44e2b4c30473ff2306ec-7ec40674654940f8805c407afc92cd2e.xml | exited | 0 | logs/918d3afd03e1434face23596fb7b2ac4/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
