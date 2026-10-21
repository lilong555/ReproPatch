# ReproPatch 2536f181ab69485994f6523ca6f19c44

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：075a19d1b097d96df3550d2f08d20a0076705210
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：12.008 秒
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
| baseline | negative\_values | 失败 | evidence/ab93b562719f432d8f0806bb7158abdd/bcfceab4a15446d2ba62e0bf85c815a4.xml |
| baseline | positive\_values | 通过 | evidence/ab93b562719f432d8f0806bb7158abdd/2154196ca7f44bdbb54bab8a9d1111b1.xml |
| baseline | empty\_values | 通过 | evidence/ab93b562719f432d8f0806bb7158abdd/c34719c89be64b3ca84714f7b3b31353.xml |
| baseline | mixed\_values | 通过 | evidence/ab93b562719f432d8f0806bb7158abdd/1b1895bfdff84c09b9f36332486e7db6.xml |
| agent\_check | negative\_values | 通过 | evidence/88a8b2c1df94407693b32860acf0b9c5/90642c812eb34e178317ba90a5da8042.xml |
| agent\_check | positive\_values | 通过 | evidence/88a8b2c1df94407693b32860acf0b9c5/297edf4f5c8948cc937a2d5dbf46279e.xml |
| agent\_check | empty\_values | 通过 | evidence/88a8b2c1df94407693b32860acf0b9c5/f695786e3ff94079be9dd90069b14e13.xml |
| agent\_check | mixed\_values | 通过 | evidence/88a8b2c1df94407693b32860acf0b9c5/a2bfa994f9344bc48533392e8b658653.xml |
| independent | negative\_values | 通过 | evidence/01ed3d6fb50e4bebb57058fde0951a4b/1125f950b04d481584c988b837ee405c.xml |
| independent | positive\_values | 通过 | evidence/01ed3d6fb50e4bebb57058fde0951a4b/385e80cff7424d0688c6d452a3974012.xml |
| independent | empty\_values | 通过 | evidence/01ed3d6fb50e4bebb57058fde0951a4b/b8582474e41742d89629efb5a12b7c69.xml |
| independent | mixed\_values | 通过 | evidence/01ed3d6fb50e4bebb57058fde0951a4b/8cbb5c334ed243ea98bb6ef41533204b.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/e959f20228ae40659405bde0ea0a7dd2/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/127006a1d7e441cb80777e26e805d5c4/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/78336477302642639e62e56f91ab7795/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/29ec61488825462e957e9097f6121ac0/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/e5653f55e42947dfad52d006f8870325/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/ab93b562719f432d8f0806bb7158abdd-bcfceab4a15446d2ba62e0bf85c815a4.xml --timeout 120.000000 | exited | 8 | logs/edaee1c5b8e54e15a0649d65c16a9d7d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ab93b562719f432d8f0806bb7158abdd-bcfceab4a15446d2ba62e0bf85c815a4.xml | exited | 0 | logs/f2cf91f4a7474103ac8708d59ff32a05/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/ab93b562719f432d8f0806bb7158abdd-2154196ca7f44bdbb54bab8a9d1111b1.xml --timeout 120.000000 | exited | 0 | logs/b06be7fc93e3427396dccf289df9618f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ab93b562719f432d8f0806bb7158abdd-2154196ca7f44bdbb54bab8a9d1111b1.xml | exited | 0 | logs/9dfebdd891f64de1961fdcecc26e078a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/ab93b562719f432d8f0806bb7158abdd-c34719c89be64b3ca84714f7b3b31353.xml --timeout 120.000000 | exited | 0 | logs/ec1ff36183b847ef8abac9651ad91d64/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ab93b562719f432d8f0806bb7158abdd-c34719c89be64b3ca84714f7b3b31353.xml | exited | 0 | logs/4d46a306a3f04521b2568d6b16d5fc7a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/ab93b562719f432d8f0806bb7158abdd-1b1895bfdff84c09b9f36332486e7db6.xml --timeout 120.000000 | exited | 0 | logs/8bacd74c212942178a72fb65827dba72/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/ab93b562719f432d8f0806bb7158abdd-1b1895bfdff84c09b9f36332486e7db6.xml | exited | 0 | logs/66c7e8c4231445f0a7b3774f8773e430/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/bbc53da8ca1b4c9995cefe26abaa713f/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/34aadeac63ef4966be56e2aac20767c6/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/0d60f8686ef644cbaba22847b9c355c6/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/a801a3961f324bc5a3e42a4eeea8c563/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/1ed0557ca6a042738f191333c7f198e5/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/88a8b2c1df94407693b32860acf0b9c5-90642c812eb34e178317ba90a5da8042.xml --timeout 120.000000 | exited | 0 | logs/1465f7474c3c4348ad9d92771d966154/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/88a8b2c1df94407693b32860acf0b9c5-90642c812eb34e178317ba90a5da8042.xml | exited | 0 | logs/3ac1e6961122483c9d802f90b63827d6/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/88a8b2c1df94407693b32860acf0b9c5-297edf4f5c8948cc937a2d5dbf46279e.xml --timeout 120.000000 | exited | 0 | logs/6763c2e62a4d42cb89d6c0b36d2853c9/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/88a8b2c1df94407693b32860acf0b9c5-297edf4f5c8948cc937a2d5dbf46279e.xml | exited | 0 | logs/2c5e867d04b7486689d63f7adc8cb68f/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/88a8b2c1df94407693b32860acf0b9c5-f695786e3ff94079be9dd90069b14e13.xml --timeout 120.000000 | exited | 0 | logs/0fb3cca19f5e4c7894e536d2ce9d5a7e/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/88a8b2c1df94407693b32860acf0b9c5-f695786e3ff94079be9dd90069b14e13.xml | exited | 0 | logs/1e3bbb181e0f488bb2d96548d8dcbc71/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/88a8b2c1df94407693b32860acf0b9c5-a2bfa994f9344bc48533392e8b658653.xml --timeout 120.000000 | exited | 0 | logs/8645a255a80b4e619dfdeebdc718e255/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/88a8b2c1df94407693b32860acf0b9c5-a2bfa994f9344bc48533392e8b658653.xml | exited | 0 | logs/604530bf425c45a295ac893028d24266/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/2e86a29c26fb4c3296b98077fc04b07e/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/6b3e8ec415374b70aad7bcd1afe2c290/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/e6f906614eae4673b73419a3dce326ca/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/e2f932afaf0946dda22e6de987c86706/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/370ca27b1646498e8a1dceee34d5e92b/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/01ed3d6fb50e4bebb57058fde0951a4b-1125f950b04d481584c988b837ee405c.xml --timeout 120.000000 | exited | 0 | logs/bdacde2ae2cc4a98bca8e52cadf21883/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/01ed3d6fb50e4bebb57058fde0951a4b-1125f950b04d481584c988b837ee405c.xml | exited | 0 | logs/cd4f03445c4b493a95f75a9a13b869a2/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/01ed3d6fb50e4bebb57058fde0951a4b-385e80cff7424d0688c6d452a3974012.xml --timeout 120.000000 | exited | 0 | logs/8ee9cc7f77634c6982bb861fe1005880/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/01ed3d6fb50e4bebb57058fde0951a4b-385e80cff7424d0688c6d452a3974012.xml | exited | 0 | logs/221541eb19a743519d3a1d96b0c99c49/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/01ed3d6fb50e4bebb57058fde0951a4b-b8582474e41742d89629efb5a12b7c69.xml --timeout 120.000000 | exited | 0 | logs/8437a743d2464737a2863f6bef8aacc4/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/01ed3d6fb50e4bebb57058fde0951a4b-b8582474e41742d89629efb5a12b7c69.xml | exited | 0 | logs/15a28dacfc9a49b1a2cd08e8f9c00714/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/01ed3d6fb50e4bebb57058fde0951a4b-8cbb5c334ed243ea98bb6ef41533204b.xml --timeout 120.000000 | exited | 0 | logs/d2119b3bd6a34342867bdda2c8813bc0/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/01ed3d6fb50e4bebb57058fde0951a4b-8cbb5c334ed243ea98bb6ef41533204b.xml | exited | 0 | logs/6666948423184e40ab071df01def74f7/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
