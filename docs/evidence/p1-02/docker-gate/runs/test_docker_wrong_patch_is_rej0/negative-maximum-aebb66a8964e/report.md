# ReproPatch run negative-maximum-aebb66a8964e

Status: **failed**
Docker isolated: True
Base commit: `ef5476cb65e8c5a4864fa05843db7542d2fab556`
Reproduced: True; independently verified: False
Elapsed: 2.853 seconds
Model turns: 2; tool calls: 1

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.198 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.566 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.090 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.117 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.194 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.561 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values)$` | 8 | False | 0.073 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
