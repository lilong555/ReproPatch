# ReproPatch f2577d7ddea64c2aa7c9834d0f9b4c70

任务：negative-maximum
入口：run
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：f11825b0eaa6231c0587dd44bdde9979db3b93a3
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.495 秒
模型步骤：2；准入工具：1
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：83


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/caae72aaf3e84585adc5e6e28ed58197/c3cba4360f4d4a30a0420e5f81e039a3.xml |
| baseline | positive\_values | 通过 | evidence/caae72aaf3e84585adc5e6e28ed58197/cf5f951471a04eb8b141871c50758f28.xml |
| baseline | empty\_values | 通过 | evidence/caae72aaf3e84585adc5e6e28ed58197/7c6e820674cb429f84563a62e9bb7c72.xml |
| baseline | mixed\_values | 通过 | evidence/caae72aaf3e84585adc5e6e28ed58197/ecc2edaaf0d646a896cafa94c628e5e3.xml |
| independent | negative\_values | 失败 | evidence/5a66e52ebf084b98ba1b38ef60f0dff5/75f8f0c535d5436d81b6ffa18b0db2a1.xml |
| independent | positive\_values | 通过 | evidence/5a66e52ebf084b98ba1b38ef60f0dff5/8f1a555543db4be9bc1b4fe952b4bee1.xml |
| independent | empty\_values | 通过 | evidence/5a66e52ebf084b98ba1b38ef60f0dff5/c43a0817b23246d6884ddc6983ff61f1.xml |
| independent | mixed\_values | 通过 | evidence/5a66e52ebf084b98ba1b38ef60f0dff5/5ecfb430612349c8aa6a4f9552f70894.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/c469c9ece33243e0894200f8094ce4c2/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/d1a2e2382864498597abb4cc4b4919eb/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/f7f74b1544e34a9ebec9ce80768d2827/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/15f9ece29c4a429cab3065886ae4d955/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/a081d75b3ad34af2a6a9989e20f67675/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/caae72aaf3e84585adc5e6e28ed58197-c3cba4360f4d4a30a0420e5f81e039a3.xml --timeout 120.000000 | exited | 8 | logs/319f6ef1bb0a40ce9d5b99fd613ce05a/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/caae72aaf3e84585adc5e6e28ed58197-c3cba4360f4d4a30a0420e5f81e039a3.xml | exited | 0 | logs/038d75515de44b58af61f9cece9989e2/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/caae72aaf3e84585adc5e6e28ed58197-cf5f951471a04eb8b141871c50758f28.xml --timeout 120.000000 | exited | 0 | logs/f21c002a9a8d4f728ddbe48007f14f65/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/caae72aaf3e84585adc5e6e28ed58197-cf5f951471a04eb8b141871c50758f28.xml | exited | 0 | logs/366f20b265bf4ac0a178af602b01d2ce/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/caae72aaf3e84585adc5e6e28ed58197-7c6e820674cb429f84563a62e9bb7c72.xml --timeout 120.000000 | exited | 0 | logs/796674b5f8cc446ca61ac2ee37e383e6/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/caae72aaf3e84585adc5e6e28ed58197-7c6e820674cb429f84563a62e9bb7c72.xml | exited | 0 | logs/4d9e0b1b025b4bffb3cc28e6c23405c8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/caae72aaf3e84585adc5e6e28ed58197-ecc2edaaf0d646a896cafa94c628e5e3.xml --timeout 120.000000 | exited | 0 | logs/83a8d3992aa5447c8d39f38d3cf269cf/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/caae72aaf3e84585adc5e6e28ed58197-ecc2edaaf0d646a896cafa94c628e5e3.xml | exited | 0 | logs/7e4422e9259d40bb8d95caa776fa327d/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/56ac70a9966a41f4b714a38a5284b4e0/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/c1e04bd0364f4a1d9d8c139808270285/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/6584586e18b84947843e6176884a21e9/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/7322c640bc3444c9b4a8a286c7728843/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/577eeb7b98594630bf6e9021631729d4/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/5a66e52ebf084b98ba1b38ef60f0dff5-75f8f0c535d5436d81b6ffa18b0db2a1.xml --timeout 120.000000 | exited | 8 | logs/6614c3576bb847569d16261c1ed42988/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5a66e52ebf084b98ba1b38ef60f0dff5-75f8f0c535d5436d81b6ffa18b0db2a1.xml | exited | 0 | logs/a95d449a4fd74c199e80e6f92bbf3342/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/5a66e52ebf084b98ba1b38ef60f0dff5-8f1a555543db4be9bc1b4fe952b4bee1.xml --timeout 120.000000 | exited | 0 | logs/cd74b98246294be486f22f0e21a2ce38/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5a66e52ebf084b98ba1b38ef60f0dff5-8f1a555543db4be9bc1b4fe952b4bee1.xml | exited | 0 | logs/91893baf9d9e478e9d85a28207e631f6/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/5a66e52ebf084b98ba1b38ef60f0dff5-c43a0817b23246d6884ddc6983ff61f1.xml --timeout 120.000000 | exited | 0 | logs/168378294e634d3186725240ddccafef/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5a66e52ebf084b98ba1b38ef60f0dff5-c43a0817b23246d6884ddc6983ff61f1.xml | exited | 0 | logs/d3e48b7e35d348a7907f1ba96bf7a591/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/5a66e52ebf084b98ba1b38ef60f0dff5-5ecfb430612349c8aa6a4f9552f70894.xml --timeout 120.000000 | exited | 0 | logs/7a62508327f24d67bb406b5054895fda/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5a66e52ebf084b98ba1b38ef60f0dff5-5ecfb430612349c8aa6a4f9552f70894.xml | exited | 0 | logs/7694a061003345cc86900c273d15d974/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
