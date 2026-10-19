# ReproPatch run negative-maximum-ead30b400a42

Status: **passed**
Docker isolated: False
Base commit: `bdbeddbe6e9bf18cdd161d9698f2cb5dc66e6ad6`
Reproduced: True; independently verified: True
Elapsed: 3.385 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.248 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.676 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.107 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.242 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.670 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error` | 0 | False | 0.107 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.259 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.750 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 0 | False | 0.108 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error` | 0 | False | 0.106 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
