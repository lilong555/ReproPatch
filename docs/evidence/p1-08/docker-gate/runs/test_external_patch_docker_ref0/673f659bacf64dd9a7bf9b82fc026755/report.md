# ReproPatch 673f659bacf64dd9a7bf9b82fc026755

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：REQUIRED\_TEST\_NOT\_RUN
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：4f36d9d37b96238c8c61a63fafc261041b241354
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：7.668 秒
模型步骤：0；准入工具：0
模型停止原因：未知
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：否；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：73


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/7b83ee15e00241d1b66978a794ffbc80/768a0d5e77cf4e29b5caa8e09a0fce5e.xml |
| baseline | positive\_values | 通过 | evidence/7b83ee15e00241d1b66978a794ffbc80/7e3ec03e8fdb44a095538ccdf98f9648.xml |
| baseline | empty\_values | 通过 | evidence/7b83ee15e00241d1b66978a794ffbc80/f3153d43596d449896df0a40508e7460.xml |
| baseline | mixed\_values | 通过 | evidence/7b83ee15e00241d1b66978a794ffbc80/52f8df1c104d4538918595feffc4b4c8.xml |
| independent | negative\_values | 跳过 | evidence/e83343b21e13461dae956ad051df3d68/6ac5de89b58f4cc09856d23910e78a20.xml |
| independent | positive\_values | 通过 | evidence/e83343b21e13461dae956ad051df3d68/17004637831942278220fda5bae1fa9d.xml |
| independent | empty\_values | 通过 | evidence/e83343b21e13461dae956ad051df3d68/06f4f4c3ab7649a9a806cb266f337a2b.xml |
| independent | mixed\_values | 失败 | evidence/e83343b21e13461dae956ad051df3d68/b0d47e6dfcd843fc83740c2b0268a5c6.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/3f694be678664507b2ce28d252348550/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/953318ddb56344b48356f830afcea7eb/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/05da7117aece4a67bef0915fffc8c997/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/e251663a59e94fd2965d47e4ca0fad78/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/2dafa7d813374e69b7434ec32531feda/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/7b83ee15e00241d1b66978a794ffbc80-768a0d5e77cf4e29b5caa8e09a0fce5e.xml --timeout 120.000000 | exited | 8 | logs/504b1eedf485477caff2a0297f768ddd/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7b83ee15e00241d1b66978a794ffbc80-768a0d5e77cf4e29b5caa8e09a0fce5e.xml | exited | 0 | logs/7e57a4f12c0c451d83f1b6b023ec77a4/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/7b83ee15e00241d1b66978a794ffbc80-7e3ec03e8fdb44a095538ccdf98f9648.xml --timeout 120.000000 | exited | 0 | logs/29239709506d4b5082b3c635117a262f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7b83ee15e00241d1b66978a794ffbc80-7e3ec03e8fdb44a095538ccdf98f9648.xml | exited | 0 | logs/b2dc3dc525b64769b2c5532c19ce3da9/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/7b83ee15e00241d1b66978a794ffbc80-f3153d43596d449896df0a40508e7460.xml --timeout 120.000000 | exited | 0 | logs/b1380e44e2ff44559f1c02c51a397f2b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7b83ee15e00241d1b66978a794ffbc80-f3153d43596d449896df0a40508e7460.xml | exited | 0 | logs/b65c284369844962a2d355f0a460efb8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/7b83ee15e00241d1b66978a794ffbc80-52f8df1c104d4538918595feffc4b4c8.xml --timeout 120.000000 | exited | 0 | logs/fce2994726144632be4e6d44d7c260a4/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7b83ee15e00241d1b66978a794ffbc80-52f8df1c104d4538918595feffc4b4c8.xml | exited | 0 | logs/78a0620cdc46475fb7fe6971da4ca8a8/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/042d50f32b19489aae37e368778c17be/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/5156ab94f6924fab940b64d1ff7050af/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/2233b37b36644e9c809701340c8a613e/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/14d83751773d407ab5ce08fd0a38f94b/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/b1164e4f2867484688642b29c141bf2d/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/e83343b21e13461dae956ad051df3d68-6ac5de89b58f4cc09856d23910e78a20.xml --timeout 120.000000 | exited | 0 | logs/7b527c4326924386be99ae4189400f7a/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e83343b21e13461dae956ad051df3d68-6ac5de89b58f4cc09856d23910e78a20.xml | exited | 0 | logs/c092211baac7401eb0c09af10a42342d/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/e83343b21e13461dae956ad051df3d68-17004637831942278220fda5bae1fa9d.xml --timeout 120.000000 | exited | 0 | logs/b294b7f55f084f7ab2fa1b131d7f1a72/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e83343b21e13461dae956ad051df3d68-17004637831942278220fda5bae1fa9d.xml | exited | 0 | logs/86b0960692884d7884e71ee106119d11/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/e83343b21e13461dae956ad051df3d68-06f4f4c3ab7649a9a806cb266f337a2b.xml --timeout 120.000000 | exited | 0 | logs/3ee25488cef14d80808c716cb1e3083b/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e83343b21e13461dae956ad051df3d68-06f4f4c3ab7649a9a806cb266f337a2b.xml | exited | 0 | logs/8d09c1b5edd14f16ab25bf1a15e193d1/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/e83343b21e13461dae956ad051df3d68-b0d47e6dfcd843fc83740c2b0268a5c6.xml --timeout 120.000000 | exited | 8 | logs/97a0e1050ec649759db195664cb54086/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e83343b21e13461dae956ad051df3d68-b0d47e6dfcd843fc83740c2b0268a5c6.xml | exited | 0 | logs/1c41c845e93b4945ad6d94a289e43253/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
