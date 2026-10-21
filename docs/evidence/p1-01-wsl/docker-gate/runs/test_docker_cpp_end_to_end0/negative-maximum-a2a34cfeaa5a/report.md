# ReproPatch run negative-maximum-a2a34cfeaa5a

Status: **passed**
Docker isolated: True
Base commit: `110b4da26dea449ebc380ec68b390f167856d1a9`
Reproduced: True; independently verified: True
Elapsed: 4.352 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.209 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.624 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 8 | False | 0.097 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.211 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.633 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error` | 0 | False | 0.088 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.220 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.614 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$` | 0 | False | 0.069 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error` | 0 | False | 0.093 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
