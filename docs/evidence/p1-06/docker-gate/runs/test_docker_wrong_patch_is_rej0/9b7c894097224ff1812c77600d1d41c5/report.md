# ReproPatch run 9b7c894097224ff1812c77600d1d41c5

Status: **failed**
Docker isolated: True
Base commit: `49ca27ae862e177e766f06ab7f3dd01019057fb8`
Reproduced: True; independently verified: False
Elapsed: 7.851 seconds
Model turns: 2; tool calls: 1

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.124 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.218 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.634 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.156 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.112 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/eea06aeef5d540f4b55fe1727091f699-d635a5ada4d446fe8e385ea104965356.xml --timeout 120.000000` | 8 | False | 0.150 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/eea06aeef5d540f4b55fe1727091f699-d635a5ada4d446fe8e385ea104965356.xml` | 0 | False | 0.125 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/eea06aeef5d540f4b55fe1727091f699-c2d8f22ebc454affa3cc78f0d1254e84.xml --timeout 120.000000` | 0 | False | 0.110 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/eea06aeef5d540f4b55fe1727091f699-c2d8f22ebc454affa3cc78f0d1254e84.xml` | 0 | False | 0.090 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/eea06aeef5d540f4b55fe1727091f699-5ab6932381a14875bdd48f0051ac1a3f.xml --timeout 120.000000` | 0 | False | 0.130 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/eea06aeef5d540f4b55fe1727091f699-5ab6932381a14875bdd48f0051ac1a3f.xml` | 0 | False | 0.141 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/eea06aeef5d540f4b55fe1727091f699-4f69bb462fd74ab9ac1002c41274d5c6.xml --timeout 120.000000` | 0 | False | 0.096 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/eea06aeef5d540f4b55fe1727091f699-4f69bb462fd74ab9ac1002c41274d5c6.xml` | 0 | False | 0.139 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.132 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.249 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.617 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.086 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.127 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/a28ea25e1af849b6b9069c4ad6e722eb-a7cd98c6b2034c5a9f4fb1860aa9b694.xml --timeout 120.000000` | 8 | False | 0.146 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a28ea25e1af849b6b9069c4ad6e722eb-a7cd98c6b2034c5a9f4fb1860aa9b694.xml` | 0 | False | 0.087 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/a28ea25e1af849b6b9069c4ad6e722eb-19ca1afcc4454ebc9bb217c1c8ef7962.xml --timeout 120.000000` | 0 | False | 0.127 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a28ea25e1af849b6b9069c4ad6e722eb-19ca1afcc4454ebc9bb217c1c8ef7962.xml` | 0 | False | 0.111 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/a28ea25e1af849b6b9069c4ad6e722eb-0e8bebbb88424f159a103d7384a28bc2.xml --timeout 120.000000` | 0 | False | 0.159 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a28ea25e1af849b6b9069c4ad6e722eb-0e8bebbb88424f159a103d7384a28bc2.xml` | 0 | False | 0.143 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/a28ea25e1af849b6b9069c4ad6e722eb-b14a7facc6904c6ea3477520c473ca51.xml --timeout 120.000000` | 0 | False | 0.135 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a28ea25e1af849b6b9069c4ad6e722eb-b14a7facc6904c6ea3477520c473ca51.xml` | 0 | False | 0.088 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
