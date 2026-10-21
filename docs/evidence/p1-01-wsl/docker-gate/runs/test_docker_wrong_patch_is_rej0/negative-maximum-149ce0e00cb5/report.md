# ReproPatch run negative-maximum-149ce0e00cb5

Status: **failed**
Docker isolated: True
Base commit: `eef810b3329a64e543dc860c8c362e921cc276b0`
Reproduced: True; independently verified: False
Elapsed: 2.717 seconds
Model turns: 2; tool calls: 1

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.236 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.579 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.078 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.210 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.576 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.083 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
