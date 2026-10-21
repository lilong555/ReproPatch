# ReproPatch 9c47bbed8ad2484c995a2df6b8738b31

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：39c1056a68c9ebb9322acd14de094c77dbbffc9d
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：13.517 秒
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
| baseline | negative\_values | 失败 | evidence/61d1f79d160b4026a6ff3fcb0afb7a90/a730aab8e7344c418129a316f7bccfdd.xml |
| baseline | positive\_values | 通过 | evidence/61d1f79d160b4026a6ff3fcb0afb7a90/ab28b6ee20194504b2208bd55e8a0567.xml |
| baseline | empty\_values | 通过 | evidence/61d1f79d160b4026a6ff3fcb0afb7a90/15a2804efa8f4f1383d6f30e5db48688.xml |
| baseline | mixed\_values | 通过 | evidence/61d1f79d160b4026a6ff3fcb0afb7a90/4399c401ab464d678889227445e9e7a7.xml |
| agent\_check | negative\_values | 通过 | evidence/0926bf9ad2574a47a1c9a76766eb8a80/807825835db044479b35707cf90af88b.xml |
| agent\_check | positive\_values | 通过 | evidence/0926bf9ad2574a47a1c9a76766eb8a80/909522f431cb48e1a34b8c63b6af5124.xml |
| agent\_check | empty\_values | 通过 | evidence/0926bf9ad2574a47a1c9a76766eb8a80/97da693c1c6c4edcb13ffddeea13b971.xml |
| agent\_check | mixed\_values | 通过 | evidence/0926bf9ad2574a47a1c9a76766eb8a80/4335ad95b5f54c35a89bba4a37f31157.xml |
| independent | negative\_values | 通过 | evidence/884b96f373784c07ba17b6a9092e37ca/66aff13a19e04c3da39ff0b0df2ad844.xml |
| independent | positive\_values | 通过 | evidence/884b96f373784c07ba17b6a9092e37ca/4ff526687d264ecb899fdab0311d0e2a.xml |
| independent | empty\_values | 通过 | evidence/884b96f373784c07ba17b6a9092e37ca/6d797ebf128a462eab7a19d6299d77c0.xml |
| independent | mixed\_values | 通过 | evidence/884b96f373784c07ba17b6a9092e37ca/e024f9c31c6f45edbe84e9aea551db92.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/3542c7928ced4502b383a71712fc88a0/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/ad847c19269047cc96360553a3e4317a/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/0614291a33fc4b61a464b3045f8c8a28/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/d9deff8f9e4745c88b2c0f5654f3c0d7/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/d6da2cb305dc4c648d03c0ef3f8cc3e3/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/61d1f79d160b4026a6ff3fcb0afb7a90-a730aab8e7344c418129a316f7bccfdd.xml --timeout 120.000000 | exited | 8 | logs/fbe91266fa184a5897cb4f738b8bc132/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/61d1f79d160b4026a6ff3fcb0afb7a90-a730aab8e7344c418129a316f7bccfdd.xml | exited | 0 | logs/755e1dc97cd0470894d80396cc0fa00c/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/61d1f79d160b4026a6ff3fcb0afb7a90-ab28b6ee20194504b2208bd55e8a0567.xml --timeout 120.000000 | exited | 0 | logs/69f77afdd4c44a57a26609578e7bb9c8/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/61d1f79d160b4026a6ff3fcb0afb7a90-ab28b6ee20194504b2208bd55e8a0567.xml | exited | 0 | logs/42b2d763fb324140b222e406dc425b2b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/61d1f79d160b4026a6ff3fcb0afb7a90-15a2804efa8f4f1383d6f30e5db48688.xml --timeout 120.000000 | exited | 0 | logs/c1e0be40f5e347499c07bb1a04d03abc/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/61d1f79d160b4026a6ff3fcb0afb7a90-15a2804efa8f4f1383d6f30e5db48688.xml | exited | 0 | logs/1f4ba4de375446c6bc66ee21f810dd6b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/61d1f79d160b4026a6ff3fcb0afb7a90-4399c401ab464d678889227445e9e7a7.xml --timeout 120.000000 | exited | 0 | logs/013e76a3a7ac42649ec91e4dff4eaac4/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/61d1f79d160b4026a6ff3fcb0afb7a90-4399c401ab464d678889227445e9e7a7.xml | exited | 0 | logs/c68ae3dbd51a479d814f63692f22072d/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/9c4153ade5e242f488218a375680f30b/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/c45ed7f58f2345f889a6aae420778329/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/f94cd8d8bf7f4aafb96e86474d347e06/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/222ceb10a69a456e848cd764ee83d2ba/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/1d67f6e94c844653adc6a66aeb7b660e/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/0926bf9ad2574a47a1c9a76766eb8a80-807825835db044479b35707cf90af88b.xml --timeout 120.000000 | exited | 0 | logs/8eba4712a78743bf8d8f278d73a52f18/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0926bf9ad2574a47a1c9a76766eb8a80-807825835db044479b35707cf90af88b.xml | exited | 0 | logs/48ba20ca8706497098387cd49026cd90/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/0926bf9ad2574a47a1c9a76766eb8a80-909522f431cb48e1a34b8c63b6af5124.xml --timeout 120.000000 | exited | 0 | logs/8be6c0126f6444839540beb0702d03bf/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0926bf9ad2574a47a1c9a76766eb8a80-909522f431cb48e1a34b8c63b6af5124.xml | exited | 0 | logs/3a5f31b2e4c04e108db029eb5cd3dd13/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/0926bf9ad2574a47a1c9a76766eb8a80-97da693c1c6c4edcb13ffddeea13b971.xml --timeout 120.000000 | exited | 0 | logs/0f4fa1b057a846d6b6c4e44a33b136f5/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0926bf9ad2574a47a1c9a76766eb8a80-97da693c1c6c4edcb13ffddeea13b971.xml | exited | 0 | logs/4956e8d4f5434926b3fe11ed42f309e6/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/0926bf9ad2574a47a1c9a76766eb8a80-4335ad95b5f54c35a89bba4a37f31157.xml --timeout 120.000000 | exited | 0 | logs/c804d379548642c996aba5365998343a/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0926bf9ad2574a47a1c9a76766eb8a80-4335ad95b5f54c35a89bba4a37f31157.xml | exited | 0 | logs/23eaee92667e447895cf6072bee72414/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/a86bc1dd4fe8406ba609d417d72a5c1f/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/58eba02e4ed84008adca1eef1dca3679/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/b91e3bbeab3148da81b10cbec006d788/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/4f851afee45a45f3bacbffe706dd45e7/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/c4fb4dabccd24972a6e0454ec76a599e/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/884b96f373784c07ba17b6a9092e37ca-66aff13a19e04c3da39ff0b0df2ad844.xml --timeout 120.000000 | exited | 0 | logs/3b203d82297d421fb9ef957bf4b81a13/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/884b96f373784c07ba17b6a9092e37ca-66aff13a19e04c3da39ff0b0df2ad844.xml | exited | 0 | logs/2eb83360b1fa4fcaa3a12dd5aec14ddc/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/884b96f373784c07ba17b6a9092e37ca-4ff526687d264ecb899fdab0311d0e2a.xml --timeout 120.000000 | exited | 0 | logs/b7462aa38e2744c080cc26b2e3eb8b24/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/884b96f373784c07ba17b6a9092e37ca-4ff526687d264ecb899fdab0311d0e2a.xml | exited | 0 | logs/d7c3060d16c54eb28c17a4a252923a79/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/884b96f373784c07ba17b6a9092e37ca-6d797ebf128a462eab7a19d6299d77c0.xml --timeout 120.000000 | exited | 0 | logs/2d1cd3bc492244d8b8575234cb1d12cf/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/884b96f373784c07ba17b6a9092e37ca-6d797ebf128a462eab7a19d6299d77c0.xml | exited | 0 | logs/1e8edc5d45c94c81b9f95644b5aba614/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/884b96f373784c07ba17b6a9092e37ca-e024f9c31c6f45edbe84e9aea551db92.xml --timeout 120.000000 | exited | 0 | logs/07278263be4948449e8ec8da5d7e1f9c/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/884b96f373784c07ba17b6a9092e37ca-e024f9c31c6f45edbe84e9aea551db92.xml | exited | 0 | logs/44064528c0f240289da4bc0524ad5785/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
