# ReproPatch run negative-maximum-172c58e91373

Status: **passed**
Docker isolated: True
Base commit: `19bdb900e8f5b3da216ce42f22d54f1c0b88d597`
Reproduced: True; independently verified: True
Elapsed: 6.086 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.354 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.743 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.102 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.091 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.228 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.593 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values\|positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.102 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.213 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.592 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values)$` | 0 | False | 0.092 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values\|positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.091 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
