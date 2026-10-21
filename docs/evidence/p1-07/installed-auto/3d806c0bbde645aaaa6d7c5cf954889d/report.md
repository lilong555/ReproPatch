# ReproPatch 3d806c0bbde645aaaa6d7c5cf954889d

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：12.981 秒
模型步骤：5；准入工具：4
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：131


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/4f18469c21e5495298026ce68fc01fc0/ac1868c814bb4f89afe8e469891d49ae.xml |
| baseline | positive\_values | 通过 | evidence/4f18469c21e5495298026ce68fc01fc0/a6f77c2c0ef34803bec8fd66b68e814e.xml |
| baseline | empty\_values | 通过 | evidence/4f18469c21e5495298026ce68fc01fc0/65a8c4f3bf4a42eda4df853d1aba26f5.xml |
| baseline | mixed\_values | 通过 | evidence/4f18469c21e5495298026ce68fc01fc0/5028274339884bf0a80577ca87d60550.xml |
| agent\_check | negative\_values | 通过 | evidence/ecdef3951fb34cf2a4918e351bfa3a2a/4c1842314f5c45749e5f319f59982f9d.xml |
| agent\_check | positive\_values | 通过 | evidence/ecdef3951fb34cf2a4918e351bfa3a2a/82b1108a17e84a4c87bf5c0f6532d0e0.xml |
| agent\_check | empty\_values | 通过 | evidence/ecdef3951fb34cf2a4918e351bfa3a2a/cf9ce0480ab24e7eaad1eb4b4bc311c4.xml |
| agent\_check | mixed\_values | 通过 | evidence/ecdef3951fb34cf2a4918e351bfa3a2a/e5af6df3e44646b788c09fabe096e71a.xml |
| independent | negative\_values | 通过 | evidence/c567d94b2bc74cb3b58c37f8d45ce22d/1b1e3a87f72644d29086929b325dbe31.xml |
| independent | positive\_values | 通过 | evidence/c567d94b2bc74cb3b58c37f8d45ce22d/ee3c486d823745a993d46a74d760f05c.xml |
| independent | empty\_values | 通过 | evidence/c567d94b2bc74cb3b58c37f8d45ce22d/bcaa7cb1f3aa43a5a79dc4e58225b8c7.xml |
| independent | mixed\_values | 通过 | evidence/c567d94b2bc74cb3b58c37f8d45ce22d/a5561c48ce4847a784dde4859c676447.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/586456f0b9e84775a06584512930dd15/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/5dd06b5631354d1186e29280b6f36d10/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/2056b85d1d3d4a6c8993544d46caa2ce/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/913c7b144e2b453fb1e5bb43796bbff1/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/e6acada78f384901a24352d1cd9b944e/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/4f18469c21e5495298026ce68fc01fc0-ac1868c814bb4f89afe8e469891d49ae.xml --timeout 120.000000 | exited | 8 | logs/e4df78b6d58142afb274758286d41f44/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4f18469c21e5495298026ce68fc01fc0-ac1868c814bb4f89afe8e469891d49ae.xml | exited | 0 | logs/538e95c54ff64c0b86cd4094d5d9297d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/4f18469c21e5495298026ce68fc01fc0-a6f77c2c0ef34803bec8fd66b68e814e.xml --timeout 120.000000 | exited | 0 | logs/6396bf958bc245e89001dd733dbf14e3/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4f18469c21e5495298026ce68fc01fc0-a6f77c2c0ef34803bec8fd66b68e814e.xml | exited | 0 | logs/ad99d87c46ca4d4488e2a300a9dad5da/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/4f18469c21e5495298026ce68fc01fc0-65a8c4f3bf4a42eda4df853d1aba26f5.xml --timeout 120.000000 | exited | 0 | logs/da8959179d7b4df4a37fea9c56163b15/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4f18469c21e5495298026ce68fc01fc0-65a8c4f3bf4a42eda4df853d1aba26f5.xml | exited | 0 | logs/bc1599f287924728b152482c8df69902/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/4f18469c21e5495298026ce68fc01fc0-5028274339884bf0a80577ca87d60550.xml --timeout 120.000000 | exited | 0 | logs/0b6d144db91149169bef4d82b4b29935/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4f18469c21e5495298026ce68fc01fc0-5028274339884bf0a80577ca87d60550.xml | exited | 0 | logs/30d8ff2e8e4046cbbd158fa9c5c451d4/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/bf784e2346d54ed8b5cd5bc2cbc9ba97/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/b57842b9cfff4ae292638df860e7c367/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/7eb858de872243f2a0cf170d4fdb1b23/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/07377932b1eb4539bb6b8b5b69f53920/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/1cb8ef2d9e7a4369a2187086669ddfd7/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/ecdef3951fb34cf2a4918e351bfa3a2a-4c1842314f5c45749e5f319f59982f9d.xml --timeout 120.000000 | exited | 0 | logs/7d271ab8419548b4a8ccf3c1ea8649aa/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ecdef3951fb34cf2a4918e351bfa3a2a-4c1842314f5c45749e5f319f59982f9d.xml | exited | 0 | logs/1b8049006dc345e38929226a08892fe3/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/ecdef3951fb34cf2a4918e351bfa3a2a-82b1108a17e84a4c87bf5c0f6532d0e0.xml --timeout 120.000000 | exited | 0 | logs/4f05b9e224204ac28e2dc363e1fc95b0/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ecdef3951fb34cf2a4918e351bfa3a2a-82b1108a17e84a4c87bf5c0f6532d0e0.xml | exited | 0 | logs/6439395ccff04da38394c1b4c19282df/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/ecdef3951fb34cf2a4918e351bfa3a2a-cf9ce0480ab24e7eaad1eb4b4bc311c4.xml --timeout 120.000000 | exited | 0 | logs/a1cff541801548d5b03e4998bb83b203/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ecdef3951fb34cf2a4918e351bfa3a2a-cf9ce0480ab24e7eaad1eb4b4bc311c4.xml | exited | 0 | logs/aa5c0ab843dd4347afaa996fd35c8833/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/ecdef3951fb34cf2a4918e351bfa3a2a-e5af6df3e44646b788c09fabe096e71a.xml --timeout 120.000000 | exited | 0 | logs/907d0d32d0824c2b980a31800c6ab404/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ecdef3951fb34cf2a4918e351bfa3a2a-e5af6df3e44646b788c09fabe096e71a.xml | exited | 0 | logs/a6107cd54902467b9eca241cdeb1f757/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/0d68b369ac9d489687ffb0823c48b0b1/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/c5dd31b082734a989256c2b6cbe0f516/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/b06a5c7652de4cb8878a7dcf379d587a/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/d0816422b69f49fd85fe091300ef76e5/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/923e9421a20841f3929a2c742bab3620/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/c567d94b2bc74cb3b58c37f8d45ce22d-1b1e3a87f72644d29086929b325dbe31.xml --timeout 120.000000 | exited | 0 | logs/6160eb8ec2fc4280904d2c0e28947592/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c567d94b2bc74cb3b58c37f8d45ce22d-1b1e3a87f72644d29086929b325dbe31.xml | exited | 0 | logs/0becdef4be2c4c6ab508a49c3b77b282/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/c567d94b2bc74cb3b58c37f8d45ce22d-ee3c486d823745a993d46a74d760f05c.xml --timeout 120.000000 | exited | 0 | logs/d4fc7bc5d39346668c94d3fe40133d76/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c567d94b2bc74cb3b58c37f8d45ce22d-ee3c486d823745a993d46a74d760f05c.xml | exited | 0 | logs/fbbd0a9b73434dad9f8ece37568c0548/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/c567d94b2bc74cb3b58c37f8d45ce22d-bcaa7cb1f3aa43a5a79dc4e58225b8c7.xml --timeout 120.000000 | exited | 0 | logs/80d6efad12654df3924737f98c8f6360/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c567d94b2bc74cb3b58c37f8d45ce22d-bcaa7cb1f3aa43a5a79dc4e58225b8c7.xml | exited | 0 | logs/621d6a3c21374a47beb94a0c89fb8657/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/c567d94b2bc74cb3b58c37f8d45ce22d-a5561c48ce4847a784dde4859c676447.xml --timeout 120.000000 | exited | 0 | logs/be7605b5952d4be995650d2bd7a8f4b0/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c567d94b2bc74cb3b58c37f8d45ce22d-a5561c48ce4847a784dde4859c676447.xml | exited | 0 | logs/8c5ba1abaae24b8dbe4b92d8e3eb6776/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
