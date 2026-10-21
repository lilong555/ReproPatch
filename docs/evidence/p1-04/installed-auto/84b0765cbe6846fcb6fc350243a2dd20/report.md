# ReproPatch run 84b0765cbe6846fcb6fc350243a2dd20

Status: **passed**
Docker isolated: True
Base commit: `075a19d1b097d96df3550d2f08d20a0076705210`
Reproduced: True; independently verified: True
Elapsed: 11.033 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.109 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.282 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.577 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.131 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.111 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/9d3da27aeaa446a0ba6d665e3c52aa9c-08433fcdf0d1463a9264c36b14fae2cc.xml --timeout 120.000000` | 8 | False | 0.153 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/9d3da27aeaa446a0ba6d665e3c52aa9c-08433fcdf0d1463a9264c36b14fae2cc.xml` | 0 | False | 0.081 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/9d3da27aeaa446a0ba6d665e3c52aa9c-458af86e101343d8afc05c0a409fad6c.xml --timeout 120.000000` | 0 | False | 0.127 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/9d3da27aeaa446a0ba6d665e3c52aa9c-458af86e101343d8afc05c0a409fad6c.xml` | 0 | False | 0.075 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/9d3da27aeaa446a0ba6d665e3c52aa9c-cb5a7a015fd644d28f326961fe0edffc.xml --timeout 120.000000` | 0 | False | 0.109 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/9d3da27aeaa446a0ba6d665e3c52aa9c-cb5a7a015fd644d28f326961fe0edffc.xml` | 0 | False | 0.103 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/9d3da27aeaa446a0ba6d665e3c52aa9c-2d0a69839bb7413aa324464c55102b42.xml --timeout 120.000000` | 0 | False | 0.126 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/9d3da27aeaa446a0ba6d665e3c52aa9c-2d0a69839bb7413aa324464c55102b42.xml` | 0 | False | 0.106 |
| agent-check | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.142 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.211 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.609 |
| agent-check | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.140 |
| agent-check | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.103 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/00208e4b9c5e499aab98a1ffef607e45-0a8372f2405d454cb2e89a526c2154a4.xml --timeout 120.000000` | 0 | False | 0.120 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/00208e4b9c5e499aab98a1ffef607e45-0a8372f2405d454cb2e89a526c2154a4.xml` | 0 | False | 0.111 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/00208e4b9c5e499aab98a1ffef607e45-f070613641cd4d6face02540fecf6d70.xml --timeout 120.000000` | 0 | False | 0.091 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/00208e4b9c5e499aab98a1ffef607e45-f070613641cd4d6face02540fecf6d70.xml` | 0 | False | 0.155 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/00208e4b9c5e499aab98a1ffef607e45-100b4ab019d24400823f64ef8e3d0610.xml --timeout 120.000000` | 0 | False | 0.108 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/00208e4b9c5e499aab98a1ffef607e45-100b4ab019d24400823f64ef8e3d0610.xml` | 0 | False | 0.095 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/00208e4b9c5e499aab98a1ffef607e45-aa4591ab0de347b7b1c37457d1c3b366.xml --timeout 120.000000` | 0 | False | 0.117 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/00208e4b9c5e499aab98a1ffef607e45-aa4591ab0de347b7b1c37457d1c3b366.xml` | 0 | False | 0.105 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.111 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.221 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.652 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.150 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.083 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/d46eee5b23184e7a9d48b7554e3f8383-634d80688aea4d6bad9efbc600f63107.xml --timeout 120.000000` | 0 | False | 0.081 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d46eee5b23184e7a9d48b7554e3f8383-634d80688aea4d6bad9efbc600f63107.xml` | 0 | False | 0.086 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/d46eee5b23184e7a9d48b7554e3f8383-586c7585a4724cf3857e59159ef34d01.xml --timeout 120.000000` | 0 | False | 0.080 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d46eee5b23184e7a9d48b7554e3f8383-586c7585a4724cf3857e59159ef34d01.xml` | 0 | False | 0.075 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/d46eee5b23184e7a9d48b7554e3f8383-3c6ffb5da7994c1c8312219922292640.xml --timeout 120.000000` | 0 | False | 0.076 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d46eee5b23184e7a9d48b7554e3f8383-3c6ffb5da7994c1c8312219922292640.xml` | 0 | False | 0.088 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/d46eee5b23184e7a9d48b7554e3f8383-cb64fa14f7a548c6b9a6bd2b7c71e81b.xml --timeout 120.000000` | 0 | False | 0.093 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d46eee5b23184e7a9d48b7554e3f8383-cb64fa14f7a548c6b9a6bd2b7c71e81b.xml` | 0 | False | 0.083 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
