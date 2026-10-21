# ReproPatch fd8fc11cf791434692fc46eda7e612e4

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：REQUIRED\_TEST\_NOT\_RUN
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：016a5f0bfbd83dfa36cdfe5046d06e923b4b610e
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：6.165 秒
模型步骤：0；准入工具：0
模型停止原因：未知
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：否；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：55


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/4d6301865f654325b34c1624a2ebe4f9/0550554afa4c47da8519f494b9969b89.xml |
| baseline | positive\_values | 通过 | evidence/4d6301865f654325b34c1624a2ebe4f9/f20a9bb31c8147c8b7bf195563e0c317.xml |
| baseline | empty\_values | 通过 | evidence/4d6301865f654325b34c1624a2ebe4f9/2be283b8e97f4ec0b896da585a74fd6a.xml |
| baseline | mixed\_values | 通过 | evidence/4d6301865f654325b34c1624a2ebe4f9/b952c7f3b8bb46b68433dfd826c833aa.xml |
| independent | negative\_values | 未运行 | 未知 |
| independent | positive\_values | 未运行 | 未知 |
| independent | empty\_values | 未运行 | 未知 |
| independent | mixed\_values | 未运行 | 未知 |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/e2ca865ebde14535a7cc240570c880f2/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/049f53bdce54427aac74c69ec5fd88fc/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/4cedeb5e5fd841608006c830f5dca52e/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/bb706860c533491bb193eb8fe783b213/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/b995f6e6b56848748b4e0aebc19a023d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/4d6301865f654325b34c1624a2ebe4f9-0550554afa4c47da8519f494b9969b89.xml --timeout 120.000000 | exited | 8 | logs/d7b3860df50e4c5a979ea41fabd3bead/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4d6301865f654325b34c1624a2ebe4f9-0550554afa4c47da8519f494b9969b89.xml | exited | 0 | logs/b106136ed51e4696a0e0730cabebdf2a/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/4d6301865f654325b34c1624a2ebe4f9-f20a9bb31c8147c8b7bf195563e0c317.xml --timeout 120.000000 | exited | 0 | logs/d2669da74259465ead1ae0884e9f3ffd/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4d6301865f654325b34c1624a2ebe4f9-f20a9bb31c8147c8b7bf195563e0c317.xml | exited | 0 | logs/6722ecad03c34086a3faa26b67dc575f/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/4d6301865f654325b34c1624a2ebe4f9-2be283b8e97f4ec0b896da585a74fd6a.xml --timeout 120.000000 | exited | 0 | logs/8c92bb335a974fcb986899e52da23fc9/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4d6301865f654325b34c1624a2ebe4f9-2be283b8e97f4ec0b896da585a74fd6a.xml | exited | 0 | logs/38cded33f2ad4203bd05ed448e1951fe/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/4d6301865f654325b34c1624a2ebe4f9-b952c7f3b8bb46b68433dfd826c833aa.xml --timeout 120.000000 | exited | 0 | logs/230fc5044be744b0b39a7d5d52b3f438/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/4d6301865f654325b34c1624a2ebe4f9-b952c7f3b8bb46b68433dfd826c833aa.xml | exited | 0 | logs/cf02f3193a644e5e959acb33dab98880/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/872f2471c77d423d97e59fc5e7f81d34/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/e620f8e0317a4ad2b9c2b21012a9a534/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/58857e229a984311826218ff842ce020/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/c3e81238a3824de08f04c11dd5eb0570/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
恢复仅支持已提交且关闭的完整输入边界；未知模型请求和历史工具不重做。
外部生成过程、预算和 trace 未受本次运行管理或验证。
