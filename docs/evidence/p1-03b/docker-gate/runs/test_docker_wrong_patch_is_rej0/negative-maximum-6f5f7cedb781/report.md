# ReproPatch run negative-maximum-6f5f7cedb781

Status: **failed**
Docker isolated: True
Base commit: `cb68191217560f8701d117fd8658e827263ae873`
Reproduced: True; independently verified: False
Elapsed: 3.594 seconds
Model turns: 2; tool calls: 1

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.219 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.593 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.091 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.096 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.215 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.572 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values)$` | 8 | False | 0.112 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
