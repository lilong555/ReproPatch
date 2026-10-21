# ReproPatch run 3cc6ddeae0914784b466cce1d2fb359b

Status: **passed**
Docker isolated: True
Base commit: `9dc40918a87eb1ea773338b5cf07a1f65a20b6c6`
Reproduced: True; independently verified: True
Elapsed: 10.558 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.094 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.224 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.598 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.095 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.097 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/188d510afb31433d8ed986734d2bebf3-276f90fa0de34683b6d6bbdecc47b5f6.xml --timeout 120.000000` | 8 | False | 0.117 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/188d510afb31433d8ed986734d2bebf3-276f90fa0de34683b6d6bbdecc47b5f6.xml` | 0 | False | 0.096 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/188d510afb31433d8ed986734d2bebf3-72fbc5dc43054efca8713e118c2a4978.xml --timeout 120.000000` | 0 | False | 0.109 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/188d510afb31433d8ed986734d2bebf3-72fbc5dc43054efca8713e118c2a4978.xml` | 0 | False | 0.100 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/188d510afb31433d8ed986734d2bebf3-8704155fc09f4d589851a3321dcdbe7e.xml --timeout 120.000000` | 0 | False | 0.085 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/188d510afb31433d8ed986734d2bebf3-8704155fc09f4d589851a3321dcdbe7e.xml` | 0 | False | 0.113 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/188d510afb31433d8ed986734d2bebf3-812e304744c643fa8ecbb461e2f41e4f.xml --timeout 120.000000` | 0 | False | 0.108 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/188d510afb31433d8ed986734d2bebf3-812e304744c643fa8ecbb461e2f41e4f.xml` | 0 | False | 0.082 |
| agent-check | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.098 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.222 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.611 |
| agent-check | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.073 |
| agent-check | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.083 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/47e67b89eef6488a945442bea7cf8068-0881d70d4b0a4442ad6acb6500cedd5c.xml --timeout 120.000000` | 0 | False | 0.094 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/47e67b89eef6488a945442bea7cf8068-0881d70d4b0a4442ad6acb6500cedd5c.xml` | 0 | False | 0.081 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/47e67b89eef6488a945442bea7cf8068-ede71d30383d47d7b2f8c7b8a6b88400.xml --timeout 120.000000` | 0 | False | 0.104 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/47e67b89eef6488a945442bea7cf8068-ede71d30383d47d7b2f8c7b8a6b88400.xml` | 0 | False | 0.095 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/47e67b89eef6488a945442bea7cf8068-d4cc98137e804517bd1845b7b338383e.xml --timeout 120.000000` | 0 | False | 0.107 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/47e67b89eef6488a945442bea7cf8068-d4cc98137e804517bd1845b7b338383e.xml` | 0 | False | 0.097 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/47e67b89eef6488a945442bea7cf8068-0db17b3700bb4f2abff3469e6193a7ff.xml --timeout 120.000000` | 0 | False | 0.103 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/47e67b89eef6488a945442bea7cf8068-0db17b3700bb4f2abff3469e6193a7ff.xml` | 0 | False | 0.093 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.080 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.234 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.620 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.073 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.077 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/11261287f88146ec944891902f592778-187072763819489aa54215497f25761c.xml --timeout 120.000000` | 0 | False | 0.089 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/11261287f88146ec944891902f592778-187072763819489aa54215497f25761c.xml` | 0 | False | 0.085 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/11261287f88146ec944891902f592778-e6fbc9dc35cf45b7bd87a00f7b7b89d0.xml --timeout 120.000000` | 0 | False | 0.089 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/11261287f88146ec944891902f592778-e6fbc9dc35cf45b7bd87a00f7b7b89d0.xml` | 0 | False | 0.083 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/11261287f88146ec944891902f592778-997552b5ae044b91ad9984f64617f0fd.xml --timeout 120.000000` | 0 | False | 0.111 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/11261287f88146ec944891902f592778-997552b5ae044b91ad9984f64617f0fd.xml` | 0 | False | 0.087 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/11261287f88146ec944891902f592778-f8b114326d4b4841b09e4d6a682c0df1.xml --timeout 120.000000` | 0 | False | 0.097 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/11261287f88146ec944891902f592778-f8b114326d4b4841b09e4d6a682c0df1.xml` | 0 | False | 0.097 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
