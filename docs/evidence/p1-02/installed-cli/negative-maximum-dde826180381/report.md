# ReproPatch run negative-maximum-dde826180381

Status: **passed**
Docker isolated: True
Base commit: `075a19d1b097d96df3550d2f08d20a0076705210`
Reproduced: True; independently verified: True
Elapsed: 4.267 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.208 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.584 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.074 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.085 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.200 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.555 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values\|positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.106 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.198 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.564 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values)$` | 0 | False | 0.086 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values\|positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.073 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
