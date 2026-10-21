# ReproPatch 2f192825ccc647d1bd26ff8ac7105d48

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：c99314a015621079257abd52587bd23df826b15b
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：8.260 秒
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
| baseline | parse\[value\]+edge | 失败 | evidence/962fe0a045574e738b312cbcda071b3e/90a29108b00240b1877187481e9f04b4.xml |
| baseline | positive\_values | 通过 | evidence/962fe0a045574e738b312cbcda071b3e/2cab431d35344094ae641c888a331f9c.xml |
| baseline | empty\_values | 通过 | evidence/962fe0a045574e738b312cbcda071b3e/15b69c9a43754ecca65fbe326e139f17.xml |
| baseline | mixed\_values | 通过 | evidence/962fe0a045574e738b312cbcda071b3e/8e0288ed659e42d19d33cc17c83c9b49.xml |
| independent | parse\[value\]+edge | 通过 | evidence/d12d848a3a1a40c88c8c297a4c941bf7/07299e53482a4126a381508ee426877c.xml |
| independent | positive\_values | 通过 | evidence/d12d848a3a1a40c88c8c297a4c941bf7/baa2841ae73f4c58b2b944cdb04716c2.xml |
| independent | empty\_values | 通过 | evidence/d12d848a3a1a40c88c8c297a4c941bf7/bf4a734ec82e441e9d11c0f8cc504efa.xml |
| independent | mixed\_values | 通过 | evidence/d12d848a3a1a40c88c8c297a4c941bf7/f50a26f84d3241e0b6e6acaf0aa6b35c.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/50843d123271485aa1cabcfbc7c99fa4/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/d49d4e89390241179a5e2fb118fd5181/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/6ee845a64c98493ca99073c1546f0489/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/96bc67e4f2904b60b579622d6cd40e1b/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/9c2d16ec234947419e9275985aa66e1e/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\\\[value\\\]\\+edge$ --output-junit /build/.repropatch-results/962fe0a045574e738b312cbcda071b3e-90a29108b00240b1877187481e9f04b4.xml --timeout 120.000000 | exited | 8 | logs/247c4282a6cd4fe18050785fa8e6a8d5/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/962fe0a045574e738b312cbcda071b3e-90a29108b00240b1877187481e9f04b4.xml | exited | 0 | logs/2b1efbec9ffd40d6947238d7ea5a72a4/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/962fe0a045574e738b312cbcda071b3e-2cab431d35344094ae641c888a331f9c.xml --timeout 120.000000 | exited | 0 | logs/aad2b5dbfe1f439c8667f839b707b86a/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/962fe0a045574e738b312cbcda071b3e-2cab431d35344094ae641c888a331f9c.xml | exited | 0 | logs/6ce42522134c45349b91c7066cf95b57/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/962fe0a045574e738b312cbcda071b3e-15b69c9a43754ecca65fbe326e139f17.xml --timeout 120.000000 | exited | 0 | logs/840d13651aac49ebb310198ab2bbae7d/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/962fe0a045574e738b312cbcda071b3e-15b69c9a43754ecca65fbe326e139f17.xml | exited | 0 | logs/fae01c826e004b57a4dc8efccc5274ee/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/962fe0a045574e738b312cbcda071b3e-8e0288ed659e42d19d33cc17c83c9b49.xml --timeout 120.000000 | exited | 0 | logs/d90e5970b25045aabcaaa48e8e547062/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/962fe0a045574e738b312cbcda071b3e-8e0288ed659e42d19d33cc17c83c9b49.xml | exited | 0 | logs/d91cf479caf844aca6836068aa703a51/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/a04b485364f44ee0971ba66b5279df73/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/dd8416525c534411b5ef2a455d00dd5c/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/451798b6110340f89d25a2bf853d8e26/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/b6bd54f30c8f4238abbb0aa34d16cb0e/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/9c2c931f2b514d048379edd6cab2ff47/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\\\[value\\\]\\+edge$ --output-junit /build/.repropatch-results/d12d848a3a1a40c88c8c297a4c941bf7-07299e53482a4126a381508ee426877c.xml --timeout 120.000000 | exited | 0 | logs/058241a3c7ee401ebbdeedba7da2778f/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d12d848a3a1a40c88c8c297a4c941bf7-07299e53482a4126a381508ee426877c.xml | exited | 0 | logs/efa2ef4b46f2432b92e8ea94bbb6461b/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/d12d848a3a1a40c88c8c297a4c941bf7-baa2841ae73f4c58b2b944cdb04716c2.xml --timeout 120.000000 | exited | 0 | logs/1e66241a4ec84c0a93bd0a3321177a0e/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d12d848a3a1a40c88c8c297a4c941bf7-baa2841ae73f4c58b2b944cdb04716c2.xml | exited | 0 | logs/a741695c40e54649bd2759b322cd0a0b/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/d12d848a3a1a40c88c8c297a4c941bf7-bf4a734ec82e441e9d11c0f8cc504efa.xml --timeout 120.000000 | exited | 0 | logs/6668b3aec62a424596bb7aa499d5b24c/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d12d848a3a1a40c88c8c297a4c941bf7-bf4a734ec82e441e9d11c0f8cc504efa.xml | exited | 0 | logs/fb21403e7f93458dae0b96aeb6251822/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/d12d848a3a1a40c88c8c297a4c941bf7-f50a26f84d3241e0b6e6acaf0aa6b35c.xml --timeout 120.000000 | exited | 0 | logs/a4c1028eeacd4b97a0d0946257a55df6/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/d12d848a3a1a40c88c8c297a4c941bf7-f50a26f84d3241e0b6e6acaf0aa6b35c.xml | exited | 0 | logs/309b9cc933e148af93ae318fb23fdf7a/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
