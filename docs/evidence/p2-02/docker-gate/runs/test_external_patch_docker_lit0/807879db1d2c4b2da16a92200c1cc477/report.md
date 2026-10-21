# ReproPatch 807879db1d2c4b2da16a92200c1cc477

任务：negative-maximum
入口：verify-patch
结局：**ACCEPTED**
原因：VERIFICATION\_PASSED
执行引擎：none
模型：未知
Docker 隔离：是
基线 commit：4565edf10eea71ce73537eaebede5fe45f8a2194
镜像：sha256:beb37ec7c7573716554cc526daf8febbe6a69b13f114612e46bc0c75504be61a
耗时：7.391 秒
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
| baseline | parse\[value\]+edge | 失败 | evidence/97330b15d2884e6ea4490bc399571bb8/aafc8270b1ff4476be97383802e56453.xml |
| baseline | positive\_values | 通过 | evidence/97330b15d2884e6ea4490bc399571bb8/39f3218b3b5448b698a8c02c84ea597d.xml |
| baseline | empty\_values | 通过 | evidence/97330b15d2884e6ea4490bc399571bb8/caedea8928674b07bb8b93d535ad580b.xml |
| baseline | mixed\_values | 通过 | evidence/97330b15d2884e6ea4490bc399571bb8/f2c95f06e0864afe855f93ea19a29fec.xml |
| independent | parse\[value\]+edge | 通过 | evidence/826c1b2cfe3d4274a6cee616798dc1f6/3e8c7b3c4f2c43d097e105b4010f9c27.xml |
| independent | positive\_values | 通过 | evidence/826c1b2cfe3d4274a6cee616798dc1f6/58f48b36aee1472683a8dbdbd2e4329e.xml |
| independent | empty\_values | 通过 | evidence/826c1b2cfe3d4274a6cee616798dc1f6/074c156f7685422dbe64e9e2a79f5441.xml |
| independent | mixed\_values | 通过 | evidence/826c1b2cfe3d4274a6cee616798dc1f6/4d24e73ff2804141a12c3e3f16bc17f1.xml |

| 评估 | 命令 | 状态 | 退出码 | stderr |
| --- | --- | --- | ---: | --- |
| baseline | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/e56210388375490b931e9c65a4d0fde1/stderr.bin |
| baseline | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/3b2f80f99f3c44dba22241160f4fbde8/stderr.bin |
| baseline | cmake --build /build --parallel 2 | exited | 0 | logs/642812c6d08c4331b96d80b61fd38434/stderr.bin |
| baseline | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/6bd063dd24ab43d4ba2b11e6a8865a69/stderr.bin |
| baseline | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/c3a804b1575e492885109fbbfeed3888/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\\\[value\\\]\\+edge$ --output-junit /build/.repropatch-results/97330b15d2884e6ea4490bc399571bb8-aafc8270b1ff4476be97383802e56453.xml --timeout 120.000000 | exited | 8 | logs/5ab0234f8c4f4d74979264a8a3e51e53/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/97330b15d2884e6ea4490bc399571bb8-aafc8270b1ff4476be97383802e56453.xml | exited | 0 | logs/14ad5322d90443a685b650683d34c1df/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/97330b15d2884e6ea4490bc399571bb8-39f3218b3b5448b698a8c02c84ea597d.xml --timeout 120.000000 | exited | 0 | logs/4ea476e9d1be4af6b8d937001f3a29fa/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/97330b15d2884e6ea4490bc399571bb8-39f3218b3b5448b698a8c02c84ea597d.xml | exited | 0 | logs/dfc0879842df4fe7a2b0e7ac00e1d68e/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/97330b15d2884e6ea4490bc399571bb8-caedea8928674b07bb8b93d535ad580b.xml --timeout 120.000000 | exited | 0 | logs/7e072662fd53427d9730e25acc1758b3/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/97330b15d2884e6ea4490bc399571bb8-caedea8928674b07bb8b93d535ad580b.xml | exited | 0 | logs/ef2af9586a5b46a3b92a6b353c8aa313/stderr.bin |
| baseline | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/97330b15d2884e6ea4490bc399571bb8-f2c95f06e0864afe855f93ea19a29fec.xml --timeout 120.000000 | exited | 0 | logs/51af4a9a1f5841c1bdb506ec9fb79484/stderr.bin |
| baseline | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/97330b15d2884e6ea4490bc399571bb8-f2c95f06e0864afe855f93ea19a29fec.xml | exited | 0 | logs/fcb0fa0e105f4d848c8b754047bcae89/stderr.bin |
| independent | /bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf &\#x27;\\nREPROPATCH\_CXX\_VERSION\\n&\#x27;; c++ --version | exited | 0 | logs/9bbc004dea1844f38dd8803b3448f27e/stderr.bin |
| independent | cmake -S /src -B /build -DCMAKE\_BUILD\_TYPE=Debug | exited | 0 | logs/7bfac714f8d746629a4eef2029575358/stderr.bin |
| independent | cmake --build /build --parallel 2 | exited | 0 | logs/f9f8222e947d43c09aac8acd5cdd4eb6/stderr.bin |
| independent | ctest --test-dir /build --show-only=json-v1 | exited | 0 | logs/e131665358a44361a200d8cd91451b09/stderr.bin |
| independent | /bin/sh -ec test \! -L /build/.repropatch-results &amp;&amp; mkdir -p -- /build/.repropatch-results | exited | 0 | logs/40abb85033a24279b79ffdc7a4c6f2fb/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\\\[value\\\]\\+edge$ --output-junit /build/.repropatch-results/826c1b2cfe3d4274a6cee616798dc1f6-3e8c7b3c4f2c43d097e105b4010f9c27.xml --timeout 120.000000 | exited | 0 | logs/7de213d42a0d45eda61efc2d71385ab0/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/826c1b2cfe3d4274a6cee616798dc1f6-3e8c7b3c4f2c43d097e105b4010f9c27.xml | exited | 0 | logs/289e83d95948483e90ed00949cf8b584/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive\_values$ --output-junit /build/.repropatch-results/826c1b2cfe3d4274a6cee616798dc1f6-58f48b36aee1472683a8dbdbd2e4329e.xml --timeout 120.000000 | exited | 0 | logs/ba35e28812734272ad3c00a7a923793f/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/826c1b2cfe3d4274a6cee616798dc1f6-58f48b36aee1472683a8dbdbd2e4329e.xml | exited | 0 | logs/c3a6253ae3f84200b198ffb73a2c30e1/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty\_values$ --output-junit /build/.repropatch-results/826c1b2cfe3d4274a6cee616798dc1f6-074c156f7685422dbe64e9e2a79f5441.xml --timeout 120.000000 | exited | 0 | logs/9af66d802d9b4ecb93ce8997d54d95a2/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/826c1b2cfe3d4274a6cee616798dc1f6-074c156f7685422dbe64e9e2a79f5441.xml | exited | 0 | logs/b5557fdecdcb48d489e394b757a492b6/stderr.bin |
| independent | ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed\_values$ --output-junit /build/.repropatch-results/826c1b2cfe3d4274a6cee616798dc1f6-4d24e73ff2804141a12c3e3f16bc17f1.xml --timeout 120.000000 | exited | 0 | logs/cb1266530fc34b369646df8b30cf2a6c/stderr.bin |
| independent | /bin/sh -ec test -f &quot;$1&quot; &amp;&amp; test \! -L &quot;$1&quot; &amp;&amp; test &quot;$\(wc -c &lt; &quot;$1&quot;\)&quot; -lt 4194304 &amp;&amp; cat -- &quot;$1&quot; repropatch-read /build/.repropatch-results/826c1b2cfe3d4274a6cee616798dc1f6-4d24e73ff2804141a12c3e3f16bc17f1.xml | exited | 0 | logs/601f161c01ef4d2aab65f0e8f7fea557/stderr.bin |

领域轨迹：events.jsonl

仅验收冻结 Task 的测试 oracle，不证明所有输入正确。
Docker 与宿主共享内核。
SQLite 记录已提交的运行事实；当前不支持中断恢复或重新执行历史工具。
外部生成过程、预算和 trace 未受本次运行管理或验证。
