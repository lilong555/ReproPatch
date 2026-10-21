# ReproPatch 5c1244fe60ed4907b95dd17ee4c2581c

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：REQUIRED\_TEST\_NOT\_RUN
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：3e2b33abc97cef6935db8a9d2a3a47b37855720f
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：7.953 秒
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
| baseline | negative\_values | 失败 | evidence/e49f84c5828b47d5aec59a9bbaa539f8/90bc28474f94409b8be035700d800d78.xml |
| baseline | positive\_values | 通过 | evidence/e49f84c5828b47d5aec59a9bbaa539f8/f66e122842ba44bb8dc74895ec4bee6e.xml |
| baseline | empty\_values | 通过 | evidence/e49f84c5828b47d5aec59a9bbaa539f8/6771437c1d5a4e6cb74bc0c3faaea401.xml |
| baseline | mixed\_values | 通过 | evidence/e49f84c5828b47d5aec59a9bbaa539f8/239ab8c028f041ba88d5fe50cdaee4f3.xml |
| independent | negative\_values | 跳过 | evidence/bf22b6af2a2c40b586507fea8faa4e0c/c52150ff0f5c44e6bfc7433ab122e561.xml |
| independent | positive\_values | 通过 | evidence/bf22b6af2a2c40b586507fea8faa4e0c/43ced2dc889d4396ad24d45c25cc9421.xml |
| independent | empty\_values | 通过 | evidence/bf22b6af2a2c40b586507fea8faa4e0c/a07f1c16bda44535bff7d764aa201922.xml |
| independent | mixed\_values | 失败 | evidence/bf22b6af2a2c40b586507fea8faa4e0c/120b8977620e416790ffd3466b0978f6.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/b9e1714f026244949d925c5da769fdd0/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/3a11fbcc3b9444bf84914645432ba61b/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/de7f29b62779480fbc54296e6b6eb4eb/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/a2558379137a43b8adc12209bf919c74/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/2d96190ca4ff4f5eb28a25218dec26bb/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/e49f84c5828b47d5aec59a9bbaa539f8-90bc28474f94409b8be035700d800d78.xml --timeout 120.000000 | exited | 8 | logs/0af90843ef7b4a139cda53265d181a4d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e49f84c5828b47d5aec59a9bbaa539f8-90bc28474f94409b8be035700d800d78.xml | exited | 0 | logs/71f41be27a374f0e871c162db91ed4b2/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/e49f84c5828b47d5aec59a9bbaa539f8-f66e122842ba44bb8dc74895ec4bee6e.xml --timeout 120.000000 | exited | 0 | logs/2164c934a3c147679fa7e10aa49f92d3/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e49f84c5828b47d5aec59a9bbaa539f8-f66e122842ba44bb8dc74895ec4bee6e.xml | exited | 0 | logs/ca06d52ed80f41c09479108c53ed8f31/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/e49f84c5828b47d5aec59a9bbaa539f8-6771437c1d5a4e6cb74bc0c3faaea401.xml --timeout 120.000000 | exited | 0 | logs/27cef1a4a81049e49e493b466b09036f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e49f84c5828b47d5aec59a9bbaa539f8-6771437c1d5a4e6cb74bc0c3faaea401.xml | exited | 0 | logs/4a4bf1cd03c3472bbdab44efa8557be2/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/e49f84c5828b47d5aec59a9bbaa539f8-239ab8c028f041ba88d5fe50cdaee4f3.xml --timeout 120.000000 | exited | 0 | logs/84d7b52c28bd45168168c7b2a8900f4f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e49f84c5828b47d5aec59a9bbaa539f8-239ab8c028f041ba88d5fe50cdaee4f3.xml | exited | 0 | logs/25f63ee042b44230af7d8d0cc746b994/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/efd4aeb44b1d4c00aa6def6ae928ff2f/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/0781c9f4f00e4bc390cf5a67c7f06e41/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/8410ab9d50e94049bbd6c46646b46ff5/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/3f437430f09349778c0f9cf6f011d653/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/94ac144d55cc441994b57e262338c328/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/bf22b6af2a2c40b586507fea8faa4e0c-c52150ff0f5c44e6bfc7433ab122e561.xml --timeout 120.000000 | exited | 0 | logs/546677b275844a90a00c298ceb1d7378/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/bf22b6af2a2c40b586507fea8faa4e0c-c52150ff0f5c44e6bfc7433ab122e561.xml | exited | 0 | logs/8559f9a9116543baa92752cc0a5ec4fb/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/bf22b6af2a2c40b586507fea8faa4e0c-43ced2dc889d4396ad24d45c25cc9421.xml --timeout 120.000000 | exited | 0 | logs/7bcf7c3518ca4f998b49ee5685a5576f/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/bf22b6af2a2c40b586507fea8faa4e0c-43ced2dc889d4396ad24d45c25cc9421.xml | exited | 0 | logs/6e8e6c09cc5f4f64b624db97eb054b92/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/bf22b6af2a2c40b586507fea8faa4e0c-a07f1c16bda44535bff7d764aa201922.xml --timeout 120.000000 | exited | 0 | logs/3f837d799610449abfd777ceadae7f81/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/bf22b6af2a2c40b586507fea8faa4e0c-a07f1c16bda44535bff7d764aa201922.xml | exited | 0 | logs/009a57cf440b452cb5d3b750462239b3/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/bf22b6af2a2c40b586507fea8faa4e0c-120b8977620e416790ffd3466b0978f6.xml --timeout 120.000000 | exited | 8 | logs/8643f8de0e9c437fa1d17a2d3e5892b4/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/bf22b6af2a2c40b586507fea8faa4e0c-120b8977620e416790ffd3466b0978f6.xml | exited | 0 | logs/5d300a48a29940a09a50005e6e753a2c/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
外部生成过程、预算和 trace 未受本次运行管理或验证。
