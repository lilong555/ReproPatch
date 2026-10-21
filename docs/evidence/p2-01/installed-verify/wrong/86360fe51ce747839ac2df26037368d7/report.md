# ReproPatch 86360fe51ce747839ac2df26037368d7

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.154 秒
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
| baseline | negative\_values | 失败 | evidence/67f03ad64d8b4274bc9e89ea66a0969e/3ff15ddda2b04e57a96f935c1a93de86.xml |
| baseline | positive\_values | 通过 | evidence/67f03ad64d8b4274bc9e89ea66a0969e/fcad05d7e6e14de699bb59424dfb833a.xml |
| baseline | empty\_values | 通过 | evidence/67f03ad64d8b4274bc9e89ea66a0969e/6ae96ea8415e4277994d593bd0911e68.xml |
| baseline | mixed\_values | 通过 | evidence/67f03ad64d8b4274bc9e89ea66a0969e/cf208aa9165f4e03b95775fee77ff1c2.xml |
| independent | negative\_values | 失败 | evidence/969c7d6dfef844cbb3b09305b0ca8e59/cb7390722b5e4fe7ba0c8ce00a6dfa6a.xml |
| independent | positive\_values | 通过 | evidence/969c7d6dfef844cbb3b09305b0ca8e59/717f101909b74066a770fab3e251e3e6.xml |
| independent | empty\_values | 通过 | evidence/969c7d6dfef844cbb3b09305b0ca8e59/b5fb772c717f402e87d98df7ef215562.xml |
| independent | mixed\_values | 通过 | evidence/969c7d6dfef844cbb3b09305b0ca8e59/4669b713480a445bb18f8d24487d0d44.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/6d43405141ab4aa29a365052ada630ac/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/dac00a21eaf14931bc5022cd781a242e/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/237c1b1456f74b83a59be6a6bd5d9785/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/7048dca59ebc4834bb504821f71a7688/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/3d1432ec00c4458ca26c0a88ded70034/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/67f03ad64d8b4274bc9e89ea66a0969e-3ff15ddda2b04e57a96f935c1a93de86.xml --timeout 120.000000 | exited | 8 | logs/24c44db957c84159b759f22955ea657c/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/67f03ad64d8b4274bc9e89ea66a0969e-3ff15ddda2b04e57a96f935c1a93de86.xml | exited | 0 | logs/0267c9ad9e5248088378c307ae0518d6/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/67f03ad64d8b4274bc9e89ea66a0969e-fcad05d7e6e14de699bb59424dfb833a.xml --timeout 120.000000 | exited | 0 | logs/122bb412fb98413b8de8d46209b3315f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/67f03ad64d8b4274bc9e89ea66a0969e-fcad05d7e6e14de699bb59424dfb833a.xml | exited | 0 | logs/f9aeb480a4de4f56ab80f26c1b34c386/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/67f03ad64d8b4274bc9e89ea66a0969e-6ae96ea8415e4277994d593bd0911e68.xml --timeout 120.000000 | exited | 0 | logs/66b12fd3a4114563a17397c8b7128b32/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/67f03ad64d8b4274bc9e89ea66a0969e-6ae96ea8415e4277994d593bd0911e68.xml | exited | 0 | logs/16a14329cbe14c2390afe71b031fcce3/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/67f03ad64d8b4274bc9e89ea66a0969e-cf208aa9165f4e03b95775fee77ff1c2.xml --timeout 120.000000 | exited | 0 | logs/d0e5f7439b0549d2aa26aa532031fae8/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/67f03ad64d8b4274bc9e89ea66a0969e-cf208aa9165f4e03b95775fee77ff1c2.xml | exited | 0 | logs/64e2495dd5d4483283b72c0b102de1fd/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/019309f570af44a2a63ba475381a08db/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/02d0c96fbd7a45e086402dcdc68f543a/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/fda5e50e195a4c1da4205291835ba78d/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/484798f0689f4752b2bc8af07f43be8d/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/4f56303ca0e548aa81a52f4b9535bcba/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/969c7d6dfef844cbb3b09305b0ca8e59-cb7390722b5e4fe7ba0c8ce00a6dfa6a.xml --timeout 120.000000 | exited | 8 | logs/6d95bd1dd17a441abc4a7f01c26834a1/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/969c7d6dfef844cbb3b09305b0ca8e59-cb7390722b5e4fe7ba0c8ce00a6dfa6a.xml | exited | 0 | logs/c0d1a1eb1cb24ff0993ac31ab4fa0d10/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/969c7d6dfef844cbb3b09305b0ca8e59-717f101909b74066a770fab3e251e3e6.xml --timeout 120.000000 | exited | 0 | logs/fc769a9b15274aa1b356e9b883dadf8e/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/969c7d6dfef844cbb3b09305b0ca8e59-717f101909b74066a770fab3e251e3e6.xml | exited | 0 | logs/a6abc9d7bf1b44b59564f4520513733f/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/969c7d6dfef844cbb3b09305b0ca8e59-b5fb772c717f402e87d98df7ef215562.xml --timeout 120.000000 | exited | 0 | logs/6a140d33526a4bb0970db6f789fd4eb0/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/969c7d6dfef844cbb3b09305b0ca8e59-b5fb772c717f402e87d98df7ef215562.xml | exited | 0 | logs/3f4c131307524b3582e1ca93cbbaf492/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/969c7d6dfef844cbb3b09305b0ca8e59-4669b713480a445bb18f8d24487d0d44.xml --timeout 120.000000 | exited | 0 | logs/a713cb8d88a049caa279c69c5ad30748/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/969c7d6dfef844cbb3b09305b0ca8e59-4669b713480a445bb18f8d24487d0d44.xml | exited | 0 | logs/5f3c168e6c2f4dfa9ed814f9b1914202/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
