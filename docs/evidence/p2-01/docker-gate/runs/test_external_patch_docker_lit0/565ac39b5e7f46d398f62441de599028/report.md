# ReproPatch 565ac39b5e7f46d398f62441de599028

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：85b411ae788f6b5a0dad12f17bb91f6e63a011c3
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.206 秒
模型步骤：0；准入工具：0
模型停止原因：未知
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：否；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：73


| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | parse\[value\]+edge | 失败 | evidence/3dd3323e28ed49c6921f30548e97e988/5798aa5fc2fc45578cfdab98ae46d195.xml |
| baseline | positive\_values | 通过 | evidence/3dd3323e28ed49c6921f30548e97e988/3abbb9d518b848b69b7c5471d563581a.xml |
| baseline | empty\_values | 通过 | evidence/3dd3323e28ed49c6921f30548e97e988/b63612394bc54dd8b67d4d8f4455f572.xml |
| baseline | mixed\_values | 通过 | evidence/3dd3323e28ed49c6921f30548e97e988/5256274907564e2d9db3cc98af8de87a.xml |
| independent | parse\[value\]+edge | 通过 | evidence/06068c76bc8b4ceb8bde0045e0331507/3cebad01ffe8445296be38d7eb6c53db.xml |
| independent | positive\_values | 通过 | evidence/06068c76bc8b4ceb8bde0045e0331507/df9c3106500c4aa08c8c1bd050edcce3.xml |
| independent | empty\_values | 通过 | evidence/06068c76bc8b4ceb8bde0045e0331507/c3019d131f51430aacbd75c5320a0ca6.xml |
| independent | mixed\_values | 通过 | evidence/06068c76bc8b4ceb8bde0045e0331507/6e952fe0e459490d95a1c9354af297fe.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/8426ef931a6c4c50909e67ecb8de793c/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/f23d37d6e7274ddfb6b96e4e68b7dc11/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/df9967e8519e42369273980258b621bc/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/9970cb0d7ac14c518f0bbada6fb1e3f8/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/fda8f2f4ed9d4da785551c1e0170a693/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\\\[value\\\]\\+edge$ --output-junit /build/.repropatch-results/3dd3323e28ed49c6921f30548e97e988-5798aa5fc2fc45578cfdab98ae46d195.xml --timeout 120.000000 | exited | 8 | logs/f6c122fa4ce14717873a339820fafaa8/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3dd3323e28ed49c6921f30548e97e988-5798aa5fc2fc45578cfdab98ae46d195.xml | exited | 0 | logs/f2b3140f7f5a47a9bcf1169f6cb5f273/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/3dd3323e28ed49c6921f30548e97e988-3abbb9d518b848b69b7c5471d563581a.xml --timeout 120.000000 | exited | 0 | logs/24ca5dff16ae427db80d4bde9870300d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3dd3323e28ed49c6921f30548e97e988-3abbb9d518b848b69b7c5471d563581a.xml | exited | 0 | logs/dfbcca5b9f8b464c80443def2968ba90/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/3dd3323e28ed49c6921f30548e97e988-b63612394bc54dd8b67d4d8f4455f572.xml --timeout 120.000000 | exited | 0 | logs/829f3a5f7a5248e7a3324ad3cabd19ac/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3dd3323e28ed49c6921f30548e97e988-b63612394bc54dd8b67d4d8f4455f572.xml | exited | 0 | logs/9b9a99a4ffc0432b92332b43f7c7a244/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/3dd3323e28ed49c6921f30548e97e988-5256274907564e2d9db3cc98af8de87a.xml --timeout 120.000000 | exited | 0 | logs/6d1c8670dfff4d08a5b2d7e77b23a823/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/3dd3323e28ed49c6921f30548e97e988-5256274907564e2d9db3cc98af8de87a.xml | exited | 0 | logs/80ca1618cf994ad2a10039aa2a930722/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/31cd59814ce24f758d94850319e56c1d/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/0268ec5561ea4e109904cd830087b0d1/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/457c3f11141a472083a3fa7ccc1e6eb0/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/2d4279b2cd1a4a7fbb66a3f381af4870/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/6c2d03f6c3ae49a69c509b1fc4192d07/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\\\[value\\\]\\+edge$ --output-junit /build/.repropatch-results/06068c76bc8b4ceb8bde0045e0331507-3cebad01ffe8445296be38d7eb6c53db.xml --timeout 120.000000 | exited | 0 | logs/c868f9b8660c424abee6157b39387848/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/06068c76bc8b4ceb8bde0045e0331507-3cebad01ffe8445296be38d7eb6c53db.xml | exited | 0 | logs/f27a720779224bb2a2646c6d9ccb1b05/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/06068c76bc8b4ceb8bde0045e0331507-df9c3106500c4aa08c8c1bd050edcce3.xml --timeout 120.000000 | exited | 0 | logs/34926cc95ea2406fb57a5b3808807066/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/06068c76bc8b4ceb8bde0045e0331507-df9c3106500c4aa08c8c1bd050edcce3.xml | exited | 0 | logs/324543c8b1fe4f069fb9dcd6b86e58dd/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/06068c76bc8b4ceb8bde0045e0331507-c3019d131f51430aacbd75c5320a0ca6.xml --timeout 120.000000 | exited | 0 | logs/fc5bf683f20a482cb696b559e327bfd3/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/06068c76bc8b4ceb8bde0045e0331507-c3019d131f51430aacbd75c5320a0ca6.xml | exited | 0 | logs/3d5d2e370b9c4e4590e416e90da6664b/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/06068c76bc8b4ceb8bde0045e0331507-6e952fe0e459490d95a1c9354af297fe.xml --timeout 120.000000 | exited | 0 | logs/92d35b74ee004b94b1fa1254ec952115/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/06068c76bc8b4ceb8bde0045e0331507-6e952fe0e459490d95a1c9354af297fe.xml | exited | 0 | logs/15f973a57a9243ffb2166b3f7c73598c/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
