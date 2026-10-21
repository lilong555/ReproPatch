# ReproPatch 17796a1043bb40a0a6c0042859ed3b6f

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：9.201 秒
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
| baseline | negative\_values | 失败 | evidence/437196fb414448bb8562ad7558cb889c/c29a31ac8a964bf99e2d7981c4a0fdf2.xml |
| baseline | positive\_values | 通过 | evidence/437196fb414448bb8562ad7558cb889c/0ce57ebccfff474290718f16a6011107.xml |
| baseline | empty\_values | 通过 | evidence/437196fb414448bb8562ad7558cb889c/e4ba857e931f4fd48550e0dfbefb7621.xml |
| baseline | mixed\_values | 通过 | evidence/437196fb414448bb8562ad7558cb889c/36af32462ba74010a628b9572c629c1d.xml |
| independent | negative\_values | 失败 | evidence/e451d280055346ae84269f86764db4a8/1ca9db53fd224740abcaf8e60e215636.xml |
| independent | positive\_values | 通过 | evidence/e451d280055346ae84269f86764db4a8/a8b137d853dd47f1aee737a4cc1cb2cc.xml |
| independent | empty\_values | 通过 | evidence/e451d280055346ae84269f86764db4a8/447dbd7f4e8d4618958c876987a3bd0c.xml |
| independent | mixed\_values | 通过 | evidence/e451d280055346ae84269f86764db4a8/d6ac20e7578944e18422cd09693f5292.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/664778d620744f6c89ab8fa9c10359ee/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/54ba69e041f84effa400f59060faec16/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/be3bffa3507b41feb0b4524d83315188/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/9356a8d38bc44453acb221c0f6287fbf/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/24944cf4cba540af9d3175843b4161a4/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/437196fb414448bb8562ad7558cb889c-c29a31ac8a964bf99e2d7981c4a0fdf2.xml --timeout 120.000000 | exited | 8 | logs/89715173d0a446a18812e263213f9665/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/437196fb414448bb8562ad7558cb889c-c29a31ac8a964bf99e2d7981c4a0fdf2.xml | exited | 0 | logs/cb64f5238d6a46beadfd9fa1e308a832/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/437196fb414448bb8562ad7558cb889c-0ce57ebccfff474290718f16a6011107.xml --timeout 120.000000 | exited | 0 | logs/60dc20827a8840d594d96d9b97c970ea/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/437196fb414448bb8562ad7558cb889c-0ce57ebccfff474290718f16a6011107.xml | exited | 0 | logs/2a81547ba50442a28fdf19cc76577001/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/437196fb414448bb8562ad7558cb889c-e4ba857e931f4fd48550e0dfbefb7621.xml --timeout 120.000000 | exited | 0 | logs/c8a00d65dbf14e1abfc27a67a3d084d0/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/437196fb414448bb8562ad7558cb889c-e4ba857e931f4fd48550e0dfbefb7621.xml | exited | 0 | logs/564cd17843cb4e47acebd8cd47fc1b58/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/437196fb414448bb8562ad7558cb889c-36af32462ba74010a628b9572c629c1d.xml --timeout 120.000000 | exited | 0 | logs/0717c52ed96a4d51bb6333f7353a0320/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/437196fb414448bb8562ad7558cb889c-36af32462ba74010a628b9572c629c1d.xml | exited | 0 | logs/08c0cdd75f2f46a7ac72ed40c77c64c5/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/13836eba78984816bcc161d582f7b933/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/66c20ac299c942c0b14c1cf5709a691b/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/7cf13321476e4ddfa38a9324660cf7dc/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/da61a960eb6948f68a28bd8ff02f8a78/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/01fe271a9a3b4d30a2a753b94ce7ccfe/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/e451d280055346ae84269f86764db4a8-1ca9db53fd224740abcaf8e60e215636.xml --timeout 120.000000 | exited | 8 | logs/e010542a773d4a2bba20694bed38890a/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e451d280055346ae84269f86764db4a8-1ca9db53fd224740abcaf8e60e215636.xml | exited | 0 | logs/1bf68cf19b1d4878b6872f26b62ed5fc/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/e451d280055346ae84269f86764db4a8-a8b137d853dd47f1aee737a4cc1cb2cc.xml --timeout 120.000000 | exited | 0 | logs/3a184f0d65944fcbba29e080231cffb4/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e451d280055346ae84269f86764db4a8-a8b137d853dd47f1aee737a4cc1cb2cc.xml | exited | 0 | logs/a5f221f122ae440ea96981c05cb9d7e1/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/e451d280055346ae84269f86764db4a8-447dbd7f4e8d4618958c876987a3bd0c.xml --timeout 120.000000 | exited | 0 | logs/707e0f90aaac43a28fb676cb03ab1d2d/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e451d280055346ae84269f86764db4a8-447dbd7f4e8d4618958c876987a3bd0c.xml | exited | 0 | logs/37715bf13f11480fa995cbec9d2b3c2b/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/e451d280055346ae84269f86764db4a8-d6ac20e7578944e18422cd09693f5292.xml --timeout 120.000000 | exited | 0 | logs/325209714f6247a7a97497d34760ec02/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e451d280055346ae84269f86764db4a8-d6ac20e7578944e18422cd09693f5292.xml | exited | 0 | logs/1624d7b039ae4f6e938a2a668fed1d96/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
