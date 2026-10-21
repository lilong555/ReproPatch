# ReproPatch run 9318c7c91085488fbcf956a287f3205e

Status: **passed**
Docker isolated: True
Base commit: `cdbb1eb3e08b49bfedeb4583570a0e1451a31b86`
Reproduced: True; independently verified: True
Elapsed: 6.332 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.104 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.238 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.619 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.115 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.091 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\[value\]\+edge$ --output-junit /build/.repropatch-results/a71fc8c2f237408b997cb880ef4f4116-d387b606d752400db52edc2199fc4cb0.xml --timeout 120.000000` | 8 | False | 0.096 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a71fc8c2f237408b997cb880ef4f4116-d387b606d752400db52edc2199fc4cb0.xml` | 0 | False | 0.104 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/a71fc8c2f237408b997cb880ef4f4116-5240b0165f1a49058a7a1cdb7c0b1e44.xml --timeout 120.000000` | 0 | False | 0.091 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a71fc8c2f237408b997cb880ef4f4116-5240b0165f1a49058a7a1cdb7c0b1e44.xml` | 0 | False | 0.081 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/a71fc8c2f237408b997cb880ef4f4116-16f953f3a4974c59bd13b4a9e1ed2f70.xml --timeout 120.000000` | 0 | False | 0.088 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a71fc8c2f237408b997cb880ef4f4116-16f953f3a4974c59bd13b4a9e1ed2f70.xml` | 0 | False | 0.089 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/a71fc8c2f237408b997cb880ef4f4116-1287ab1424d740c6ab80f71e28d70ba2.xml --timeout 120.000000` | 0 | False | 0.082 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a71fc8c2f237408b997cb880ef4f4116-1287ab1424d740c6ab80f71e28d70ba2.xml` | 0 | False | 0.080 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.103 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.218 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.584 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.089 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.086 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\[value\]\+edge$ --output-junit /build/.repropatch-results/f9d203756ffa41fd90ede44c08fa2662-c09099ec9abe42f1b4e00d0f3c5db10f.xml --timeout 120.000000` | 0 | False | 0.097 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f9d203756ffa41fd90ede44c08fa2662-c09099ec9abe42f1b4e00d0f3c5db10f.xml` | 0 | False | 0.101 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/f9d203756ffa41fd90ede44c08fa2662-cb38966c769a41019312e90d3ca8be85.xml --timeout 120.000000` | 0 | False | 0.089 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f9d203756ffa41fd90ede44c08fa2662-cb38966c769a41019312e90d3ca8be85.xml` | 0 | False | 0.077 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/f9d203756ffa41fd90ede44c08fa2662-59e8d0cf41794a538e380b354c390826.xml --timeout 120.000000` | 0 | False | 0.099 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f9d203756ffa41fd90ede44c08fa2662-59e8d0cf41794a538e380b354c390826.xml` | 0 | False | 0.092 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/f9d203756ffa41fd90ede44c08fa2662-8829032c9cb4464ca491b128f6801823.xml --timeout 120.000000` | 0 | False | 0.092 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f9d203756ffa41fd90ede44c08fa2662-8829032c9cb4464ca491b128f6801823.xml` | 0 | False | 0.085 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
