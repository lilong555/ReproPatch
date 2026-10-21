# ReproPatch 776edf1df2c24bafa4e96a71d98c7c72

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：12fd5f8bcb03f290ab758336a3c4977981e477e8
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.334 秒
模型步骤：0；准入工具：0
模型停止原因：未知
HTTP 请求次数：0
Token 输入 / 输出 / 合计：未知 / 未知 / 未知
合成用量：否；费用：未知
执行清理确认：是
产物完整：是
事件截止序号：73

外部来源标签（未认证）：fixture
外部轨迹：未验证的 opaque 附件，不作为测试或用量证据。

| 评估 | 测试 | 观察 | 证据 |
| --- | --- | --- | --- |
| baseline | negative\_values | 失败 | evidence/f57727f16fb843578591cf6ce57c5921/93c59556a6524c398a5125b47fc82743.xml |
| baseline | positive\_values | 通过 | evidence/f57727f16fb843578591cf6ce57c5921/e708fd4a143b4edda403a36a5ed96b09.xml |
| baseline | empty\_values | 通过 | evidence/f57727f16fb843578591cf6ce57c5921/8ee6ff567f8a41058bf38f70fac5836e.xml |
| baseline | mixed\_values | 通过 | evidence/f57727f16fb843578591cf6ce57c5921/a82b0fa1a6c549af9b1a4f17e9174cc1.xml |
| independent | negative\_values | 通过 | evidence/a8fd7ced048b42ec8c26c4fe19e2705a/0fb9b7a66a7f49b69c90da4113287db4.xml |
| independent | positive\_values | 通过 | evidence/a8fd7ced048b42ec8c26c4fe19e2705a/82baa5bb984749f78519a987a05c30b6.xml |
| independent | empty\_values | 通过 | evidence/a8fd7ced048b42ec8c26c4fe19e2705a/0303de1b503a4085a76a66bdeff81ad0.xml |
| independent | mixed\_values | 通过 | evidence/a8fd7ced048b42ec8c26c4fe19e2705a/478a62d8d010467e9352902bc4a8141a.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/def8317bba8145d1bd5002a65e9fe721/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/aeac58c08e984b578c24145c9630160e/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/d3d227bf12d94df6a6dfed2d17355606/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/0af13ad3a40943f797f60f5478ede035/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/5f86c0891cde4879906177f836bc98d2/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/f57727f16fb843578591cf6ce57c5921-93c59556a6524c398a5125b47fc82743.xml --timeout 120.000000 | exited | 8 | logs/e9391540abf443ada938f0d97b52371c/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f57727f16fb843578591cf6ce57c5921-93c59556a6524c398a5125b47fc82743.xml | exited | 0 | logs/b5fb004c166e4dd081d77902664369a6/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/f57727f16fb843578591cf6ce57c5921-e708fd4a143b4edda403a36a5ed96b09.xml --timeout 120.000000 | exited | 0 | logs/efccf0765b5b4082bfcdb03597e2e6d6/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f57727f16fb843578591cf6ce57c5921-e708fd4a143b4edda403a36a5ed96b09.xml | exited | 0 | logs/1df108cee593412691297fe666573368/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/f57727f16fb843578591cf6ce57c5921-8ee6ff567f8a41058bf38f70fac5836e.xml --timeout 120.000000 | exited | 0 | logs/3f4ddcedcf754993b865bf19ae58aca2/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f57727f16fb843578591cf6ce57c5921-8ee6ff567f8a41058bf38f70fac5836e.xml | exited | 0 | logs/791795957be04b5c973fa976c1a2151e/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/f57727f16fb843578591cf6ce57c5921-a82b0fa1a6c549af9b1a4f17e9174cc1.xml --timeout 120.000000 | exited | 0 | logs/6b64b14fb46c4ad789123d007de30c1b/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/f57727f16fb843578591cf6ce57c5921-a82b0fa1a6c549af9b1a4f17e9174cc1.xml | exited | 0 | logs/559b68c5810945c198e64e87e3aed10e/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/63a9050b7c40449790d381f8e60ae2ae/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/60eb2af371984efeaa1bbff23f77df45/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/b56894e020a04f1fb8fa23dbb8e54503/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/577a163a2aac4c7fb8f8b09dde36657a/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/32f527a49b564988a8b6d1ed548d58cc/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative\_values$ --output-junit /build/.repropatch-results/a8fd7ced048b42ec8c26c4fe19e2705a-0fb9b7a66a7f49b69c90da4113287db4.xml --timeout 120.000000 | exited | 0 | logs/2e3f805f7b994873888bee631ce83b17/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a8fd7ced048b42ec8c26c4fe19e2705a-0fb9b7a66a7f49b69c90da4113287db4.xml | exited | 0 | logs/74d93462a65544069a61744eabbc9660/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/a8fd7ced048b42ec8c26c4fe19e2705a-82baa5bb984749f78519a987a05c30b6.xml --timeout 120.000000 | exited | 0 | logs/682e99a196314a5cb4a24fc179b7c03b/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a8fd7ced048b42ec8c26c4fe19e2705a-82baa5bb984749f78519a987a05c30b6.xml | exited | 0 | logs/a87bde823bee4388ab9a47627fd64af2/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/a8fd7ced048b42ec8c26c4fe19e2705a-0303de1b503a4085a76a66bdeff81ad0.xml --timeout 120.000000 | exited | 0 | logs/c5b38eb0276546089c56e8e053920129/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a8fd7ced048b42ec8c26c4fe19e2705a-0303de1b503a4085a76a66bdeff81ad0.xml | exited | 0 | logs/0f972a8868f548dc9126107bab39e08b/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/a8fd7ced048b42ec8c26c4fe19e2705a-478a62d8d010467e9352902bc4a8141a.xml --timeout 120.000000 | exited | 0 | logs/6aced60f9bb44e1d9b57064ec11cecfc/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/a8fd7ced048b42ec8c26c4fe19e2705a-478a62d8d010467e9352902bc4a8141a.xml | exited | 0 | logs/6835a51d69ba4bea876bf48b785b4e85/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
