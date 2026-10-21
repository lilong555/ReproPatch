# ReproPatch run negative-maximum-27c058995be6

Status: **passed**
Docker isolated: True
Base commit: `3ae3eadc17bf04c53a2dd82fba644d0f48794d64`
Reproduced: True; independently verified: True
Elapsed: 5.344 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.242 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.621 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.106 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.087 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.261 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.607 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values\|positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.082 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.211 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.555 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values)$` | 0 | False | 0.087 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values\|positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.077 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
