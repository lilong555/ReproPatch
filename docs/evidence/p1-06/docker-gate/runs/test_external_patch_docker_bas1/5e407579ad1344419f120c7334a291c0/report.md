# ReproPatch run 5e407579ad1344419f120c7334a291c0

Status: **failed**
Docker isolated: True
Base commit: `fcca44a3352952a58bae7316a87ccfb74e0fdd5d`
Reproduced: True; independently verified: False
Elapsed: 8.064 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.124 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.207 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.583 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.153 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.119 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/f22baa074bdb46f7b1d753a48c450c32-577244078fab4de4b2ba148846d817f5.xml --timeout 120.000000` | 8 | False | 0.102 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f22baa074bdb46f7b1d753a48c450c32-577244078fab4de4b2ba148846d817f5.xml` | 0 | False | 0.130 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/f22baa074bdb46f7b1d753a48c450c32-3fc6cfa4cf6d43ce9ef3133ac19bce69.xml --timeout 120.000000` | 0 | False | 0.156 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f22baa074bdb46f7b1d753a48c450c32-3fc6cfa4cf6d43ce9ef3133ac19bce69.xml` | 0 | False | 0.109 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/f22baa074bdb46f7b1d753a48c450c32-f04ebe9b9f03485080c066836dfdd8b5.xml --timeout 120.000000` | 0 | False | 0.133 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f22baa074bdb46f7b1d753a48c450c32-f04ebe9b9f03485080c066836dfdd8b5.xml` | 0 | False | 0.112 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/f22baa074bdb46f7b1d753a48c450c32-dff2b39414514336b694df1a471bc31a.xml --timeout 120.000000` | 0 | False | 0.099 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f22baa074bdb46f7b1d753a48c450c32-dff2b39414514336b694df1a471bc31a.xml` | 0 | False | 0.075 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.102 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.202 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.616 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.096 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.132 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/6b39e1cc7dea449b90730636d6316f96-1b3257f5bf9d4676808b978740142d16.xml --timeout 120.000000` | 8 | False | 0.150 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/6b39e1cc7dea449b90730636d6316f96-1b3257f5bf9d4676808b978740142d16.xml` | 0 | False | 0.103 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/6b39e1cc7dea449b90730636d6316f96-cfdd3535c6834b14b649af6b5658701a.xml --timeout 120.000000` | 0 | False | 0.126 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/6b39e1cc7dea449b90730636d6316f96-cfdd3535c6834b14b649af6b5658701a.xml` | 0 | False | 0.115 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/6b39e1cc7dea449b90730636d6316f96-117fbf41fdc74b29a83ba98e7870607d.xml --timeout 120.000000` | 0 | False | 0.095 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/6b39e1cc7dea449b90730636d6316f96-117fbf41fdc74b29a83ba98e7870607d.xml` | 0 | False | 0.157 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/6b39e1cc7dea449b90730636d6316f96-82d285ef28864736970fbe99415659db.xml --timeout 120.000000` | 0 | False | 0.111 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/6b39e1cc7dea449b90730636d6316f96-82d285ef28864736970fbe99415659db.xml` | 0 | False | 0.092 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
