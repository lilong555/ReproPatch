# ReproPatch run c49b00c6988149b58f3be029e5d3be81

Status: **passed**
Docker isolated: True
Base commit: `ee6d64b93eadbfd6df8c98f53cea20948d9eedd6`
Reproduced: True; independently verified: True
Elapsed: 6.797 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.132 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.250 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.664 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.109 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.107 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/f351cb4774cd48cc97084f444cf15628-42e81f12f11a4e9ea85573a3d903095f.xml --timeout 120.000000` | 8 | False | 0.096 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f351cb4774cd48cc97084f444cf15628-42e81f12f11a4e9ea85573a3d903095f.xml` | 0 | False | 0.096 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/f351cb4774cd48cc97084f444cf15628-ed102e1b478848968ad2b532a60a48e8.xml --timeout 120.000000` | 0 | False | 0.112 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f351cb4774cd48cc97084f444cf15628-ed102e1b478848968ad2b532a60a48e8.xml` | 0 | False | 0.088 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/f351cb4774cd48cc97084f444cf15628-9ba70a8cdb804d2e81af31aa80a42e7b.xml --timeout 120.000000` | 0 | False | 0.115 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f351cb4774cd48cc97084f444cf15628-9ba70a8cdb804d2e81af31aa80a42e7b.xml` | 0 | False | 0.102 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/f351cb4774cd48cc97084f444cf15628-2ce13e839c0844fb817d87b3017522a5.xml --timeout 120.000000` | 0 | False | 0.107 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f351cb4774cd48cc97084f444cf15628-2ce13e839c0844fb817d87b3017522a5.xml` | 0 | False | 0.091 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.108 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.236 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.604 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.096 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.093 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/d1529456299d4d7993bc7ca344ccc9d4-9f96eb9fcce0497eb1ac7a2087ee236c.xml --timeout 120.000000` | 0 | False | 0.105 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d1529456299d4d7993bc7ca344ccc9d4-9f96eb9fcce0497eb1ac7a2087ee236c.xml` | 0 | False | 0.099 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/d1529456299d4d7993bc7ca344ccc9d4-9d8ee5e91b2445e2b3811f15467fd5d9.xml --timeout 120.000000` | 0 | False | 0.106 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d1529456299d4d7993bc7ca344ccc9d4-9d8ee5e91b2445e2b3811f15467fd5d9.xml` | 0 | False | 0.085 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/d1529456299d4d7993bc7ca344ccc9d4-0c8bd60cdbd648689bf18c9e0835410d.xml --timeout 120.000000` | 0 | False | 0.093 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d1529456299d4d7993bc7ca344ccc9d4-0c8bd60cdbd648689bf18c9e0835410d.xml` | 0 | False | 0.082 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/d1529456299d4d7993bc7ca344ccc9d4-4382b38a8ad04fffbab53648e6f7971f.xml --timeout 120.000000` | 0 | False | 0.103 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d1529456299d4d7993bc7ca344ccc9d4-4382b38a8ad04fffbab53648e6f7971f.xml` | 0 | False | 0.087 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
