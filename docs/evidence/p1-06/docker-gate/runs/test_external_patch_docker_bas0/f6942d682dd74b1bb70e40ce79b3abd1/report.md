# ReproPatch run f6942d682dd74b1bb70e40ce79b3abd1

Status: **passed**
Docker isolated: True
Base commit: `8d6483c30ae587e6b77174677be224b9c39ea675`
Reproduced: True; independently verified: True
Elapsed: 8.024 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.115 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.211 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.584 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.146 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.094 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/affecd3fbc5c4efd9a7f7a5b41ab9b57-9283e2e6ce0d4f7297b8bcb196d5e6c5.xml --timeout 120.000000` | 8 | False | 0.167 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/affecd3fbc5c4efd9a7f7a5b41ab9b57-9283e2e6ce0d4f7297b8bcb196d5e6c5.xml` | 0 | False | 0.113 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/affecd3fbc5c4efd9a7f7a5b41ab9b57-a816d608b5ed4d448b7b7c311e85532f.xml --timeout 120.000000` | 0 | False | 0.130 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/affecd3fbc5c4efd9a7f7a5b41ab9b57-a816d608b5ed4d448b7b7c311e85532f.xml` | 0 | False | 0.154 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/affecd3fbc5c4efd9a7f7a5b41ab9b57-f4d748b8b4b54255820974475eb6b973.xml --timeout 120.000000` | 0 | False | 0.114 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/affecd3fbc5c4efd9a7f7a5b41ab9b57-f4d748b8b4b54255820974475eb6b973.xml` | 0 | False | 0.091 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/affecd3fbc5c4efd9a7f7a5b41ab9b57-f3bb60c67d5b479daa0ce7c7c97123c9.xml --timeout 120.000000` | 0 | False | 0.125 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/affecd3fbc5c4efd9a7f7a5b41ab9b57-f3bb60c67d5b479daa0ce7c7c97123c9.xml` | 0 | False | 0.116 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.129 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.223 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.595 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.158 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.107 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/e8e162e13dc84fbc9ddc4f10802443af-c563573e95a04ed499b6a748c760be58.xml --timeout 120.000000` | 0 | False | 0.089 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/e8e162e13dc84fbc9ddc4f10802443af-c563573e95a04ed499b6a748c760be58.xml` | 0 | False | 0.166 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/e8e162e13dc84fbc9ddc4f10802443af-43fdfab312f4480080b1874279027a34.xml --timeout 120.000000` | 0 | False | 0.114 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/e8e162e13dc84fbc9ddc4f10802443af-43fdfab312f4480080b1874279027a34.xml` | 0 | False | 0.094 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/e8e162e13dc84fbc9ddc4f10802443af-d531eae54c5d45528bdce37580dcbb41.xml --timeout 120.000000` | 0 | False | 0.114 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/e8e162e13dc84fbc9ddc4f10802443af-d531eae54c5d45528bdce37580dcbb41.xml` | 0 | False | 0.117 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/e8e162e13dc84fbc9ddc4f10802443af-d9697728ff4546d18829334a52ece72d.xml --timeout 120.000000` | 0 | False | 0.098 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/e8e162e13dc84fbc9ddc4f10802443af-d9697728ff4546d18829334a52ece72d.xml` | 0 | False | 0.124 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
