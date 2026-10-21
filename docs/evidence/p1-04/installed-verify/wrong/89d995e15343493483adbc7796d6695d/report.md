# ReproPatch run 89d995e15343493483adbc7796d6695d

Status: **failed**
Docker isolated: True
Base commit: `075a19d1b097d96df3550d2f08d20a0076705210`
Reproduced: True; independently verified: False
Elapsed: 8.439 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.095 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.277 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.597 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.134 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.107 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/d57d0e6f7d6f40718d5c2dba47b6a229-41e439c58b0a4434bd5476e44e6d8db3.xml --timeout 120.000000` | 8 | False | 0.105 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d57d0e6f7d6f40718d5c2dba47b6a229-41e439c58b0a4434bd5476e44e6d8db3.xml` | 0 | False | 0.128 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/d57d0e6f7d6f40718d5c2dba47b6a229-752b2e8dd84b4bd7a225c254de74fa7d.xml --timeout 120.000000` | 0 | False | 0.111 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d57d0e6f7d6f40718d5c2dba47b6a229-752b2e8dd84b4bd7a225c254de74fa7d.xml` | 0 | False | 0.094 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/d57d0e6f7d6f40718d5c2dba47b6a229-ad346fa6f2cb463184b7d997b6748fc6.xml --timeout 120.000000` | 0 | False | 0.125 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d57d0e6f7d6f40718d5c2dba47b6a229-ad346fa6f2cb463184b7d997b6748fc6.xml` | 0 | False | 0.137 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/d57d0e6f7d6f40718d5c2dba47b6a229-61f89a3359f5468a8dd797aa88a35922.xml --timeout 120.000000` | 0 | False | 0.087 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d57d0e6f7d6f40718d5c2dba47b6a229-61f89a3359f5468a8dd797aa88a35922.xml` | 0 | False | 0.119 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.109 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.240 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.547 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.094 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.127 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/f558d99078374051926db9a26e11afd7-f0fcbba830df434ba7b582d18b1e4564.xml --timeout 120.000000` | 8 | False | 0.159 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f558d99078374051926db9a26e11afd7-f0fcbba830df434ba7b582d18b1e4564.xml` | 0 | False | 0.105 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/f558d99078374051926db9a26e11afd7-963845d52cc644289f0c9634f646d55b.xml --timeout 120.000000` | 0 | False | 0.131 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f558d99078374051926db9a26e11afd7-963845d52cc644289f0c9634f646d55b.xml` | 0 | False | 0.145 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/f558d99078374051926db9a26e11afd7-36292bd433b745f4ba94af41387b7a56.xml --timeout 120.000000` | 0 | False | 0.089 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f558d99078374051926db9a26e11afd7-36292bd433b745f4ba94af41387b7a56.xml` | 0 | False | 0.095 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/f558d99078374051926db9a26e11afd7-03edb750e0e040c49dc564a726abbe15.xml --timeout 120.000000` | 0 | False | 0.121 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f558d99078374051926db9a26e11afd7-03edb750e0e040c49dc564a726abbe15.xml` | 0 | False | 0.145 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
