# ReproPatch run 3a3cd5540072400d82f477815e2b0157

Status: **passed**
Docker isolated: True
Base commit: `22fb339bfa7b27e076c1ff87aeb3951a32763ee5`
Reproduced: True; independently verified: True
Elapsed: 11.945 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.182 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.288 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.630 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.089 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.093 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/b4f53cac8ee74275b45ddd358d49bdb8-292a80cfd4ff4985960e83c575187cc9.xml --timeout 120.000000` | 8 | False | 0.082 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b4f53cac8ee74275b45ddd358d49bdb8-292a80cfd4ff4985960e83c575187cc9.xml` | 0 | False | 0.097 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/b4f53cac8ee74275b45ddd358d49bdb8-ca6719d52fd9445abe6fcd1187826c4c.xml --timeout 120.000000` | 0 | False | 0.089 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b4f53cac8ee74275b45ddd358d49bdb8-ca6719d52fd9445abe6fcd1187826c4c.xml` | 0 | False | 0.077 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/b4f53cac8ee74275b45ddd358d49bdb8-af29bd94d4f844c2b6d15da63521b78c.xml --timeout 120.000000` | 0 | False | 0.079 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b4f53cac8ee74275b45ddd358d49bdb8-af29bd94d4f844c2b6d15da63521b78c.xml` | 0 | False | 0.080 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/b4f53cac8ee74275b45ddd358d49bdb8-a09315a9caee422e8a65841f22c6305d.xml --timeout 120.000000` | 0 | False | 0.079 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b4f53cac8ee74275b45ddd358d49bdb8-a09315a9caee422e8a65841f22c6305d.xml` | 0 | False | 0.096 |
| agent-check | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.202 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.233 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.665 |
| agent-check | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.123 |
| agent-check | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.089 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/a21ee28b86a64c96a7c0ee726520c7b0-90c3c6fe2a864107af3c56c6bc3d8be6.xml --timeout 120.000000` | 0 | False | 0.177 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a21ee28b86a64c96a7c0ee726520c7b0-90c3c6fe2a864107af3c56c6bc3d8be6.xml` | 0 | False | 0.131 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/a21ee28b86a64c96a7c0ee726520c7b0-d20dcf7044cd46ad942f57fcb238e86a.xml --timeout 120.000000` | 0 | False | 0.090 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a21ee28b86a64c96a7c0ee726520c7b0-d20dcf7044cd46ad942f57fcb238e86a.xml` | 0 | False | 0.166 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/a21ee28b86a64c96a7c0ee726520c7b0-be355317b8954b73b401f1100a9b0944.xml --timeout 120.000000` | 0 | False | 0.131 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a21ee28b86a64c96a7c0ee726520c7b0-be355317b8954b73b401f1100a9b0944.xml` | 0 | False | 0.091 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/a21ee28b86a64c96a7c0ee726520c7b0-e10bd43cd09e43039e95ea4d26babf20.xml --timeout 120.000000` | 0 | False | 0.163 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a21ee28b86a64c96a7c0ee726520c7b0-e10bd43cd09e43039e95ea4d26babf20.xml` | 0 | False | 0.135 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.172 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.315 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.643 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.174 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.159 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/f7c17b53c75d490d9bdec1547266b681-b9d3c6742f2a4a8d83566adb0e304bb9.xml --timeout 120.000000` | 0 | False | 0.123 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f7c17b53c75d490d9bdec1547266b681-b9d3c6742f2a4a8d83566adb0e304bb9.xml` | 0 | False | 0.193 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/f7c17b53c75d490d9bdec1547266b681-70e4f69ca41640adb8840a18c8d83db0.xml --timeout 120.000000` | 0 | False | 0.114 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f7c17b53c75d490d9bdec1547266b681-70e4f69ca41640adb8840a18c8d83db0.xml` | 0 | False | 0.087 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/f7c17b53c75d490d9bdec1547266b681-a60f253946e345a1ba3d456137e3ff17.xml --timeout 120.000000` | 0 | False | 0.123 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f7c17b53c75d490d9bdec1547266b681-a60f253946e345a1ba3d456137e3ff17.xml` | 0 | False | 0.107 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/f7c17b53c75d490d9bdec1547266b681-db1781a9c687497a90433e4f2bf133f2.xml --timeout 120.000000` | 0 | False | 0.097 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f7c17b53c75d490d9bdec1547266b681-db1781a9c687497a90433e4f2bf133f2.xml` | 0 | False | 0.172 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
