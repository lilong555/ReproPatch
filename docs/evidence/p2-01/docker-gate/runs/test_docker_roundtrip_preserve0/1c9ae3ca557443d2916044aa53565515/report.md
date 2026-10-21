# ReproPatch 1c9ae3ca557443d2916044aa53565515

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：9df43d61ca4f10b6b22d7464653ca80ad1980571
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：13.533 秒
模型步骤：5；准入工具：4
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：131


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/ce0de4102e7a4306bbe3539914127d03/e44d614693574614b7e1b3ec1d83de2f.xml |
| baseline | positive\_values | 通过 | evidence/ce0de4102e7a4306bbe3539914127d03/35015fdacf5c4cd9869cb7e8ae2a1a60.xml |
| baseline | empty\_values | 通过 | evidence/ce0de4102e7a4306bbe3539914127d03/7a119cb3909346829689567bf08e2899.xml |
| baseline | mixed\_values | 通过 | evidence/ce0de4102e7a4306bbe3539914127d03/b3941e2b48b44cfdb5e7e341efb80374.xml |
| agent\_check | negative\_values | 通过 | evidence/e74402536a6f4df1b7b1b5fdc2b287df/b16cc8bfe2d94690ba7609870842f655.xml |
| agent\_check | positive\_values | 通过 | evidence/e74402536a6f4df1b7b1b5fdc2b287df/4cc9f7469a7847e7a0cd1e8422f3c960.xml |
| agent\_check | empty\_values | 通过 | evidence/e74402536a6f4df1b7b1b5fdc2b287df/e6a7ae2e491f453f8e1c614d7a501d11.xml |
| agent\_check | mixed\_values | 通过 | evidence/e74402536a6f4df1b7b1b5fdc2b287df/c62e97a694704739bea2c7c5855100b8.xml |
| independent | negative\_values | 通过 | evidence/ead5cd02987b4d0f8901115c3c5cfc72/a89cfaf4cc0148fba9c11fab17e0761a.xml |
| independent | positive\_values | 通过 | evidence/ead5cd02987b4d0f8901115c3c5cfc72/05379a9f06584127baf3d8e18f226e21.xml |
| independent | empty\_values | 通过 | evidence/ead5cd02987b4d0f8901115c3c5cfc72/809523cf963847d5946677594d26b776.xml |
| independent | mixed\_values | 通过 | evidence/ead5cd02987b4d0f8901115c3c5cfc72/f5121864e0c645b882964daad203d960.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/0f73b92c53e848699d2550e5d93c8d8c/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/a759cfa7318440579cb6c4c7e5cd3060/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/a3059e9a8bb44e17a614861728872021/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/09eefbd5eef748a1a9cf649e97ac75e8/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/439c6719ecec48eaac25ae974528f32d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/ce0de4102e7a4306bbe3539914127d03-e44d614693574614b7e1b3ec1d83de2f.xml --timeout 120.000000 | exited | 8 | logs/f9fbd005705a48cb8fbcb70042aa97e3/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ce0de4102e7a4306bbe3539914127d03-e44d614693574614b7e1b3ec1d83de2f.xml | exited | 0 | logs/dba42fa26e314829b20260bd1c355c7a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/ce0de4102e7a4306bbe3539914127d03-35015fdacf5c4cd9869cb7e8ae2a1a60.xml --timeout 120.000000 | exited | 0 | logs/ebf3f67088f84c8b91713379568153ae/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ce0de4102e7a4306bbe3539914127d03-35015fdacf5c4cd9869cb7e8ae2a1a60.xml | exited | 0 | logs/824bae13520942f8ab944abf30ca87cf/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/ce0de4102e7a4306bbe3539914127d03-7a119cb3909346829689567bf08e2899.xml --timeout 120.000000 | exited | 0 | logs/3c8bb4bbd5744e0b8c3b23cc8d896c8f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ce0de4102e7a4306bbe3539914127d03-7a119cb3909346829689567bf08e2899.xml | exited | 0 | logs/9630de05c6574f8fb74b2727df5f5b00/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/ce0de4102e7a4306bbe3539914127d03-b3941e2b48b44cfdb5e7e341efb80374.xml --timeout 120.000000 | exited | 0 | logs/2317d16b3ea84908a8045f6ce33c292f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ce0de4102e7a4306bbe3539914127d03-b3941e2b48b44cfdb5e7e341efb80374.xml | exited | 0 | logs/1fe153f8ca4c4e6dad44bde193701da9/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/f909b24ea62f4d07b287d009afc59ba2/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/13d5d266bb7043efb0312ac022134dbf/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/6b0395fee5c54600b77faf1717dc552b/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/c8ef0bcf15c0415ba0f85d21efd7bb1d/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/a74b795537f548948aa4fe7f1de4dc2c/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/e74402536a6f4df1b7b1b5fdc2b287df-b16cc8bfe2d94690ba7609870842f655.xml --timeout 120.000000 | exited | 0 | logs/4cc72d2cc85742ad952c7e991f28b821/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e74402536a6f4df1b7b1b5fdc2b287df-b16cc8bfe2d94690ba7609870842f655.xml | exited | 0 | logs/1c14a7c31cfd497baa22c3894964da9b/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/e74402536a6f4df1b7b1b5fdc2b287df-4cc9f7469a7847e7a0cd1e8422f3c960.xml --timeout 120.000000 | exited | 0 | logs/f6499cfdc6a34173a015aad1b047ffee/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e74402536a6f4df1b7b1b5fdc2b287df-4cc9f7469a7847e7a0cd1e8422f3c960.xml | exited | 0 | logs/5b5049dda81240f09d4ba41a0e794a49/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/e74402536a6f4df1b7b1b5fdc2b287df-e6a7ae2e491f453f8e1c614d7a501d11.xml --timeout 120.000000 | exited | 0 | logs/87d52ac0c4524e7cbf5c99ed49c60af4/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e74402536a6f4df1b7b1b5fdc2b287df-e6a7ae2e491f453f8e1c614d7a501d11.xml | exited | 0 | logs/5e18c3fe55624972ae39cc6b823ed509/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/e74402536a6f4df1b7b1b5fdc2b287df-c62e97a694704739bea2c7c5855100b8.xml --timeout 120.000000 | exited | 0 | logs/ad53ea72796f47d6b12e722d8bdd4109/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/e74402536a6f4df1b7b1b5fdc2b287df-c62e97a694704739bea2c7c5855100b8.xml | exited | 0 | logs/b35811c3ce88445398a3634ab37f76be/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/8bacb5214d5b47d9aa9d227841bb460b/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/e8971388405642e5ab0936be91919a25/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/c5a0005114e146a8877c160a4a4a1d3b/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/24964843ace44b0dab670e0cc489ee51/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/9bbc9f2c3a344a9d894e6a7b42f67212/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/ead5cd02987b4d0f8901115c3c5cfc72-a89cfaf4cc0148fba9c11fab17e0761a.xml --timeout 120.000000 | exited | 0 | logs/9049f7c4ded7490698394de1e66e7a1f/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ead5cd02987b4d0f8901115c3c5cfc72-a89cfaf4cc0148fba9c11fab17e0761a.xml | exited | 0 | logs/548c581873954f90a55f29888ad2cdd0/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/ead5cd02987b4d0f8901115c3c5cfc72-05379a9f06584127baf3d8e18f226e21.xml --timeout 120.000000 | exited | 0 | logs/e9180d82d1904b51bc8a041a793a8b7f/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ead5cd02987b4d0f8901115c3c5cfc72-05379a9f06584127baf3d8e18f226e21.xml | exited | 0 | logs/43651400357540aa89c306dd442698e2/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/ead5cd02987b4d0f8901115c3c5cfc72-809523cf963847d5946677594d26b776.xml --timeout 120.000000 | exited | 0 | logs/af68e7a8923c45b8a816d09df9de0f9e/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ead5cd02987b4d0f8901115c3c5cfc72-809523cf963847d5946677594d26b776.xml | exited | 0 | logs/0384f5bed734411c9b990d193a2a3649/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/ead5cd02987b4d0f8901115c3c5cfc72-f5121864e0c645b882964daad203d960.xml --timeout 120.000000 | exited | 0 | logs/88b9b91c393b400cbbde617b0ee2f2b6/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ead5cd02987b4d0f8901115c3c5cfc72-f5121864e0c645b882964daad203d960.xml | exited | 0 | logs/2f6953ad8220496ebac3daae9b09cbba/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
