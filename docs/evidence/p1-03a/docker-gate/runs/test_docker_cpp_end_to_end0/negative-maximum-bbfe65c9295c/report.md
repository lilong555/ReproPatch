# ReproPatch run negative-maximum-bbfe65c9295c

Status: **passed**
Docker isolated: True
Base commit: `67e8c8c294f4bc17731de0a7b78ecbf336fa649e`
Reproduced: True; independently verified: True
Elapsed: 5.165 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.357 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.701 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.095 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.091 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.230 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.619 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values\|positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.100 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.262 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.674 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values)$` | 0 | False | 0.088 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values\|positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.100 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
