# ReproPatch aed4c6c25a9a4cf596a3284415c60e63

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.545 秒
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
| baseline | negative\_values | 失败 | evidence/8a97c46a0b8d4f4a9b3d677cdbe14797/1ce0e9d78fa5414bbd3f86aef42254fb.xml |
| baseline | positive\_values | 通过 | evidence/8a97c46a0b8d4f4a9b3d677cdbe14797/574182483d684003a60413db72704448.xml |
| baseline | empty\_values | 通过 | evidence/8a97c46a0b8d4f4a9b3d677cdbe14797/6eb5644950054cad982abeb5c454ab85.xml |
| baseline | mixed\_values | 通过 | evidence/8a97c46a0b8d4f4a9b3d677cdbe14797/095cf335814b4b59832627aff4ae86f2.xml |
| independent | negative\_values | 通过 | evidence/d9894decb7584bd9860895a50f19cc53/91ae49bf3d0b489a8aaa1b2d52a876b7.xml |
| independent | positive\_values | 通过 | evidence/d9894decb7584bd9860895a50f19cc53/a15c6aa46f614da2b78c9d56110069c4.xml |
| independent | empty\_values | 通过 | evidence/d9894decb7584bd9860895a50f19cc53/ca6834504233466cac13598b9ed8daa7.xml |
| independent | mixed\_values | 通过 | evidence/d9894decb7584bd9860895a50f19cc53/62fd8b6c058242f8848c627120e3c3a8.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/55aaf062e3e442fc8bd67d758b3ddde8/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/5a438b7bc82547d390fc18e952429ade/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/1ee3fdc36dc34dba8a0c9f1f2ea59f15/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/5970894ab33c43e699c2f7a0d8ef5201/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/92be19a87d3747b6b0522408467c00a4/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/8a97c46a0b8d4f4a9b3d677cdbe14797-1ce0e9d78fa5414bbd3f86aef42254fb.xml --timeout 120.000000 | exited | 8 | logs/635d256636e2443b8967a0e3f4332712/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8a97c46a0b8d4f4a9b3d677cdbe14797-1ce0e9d78fa5414bbd3f86aef42254fb.xml | exited | 0 | logs/04f7280156bc45c6bd05b024c7785206/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/8a97c46a0b8d4f4a9b3d677cdbe14797-574182483d684003a60413db72704448.xml --timeout 120.000000 | exited | 0 | logs/a8846de692f5442ba5acb8f931159d47/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8a97c46a0b8d4f4a9b3d677cdbe14797-574182483d684003a60413db72704448.xml | exited | 0 | logs/56e11a6deb0d4c5a9ef2d3b4ceca69ef/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/8a97c46a0b8d4f4a9b3d677cdbe14797-6eb5644950054cad982abeb5c454ab85.xml --timeout 120.000000 | exited | 0 | logs/5ef8381d8c3e4c1794d0feb89ca7894b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8a97c46a0b8d4f4a9b3d677cdbe14797-6eb5644950054cad982abeb5c454ab85.xml | exited | 0 | logs/c451f5b6d12a4652ac45662222e3006a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/8a97c46a0b8d4f4a9b3d677cdbe14797-095cf335814b4b59832627aff4ae86f2.xml --timeout 120.000000 | exited | 0 | logs/cc9efe6579644db1a67a8cec5509cfaa/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/8a97c46a0b8d4f4a9b3d677cdbe14797-095cf335814b4b59832627aff4ae86f2.xml | exited | 0 | logs/393a18cf27ec4ff4a1b7c7893d7ffdb7/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/5bd5d397bc5544ce81cdd160f3d695fd/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/02f0eb40813249e0aa28c92c9daf03d5/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/2316909a8e3342359b45522e85cd94e9/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/910192b32dd348419d414f171d04dfe5/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/ebf92f238b0048aba0ad990713db859d/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/d9894decb7584bd9860895a50f19cc53-91ae49bf3d0b489a8aaa1b2d52a876b7.xml --timeout 120.000000 | exited | 0 | logs/7947e2ca665d40dbb3c8623486bba0d8/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d9894decb7584bd9860895a50f19cc53-91ae49bf3d0b489a8aaa1b2d52a876b7.xml | exited | 0 | logs/434601d71748469daa617fc43935e469/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/d9894decb7584bd9860895a50f19cc53-a15c6aa46f614da2b78c9d56110069c4.xml --timeout 120.000000 | exited | 0 | logs/153445b7ae634ad0a14a79c7ce451187/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d9894decb7584bd9860895a50f19cc53-a15c6aa46f614da2b78c9d56110069c4.xml | exited | 0 | logs/6d4204c11c3f49b1ae5775479a3641bf/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/d9894decb7584bd9860895a50f19cc53-ca6834504233466cac13598b9ed8daa7.xml --timeout 120.000000 | exited | 0 | logs/ff042918aed843ba97a497b112c270a4/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d9894decb7584bd9860895a50f19cc53-ca6834504233466cac13598b9ed8daa7.xml | exited | 0 | logs/67ea76aeab4f48cebf1ad0d62e743d62/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/d9894decb7584bd9860895a50f19cc53-62fd8b6c058242f8848c627120e3c3a8.xml --timeout 120.000000 | exited | 0 | logs/6c4fca56b6fb446aa8286d0457e0075d/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d9894decb7584bd9860895a50f19cc53-62fd8b6c058242f8848c627120e3c3a8.xml | exited | 0 | logs/6c489493e67e4019b70a3842007d85a9/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
