# ReproPatch a1b38dd046c74ae0a0d2f5d256ec3b2b

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：REQUIRED\_TEST\_NOT\_RUN
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：80b64c76a066ee655a3fb3a39ba95803696af9ad
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：6.479 秒
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
| baseline | negative\_values | 失败 | evidence/838d9a46d73b477e91af8b91a634c98b/1a3c6dcf63ea440c82865e16632b356f.xml |
| baseline | positive\_values | 通过 | evidence/838d9a46d73b477e91af8b91a634c98b/9d2f4fc6922640269ccf4cd121720ad9.xml |
| baseline | empty\_values | 通过 | evidence/838d9a46d73b477e91af8b91a634c98b/d18cddb33535465fb08562490bc74226.xml |
| baseline | mixed\_values | 通过 | evidence/838d9a46d73b477e91af8b91a634c98b/2008991edbdb459ebc52c37eac70de85.xml |
| independent | negative\_values | 未运行 | 未知 |
| independent | positive\_values | 未运行 | 未知 |
| independent | empty\_values | 未运行 | 未知 |
| independent | mixed\_values | 未运行 | 未知 |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/fae10d48115345b39bfd88efc7b29771/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/ee63b1c0df5d4ff8b8b0c75a45180f0a/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/b5b4f840cc12482493cd70322d0795b7/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/9897f7a0ab2c4fd699bd0f893c2cd656/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/c594c0e4856a4a5b8aeb6f0c5523d9ca/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/838d9a46d73b477e91af8b91a634c98b-1a3c6dcf63ea440c82865e16632b356f.xml --timeout 120.000000 | exited | 8 | logs/79ba8c014fcc4c33a7439f98dd00230c/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/838d9a46d73b477e91af8b91a634c98b-1a3c6dcf63ea440c82865e16632b356f.xml | exited | 0 | logs/0ac937d906dc4b6ab63ee5e3a5a7a2cf/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/838d9a46d73b477e91af8b91a634c98b-9d2f4fc6922640269ccf4cd121720ad9.xml --timeout 120.000000 | exited | 0 | logs/98c2689f039149a08f3c5f5f5008dc23/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/838d9a46d73b477e91af8b91a634c98b-9d2f4fc6922640269ccf4cd121720ad9.xml | exited | 0 | logs/e672205c70294e90839dadd05d949664/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/838d9a46d73b477e91af8b91a634c98b-d18cddb33535465fb08562490bc74226.xml --timeout 120.000000 | exited | 0 | logs/45bc86533b784ebfa4940fa5945430a1/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/838d9a46d73b477e91af8b91a634c98b-d18cddb33535465fb08562490bc74226.xml | exited | 0 | logs/3e21f566874e4bf5907c2dc04cb6c32d/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/838d9a46d73b477e91af8b91a634c98b-2008991edbdb459ebc52c37eac70de85.xml --timeout 120.000000 | exited | 0 | logs/8240225e07834601a5edcf5df05e0e75/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/838d9a46d73b477e91af8b91a634c98b-2008991edbdb459ebc52c37eac70de85.xml | exited | 0 | logs/38c45904bbb14e1a943f71d1af25eb2f/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/ac7974ca349d4962a920fdc76a3a9569/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/3ee1fe101b8145ceb9bd78c049d44d03/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/94b43bb6243245369447d64255260d49/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/8532aa6b17b24f199a2ac2bbd586572c/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
