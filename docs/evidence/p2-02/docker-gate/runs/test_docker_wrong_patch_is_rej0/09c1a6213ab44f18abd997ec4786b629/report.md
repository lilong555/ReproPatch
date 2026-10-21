# ReproPatch 09c1a6213ab44f18abd997ec4786b629

任务：negative-maximum
入口：run
结局：**REJECTED**
原因：F2P\_FAILED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：6107172d8ec4f9e5504fa36a1b9afa21113e81f9
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.548 秒
模型步骤：2；准入工具：1
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：85


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/b93d9691c823413e8c400d1fb1be4d17/6b0035b0d6394e368effe0862d70b5d1.xml |
| baseline | positive\_values | 通过 | evidence/b93d9691c823413e8c400d1fb1be4d17/a3b1cc4fd1d14b46ad2d4bc87ec010bc.xml |
| baseline | empty\_values | 通过 | evidence/b93d9691c823413e8c400d1fb1be4d17/704b712fab2143b5ad87d51060818e1f.xml |
| baseline | mixed\_values | 通过 | evidence/b93d9691c823413e8c400d1fb1be4d17/bb6dc8e1f62f4f209537701ba678a0e1.xml |
| independent | negative\_values | 失败 | evidence/081bba79a2d14b3faa41f14c58814f11/f3d0d2c26835419395444aa5ad901e3d.xml |
| independent | positive\_values | 通过 | evidence/081bba79a2d14b3faa41f14c58814f11/d23cda1d28d9499bb6baab06d01b97ca.xml |
| independent | empty\_values | 通过 | evidence/081bba79a2d14b3faa41f14c58814f11/df6eebdb0d5e4195a0d2aa1eba5f254b.xml |
| independent | mixed\_values | 通过 | evidence/081bba79a2d14b3faa41f14c58814f11/1d890d4abef442d4896d3c0a55bf768e.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/cb4132a3501b4dea864c6ee08ecb0db0/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/c7f14316a1c340b3beb374763b1949c5/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/c18a33e405ad42a1bf28914c23a6b2c5/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/f4f1eca028994486b1a00040598e3157/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/91925b76691d41ea887fd9c048529cdc/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/b93d9691c823413e8c400d1fb1be4d17-6b0035b0d6394e368effe0862d70b5d1.xml --timeout 120.000000 | exited | 8 | logs/e69ac8396e8046689e44cff1504e438e/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b93d9691c823413e8c400d1fb1be4d17-6b0035b0d6394e368effe0862d70b5d1.xml | exited | 0 | logs/79d8bc7c4ddc4dae943befd408202e74/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/b93d9691c823413e8c400d1fb1be4d17-a3b1cc4fd1d14b46ad2d4bc87ec010bc.xml --timeout 120.000000 | exited | 0 | logs/c1807eebcc4e45c6945906fe4e90f931/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b93d9691c823413e8c400d1fb1be4d17-a3b1cc4fd1d14b46ad2d4bc87ec010bc.xml | exited | 0 | logs/75874694cb9f443c98ba60e73d7b0171/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/b93d9691c823413e8c400d1fb1be4d17-704b712fab2143b5ad87d51060818e1f.xml --timeout 120.000000 | exited | 0 | logs/a779431b534442b6ac8a196c95b94291/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b93d9691c823413e8c400d1fb1be4d17-704b712fab2143b5ad87d51060818e1f.xml | exited | 0 | logs/d1e51963224144f29eefde743f9ed4c5/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/b93d9691c823413e8c400d1fb1be4d17-bb6dc8e1f62f4f209537701ba678a0e1.xml --timeout 120.000000 | exited | 0 | logs/97c7cc4ce09441f49bef6a1776c42c55/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/b93d9691c823413e8c400d1fb1be4d17-bb6dc8e1f62f4f209537701ba678a0e1.xml | exited | 0 | logs/9872aa5b2ecf4c79adaf0aa142395ce2/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/236ec02dc143470ea69ddf51c8b26c26/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/b7d0c922ef47466c94ec1e11c4cf5229/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/3d24537d4e444c5683da09534f1db3e3/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/60f2dc85c7ea496d81c71ae9d9bdb832/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/46728f16b7304e15a85a0ea447a8d0cc/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/081bba79a2d14b3faa41f14c58814f11-f3d0d2c26835419395444aa5ad901e3d.xml --timeout 120.000000 | exited | 8 | logs/ba41f451afec4940b962ddc029edbdaf/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/081bba79a2d14b3faa41f14c58814f11-f3d0d2c26835419395444aa5ad901e3d.xml | exited | 0 | logs/c4f8da4431e1463cb9a5455bcb07ec93/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/081bba79a2d14b3faa41f14c58814f11-d23cda1d28d9499bb6baab06d01b97ca.xml --timeout 120.000000 | exited | 0 | logs/6fd1405f6c5a4356946212ca549ffb90/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/081bba79a2d14b3faa41f14c58814f11-d23cda1d28d9499bb6baab06d01b97ca.xml | exited | 0 | logs/0d6b66815dda4b8f8c0f9249ba1f811e/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/081bba79a2d14b3faa41f14c58814f11-df6eebdb0d5e4195a0d2aa1eba5f254b.xml --timeout 120.000000 | exited | 0 | logs/db3b98e9e06544d5964180ff2335a407/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/081bba79a2d14b3faa41f14c58814f11-df6eebdb0d5e4195a0d2aa1eba5f254b.xml | exited | 0 | logs/06db98bc860449beb62dd14f17404acc/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/081bba79a2d14b3faa41f14c58814f11-1d890d4abef442d4896d3c0a55bf768e.xml --timeout 120.000000 | exited | 0 | logs/945af6852c9c4614bd56db1fbc5ce1eb/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/081bba79a2d14b3faa41f14c58814f11-1d890d4abef442d4896d3c0a55bf768e.xml | exited | 0 | logs/e0b800c2eef940ba8ebef528141d7bce/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
