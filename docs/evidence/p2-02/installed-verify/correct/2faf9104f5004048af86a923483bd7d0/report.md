# ReproPatch 2faf9104f5004048af86a923483bd7d0

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：9.887 秒
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
| baseline | negative\_values | 失败 | evidence/fb1b844e6cd5420ca7fb93db74d467d5/c7e687a5e1a34d62823b08ceefa4d36f.xml |
| baseline | positive\_values | 通过 | evidence/fb1b844e6cd5420ca7fb93db74d467d5/aa6c268cff704f3891af95bc65cb1065.xml |
| baseline | empty\_values | 通过 | evidence/fb1b844e6cd5420ca7fb93db74d467d5/bbd42661e41c47718ebc83da411972df.xml |
| baseline | mixed\_values | 通过 | evidence/fb1b844e6cd5420ca7fb93db74d467d5/1883dbd7db024d5d85ee333f295b418b.xml |
| independent | negative\_values | 通过 | evidence/fc620a26eb0d4dddb36935474f340716/a47cf44cfd5b4f3fbf3b189cab905096.xml |
| independent | positive\_values | 通过 | evidence/fc620a26eb0d4dddb36935474f340716/49292af5431c4d20be7796e1d4f23dab.xml |
| independent | empty\_values | 通过 | evidence/fc620a26eb0d4dddb36935474f340716/6e9f575c6afb4a96b639733b5b88d1e1.xml |
| independent | mixed\_values | 通过 | evidence/fc620a26eb0d4dddb36935474f340716/16da121e42554b80a9cae7bcfef13f9d.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/fa792aa1d9e54523838e6fbb5f4b99fc/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/72ab5eb0fb2444fca17e6a9031340842/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/ce2b7cce08bf4e76a772bc9e2bd6d194/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/e1127dd936244b8fa077b0e98ac1306b/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/03f57ff0e8304bb08fa73a6b4f62ff60/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/fb1b844e6cd5420ca7fb93db74d467d5-c7e687a5e1a34d62823b08ceefa4d36f.xml --timeout 120.000000 | exited | 8 | logs/f71fa4636a274d9f829b9492b20a2c45/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fb1b844e6cd5420ca7fb93db74d467d5-c7e687a5e1a34d62823b08ceefa4d36f.xml | exited | 0 | logs/5312063d58e34022a35e6ab8f61890cb/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/fb1b844e6cd5420ca7fb93db74d467d5-aa6c268cff704f3891af95bc65cb1065.xml --timeout 120.000000 | exited | 0 | logs/349a338e1be343ddb9261bc7e425590d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fb1b844e6cd5420ca7fb93db74d467d5-aa6c268cff704f3891af95bc65cb1065.xml | exited | 0 | logs/c70c6744cd6e4fa68f4ad917b48de98e/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/fb1b844e6cd5420ca7fb93db74d467d5-bbd42661e41c47718ebc83da411972df.xml --timeout 120.000000 | exited | 0 | logs/340d1413170749adbf03d57020d2ff27/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fb1b844e6cd5420ca7fb93db74d467d5-bbd42661e41c47718ebc83da411972df.xml | exited | 0 | logs/3d59ccfabfb14ae68bf5a9b4d9c92af8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/fb1b844e6cd5420ca7fb93db74d467d5-1883dbd7db024d5d85ee333f295b418b.xml --timeout 120.000000 | exited | 0 | logs/5bd5663b609445a192953f7b6fcefc45/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fb1b844e6cd5420ca7fb93db74d467d5-1883dbd7db024d5d85ee333f295b418b.xml | exited | 0 | logs/b82a5ffe492d4211bbfb5084514f7e09/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/9c3a5cf7033f47d0b26c89406969b2ac/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/5a41ba21ffa341f2960fc28b72b30b88/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/007fd3ddc8aa40a8b9f124afc47b6445/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/98d2bc5235504665bf8c5c35a8e74345/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/8c6bead0045a4292b66b3661d9e09033/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/fc620a26eb0d4dddb36935474f340716-a47cf44cfd5b4f3fbf3b189cab905096.xml --timeout 120.000000 | exited | 0 | logs/dfc1972d81334b4289ade608e91d5705/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fc620a26eb0d4dddb36935474f340716-a47cf44cfd5b4f3fbf3b189cab905096.xml | exited | 0 | logs/056fb56c1ecc49bdbee5419ba3035d7a/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/fc620a26eb0d4dddb36935474f340716-49292af5431c4d20be7796e1d4f23dab.xml --timeout 120.000000 | exited | 0 | logs/e6c509728b984c4c83b82972a3c52d04/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fc620a26eb0d4dddb36935474f340716-49292af5431c4d20be7796e1d4f23dab.xml | exited | 0 | logs/55a942632e4c4e32af76bb001625f29d/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/fc620a26eb0d4dddb36935474f340716-6e9f575c6afb4a96b639733b5b88d1e1.xml --timeout 120.000000 | exited | 0 | logs/53df4685fae84b39abb7407d6145a5ca/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fc620a26eb0d4dddb36935474f340716-6e9f575c6afb4a96b639733b5b88d1e1.xml | exited | 0 | logs/e5452abf74244165abd5581fcf534b84/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/fc620a26eb0d4dddb36935474f340716-16da121e42554b80a9cae7bcfef13f9d.xml --timeout 120.000000 | exited | 0 | logs/f5a3acff5a5b4b72b9c8a21ae06051b3/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fc620a26eb0d4dddb36935474f340716-16da121e42554b80a9cae7bcfef13f9d.xml | exited | 0 | logs/f345b776ee634e429006e1569a6a2c2a/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
