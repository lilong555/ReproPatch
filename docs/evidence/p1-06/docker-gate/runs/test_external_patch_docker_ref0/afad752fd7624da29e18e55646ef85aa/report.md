# ReproPatch run afad752fd7624da29e18e55646ef85aa

Status: **failed**
Docker isolated: True
Base commit: `6ffbc88a24c8719b67a6f6cbc54d36c175543d17`
Reproduced: True; independently verified: False
Elapsed: 7.906 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.145 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.229 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.614 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.147 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.094 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/88cddee5fc3b4192a3eebd78f6ec6466-648154dff4df47c2ac3e942a62a4cfc9.xml --timeout 120.000000` | 8 | False | 0.162 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/88cddee5fc3b4192a3eebd78f6ec6466-648154dff4df47c2ac3e942a62a4cfc9.xml` | 0 | False | 0.142 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/88cddee5fc3b4192a3eebd78f6ec6466-3207ab93c8b343cd8ca5af1370433aa1.xml --timeout 120.000000` | 0 | False | 0.092 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/88cddee5fc3b4192a3eebd78f6ec6466-3207ab93c8b343cd8ca5af1370433aa1.xml` | 0 | False | 0.093 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/88cddee5fc3b4192a3eebd78f6ec6466-0781e324e8664d2a9818e70c919482a4.xml --timeout 120.000000` | 0 | False | 0.132 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/88cddee5fc3b4192a3eebd78f6ec6466-0781e324e8664d2a9818e70c919482a4.xml` | 0 | False | 0.110 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/88cddee5fc3b4192a3eebd78f6ec6466-80a6c81bdfc04a52a5008d223e1f403d.xml --timeout 120.000000` | 0 | False | 0.103 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/88cddee5fc3b4192a3eebd78f6ec6466-80a6c81bdfc04a52a5008d223e1f403d.xml` | 0 | False | 0.160 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.105 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.245 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.649 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.092 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.074 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/680446337eb34cb69c7c859155064ce9-d809f3968c2b400e882ba2545d8cb59e.xml --timeout 120.000000` | 0 | False | 0.116 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/680446337eb34cb69c7c859155064ce9-d809f3968c2b400e882ba2545d8cb59e.xml` | 0 | False | 0.087 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/680446337eb34cb69c7c859155064ce9-818b73a7546144a1bfd9b5a5f24d0179.xml --timeout 120.000000` | 0 | False | 0.097 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/680446337eb34cb69c7c859155064ce9-818b73a7546144a1bfd9b5a5f24d0179.xml` | 0 | False | 0.115 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/680446337eb34cb69c7c859155064ce9-597a7b1b8eb24328a7d3240aa88f71d1.xml --timeout 120.000000` | 0 | False | 0.108 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/680446337eb34cb69c7c859155064ce9-597a7b1b8eb24328a7d3240aa88f71d1.xml` | 0 | False | 0.090 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/680446337eb34cb69c7c859155064ce9-fee0823a9cac4b548337b9e145e79ae5.xml --timeout 120.000000` | 8 | False | 0.162 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/680446337eb34cb69c7c859155064ce9-fee0823a9cac4b548337b9e145e79ae5.xml` | 0 | False | 0.123 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
