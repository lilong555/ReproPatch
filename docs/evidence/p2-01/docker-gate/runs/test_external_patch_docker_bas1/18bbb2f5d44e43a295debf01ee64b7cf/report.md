# ReproPatch 18bbb2f5d44e43a295debf01ee64b7cf

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：83d783bb69c9a3ccb21919619c5daca5e442d0c1
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.132 秒
模型步骤：0；准入工具：0
模型停止原因：未知
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：否；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：73

外部来源标签（未认证）：fixture
外部轨迹：未验证的 opaque 附件，不作为测试或用量证据。

| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/4c6c8021d3264f0dbbd3c2e990be81e2/9e09e8d3862c4bdd8ecc0d8cab7ddfb5.xml |
| baseline | positive\_values | 通过 | evidence/4c6c8021d3264f0dbbd3c2e990be81e2/605e817d36774c9f8c0d057e02604138.xml |
| baseline | empty\_values | 通过 | evidence/4c6c8021d3264f0dbbd3c2e990be81e2/f73a6826aa8b4fa48da6b88c341b344c.xml |
| baseline | mixed\_values | 通过 | evidence/4c6c8021d3264f0dbbd3c2e990be81e2/e8e0c69483d9476ab88e69b57d67d4ec.xml |
| independent | negative\_values | 失败 | evidence/9ff7ee3986a9454284ae978cb9091f89/977fc54fc75e491581e904a3ca34dab5.xml |
| independent | positive\_values | 通过 | evidence/9ff7ee3986a9454284ae978cb9091f89/78832c5ada464ef39a267c86c7c04355.xml |
| independent | empty\_values | 通过 | evidence/9ff7ee3986a9454284ae978cb9091f89/790618fc0eb04eee8e52d82bb6a835c5.xml |
| independent | mixed\_values | 通过 | evidence/9ff7ee3986a9454284ae978cb9091f89/8990eda1a02d46fb82e6f20858c0476e.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/2bc6600fa213490889b6a2b891d96c05/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/2deeb1853617486fb27d89c6e62c3c30/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/01dcbf6a0856475d9c14b004bc2f22a1/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/8721d35a9df54503aef9635cda010783/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/4caa594575e0438185ca23f338833d76/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/4c6c8021d3264f0dbbd3c2e990be81e2-9e09e8d3862c4bdd8ecc0d8cab7ddfb5.xml --timeout 120.000000 | exited | 8 | logs/24c63870d590418ca59160fc3706c2be/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4c6c8021d3264f0dbbd3c2e990be81e2-9e09e8d3862c4bdd8ecc0d8cab7ddfb5.xml | exited | 0 | logs/d549fc8726284e809cee3ce9a8db0a22/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/4c6c8021d3264f0dbbd3c2e990be81e2-605e817d36774c9f8c0d057e02604138.xml --timeout 120.000000 | exited | 0 | logs/a2ee62846ae4437e85fb54afbc1c60bd/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4c6c8021d3264f0dbbd3c2e990be81e2-605e817d36774c9f8c0d057e02604138.xml | exited | 0 | logs/3df50ced215e4cf7a2a2f30fa1e7c224/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/4c6c8021d3264f0dbbd3c2e990be81e2-f73a6826aa8b4fa48da6b88c341b344c.xml --timeout 120.000000 | exited | 0 | logs/38332553a9844d9793a4ea05ba57d395/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4c6c8021d3264f0dbbd3c2e990be81e2-f73a6826aa8b4fa48da6b88c341b344c.xml | exited | 0 | logs/7d267411d7ed47e58f4a3578a88bd899/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/4c6c8021d3264f0dbbd3c2e990be81e2-e8e0c69483d9476ab88e69b57d67d4ec.xml --timeout 120.000000 | exited | 0 | logs/5727e07d428e42d598097ccc49f151e0/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4c6c8021d3264f0dbbd3c2e990be81e2-e8e0c69483d9476ab88e69b57d67d4ec.xml | exited | 0 | logs/02168b870b274f3f99ea1180129e8834/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/067d58b7dfb74f20a8d980235e0d63c4/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/0a83cb4202864a3aa5f0461928eddf69/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/af3e5f1c1f4b4846aeed42b89ee08566/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/1948022e09fc4ebb8cee355a08aa2746/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/e8012ec2b093489c8b0e4054b28a53d1/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/9ff7ee3986a9454284ae978cb9091f89-977fc54fc75e491581e904a3ca34dab5.xml --timeout 120.000000 | exited | 8 | logs/3939279456cb48d1ae7923003f004d39/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/9ff7ee3986a9454284ae978cb9091f89-977fc54fc75e491581e904a3ca34dab5.xml | exited | 0 | logs/26e6d51b5150467194bb8f3037f309c7/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/9ff7ee3986a9454284ae978cb9091f89-78832c5ada464ef39a267c86c7c04355.xml --timeout 120.000000 | exited | 0 | logs/4016c59202194742864caab31ac617dd/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/9ff7ee3986a9454284ae978cb9091f89-78832c5ada464ef39a267c86c7c04355.xml | exited | 0 | logs/0cd606d2629544caa48b860ec1716d20/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/9ff7ee3986a9454284ae978cb9091f89-790618fc0eb04eee8e52d82bb6a835c5.xml --timeout 120.000000 | exited | 0 | logs/91dc0543b40143c8a49706e90aa54f91/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/9ff7ee3986a9454284ae978cb9091f89-790618fc0eb04eee8e52d82bb6a835c5.xml | exited | 0 | logs/7afbd164670e4a5d9bdaaba6ae530ac7/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/9ff7ee3986a9454284ae978cb9091f89-8990eda1a02d46fb82e6f20858c0476e.xml --timeout 120.000000 | exited | 0 | logs/52000a873bbd4f78a9d3ea10a142fa19/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/9ff7ee3986a9454284ae978cb9091f89-8990eda1a02d46fb82e6f20858c0476e.xml | exited | 0 | logs/39a18f9fb29246c98d945d7602b78d35/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
