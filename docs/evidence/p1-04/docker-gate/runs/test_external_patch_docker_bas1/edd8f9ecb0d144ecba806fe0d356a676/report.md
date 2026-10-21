# ReproPatch run edd8f9ecb0d144ecba806fe0d356a676

Status: **failed**
Docker isolated: True
Base commit: `f8f2b4f4a41f80bda7499647cfd73ca7ba2a9c09`
Reproduced: True; independently verified: False
Elapsed: 6.331 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.102 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.226 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.603 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.088 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.078 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/2d9ade8b874342519722530bc952b14b-ae32272af78d4c1680adb7598b3d3008.xml --timeout 120.000000` | 8 | False | 0.096 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2d9ade8b874342519722530bc952b14b-ae32272af78d4c1680adb7598b3d3008.xml` | 0 | False | 0.091 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/2d9ade8b874342519722530bc952b14b-432f5ac9fd37440c8ca7409356b595f5.xml --timeout 120.000000` | 0 | False | 0.098 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2d9ade8b874342519722530bc952b14b-432f5ac9fd37440c8ca7409356b595f5.xml` | 0 | False | 0.085 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/2d9ade8b874342519722530bc952b14b-db535af791634b19ad86fb0dd34f5654.xml --timeout 120.000000` | 0 | False | 0.090 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2d9ade8b874342519722530bc952b14b-db535af791634b19ad86fb0dd34f5654.xml` | 0 | False | 0.091 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/2d9ade8b874342519722530bc952b14b-a079762efa0d4483a583805de29af60a.xml --timeout 120.000000` | 0 | False | 0.090 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2d9ade8b874342519722530bc952b14b-a079762efa0d4483a583805de29af60a.xml` | 0 | False | 0.088 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.114 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.222 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.602 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.110 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.102 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/bf5c08b283f547b49256d75128fb5582-f6526e1722744dd0bdb0150d9630e67a.xml --timeout 120.000000` | 8 | False | 0.093 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/bf5c08b283f547b49256d75128fb5582-f6526e1722744dd0bdb0150d9630e67a.xml` | 0 | False | 0.090 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/bf5c08b283f547b49256d75128fb5582-92260f3a15e34be9a3b8ec07386a316e.xml --timeout 120.000000` | 0 | False | 0.092 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/bf5c08b283f547b49256d75128fb5582-92260f3a15e34be9a3b8ec07386a316e.xml` | 0 | False | 0.101 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/bf5c08b283f547b49256d75128fb5582-40403467b562454299d63341b349a199.xml --timeout 120.000000` | 0 | False | 0.093 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/bf5c08b283f547b49256d75128fb5582-40403467b562454299d63341b349a199.xml` | 0 | False | 0.088 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/bf5c08b283f547b49256d75128fb5582-d01cd11439524fd280e7c867a6c44c3b.xml --timeout 120.000000` | 0 | False | 0.098 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/bf5c08b283f547b49256d75128fb5582-d01cd11439524fd280e7c867a6c44c3b.xml` | 0 | False | 0.099 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
