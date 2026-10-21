# ReproPatch run 0912e3e911c84094b67b2abc83d1e5ef

Status: **passed**
Docker isolated: True
Base commit: `075a19d1b097d96df3550d2f08d20a0076705210`
Reproduced: True; independently verified: True
Elapsed: 10.789 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.083 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.214 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.667 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.102 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.094 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/49c5510144b2481ca289b8339b2c3e5f-0dcfd69dd79844eb955cc79e6697e8e6.xml --timeout 120.000000` | 8 | False | 0.100 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/49c5510144b2481ca289b8339b2c3e5f-0dcfd69dd79844eb955cc79e6697e8e6.xml` | 0 | False | 0.090 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/49c5510144b2481ca289b8339b2c3e5f-0f7e7c7a2cd040a8aade2c87ada2435b.xml --timeout 120.000000` | 0 | False | 0.106 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/49c5510144b2481ca289b8339b2c3e5f-0f7e7c7a2cd040a8aade2c87ada2435b.xml` | 0 | False | 0.103 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/49c5510144b2481ca289b8339b2c3e5f-51a43165d0314157a5bbc24b80437a73.xml --timeout 120.000000` | 0 | False | 0.079 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/49c5510144b2481ca289b8339b2c3e5f-51a43165d0314157a5bbc24b80437a73.xml` | 0 | False | 0.068 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/49c5510144b2481ca289b8339b2c3e5f-7624a498dc4643ee9c3f4b6fec142220.xml --timeout 120.000000` | 0 | False | 0.093 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/49c5510144b2481ca289b8339b2c3e5f-7624a498dc4643ee9c3f4b6fec142220.xml` | 0 | False | 0.087 |
| agent-check | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.098 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.221 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.698 |
| agent-check | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.107 |
| agent-check | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.088 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/7afe31b29900488980d06eeb6b96e9c2-e2ca138ed8814e23b2abc4904c4575ed.xml --timeout 120.000000` | 0 | False | 0.083 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/7afe31b29900488980d06eeb6b96e9c2-e2ca138ed8814e23b2abc4904c4575ed.xml` | 0 | False | 0.070 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/7afe31b29900488980d06eeb6b96e9c2-f08bcc35228c40d688ca758f18beb8b6.xml --timeout 120.000000` | 0 | False | 0.097 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/7afe31b29900488980d06eeb6b96e9c2-f08bcc35228c40d688ca758f18beb8b6.xml` | 0 | False | 0.093 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/7afe31b29900488980d06eeb6b96e9c2-db5a1165908a40a4967089bdc878a2e6.xml --timeout 120.000000` | 0 | False | 0.100 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/7afe31b29900488980d06eeb6b96e9c2-db5a1165908a40a4967089bdc878a2e6.xml` | 0 | False | 0.089 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/7afe31b29900488980d06eeb6b96e9c2-9caa777d5f904c4493174b22c1d30269.xml --timeout 120.000000` | 0 | False | 0.097 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/7afe31b29900488980d06eeb6b96e9c2-9caa777d5f904c4493174b22c1d30269.xml` | 0 | False | 0.094 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.104 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.241 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.674 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.102 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.086 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/79b88665587f4433976c80b27e7d5bad-edc157cb87574867b434cf1cafa9a031.xml --timeout 120.000000` | 0 | False | 0.114 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/79b88665587f4433976c80b27e7d5bad-edc157cb87574867b434cf1cafa9a031.xml` | 0 | False | 0.103 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/79b88665587f4433976c80b27e7d5bad-d5529697233946478ea2b48b670bb656.xml --timeout 120.000000` | 0 | False | 0.108 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/79b88665587f4433976c80b27e7d5bad-d5529697233946478ea2b48b670bb656.xml` | 0 | False | 0.099 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/79b88665587f4433976c80b27e7d5bad-5926b650d7f14cc383465e3e15433f07.xml --timeout 120.000000` | 0 | False | 0.092 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/79b88665587f4433976c80b27e7d5bad-5926b650d7f14cc383465e3e15433f07.xml` | 0 | False | 0.107 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/79b88665587f4433976c80b27e7d5bad-27c45c4ad8a4445dbb084a6fa9ae9ca7.xml --timeout 120.000000` | 0 | False | 0.099 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/79b88665587f4433976c80b27e7d5bad-27c45c4ad8a4445dbb084a6fa9ae9ca7.xml` | 0 | False | 0.087 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
