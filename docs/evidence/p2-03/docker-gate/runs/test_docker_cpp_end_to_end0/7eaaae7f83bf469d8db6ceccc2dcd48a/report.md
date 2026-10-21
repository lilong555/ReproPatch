# ReproPatch 7eaaae7f83bf469d8db6ceccc2dcd48a

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：8286f96a04c3c9698ebf13741aa91ace4256c699
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：13.846 秒
模型步骤：5；准入工具：4
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：136


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/edce8198a4d24b29901cd5f72a282fa1/b6e270b15b934772bae85246fc1d4cf2.xml |
| baseline | positive\_values | 通过 | evidence/edce8198a4d24b29901cd5f72a282fa1/80343ce99b9e412ab8f5f7f87e132b43.xml |
| baseline | empty\_values | 通过 | evidence/edce8198a4d24b29901cd5f72a282fa1/1142e32898c443bcb56239cfc0d84ba9.xml |
| baseline | mixed\_values | 通过 | evidence/edce8198a4d24b29901cd5f72a282fa1/9c5fd1a160e74030b390645a2b1433cf.xml |
| agent\_check | negative\_values | 通过 | evidence/a5b11416f1dd4b81ab2f23a44123ecc4/b137692a410c481f8d2a11c0b0759307.xml |
| agent\_check | positive\_values | 通过 | evidence/a5b11416f1dd4b81ab2f23a44123ecc4/654c6d8cc24b41bf83ccf40b78346826.xml |
| agent\_check | empty\_values | 通过 | evidence/a5b11416f1dd4b81ab2f23a44123ecc4/ffc0b1505ffa49c08cd1af4195c642bb.xml |
| agent\_check | mixed\_values | 通过 | evidence/a5b11416f1dd4b81ab2f23a44123ecc4/40fc1f0d83fd4437af390448f6ad1bfe.xml |
| independent | negative\_values | 通过 | evidence/c41c885efa0f404e82531526fa13377e/23e1221fe8114d59ac795bd1161160cb.xml |
| independent | positive\_values | 通过 | evidence/c41c885efa0f404e82531526fa13377e/05c240ca6994464d826e179c850745d7.xml |
| independent | empty\_values | 通过 | evidence/c41c885efa0f404e82531526fa13377e/bac4f391f70f41109373026d06c9098e.xml |
| independent | mixed\_values | 通过 | evidence/c41c885efa0f404e82531526fa13377e/7bb2b332a9b54a9bac720d575f92a389.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/57eb5517a7004795b3512bd0097b643d/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/80c3a44fa08c4975925eb1a154953dcd/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/55d977cbb815437da4d3d9f2dc81bafe/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/61a55cc530124e6a8e4863acc3ff6d37/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/9ee528cd13f943dc86528bf184535d77/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/edce8198a4d24b29901cd5f72a282fa1-b6e270b15b934772bae85246fc1d4cf2.xml --timeout 120.000000 | exited | 8 | logs/319b01c4bcb24bc7b942cec2fc58a8bf/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/edce8198a4d24b29901cd5f72a282fa1-b6e270b15b934772bae85246fc1d4cf2.xml | exited | 0 | logs/01867875b4e943a3a5dd70a1399a6dbf/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/edce8198a4d24b29901cd5f72a282fa1-80343ce99b9e412ab8f5f7f87e132b43.xml --timeout 120.000000 | exited | 0 | logs/ebe666d6d9cf456b85ab626e5ad3b92b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/edce8198a4d24b29901cd5f72a282fa1-80343ce99b9e412ab8f5f7f87e132b43.xml | exited | 0 | logs/db8da8c3095644e2bd51869b24419690/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/edce8198a4d24b29901cd5f72a282fa1-1142e32898c443bcb56239cfc0d84ba9.xml --timeout 120.000000 | exited | 0 | logs/fb91c566f88c4c7e85797d9b85c508c2/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/edce8198a4d24b29901cd5f72a282fa1-1142e32898c443bcb56239cfc0d84ba9.xml | exited | 0 | logs/cbf1687d642d4f5c8b23d7453ca3048d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/edce8198a4d24b29901cd5f72a282fa1-9c5fd1a160e74030b390645a2b1433cf.xml --timeout 120.000000 | exited | 0 | logs/aeaebe39f0d945b3b30ddf641b462ce0/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/edce8198a4d24b29901cd5f72a282fa1-9c5fd1a160e74030b390645a2b1433cf.xml | exited | 0 | logs/b7e4a4a084a540deabd245bb445bb7e2/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/bf5002ed5f224d65b05bd5778d6fdc68/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/1d60ff05dfb34669a844a00de8856d70/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/39ccae43b27e4bc3970cf738e22f5393/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/90de1e4afde847ab99e04392823f7226/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/2bed7ad20be54588ae28bf2a1ad786e5/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/a5b11416f1dd4b81ab2f23a44123ecc4-b137692a410c481f8d2a11c0b0759307.xml --timeout 120.000000 | exited | 0 | logs/b685792af4164e3a9a9557623a9faa79/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a5b11416f1dd4b81ab2f23a44123ecc4-b137692a410c481f8d2a11c0b0759307.xml | exited | 0 | logs/755d1aef58674098ab919d719c988b60/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/a5b11416f1dd4b81ab2f23a44123ecc4-654c6d8cc24b41bf83ccf40b78346826.xml --timeout 120.000000 | exited | 0 | logs/2b49e861edd444869ed73a7546b09041/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a5b11416f1dd4b81ab2f23a44123ecc4-654c6d8cc24b41bf83ccf40b78346826.xml | exited | 0 | logs/f10cd3c4092543b5966bab3039d1aef4/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/a5b11416f1dd4b81ab2f23a44123ecc4-ffc0b1505ffa49c08cd1af4195c642bb.xml --timeout 120.000000 | exited | 0 | logs/3c610b59dfd944129154520ac4865b6a/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a5b11416f1dd4b81ab2f23a44123ecc4-ffc0b1505ffa49c08cd1af4195c642bb.xml | exited | 0 | logs/8973af58ad1e469e97691cee893a7bd0/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/a5b11416f1dd4b81ab2f23a44123ecc4-40fc1f0d83fd4437af390448f6ad1bfe.xml --timeout 120.000000 | exited | 0 | logs/b5605ba62bdf4846bf3cdfab8378ac70/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a5b11416f1dd4b81ab2f23a44123ecc4-40fc1f0d83fd4437af390448f6ad1bfe.xml | exited | 0 | logs/ce115dba09034bdbbbb8f69d9a67c00c/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/bae9c7c7e8bf49208fa644eb45826627/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/c21361f6659e4094842b30b03dcd53a7/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/beac9cbcd56c4797bb436df8585125c5/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/896d2075afc14fb2a081cf7999b8cc62/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/8b6263a0c2e144b4aac4eb37d156dbe1/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/c41c885efa0f404e82531526fa13377e-23e1221fe8114d59ac795bd1161160cb.xml --timeout 120.000000 | exited | 0 | logs/6cf6f78311294b1eac71bcac256d0b0e/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c41c885efa0f404e82531526fa13377e-23e1221fe8114d59ac795bd1161160cb.xml | exited | 0 | logs/ec8dcbe3f36842ffae9a5d7834280071/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/c41c885efa0f404e82531526fa13377e-05c240ca6994464d826e179c850745d7.xml --timeout 120.000000 | exited | 0 | logs/dca7b9ee1c654ff992abf96ab1007f70/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c41c885efa0f404e82531526fa13377e-05c240ca6994464d826e179c850745d7.xml | exited | 0 | logs/c0ad6e44b8ef4fa2b598da9be191ea3f/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/c41c885efa0f404e82531526fa13377e-bac4f391f70f41109373026d06c9098e.xml --timeout 120.000000 | exited | 0 | logs/323e266815554acdb13d4ebb38587e74/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c41c885efa0f404e82531526fa13377e-bac4f391f70f41109373026d06c9098e.xml | exited | 0 | logs/7058ab6e037d4be5a3e4f59048e67567/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/c41c885efa0f404e82531526fa13377e-7bb2b332a9b54a9bac720d575f92a389.xml --timeout 120.000000 | exited | 0 | logs/e424bc3d832b48a8af42cf16c7da6fcf/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/c41c885efa0f404e82531526fa13377e-7bb2b332a9b54a9bac720d575f92a389.xml | exited | 0 | logs/4e68b6b891ac417eb191af06d81c94e4/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
