# ReproPatch 23720bece7b943b6b32a8b7c985d6910

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：6.587 秒
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
| baseline | negative\_values | 失败 | evidence/7d116ff864d64241b1497d56799a824d/9bcf63ebb53a4fa38be8f494f0d57c79.xml |
| baseline | positive\_values | 通过 | evidence/7d116ff864d64241b1497d56799a824d/ce47dac5e305419d91a991148c3dba2c.xml |
| baseline | empty\_values | 通过 | evidence/7d116ff864d64241b1497d56799a824d/05d618b1a00e4312aca797bbb8f7dfe3.xml |
| baseline | mixed\_values | 通过 | evidence/7d116ff864d64241b1497d56799a824d/c209fac51ea74889afc7a357c68d7f37.xml |
| independent | negative\_values | 失败 | evidence/e71a5b2491f04508867e1048764f4d42/d14780b101204ab79613700af7fed7f3.xml |
| independent | positive\_values | 通过 | evidence/e71a5b2491f04508867e1048764f4d42/9683a667abee4586936a5dfdec2c81e1.xml |
| independent | empty\_values | 通过 | evidence/e71a5b2491f04508867e1048764f4d42/a27b7d4186f54f40ab2d1e58e6d7dfdd.xml |
| independent | mixed\_values | 通过 | evidence/e71a5b2491f04508867e1048764f4d42/ea88ccc63d14449992fb8ceb238b395d.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/b93822a55e024aacbc0cbd1352d2f246/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/a0cc285f20f842329783e6bab6390ec9/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/4baa787aee324d9a84781943224fd23e/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/a8a73d8cadda48a9bef2d90015ed764c/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/0c8033679a0e49ee831a5fdba3412f96/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/7d116ff864d64241b1497d56799a824d-9bcf63ebb53a4fa38be8f494f0d57c79.xml --timeout 120.000000 | exited | 8 | logs/8ebe49394ae649af9a5dcb6decf121ef/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7d116ff864d64241b1497d56799a824d-9bcf63ebb53a4fa38be8f494f0d57c79.xml | exited | 0 | logs/020ad47e3411489292615f1b9732a348/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/7d116ff864d64241b1497d56799a824d-ce47dac5e305419d91a991148c3dba2c.xml --timeout 120.000000 | exited | 0 | logs/9d6b346ff1ff41119637208cb4e3d3d9/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7d116ff864d64241b1497d56799a824d-ce47dac5e305419d91a991148c3dba2c.xml | exited | 0 | logs/086f2cea72094981993fab0edb83c97d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/7d116ff864d64241b1497d56799a824d-05d618b1a00e4312aca797bbb8f7dfe3.xml --timeout 120.000000 | exited | 0 | logs/27637cc35575414ba3c9f8f9c8e2c84e/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7d116ff864d64241b1497d56799a824d-05d618b1a00e4312aca797bbb8f7dfe3.xml | exited | 0 | logs/8e42f7f7d6874b09a87631fab81b16be/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/7d116ff864d64241b1497d56799a824d-c209fac51ea74889afc7a357c68d7f37.xml --timeout 120.000000 | exited | 0 | logs/b75272c7546a4ca4aed364bcd9fc2a55/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/7d116ff864d64241b1497d56799a824d-c209fac51ea74889afc7a357c68d7f37.xml | exited | 0 | logs/d29dc5d55033443692cf51062cdc658f/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/b2df9a73f3c54f2f82d75ec11b4610eb/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/0988d6740bcf4c87b6dce0acb545c012/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/e35a9fdecff44c53b8653d7080adbf93/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/9aeeb72f0d0246628ee7ad85d53747de/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/f275791b038e476398e65bea065f9062/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/e71a5b2491f04508867e1048764f4d42-d14780b101204ab79613700af7fed7f3.xml --timeout 120.000000 | exited | 8 | logs/b613d17957ba44ec94147b8fee1e1343/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e71a5b2491f04508867e1048764f4d42-d14780b101204ab79613700af7fed7f3.xml | exited | 0 | logs/d0b3ce73ffbc4ee796612b5213ff1216/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/e71a5b2491f04508867e1048764f4d42-9683a667abee4586936a5dfdec2c81e1.xml --timeout 120.000000 | exited | 0 | logs/8a566c34f54b46a196e1b2ebf6319755/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e71a5b2491f04508867e1048764f4d42-9683a667abee4586936a5dfdec2c81e1.xml | exited | 0 | logs/fbe42fc7895c41bf9662cdac5658d05e/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/e71a5b2491f04508867e1048764f4d42-a27b7d4186f54f40ab2d1e58e6d7dfdd.xml --timeout 120.000000 | exited | 0 | logs/f311e442e62443b493bed67bcbf79879/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e71a5b2491f04508867e1048764f4d42-a27b7d4186f54f40ab2d1e58e6d7dfdd.xml | exited | 0 | logs/980ebd446a654cafaa1e004765c5a1dd/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/e71a5b2491f04508867e1048764f4d42-ea88ccc63d14449992fb8ceb238b395d.xml --timeout 120.000000 | exited | 0 | logs/1dff13b1f45b4f45b245fc7dc25506e4/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e71a5b2491f04508867e1048764f4d42-ea88ccc63d14449992fb8ceb238b395d.xml | exited | 0 | logs/9c1add592c80412fb51e4f864e41e0da/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
