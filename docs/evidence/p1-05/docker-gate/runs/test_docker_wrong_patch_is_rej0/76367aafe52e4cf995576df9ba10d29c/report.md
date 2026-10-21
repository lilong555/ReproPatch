# ReproPatch run 76367aafe52e4cf995576df9ba10d29c

Status: **failed**
Docker isolated: True
Base commit: `452d86032daf25163e21825bc7b31b61488b9096`
Reproduced: True; independently verified: False
Elapsed: 6.403 seconds
Model turns: 2; tool calls: 1

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.108 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.231 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.571 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.079 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.093 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/a8a5fb8be4ee44b3b2f1baf75c050ef3-1a51487bf450416396cd3acd72b4dd90.xml --timeout 120.000000` | 8 | False | 0.090 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a8a5fb8be4ee44b3b2f1baf75c050ef3-1a51487bf450416396cd3acd72b4dd90.xml` | 0 | False | 0.082 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/a8a5fb8be4ee44b3b2f1baf75c050ef3-ec97e2829d96481c8bff1c8036dcf831.xml --timeout 120.000000` | 0 | False | 0.089 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a8a5fb8be4ee44b3b2f1baf75c050ef3-ec97e2829d96481c8bff1c8036dcf831.xml` | 0 | False | 0.077 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/a8a5fb8be4ee44b3b2f1baf75c050ef3-cdf1f2f9d27d419785bec27318a40356.xml --timeout 120.000000` | 0 | False | 0.085 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a8a5fb8be4ee44b3b2f1baf75c050ef3-cdf1f2f9d27d419785bec27318a40356.xml` | 0 | False | 0.082 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/a8a5fb8be4ee44b3b2f1baf75c050ef3-3dd0519663bd4a7db5ff155932b92ace.xml --timeout 120.000000` | 0 | False | 0.102 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a8a5fb8be4ee44b3b2f1baf75c050ef3-3dd0519663bd4a7db5ff155932b92ace.xml` | 0 | False | 0.092 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.103 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.216 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.577 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.099 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.084 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/f6232be478374294b1e4e474b150af1c-c754f629232e42878d415cf68e7909e0.xml --timeout 120.000000` | 8 | False | 0.094 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f6232be478374294b1e4e474b150af1c-c754f629232e42878d415cf68e7909e0.xml` | 0 | False | 0.082 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/f6232be478374294b1e4e474b150af1c-39cb67f714ef481d87a3097f73dd4021.xml --timeout 120.000000` | 0 | False | 0.096 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f6232be478374294b1e4e474b150af1c-39cb67f714ef481d87a3097f73dd4021.xml` | 0 | False | 0.088 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/f6232be478374294b1e4e474b150af1c-3419974941b0497e8825b775ba237966.xml --timeout 120.000000` | 0 | False | 0.084 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f6232be478374294b1e4e474b150af1c-3419974941b0497e8825b775ba237966.xml` | 0 | False | 0.104 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/f6232be478374294b1e4e474b150af1c-8ccd1adef9f14b14b2bc9044633e9dad.xml --timeout 120.000000` | 0 | False | 0.107 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f6232be478374294b1e4e474b150af1c-8ccd1adef9f14b14b2bc9044633e9dad.xml` | 0 | False | 0.092 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
