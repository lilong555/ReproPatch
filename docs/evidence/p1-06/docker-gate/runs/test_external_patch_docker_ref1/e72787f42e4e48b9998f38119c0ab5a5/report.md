# ReproPatch run e72787f42e4e48b9998f38119c0ab5a5

Status: **failed**
Docker isolated: True
Base commit: `b8d62df7b012cabf49d8dd63bd52294a60e36cbc`
Reproduced: True; independently verified: False
Elapsed: 6.147 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.106 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.233 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.573 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.128 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.120 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/2389ee8e1daa412596e8fd793d9a0874-8aa5372ba15d46b5b36a9418922c55be.xml --timeout 120.000000` | 8 | False | 0.101 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2389ee8e1daa412596e8fd793d9a0874-8aa5372ba15d46b5b36a9418922c55be.xml` | 0 | False | 0.074 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/2389ee8e1daa412596e8fd793d9a0874-6e12009686f8472d88be91bfbb20c816.xml --timeout 120.000000` | 0 | False | 0.109 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2389ee8e1daa412596e8fd793d9a0874-6e12009686f8472d88be91bfbb20c816.xml` | 0 | False | 0.087 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/2389ee8e1daa412596e8fd793d9a0874-747bd224e17f4b169f0bb673b921748f.xml --timeout 120.000000` | 0 | False | 0.129 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2389ee8e1daa412596e8fd793d9a0874-747bd224e17f4b169f0bb673b921748f.xml` | 0 | False | 0.115 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/2389ee8e1daa412596e8fd793d9a0874-38fd2a5c69d64c63a26c65829ff639b8.xml --timeout 120.000000` | 0 | False | 0.090 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2389ee8e1daa412596e8fd793d9a0874-38fd2a5c69d64c63a26c65829ff639b8.xml` | 0 | False | 0.134 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.093 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.258 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.655 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.096 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
