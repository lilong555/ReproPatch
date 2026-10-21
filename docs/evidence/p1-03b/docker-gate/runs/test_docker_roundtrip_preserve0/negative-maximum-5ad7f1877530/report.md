# ReproPatch run negative-maximum-5ad7f1877530

Status: **passed**
Docker isolated: True
Base commit: `4cfe401d73211727fd25ada771db849b22c39ad4`
Reproduced: True; independently verified: True
Elapsed: 5.431 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.215 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.588 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.093 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.092 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.208 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.577 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values\|positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.092 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.219 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.549 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values)$` | 0 | False | 0.109 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values\|positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.101 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
