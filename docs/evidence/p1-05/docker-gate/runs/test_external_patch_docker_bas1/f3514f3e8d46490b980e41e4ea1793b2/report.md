# ReproPatch run f3514f3e8d46490b980e41e4ea1793b2

Status: **failed**
Docker isolated: True
Base commit: `15f537899bc4c50cd4160be77134bb241583ec89`
Reproduced: True; independently verified: False
Elapsed: 6.664 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.105 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.230 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.603 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.108 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.086 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/b51f8758862e41ef95feb018b6d6ba02-a2788496a36b4e85b98aaa63cb514b81.xml --timeout 120.000000` | 8 | False | 0.109 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b51f8758862e41ef95feb018b6d6ba02-a2788496a36b4e85b98aaa63cb514b81.xml` | 0 | False | 0.093 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/b51f8758862e41ef95feb018b6d6ba02-ebb37ca40bba4da68129376c9f31dd6d.xml --timeout 120.000000` | 0 | False | 0.107 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b51f8758862e41ef95feb018b6d6ba02-ebb37ca40bba4da68129376c9f31dd6d.xml` | 0 | False | 0.098 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/b51f8758862e41ef95feb018b6d6ba02-2e36658cf2084475874b6b9325a371a8.xml --timeout 120.000000` | 0 | False | 0.111 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b51f8758862e41ef95feb018b6d6ba02-2e36658cf2084475874b6b9325a371a8.xml` | 0 | False | 0.097 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/b51f8758862e41ef95feb018b6d6ba02-4ac3504b9fb44ffb8da58c5944f542bf.xml --timeout 120.000000` | 0 | False | 0.088 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b51f8758862e41ef95feb018b6d6ba02-4ac3504b9fb44ffb8da58c5944f542bf.xml` | 0 | False | 0.099 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.107 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.232 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.608 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.091 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.081 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/a1b603b4ad154c408b9336980b89372a-f623e3dd720a4e8ca96cd4505ee768e7.xml --timeout 120.000000` | 8 | False | 0.097 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a1b603b4ad154c408b9336980b89372a-f623e3dd720a4e8ca96cd4505ee768e7.xml` | 0 | False | 0.094 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/a1b603b4ad154c408b9336980b89372a-af0d59dd8bc2405a848972d40f347372.xml --timeout 120.000000` | 0 | False | 0.090 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a1b603b4ad154c408b9336980b89372a-af0d59dd8bc2405a848972d40f347372.xml` | 0 | False | 0.103 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/a1b603b4ad154c408b9336980b89372a-07195007876044728621e49441e0375e.xml --timeout 120.000000` | 0 | False | 0.181 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a1b603b4ad154c408b9336980b89372a-07195007876044728621e49441e0375e.xml` | 0 | False | 0.094 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/a1b603b4ad154c408b9336980b89372a-5c08c4f8ba374f9c90f1dd3121e6a49a.xml --timeout 120.000000` | 0 | False | 0.086 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a1b603b4ad154c408b9336980b89372a-5c08c4f8ba374f9c90f1dd3121e6a49a.xml` | 0 | False | 0.085 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
