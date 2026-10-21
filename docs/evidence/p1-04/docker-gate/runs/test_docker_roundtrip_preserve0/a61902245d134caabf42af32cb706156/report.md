# ReproPatch run a61902245d134caabf42af32cb706156

Status: **passed**
Docker isolated: True
Base commit: `dc9293d816083d33e3409a4244215d8db5dec6e4`
Reproduced: True; independently verified: True
Elapsed: 9.327 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.085 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.220 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.589 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.087 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.091 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/95de8bcfd2c54a60970dd1854a4080ce-c19337e1c9714d6b8e5069cdb710a5a1.xml --timeout 120.000000` | 8 | False | 0.097 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/95de8bcfd2c54a60970dd1854a4080ce-c19337e1c9714d6b8e5069cdb710a5a1.xml` | 0 | False | 0.095 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/95de8bcfd2c54a60970dd1854a4080ce-bc8f8f6389c84b38bc273f3f68a1b7fa.xml --timeout 120.000000` | 0 | False | 0.101 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/95de8bcfd2c54a60970dd1854a4080ce-bc8f8f6389c84b38bc273f3f68a1b7fa.xml` | 0 | False | 0.098 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/95de8bcfd2c54a60970dd1854a4080ce-354f5490982b45e3b3e190307c9b22a6.xml --timeout 120.000000` | 0 | False | 0.082 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/95de8bcfd2c54a60970dd1854a4080ce-354f5490982b45e3b3e190307c9b22a6.xml` | 0 | False | 0.084 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/95de8bcfd2c54a60970dd1854a4080ce-0b9f2b90ede346468096833b5918ea34.xml --timeout 120.000000` | 0 | False | 0.092 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/95de8bcfd2c54a60970dd1854a4080ce-0b9f2b90ede346468096833b5918ea34.xml` | 0 | False | 0.083 |
| agent-check | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.120 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.234 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.603 |
| agent-check | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.089 |
| agent-check | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.084 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/b54ba66421ca4c2cb624378654066b44-8a5c013719b341f3aca59b9a47b85df7.xml --timeout 120.000000` | 0 | False | 0.086 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b54ba66421ca4c2cb624378654066b44-8a5c013719b341f3aca59b9a47b85df7.xml` | 0 | False | 0.087 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/b54ba66421ca4c2cb624378654066b44-734efe85cd0d49d1a5c342a537efab64.xml --timeout 120.000000` | 0 | False | 0.086 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b54ba66421ca4c2cb624378654066b44-734efe85cd0d49d1a5c342a537efab64.xml` | 0 | False | 0.077 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/b54ba66421ca4c2cb624378654066b44-0e6b657b2f1648fe84b365f770b70691.xml --timeout 120.000000` | 0 | False | 0.099 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b54ba66421ca4c2cb624378654066b44-0e6b657b2f1648fe84b365f770b70691.xml` | 0 | False | 0.085 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/b54ba66421ca4c2cb624378654066b44-7a57f47b19a04de68ce8db314dc0348b.xml --timeout 120.000000` | 0 | False | 0.087 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b54ba66421ca4c2cb624378654066b44-7a57f47b19a04de68ce8db314dc0348b.xml` | 0 | False | 0.088 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.101 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.226 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.601 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.088 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.089 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/4940ba9a21114c91a1b35cfdf054027f-0278e88c3d024bffa736983111f80066.xml --timeout 120.000000` | 0 | False | 0.093 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/4940ba9a21114c91a1b35cfdf054027f-0278e88c3d024bffa736983111f80066.xml` | 0 | False | 0.078 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/4940ba9a21114c91a1b35cfdf054027f-4e1282c3e4cb4c9aaa1ea57a6247c45d.xml --timeout 120.000000` | 0 | False | 0.100 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/4940ba9a21114c91a1b35cfdf054027f-4e1282c3e4cb4c9aaa1ea57a6247c45d.xml` | 0 | False | 0.094 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/4940ba9a21114c91a1b35cfdf054027f-2348be4f4d994c4fba207007f637e175.xml --timeout 120.000000` | 0 | False | 0.102 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/4940ba9a21114c91a1b35cfdf054027f-2348be4f4d994c4fba207007f637e175.xml` | 0 | False | 0.085 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/4940ba9a21114c91a1b35cfdf054027f-13ec61d59a2f4ba697428171356e5b9b.xml --timeout 120.000000` | 0 | False | 0.095 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/4940ba9a21114c91a1b35cfdf054027f-13ec61d59a2f4ba697428171356e5b9b.xml` | 0 | False | 0.093 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
