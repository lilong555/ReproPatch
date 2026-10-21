# ReproPatch a61734706af545179f7ae74b1974ddaf

任务：negative-maximum
入口：verify-patch
结局：**REJECTED**
原因：REQUIRED\_TEST\_NOT\_RUN
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：df81346ebf8bc5afb7562df85197e566aca8b747
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：6.763 秒
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
| baseline | negative\_values | 失败 | evidence/0d994fdd30d14b8d9619acd4171273e7/ef68c6646e4c45dbbefade3da7f43463.xml |
| baseline | positive\_values | 通过 | evidence/0d994fdd30d14b8d9619acd4171273e7/8b605bbbd7664a29a41a910034012506.xml |
| baseline | empty\_values | 通过 | evidence/0d994fdd30d14b8d9619acd4171273e7/ea9393d6d5684ae18372212c47d23704.xml |
| baseline | mixed\_values | 通过 | evidence/0d994fdd30d14b8d9619acd4171273e7/d209f23d06d04da887427eb77a092f6b.xml |
| independent | negative\_values | 未运行 | 未知 |
| independent | positive\_values | 未运行 | 未知 |
| independent | empty\_values | 未运行 | 未知 |
| independent | mixed\_values | 未运行 | 未知 |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/e30bb89e55e9442fa32fdc9e4464e398/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/e81526a077d3474e8f2ad94e59c1fe70/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/f3442d6b36d141efa157875093747909/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/b2cbfa40ae184f15a8b06518443087d5/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/8ff3766220ed447fad0f89fd8284a347/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/0d994fdd30d14b8d9619acd4171273e7-ef68c6646e4c45dbbefade3da7f43463.xml --timeout 120.000000 | exited | 8 | logs/41e2012d6d2c441680e1272d79460747/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0d994fdd30d14b8d9619acd4171273e7-ef68c6646e4c45dbbefade3da7f43463.xml | exited | 0 | logs/aec4baae3ec74b09a78128194020e2d7/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/0d994fdd30d14b8d9619acd4171273e7-8b605bbbd7664a29a41a910034012506.xml --timeout 120.000000 | exited | 0 | logs/0bb0396ebed648f1a77dbf79926ee520/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0d994fdd30d14b8d9619acd4171273e7-8b605bbbd7664a29a41a910034012506.xml | exited | 0 | logs/def23a7d979e470e82ddabaf38babf9b/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/0d994fdd30d14b8d9619acd4171273e7-ea9393d6d5684ae18372212c47d23704.xml --timeout 120.000000 | exited | 0 | logs/9c1d79ba6dce4f0d85db2f38706b4b16/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0d994fdd30d14b8d9619acd4171273e7-ea9393d6d5684ae18372212c47d23704.xml | exited | 0 | logs/d43a664f52bf42438f2198b920dbeba8/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/0d994fdd30d14b8d9619acd4171273e7-d209f23d06d04da887427eb77a092f6b.xml --timeout 120.000000 | exited | 0 | logs/51d8cf1d384b4480ad35abef38312ba3/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/0d994fdd30d14b8d9619acd4171273e7-d209f23d06d04da887427eb77a092f6b.xml | exited | 0 | logs/2723d2da3a3d45dc900214236936f2a1/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/3f2759d8b559487dbbfb7f1ec8f2bdb5/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/477a929885bb4c48a2062576de5cb30d/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/f1dfdcbd57e04e3c9ff97f85e6916076/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/a089fd953cc0472fb4cfbcaf35025906/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
