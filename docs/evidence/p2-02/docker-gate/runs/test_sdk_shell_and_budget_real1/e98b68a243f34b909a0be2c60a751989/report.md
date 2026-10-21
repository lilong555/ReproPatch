# ReproPatch e98b68a243f34b909a0be2c60a751989

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：5dbc1a5c251a8dbf13ef46defbabff1262176639
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：9.652 秒
模型步骤：3；准入工具：2
模型停止原因：MODEL\_FINISHED
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：97


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/104bf29e0019479da875751a5f09c40e/ce66ba3d6c574912bde66bfa202f100f.xml |
| baseline | positive\_values | 通过 | evidence/104bf29e0019479da875751a5f09c40e/5f38b57fe2f6460d84f79c97dacf92d8.xml |
| baseline | empty\_values | 通过 | evidence/104bf29e0019479da875751a5f09c40e/92f00b0489f34ad796655455cedb0175.xml |
| baseline | mixed\_values | 通过 | evidence/104bf29e0019479da875751a5f09c40e/3ad95447da174e03ad3f97185d804c51.xml |
| independent | negative\_values | 通过 | evidence/79f28522d01a4aae81eb1fdda6336142/41b30d9f5bc84a4292dc83e42d8127e9.xml |
| independent | positive\_values | 通过 | evidence/79f28522d01a4aae81eb1fdda6336142/d33d6b1bfdcf4b0dac5a71c390d24d11.xml |
| independent | empty\_values | 通过 | evidence/79f28522d01a4aae81eb1fdda6336142/34efd63f816e42cda718754d7a9b792b.xml |
| independent | mixed\_values | 通过 | evidence/79f28522d01a4aae81eb1fdda6336142/9afc2ac0af194556ae6b80e26f9598b0.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/34809795a78a4153a765d1090302f5d9/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/578211a0ef534af68b167f6e909e7921/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/85ba6760caf14529a93dcea267b916c0/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/56c1565726d54ef2bf99e59ffc38e448/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/bf67e041885e455b9c4bde4b3248a515/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/104bf29e0019479da875751a5f09c40e-ce66ba3d6c574912bde66bfa202f100f.xml --timeout 120.000000 | exited | 8 | logs/10387cf6ca994994bbb3f86e4a82033f/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/104bf29e0019479da875751a5f09c40e-ce66ba3d6c574912bde66bfa202f100f.xml | exited | 0 | logs/3fbe9f7701c64305bade49d109df8b7e/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/104bf29e0019479da875751a5f09c40e-5f38b57fe2f6460d84f79c97dacf92d8.xml --timeout 120.000000 | exited | 0 | logs/36e2c68147e74f148850098879848d41/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/104bf29e0019479da875751a5f09c40e-5f38b57fe2f6460d84f79c97dacf92d8.xml | exited | 0 | logs/8b8f756213b44d1383d41c04ac18028d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/104bf29e0019479da875751a5f09c40e-92f00b0489f34ad796655455cedb0175.xml --timeout 120.000000 | exited | 0 | logs/1e53b40d5f074344a84f00bfdff1298c/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/104bf29e0019479da875751a5f09c40e-92f00b0489f34ad796655455cedb0175.xml | exited | 0 | logs/25589f60c03341a3b3610258beae5a71/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/104bf29e0019479da875751a5f09c40e-3ad95447da174e03ad3f97185d804c51.xml --timeout 120.000000 | exited | 0 | logs/5619d20b8d3e4a6bb37969d3ea5f0df1/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/104bf29e0019479da875751a5f09c40e-3ad95447da174e03ad3f97185d804c51.xml | exited | 0 | logs/1b51f8c346f447719a851966553d6b62/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/cba1e2c3d7164223a3af3c70e5697243/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/0143185ef6eb4d77935b0746852b0723/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/2b575514c46c46b3a81c08c88389e3cc/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/d7a1bccdd54944aab3708f0415782eca/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/8186e66cd0554f3c9711142d56dba173/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/79f28522d01a4aae81eb1fdda6336142-41b30d9f5bc84a4292dc83e42d8127e9.xml --timeout 120.000000 | exited | 0 | logs/20c4769a78c34648ab185507cd13e926/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/79f28522d01a4aae81eb1fdda6336142-41b30d9f5bc84a4292dc83e42d8127e9.xml | exited | 0 | logs/634b3e002c364e708632625ba7f6f6b3/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/79f28522d01a4aae81eb1fdda6336142-d33d6b1bfdcf4b0dac5a71c390d24d11.xml --timeout 120.000000 | exited | 0 | logs/b10bca60f51744859a4c89a0d3b33905/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/79f28522d01a4aae81eb1fdda6336142-d33d6b1bfdcf4b0dac5a71c390d24d11.xml | exited | 0 | logs/2c5fc84f87434fd897fc57a46ffe28af/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/79f28522d01a4aae81eb1fdda6336142-34efd63f816e42cda718754d7a9b792b.xml --timeout 120.000000 | exited | 0 | logs/59c7725e35fc40679d9d4d48ece971e4/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/79f28522d01a4aae81eb1fdda6336142-34efd63f816e42cda718754d7a9b792b.xml | exited | 0 | logs/4414ae08159a4a1f9e03bbe0c4bb5d60/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/79f28522d01a4aae81eb1fdda6336142-9afc2ac0af194556ae6b80e26f9598b0.xml --timeout 120.000000 | exited | 0 | logs/2668a9638632476a88d1b792e8bfbc6d/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/79f28522d01a4aae81eb1fdda6336142-9afc2ac0af194556ae6b80e26f9598b0.xml | exited | 0 | logs/32c914c467af4268b11e34018c1db758/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
