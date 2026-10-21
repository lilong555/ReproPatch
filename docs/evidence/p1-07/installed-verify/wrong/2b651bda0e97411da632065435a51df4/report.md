# ReproPatch 2b651bda0e97411da632065435a51df4

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：9.183 秒
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
| baseline | negative\_values | 失败 | evidence/d06761d4e3a949008855e7974a79e3f4/bf0d764f5fd742cc89b9a037bc4d1372.xml |
| baseline | positive\_values | 通过 | evidence/d06761d4e3a949008855e7974a79e3f4/cbe1eea9d1cb427a85be1a74762a8da6.xml |
| baseline | empty\_values | 通过 | evidence/d06761d4e3a949008855e7974a79e3f4/55fdbcf05b5a446bbc5d5d2a540d0394.xml |
| baseline | mixed\_values | 通过 | evidence/d06761d4e3a949008855e7974a79e3f4/f01ed51706fa40ee94fa32bf944db7a2.xml |
| independent | negative\_values | 失败 | evidence/3cfa4a2b49504a9abdf3e321f81afbd3/e17b444725ae4c90bf7162fc23d52e8a.xml |
| independent | positive\_values | 通过 | evidence/3cfa4a2b49504a9abdf3e321f81afbd3/6bb66f9c88094e13b81c7d6fa6c25bfe.xml |
| independent | empty\_values | 通过 | evidence/3cfa4a2b49504a9abdf3e321f81afbd3/795574ca764a452686122530db6a97b5.xml |
| independent | mixed\_values | 通过 | evidence/3cfa4a2b49504a9abdf3e321f81afbd3/7007d6d1e79747049fb606bb18841ffa.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/a3ed444fab5c45009cb47ce3db22bab0/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/fe2bebc4f9b14d26839addb716287451/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/a8983336bf7746db9598b2a8628689c7/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/48d1f972d917427f8f57253c5b1563e7/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/19b2b7834ff748788e2973c036ab95f7/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/d06761d4e3a949008855e7974a79e3f4-bf0d764f5fd742cc89b9a037bc4d1372.xml --timeout 120.000000 | exited | 8 | logs/a046f9a26ac44c559f81b6149cb89287/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d06761d4e3a949008855e7974a79e3f4-bf0d764f5fd742cc89b9a037bc4d1372.xml | exited | 0 | logs/6caaf4d5efc145b3b98739b27711f6da/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/d06761d4e3a949008855e7974a79e3f4-cbe1eea9d1cb427a85be1a74762a8da6.xml --timeout 120.000000 | exited | 0 | logs/f216c469cb5b4535b25b82af186f7d8f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d06761d4e3a949008855e7974a79e3f4-cbe1eea9d1cb427a85be1a74762a8da6.xml | exited | 0 | logs/bf48f2fea55c432cb00c015d79001315/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/d06761d4e3a949008855e7974a79e3f4-55fdbcf05b5a446bbc5d5d2a540d0394.xml --timeout 120.000000 | exited | 0 | logs/bd34be74a4ca428cb25ca985a841c731/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d06761d4e3a949008855e7974a79e3f4-55fdbcf05b5a446bbc5d5d2a540d0394.xml | exited | 0 | logs/208f9ff5eeb64eaf9797b10e66f8dea0/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/d06761d4e3a949008855e7974a79e3f4-f01ed51706fa40ee94fa32bf944db7a2.xml --timeout 120.000000 | exited | 0 | logs/21776b4927ca4537a9c5a7315c59cad7/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d06761d4e3a949008855e7974a79e3f4-f01ed51706fa40ee94fa32bf944db7a2.xml | exited | 0 | logs/56e8b835532b4be19dd85bde631cee67/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/551fc2e1cf57428696daa7a880151a91/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/dbc91339a074408ba4797ff5ffbde7c3/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/26dfff6d08bb4d5995d4898948552e4f/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/9bf152ea0d9c42acabc1045373c0bf84/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/c351c960bc6b4b839f35048dd8a466a9/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/3cfa4a2b49504a9abdf3e321f81afbd3-e17b444725ae4c90bf7162fc23d52e8a.xml --timeout 120.000000 | exited | 8 | logs/ce239f6ed67f409bbfba036978901d0c/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3cfa4a2b49504a9abdf3e321f81afbd3-e17b444725ae4c90bf7162fc23d52e8a.xml | exited | 0 | logs/afe36dc7fa0b441e934067a32c3356bb/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/3cfa4a2b49504a9abdf3e321f81afbd3-6bb66f9c88094e13b81c7d6fa6c25bfe.xml --timeout 120.000000 | exited | 0 | logs/e55015b2ee2c41699e0259208c6e768b/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3cfa4a2b49504a9abdf3e321f81afbd3-6bb66f9c88094e13b81c7d6fa6c25bfe.xml | exited | 0 | logs/e8d1606a8e4b4b37a699416ef8a328aa/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/3cfa4a2b49504a9abdf3e321f81afbd3-795574ca764a452686122530db6a97b5.xml --timeout 120.000000 | exited | 0 | logs/cd0ab3b4821845b5962773fe799378af/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3cfa4a2b49504a9abdf3e321f81afbd3-795574ca764a452686122530db6a97b5.xml | exited | 0 | logs/a4a7f6d919b94c54ab54bd86a56b31c1/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/3cfa4a2b49504a9abdf3e321f81afbd3-7007d6d1e79747049fb606bb18841ffa.xml --timeout 120.000000 | exited | 0 | logs/5d31401ad98e40ba924b1cbc5646c52a/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3cfa4a2b49504a9abdf3e321f81afbd3-7007d6d1e79747049fb606bb18841ffa.xml | exited | 0 | logs/7f74515db6014caaad18d56706d5eb2e/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
