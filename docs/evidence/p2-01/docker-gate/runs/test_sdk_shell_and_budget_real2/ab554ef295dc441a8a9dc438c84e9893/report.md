# ReproPatch ab554ef295dc441a8a9dc438c84e9893

任务：negative-maximum
入口：run
结局：**BUDGET\_EXHAUSTED**
原因：TOOL\_BUDGET
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：4d6595b07b341677cf30ec3f6b2cc9b6dfc89690
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：4.137 秒
模型步骤：1；准入工具：0
模型停止原因：TOOL\_BUDGET
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：是；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：43


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/39a0a477d55a45fd8a6bcfb2b755a00c/3f9fb5048d474de19b532d7f880e4e9e.xml |
| baseline | positive\_values | 通过 | evidence/39a0a477d55a45fd8a6bcfb2b755a00c/a68bf18782c74bb6b41220a86d5bee85.xml |
| baseline | empty\_values | 通过 | evidence/39a0a477d55a45fd8a6bcfb2b755a00c/b168f77d32bb457d9ed69407c8ad53ea.xml |
| baseline | mixed\_values | 通过 | evidence/39a0a477d55a45fd8a6bcfb2b755a00c/332cb8900098429ba4387b1449e0e8ad.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/8171cc3d4d7b4b80a2db81dc0262d1e2/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/2e480787151b464f9f5140bdfb875874/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/e69b16045a5147f0994580855689bbe3/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/ea70927c13c2470e9c747aa7e138b49a/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/253551dea24a4879982d2873a623120f/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/39a0a477d55a45fd8a6bcfb2b755a00c-3f9fb5048d474de19b532d7f880e4e9e.xml --timeout 120.000000 | exited | 8 | logs/198524daae424c88b40c71601867660a/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/39a0a477d55a45fd8a6bcfb2b755a00c-3f9fb5048d474de19b532d7f880e4e9e.xml | exited | 0 | logs/4712d1e8ff5c4964a037a91831e92ef7/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/39a0a477d55a45fd8a6bcfb2b755a00c-a68bf18782c74bb6b41220a86d5bee85.xml --timeout 120.000000 | exited | 0 | logs/369e033051a84dd9a982b6b14d76181e/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/39a0a477d55a45fd8a6bcfb2b755a00c-a68bf18782c74bb6b41220a86d5bee85.xml | exited | 0 | logs/91428d5867384a93a3ae42175dfc1a40/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/39a0a477d55a45fd8a6bcfb2b755a00c-b168f77d32bb457d9ed69407c8ad53ea.xml --timeout 120.000000 | exited | 0 | logs/11a23b12ccb14710bf50a33835542d00/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/39a0a477d55a45fd8a6bcfb2b755a00c-b168f77d32bb457d9ed69407c8ad53ea.xml | exited | 0 | logs/04b50017727c447fb8fc890632a62981/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/39a0a477d55a45fd8a6bcfb2b755a00c-332cb8900098429ba4387b1449e0e8ad.xml --timeout 120.000000 | exited | 0 | logs/7d59cb066a5b46819122541f0def1c02/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/39a0a477d55a45fd8a6bcfb2b755a00c-332cb8900098429ba4387b1449e0e8ad.xml | exited | 0 | logs/bc6b9fafa4cf4418a692c51a5eeed095/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
