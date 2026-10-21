# ReproPatch run e99668a796d54008904201c082aa805a

Status: **passed**
Docker isolated: True
Base commit: `2f7e02328ae11e6099aa0a0ccad2622e2d2f6509`
Reproduced: True; independently verified: True
Elapsed: 6.168 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.104 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.214 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.588 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.084 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.080 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/d16126dcec7143499b874a2c3ad3958b-7bbf0f714ee84f1d8d0fef70fddd7080.xml --timeout 120.000000` | 8 | False | 0.087 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d16126dcec7143499b874a2c3ad3958b-7bbf0f714ee84f1d8d0fef70fddd7080.xml` | 0 | False | 0.095 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/d16126dcec7143499b874a2c3ad3958b-9de6565d5c1e41f4b1144c9cecd728aa.xml --timeout 120.000000` | 0 | False | 0.101 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d16126dcec7143499b874a2c3ad3958b-9de6565d5c1e41f4b1144c9cecd728aa.xml` | 0 | False | 0.104 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/d16126dcec7143499b874a2c3ad3958b-57151108b0c6475792bac4a508d81e8d.xml --timeout 120.000000` | 0 | False | 0.098 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d16126dcec7143499b874a2c3ad3958b-57151108b0c6475792bac4a508d81e8d.xml` | 0 | False | 0.087 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/d16126dcec7143499b874a2c3ad3958b-71ef7b7afd7e4583b94c6c8c709745fb.xml --timeout 120.000000` | 0 | False | 0.101 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d16126dcec7143499b874a2c3ad3958b-71ef7b7afd7e4583b94c6c8c709745fb.xml` | 0 | False | 0.092 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.104 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.228 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.601 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.095 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.088 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/a7e4c3c52c38498daad1b9fbcfa9c274-db9446a833d54fdbbfc2a9378f571e6f.xml --timeout 120.000000` | 0 | False | 0.092 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a7e4c3c52c38498daad1b9fbcfa9c274-db9446a833d54fdbbfc2a9378f571e6f.xml` | 0 | False | 0.090 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/a7e4c3c52c38498daad1b9fbcfa9c274-af17bf3b773849f6aff7987fe0672a15.xml --timeout 120.000000` | 0 | False | 0.088 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a7e4c3c52c38498daad1b9fbcfa9c274-af17bf3b773849f6aff7987fe0672a15.xml` | 0 | False | 0.081 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/a7e4c3c52c38498daad1b9fbcfa9c274-e40e5972e99142e2bff69a6b9ac4a78b.xml --timeout 120.000000` | 0 | False | 0.101 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a7e4c3c52c38498daad1b9fbcfa9c274-e40e5972e99142e2bff69a6b9ac4a78b.xml` | 0 | False | 0.095 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/a7e4c3c52c38498daad1b9fbcfa9c274-c3f7436a880a40a3b1443395dff15478.xml --timeout 120.000000` | 0 | False | 0.111 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a7e4c3c52c38498daad1b9fbcfa9c274-c3f7436a880a40a3b1443395dff15478.xml` | 0 | False | 0.088 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
