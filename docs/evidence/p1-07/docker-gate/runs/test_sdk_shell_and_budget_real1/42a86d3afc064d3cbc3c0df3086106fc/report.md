# ReproPatch 42a86d3afc064d3cbc3c0df3086106fc

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：7ec26966062315a3696b62686da383cad6646e6b
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：10.374 秒
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
| baseline | negative\_values | 失败 | evidence/93a18cacf3694678afad5e5f908ed65d/82bc672ccf75452bbef178811b7694be.xml |
| baseline | positive\_values | 通过 | evidence/93a18cacf3694678afad5e5f908ed65d/4be05be4f681480b9843d508491b116f.xml |
| baseline | empty\_values | 通过 | evidence/93a18cacf3694678afad5e5f908ed65d/861f65fc76204a9e868fb344cde8ba5a.xml |
| baseline | mixed\_values | 通过 | evidence/93a18cacf3694678afad5e5f908ed65d/5e70611e08544427bd72e789a7197d0e.xml |
| independent | negative\_values | 通过 | evidence/8d2dc7c0ecd749a8b76f1e4471442941/3477efe1232e4ce6869bb08f4d1b139a.xml |
| independent | positive\_values | 通过 | evidence/8d2dc7c0ecd749a8b76f1e4471442941/83de432544d14b89a85599e34f053890.xml |
| independent | empty\_values | 通过 | evidence/8d2dc7c0ecd749a8b76f1e4471442941/6db813ea8db04a37ae732e280e63ad89.xml |
| independent | mixed\_values | 通过 | evidence/8d2dc7c0ecd749a8b76f1e4471442941/3d14b6fad001405ea482df78a91a5085.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/3683a9767109403fa77eefa691386ed4/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/1367f7741fa3447c9c6fe05dbb2b526e/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/d8172a7ee39249d5b4c4b480d31aabad/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/2e77c628b4b84faa8bb8ac709c92beda/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/09e618d57b51439095c1565e4f3df15b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/93a18cacf3694678afad5e5f908ed65d-82bc672ccf75452bbef178811b7694be.xml --timeout 120.000000 | exited | 8 | logs/08e919461d234b47abc03398ff56b74d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/93a18cacf3694678afad5e5f908ed65d-82bc672ccf75452bbef178811b7694be.xml | exited | 0 | logs/4d05a53657bc450f8ef8ecaf49f1bdc6/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/93a18cacf3694678afad5e5f908ed65d-4be05be4f681480b9843d508491b116f.xml --timeout 120.000000 | exited | 0 | logs/81d13f21bb61446aa513eb5d36d894ce/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/93a18cacf3694678afad5e5f908ed65d-4be05be4f681480b9843d508491b116f.xml | exited | 0 | logs/091f8e21b6624c02b4f11d4988f04c8c/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/93a18cacf3694678afad5e5f908ed65d-861f65fc76204a9e868fb344cde8ba5a.xml --timeout 120.000000 | exited | 0 | logs/7b7d91d0460f46e58bdd19e68748d5db/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/93a18cacf3694678afad5e5f908ed65d-861f65fc76204a9e868fb344cde8ba5a.xml | exited | 0 | logs/b2b143d5a12043d4bdc754bdcd4a6bcd/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/93a18cacf3694678afad5e5f908ed65d-5e70611e08544427bd72e789a7197d0e.xml --timeout 120.000000 | exited | 0 | logs/6fdbed4e81074f269316abd4d8f0c13b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/93a18cacf3694678afad5e5f908ed65d-5e70611e08544427bd72e789a7197d0e.xml | exited | 0 | logs/7bc8d61e00db4d6ca9a64ba4c666bc0d/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/db2f2d0d0d7e47aea81fcfa2cd07c944/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/0ce57f481986486aac08bffe2541821c/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/79244d67cfa14c338c36fe1c805e0774/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/2bd0e03c09fd41949b28942e0a8dd061/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/e067f8bc5e60482d861a4eed5b377ec2/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/8d2dc7c0ecd749a8b76f1e4471442941-3477efe1232e4ce6869bb08f4d1b139a.xml --timeout 120.000000 | exited | 0 | logs/12da5b79aabe4816b43648ae13b9361b/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8d2dc7c0ecd749a8b76f1e4471442941-3477efe1232e4ce6869bb08f4d1b139a.xml | exited | 0 | logs/ac44c026d11c41a283063d40c2e4b5da/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/8d2dc7c0ecd749a8b76f1e4471442941-83de432544d14b89a85599e34f053890.xml --timeout 120.000000 | exited | 0 | logs/562f858bcb5145ecb2efee1f431e4467/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8d2dc7c0ecd749a8b76f1e4471442941-83de432544d14b89a85599e34f053890.xml | exited | 0 | logs/6c659d7d34134306b293cf7aeed67165/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/8d2dc7c0ecd749a8b76f1e4471442941-6db813ea8db04a37ae732e280e63ad89.xml --timeout 120.000000 | exited | 0 | logs/8d5abb9039aa437c8fa29c1dd9e6e539/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8d2dc7c0ecd749a8b76f1e4471442941-6db813ea8db04a37ae732e280e63ad89.xml | exited | 0 | logs/9b6c544c68f140f8bc2b46c9cf3c9462/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/8d2dc7c0ecd749a8b76f1e4471442941-3d14b6fad001405ea482df78a91a5085.xml --timeout 120.000000 | exited | 0 | logs/7fc37efd07ab445198b05565e44896b0/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8d2dc7c0ecd749a8b76f1e4471442941-3d14b6fad001405ea482df78a91a5085.xml | exited | 0 | logs/2f3989d0bff54e998aa12b2d84facfc4/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
