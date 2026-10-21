# ReproPatch run negative-maximum-39b2044f3e1c

Status: **failed**
Docker isolated: True
Base commit: `6f24189efcf78bf5a89f3ee006debad5b9ebdfe9`
Reproduced: True; independently verified: False
Elapsed: 3.247 seconds
Model turns: 2; tool calls: 1

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.259 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.660 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.085 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(positive_values\|empty_values\|mixed_values)$` | 0 | False | 0.092 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.223 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.600 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^(negative_values)$` | 8 | False | 0.082 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
