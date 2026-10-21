# ReproPatch run negative-maximum-a4d14d3559ba

Status: **passed**
Docker isolated: True
Base commit: `aa807d003dfe9f46aea44ef56bb777525edea0d1`
Reproduced: True; independently verified: True
Elapsed: 4.701 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.340 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.657 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.105 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.084 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.201 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.587 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values\|positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.083 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.224 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.599 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values)$` | 0 | False | 0.089 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values\|positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.098 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
