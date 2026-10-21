# ReproPatch run f707663f0b284afa8ab96411427fe80d

Status: **failed**
Docker isolated: True
Base commit: `0b4cfa7820ee893b7f7176404121d0fb39fc8078`
Reproduced: True; independently verified: False
Elapsed: 6.475 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.123 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.228 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.569 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.086 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.076 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/f564ab8ab2d3499f9e84e0cb7df88624-188f18fc12e246ea80a77d47eb053f82.xml --timeout 120.000000` | 8 | False | 0.093 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f564ab8ab2d3499f9e84e0cb7df88624-188f18fc12e246ea80a77d47eb053f82.xml` | 0 | False | 0.101 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/f564ab8ab2d3499f9e84e0cb7df88624-cd2d0c1b13344a549130723b97c92da6.xml --timeout 120.000000` | 0 | False | 0.087 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f564ab8ab2d3499f9e84e0cb7df88624-cd2d0c1b13344a549130723b97c92da6.xml` | 0 | False | 0.086 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/f564ab8ab2d3499f9e84e0cb7df88624-99e6d58ff38947c7b6d6ccc22d4585c6.xml --timeout 120.000000` | 0 | False | 0.107 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f564ab8ab2d3499f9e84e0cb7df88624-99e6d58ff38947c7b6d6ccc22d4585c6.xml` | 0 | False | 0.081 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/f564ab8ab2d3499f9e84e0cb7df88624-a5fd4c4294d24951946a3b271c117ef2.xml --timeout 120.000000` | 0 | False | 0.106 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f564ab8ab2d3499f9e84e0cb7df88624-a5fd4c4294d24951946a3b271c117ef2.xml` | 0 | False | 0.090 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.104 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.227 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.607 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.095 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.091 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/3ef0894d7e5648428357ec39cd7638d7-6fd24ce6c7f74fe99cc807491d5dc3cc.xml --timeout 120.000000` | 0 | False | 0.093 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3ef0894d7e5648428357ec39cd7638d7-6fd24ce6c7f74fe99cc807491d5dc3cc.xml` | 0 | False | 0.095 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/3ef0894d7e5648428357ec39cd7638d7-b4a5cd2feb3f497495a02aaa774adc79.xml --timeout 120.000000` | 0 | False | 0.090 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3ef0894d7e5648428357ec39cd7638d7-b4a5cd2feb3f497495a02aaa774adc79.xml` | 0 | False | 0.075 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/3ef0894d7e5648428357ec39cd7638d7-4920816840a64978938ef86a06804cb6.xml --timeout 120.000000` | 0 | False | 0.098 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3ef0894d7e5648428357ec39cd7638d7-4920816840a64978938ef86a06804cb6.xml` | 0 | False | 0.097 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/3ef0894d7e5648428357ec39cd7638d7-5eb21efb185845dab70ad59cccc4afa0.xml --timeout 120.000000` | 8 | False | 0.092 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3ef0894d7e5648428357ec39cd7638d7-5eb21efb185845dab70ad59cccc4afa0.xml` | 0 | False | 0.101 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
