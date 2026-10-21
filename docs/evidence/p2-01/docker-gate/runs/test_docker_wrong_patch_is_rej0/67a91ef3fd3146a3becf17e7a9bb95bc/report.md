# ReproPatch 67a91ef3fd3146a3becf17e7a9bb95bc

任务：negative-maximum
入口：run
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：ff63debfa72883d2d3c46e12b0b5fcbcf338d38e
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.728 秒
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
| baseline | negative\_values | 失败 | evidence/ec546a0cdc934398aa0f3d5fe00a1823/bda8f1ded09d4b0e85798fd414a177bc.xml |
| baseline | positive\_values | 通过 | evidence/ec546a0cdc934398aa0f3d5fe00a1823/13d712ed626d47e09e7b816c3a8fd227.xml |
| baseline | empty\_values | 通过 | evidence/ec546a0cdc934398aa0f3d5fe00a1823/e5f25b8e49be432e968fc15adf5076ab.xml |
| baseline | mixed\_values | 通过 | evidence/ec546a0cdc934398aa0f3d5fe00a1823/c109605491244b1295edcb30e569deb7.xml |
| independent | negative\_values | 失败 | evidence/fe9f26624350470b927acfa122a868cc/915c745bb9744c4ea68852890c5ab123.xml |
| independent | positive\_values | 通过 | evidence/fe9f26624350470b927acfa122a868cc/eb7dd3495b934d6a8d789eaec5e4afae.xml |
| independent | empty\_values | 通过 | evidence/fe9f26624350470b927acfa122a868cc/afe7c2f6be8c4d8f82df9e3c8e13808a.xml |
| independent | mixed\_values | 通过 | evidence/fe9f26624350470b927acfa122a868cc/5338811c68bb41aba5378a3beba61c18.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/0410c25e220f4553a323ac7ece3a8a90/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/2d0664a7fbea419885a4f36d29ffa9c3/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/ba3e8ae0eb7b4f47bb6793a07397ce61/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/ad3e598974f54ee69d3ec8fbeb7706a9/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/b92f19949ab74ba7ae72f46ff425f5e2/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/ec546a0cdc934398aa0f3d5fe00a1823-bda8f1ded09d4b0e85798fd414a177bc.xml --timeout 120.000000 | exited | 8 | logs/183190c7605c4c3a9d642af30a28c317/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ec546a0cdc934398aa0f3d5fe00a1823-bda8f1ded09d4b0e85798fd414a177bc.xml | exited | 0 | logs/d45a5cffc6b448489cd45ea45bac82c8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/ec546a0cdc934398aa0f3d5fe00a1823-13d712ed626d47e09e7b816c3a8fd227.xml --timeout 120.000000 | exited | 0 | logs/b2f655640b5945a1bf7cd3a14d12fb36/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ec546a0cdc934398aa0f3d5fe00a1823-13d712ed626d47e09e7b816c3a8fd227.xml | exited | 0 | logs/e5afd2b20bcb4116a7c8b29aed4f88d8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/ec546a0cdc934398aa0f3d5fe00a1823-e5f25b8e49be432e968fc15adf5076ab.xml --timeout 120.000000 | exited | 0 | logs/be79ee0b1ea54299b650fc86e662b259/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ec546a0cdc934398aa0f3d5fe00a1823-e5f25b8e49be432e968fc15adf5076ab.xml | exited | 0 | logs/e5344b58905a4006810f644fc3e02e68/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/ec546a0cdc934398aa0f3d5fe00a1823-c109605491244b1295edcb30e569deb7.xml --timeout 120.000000 | exited | 0 | logs/af5a913bb24e488c9a66c172e42747be/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ec546a0cdc934398aa0f3d5fe00a1823-c109605491244b1295edcb30e569deb7.xml | exited | 0 | logs/62ce77b851d14b4b9991aa9992d4f631/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/2f509c716d654d169c56a82472be50bd/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/6d3ff3cad858438d91ac01685e5264cd/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/1d5f4b9e6f344c088a78c88453483336/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/8923dccf2667499c9c1e3a6a21f71ff4/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/81f7e0c0b4064cbab68374d9a402e240/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/fe9f26624350470b927acfa122a868cc-915c745bb9744c4ea68852890c5ab123.xml --timeout 120.000000 | exited | 8 | logs/fc731ddbc9bd406184662386d8028ac0/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fe9f26624350470b927acfa122a868cc-915c745bb9744c4ea68852890c5ab123.xml | exited | 0 | logs/0317e3f63d824e049b89a0a31f871ebd/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/fe9f26624350470b927acfa122a868cc-eb7dd3495b934d6a8d789eaec5e4afae.xml --timeout 120.000000 | exited | 0 | logs/e1b06fd0162649f6ae36fad06665e642/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fe9f26624350470b927acfa122a868cc-eb7dd3495b934d6a8d789eaec5e4afae.xml | exited | 0 | logs/fcb47cb4bc7047daa77a5d6bd2f40c77/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/fe9f26624350470b927acfa122a868cc-afe7c2f6be8c4d8f82df9e3c8e13808a.xml --timeout 120.000000 | exited | 0 | logs/b22e2ef7f9664cd198233e2448984ff9/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fe9f26624350470b927acfa122a868cc-afe7c2f6be8c4d8f82df9e3c8e13808a.xml | exited | 0 | logs/fc236ea859a242c48b5341667b5d3b8e/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/fe9f26624350470b927acfa122a868cc-5338811c68bb41aba5378a3beba61c18.xml --timeout 120.000000 | exited | 0 | logs/2c328a5d42654c529231e65b835ac4c9/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/fe9f26624350470b927acfa122a868cc-5338811c68bb41aba5378a3beba61c18.xml | exited | 0 | logs/38090d37e4b040c38c40efaeaf599460/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
