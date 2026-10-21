# ReproPatch run negative-maximum-cdcdd582c186

Status: **passed**
Docker isolated: True
Base commit: `075a19d1b097d96df3550d2f08d20a0076705210`
Reproduced: True; independently verified: True
Elapsed: 4.906 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.534 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.722 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.094 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.208 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.613 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error` | 0 | False | 0.084 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.219 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.575 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 0 | False | 0.073 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error` | 0 | False | 0.091 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
