# ReproPatch b2ce17a4145c419cabe27e9d4fc6dfc3

任务：negative-maximum
入口：run
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：fake
模型：未知
Docker 隔离：是
基线 commit：cda9cc25f067a0e23e0f6664f548df449c1c021f
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：13.470 秒
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
| baseline | negative\_values | 失败 | evidence/893fe0aaa1b544f0a4463df1d3f5ded9/82b3674301d744758fbc53b0396831c0.xml |
| baseline | positive\_values | 通过 | evidence/893fe0aaa1b544f0a4463df1d3f5ded9/b8684e35e5af409ab2bfc45159e9f47c.xml |
| baseline | empty\_values | 通过 | evidence/893fe0aaa1b544f0a4463df1d3f5ded9/d53f4ef93cba4798b67dfe7e9c8cf9b9.xml |
| baseline | mixed\_values | 通过 | evidence/893fe0aaa1b544f0a4463df1d3f5ded9/4e8c1961f75742319937b6ed0a271db5.xml |
| agent\_check | negative\_values | 通过 | evidence/25bc5e0d5ce54417ac808cad7a94ff93/858bd10d29064146b1241ea9495baa3e.xml |
| agent\_check | positive\_values | 通过 | evidence/25bc5e0d5ce54417ac808cad7a94ff93/607e684f2d784ce89836cd54ede07a8a.xml |
| agent\_check | empty\_values | 通过 | evidence/25bc5e0d5ce54417ac808cad7a94ff93/b13fe98d1ec74aa58d5be32acae89d86.xml |
| agent\_check | mixed\_values | 通过 | evidence/25bc5e0d5ce54417ac808cad7a94ff93/10ec9d7e73044532b0b82702381e1645.xml |
| independent | negative\_values | 通过 | evidence/5e4c372425c741fb8917c8e77e876a5b/8c1ff0c2ad3242a889a6541f9aa2b9b6.xml |
| independent | positive\_values | 通过 | evidence/5e4c372425c741fb8917c8e77e876a5b/cd7c9041f6d441f59b2670eb9c45862e.xml |
| independent | empty\_values | 通过 | evidence/5e4c372425c741fb8917c8e77e876a5b/0b0a48be214d4aa3a0ba99898b66b43f.xml |
| independent | mixed\_values | 通过 | evidence/5e4c372425c741fb8917c8e77e876a5b/b5922773f1fc4ddf9eaaa2c883e288fc.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/d3435b9219df44c3b3602a172cd22ed1/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/a3d1d0c246b945a7814598ca21fa1dd8/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/a486b4ef265343679db958c9eaf42c62/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/97b6ff861c9e4b16b3aa40c60eb759d6/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/afd2f2e5258b45fab5f8c0f4b6f1e197/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/893fe0aaa1b544f0a4463df1d3f5ded9-82b3674301d744758fbc53b0396831c0.xml --timeout 120.000000 | exited | 8 | logs/93119feb767b48c9a814e0c8d9e2fac0/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/893fe0aaa1b544f0a4463df1d3f5ded9-82b3674301d744758fbc53b0396831c0.xml | exited | 0 | logs/fc6b999e458f40c686e0d3ab2a3942fb/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/893fe0aaa1b544f0a4463df1d3f5ded9-b8684e35e5af409ab2bfc45159e9f47c.xml --timeout 120.000000 | exited | 0 | logs/d2af0166f1d041f99d972da30ccd5543/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/893fe0aaa1b544f0a4463df1d3f5ded9-b8684e35e5af409ab2bfc45159e9f47c.xml | exited | 0 | logs/bffadd3355684fda9fd5cc1b0ece17e6/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/893fe0aaa1b544f0a4463df1d3f5ded9-d53f4ef93cba4798b67dfe7e9c8cf9b9.xml --timeout 120.000000 | exited | 0 | logs/08294c1b30784d6b87c3dba1ca0f61c8/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/893fe0aaa1b544f0a4463df1d3f5ded9-d53f4ef93cba4798b67dfe7e9c8cf9b9.xml | exited | 0 | logs/ed7c8ff4020249a8aa21d934238f4732/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/893fe0aaa1b544f0a4463df1d3f5ded9-4e8c1961f75742319937b6ed0a271db5.xml --timeout 120.000000 | exited | 0 | logs/2bb6b6a62a094f7e8212a918ba28718a/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/893fe0aaa1b544f0a4463df1d3f5ded9-4e8c1961f75742319937b6ed0a271db5.xml | exited | 0 | logs/7fb8ea3cc52146e8b08f5efce2f28f5b/stderr.bin |
| agent\_check | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/91284143e81b423f96d5036da50a0c8e/stderr.bin |
| agent\_check | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/902930dd2c484c4c88c9f2c07d102b34/stderr.bin |
| agent\_check | cmake --build /build --parallel 2 | exited | 0 | logs/12491fd291ef455aa71fb20308a7fa10/stderr.bin |
| agent\_check | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/bb7011fb661e4d8c9a75b2114ffd2c43/stderr.bin |
| agent\_check | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/960719bebaff413594fcfc7f04d2f75b/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/25bc5e0d5ce54417ac808cad7a94ff93-858bd10d29064146b1241ea9495baa3e.xml --timeout 120.000000 | exited | 0 | logs/030ade0fc1a646298afd1eb5d1e97972/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/25bc5e0d5ce54417ac808cad7a94ff93-858bd10d29064146b1241ea9495baa3e.xml | exited | 0 | logs/6c22598575824081a9b6bb5a156d9c5e/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/25bc5e0d5ce54417ac808cad7a94ff93-607e684f2d784ce89836cd54ede07a8a.xml --timeout 120.000000 | exited | 0 | logs/0702a928af254e01858900c13df1d82b/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/25bc5e0d5ce54417ac808cad7a94ff93-607e684f2d784ce89836cd54ede07a8a.xml | exited | 0 | logs/73b0a3313deb4e168da369dc091e51f2/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/25bc5e0d5ce54417ac808cad7a94ff93-b13fe98d1ec74aa58d5be32acae89d86.xml --timeout 120.000000 | exited | 0 | logs/32454753c8554a68a509acc6384dd9d1/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/25bc5e0d5ce54417ac808cad7a94ff93-b13fe98d1ec74aa58d5be32acae89d86.xml | exited | 0 | logs/e0fac8439c2c4a3ea0ede05d45f8ca9b/stderr.bin |
| agent\_check | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/25bc5e0d5ce54417ac808cad7a94ff93-10ec9d7e73044532b0b82702381e1645.xml --timeout 120.000000 | exited | 0 | logs/8033d620cdab4a6d81f7efced63ca1b7/stderr.bin |
| agent\_check | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/25bc5e0d5ce54417ac808cad7a94ff93-10ec9d7e73044532b0b82702381e1645.xml | exited | 0 | logs/a42ea6cebba84cd893e248a3c23abd01/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/17c22cf2a2734e188eee807e9b964a4b/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/37891f30b44f4310bdb46ce72598661c/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/a53a3b00ff594083bec95b5c29978cd0/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/e11de6888eaf460dae963bd3c86ff229/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/78fe4a47aa374602a75b6b9bebe7dee9/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/5e4c372425c741fb8917c8e77e876a5b-8c1ff0c2ad3242a889a6541f9aa2b9b6.xml --timeout 120.000000 | exited | 0 | logs/25e3d5aee8fb4fac8c11ffe3adf33ac9/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5e4c372425c741fb8917c8e77e876a5b-8c1ff0c2ad3242a889a6541f9aa2b9b6.xml | exited | 0 | logs/629b534f246e4ade93ab891eb34bcb94/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/5e4c372425c741fb8917c8e77e876a5b-cd7c9041f6d441f59b2670eb9c45862e.xml --timeout 120.000000 | exited | 0 | logs/a0b8b72265ac42668b8ade66511cf1e4/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5e4c372425c741fb8917c8e77e876a5b-cd7c9041f6d441f59b2670eb9c45862e.xml | exited | 0 | logs/5599a5a2180646edb8a866ece5987bad/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/5e4c372425c741fb8917c8e77e876a5b-0b0a48be214d4aa3a0ba99898b66b43f.xml --timeout 120.000000 | exited | 0 | logs/4a2dc1df8f654180947aac611d98bd26/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5e4c372425c741fb8917c8e77e876a5b-0b0a48be214d4aa3a0ba99898b66b43f.xml | exited | 0 | logs/355d4dd1c9614c8fbb6bc249838ad347/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/5e4c372425c741fb8917c8e77e876a5b-b5922773f1fc4ddf9eaaa2c883e288fc.xml --timeout 120.000000 | exited | 0 | logs/80c838b8d32d44ec92b9e67e6b3539be/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/5e4c372425c741fb8917c8e77e876a5b-b5922773f1fc4ddf9eaaa2c883e288fc.xml | exited | 0 | logs/0bb7c72d708c491d97f2371f2cd4a5a5/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
模型生成不保证正确；通过 SDK 受控工具产生候选，最终结局由独立验证决定。
