# ReproPatch 4186c23e7a484c05823b9d3f7673dc06

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：ec0b9223b49dda2e8ec81d43835e8b399971e973
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：7.615 秒
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
| baseline | negative\_values | 失败 | evidence/7e806e11a3424f6581647150435daea0/31932e08c79e4706a4aed7259cefec16.xml |
| baseline | positive\_values | 通过 | evidence/7e806e11a3424f6581647150435daea0/2681935dc6e34fcbad8b825bc9abccab.xml |
| baseline | empty\_values | 通过 | evidence/7e806e11a3424f6581647150435daea0/7e9f8501b39d428f89fc28d480895186.xml |
| baseline | mixed\_values | 通过 | evidence/7e806e11a3424f6581647150435daea0/24732aba4bfb442e9f08b03456576618.xml |
| independent | negative\_values | 通过 | evidence/d88e06d2c5114e35a85f1f7722e0ed8d/de4ff4bf693a47a3a4c9260f111de66c.xml |
| independent | positive\_values | 通过 | evidence/d88e06d2c5114e35a85f1f7722e0ed8d/9dfb51e5e42442848966aecc7e847586.xml |
| independent | empty\_values | 通过 | evidence/d88e06d2c5114e35a85f1f7722e0ed8d/cba1772f81a84bfd93c6d17a9d8678bf.xml |
| independent | mixed\_values | 通过 | evidence/d88e06d2c5114e35a85f1f7722e0ed8d/e256d23663ec4450bf2f8f9a1ff26eb1.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/e064afcc16124d4297a51af411fa21d8/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/fce2803fac934f00aaf4ed89e81f1042/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/879af118e9bc4884a9082edf306fb5b6/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/5aaaaa124b834387853944145c29dc17/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/b531ba596aa347f6a3fb13189c3fd9a3/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/7e806e11a3424f6581647150435daea0-31932e08c79e4706a4aed7259cefec16.xml --timeout 120.000000 | exited | 8 | logs/dbf2cf3230804fabb1ea162e413d4e12/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7e806e11a3424f6581647150435daea0-31932e08c79e4706a4aed7259cefec16.xml | exited | 0 | logs/a600bef796454694b7bc6d4431f42ddd/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/7e806e11a3424f6581647150435daea0-2681935dc6e34fcbad8b825bc9abccab.xml --timeout 120.000000 | exited | 0 | logs/0f0347204ce248bd93457a8a81b5059d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7e806e11a3424f6581647150435daea0-2681935dc6e34fcbad8b825bc9abccab.xml | exited | 0 | logs/96ff861ead61439791fdf600fb03ddb3/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/7e806e11a3424f6581647150435daea0-7e9f8501b39d428f89fc28d480895186.xml --timeout 120.000000 | exited | 0 | logs/0c950e5439144f059c13190f0a222c6a/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7e806e11a3424f6581647150435daea0-7e9f8501b39d428f89fc28d480895186.xml | exited | 0 | logs/d3a6a3599b724f898392e4961df7edf3/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/7e806e11a3424f6581647150435daea0-24732aba4bfb442e9f08b03456576618.xml --timeout 120.000000 | exited | 0 | logs/e9d32269760a4d2fa6a8897973544943/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7e806e11a3424f6581647150435daea0-24732aba4bfb442e9f08b03456576618.xml | exited | 0 | logs/3e38f734f0a74143b5933c195239ad81/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/11e33c7f6217414c9b2e332134ffbe0e/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/daac6727bf584cf4b0a08e05b7adf6fb/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/6c79d7e6192f4a3c8f64a2d38b4e58b4/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/ce75aff14abf4f35b82de7385b90de2a/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/a870c47d75ea4f2dba09dd8ef5659129/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/d88e06d2c5114e35a85f1f7722e0ed8d-de4ff4bf693a47a3a4c9260f111de66c.xml --timeout 120.000000 | exited | 0 | logs/9d9f20a9ee9149468dae1afe1a6f293b/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d88e06d2c5114e35a85f1f7722e0ed8d-de4ff4bf693a47a3a4c9260f111de66c.xml | exited | 0 | logs/110705328f5646c98a96fbae3010280f/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/d88e06d2c5114e35a85f1f7722e0ed8d-9dfb51e5e42442848966aecc7e847586.xml --timeout 120.000000 | exited | 0 | logs/94f33b42d7894531821307228b94f16a/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d88e06d2c5114e35a85f1f7722e0ed8d-9dfb51e5e42442848966aecc7e847586.xml | exited | 0 | logs/42315c99f86148d1a542bffcdf842646/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/d88e06d2c5114e35a85f1f7722e0ed8d-cba1772f81a84bfd93c6d17a9d8678bf.xml --timeout 120.000000 | exited | 0 | logs/bca9a8c0228f4e8b96a22d8e2682c305/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d88e06d2c5114e35a85f1f7722e0ed8d-cba1772f81a84bfd93c6d17a9d8678bf.xml | exited | 0 | logs/aa8544b84c504affbc5d5ca7b9abe72c/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/d88e06d2c5114e35a85f1f7722e0ed8d-e256d23663ec4450bf2f8f9a1ff26eb1.xml --timeout 120.000000 | exited | 0 | logs/c5648901991c4cce8261f98fbcebbd11/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d88e06d2c5114e35a85f1f7722e0ed8d-e256d23663ec4450bf2f8f9a1ff26eb1.xml | exited | 0 | logs/8964a4c0770b4ae7964c46a2524399ac/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
