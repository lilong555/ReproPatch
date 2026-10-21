# ReproPatch run 3a4d70c80e204137bfbab6a6a3bb0db3

Status: **passed**
Docker isolated: True
Base commit: `35bc59b3fd9a36b51ae7c7c7d4836c722a9cd896`
Reproduced: True; independently verified: True
Elapsed: 9.964 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.082 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.226 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.567 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.086 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.095 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/7412515941f9482280c72ea5a589b1ca-ca3f7ade8f984c9a995dec8065692cab.xml --timeout 120.000000` | 8 | False | 0.107 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/7412515941f9482280c72ea5a589b1ca-ca3f7ade8f984c9a995dec8065692cab.xml` | 0 | False | 0.096 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/7412515941f9482280c72ea5a589b1ca-e66f99e767fb40e9a3f93abe61358259.xml --timeout 120.000000` | 0 | False | 0.107 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/7412515941f9482280c72ea5a589b1ca-e66f99e767fb40e9a3f93abe61358259.xml` | 0 | False | 0.087 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/7412515941f9482280c72ea5a589b1ca-fa1931c8f4f647d3b16a94579b2dbd4b.xml --timeout 120.000000` | 0 | False | 0.100 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/7412515941f9482280c72ea5a589b1ca-fa1931c8f4f647d3b16a94579b2dbd4b.xml` | 0 | False | 0.101 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/7412515941f9482280c72ea5a589b1ca-041c245697c0439882e493d544e95664.xml --timeout 120.000000` | 0 | False | 0.099 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/7412515941f9482280c72ea5a589b1ca-041c245697c0439882e493d544e95664.xml` | 0 | False | 0.080 |
| agent-check | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.104 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.229 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.576 |
| agent-check | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.087 |
| agent-check | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.089 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/d4f6aa37b1cd4526b260d35a05f44f6d-601a0159eb34411186ab1bc1a75ec36b.xml --timeout 120.000000` | 0 | False | 0.095 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d4f6aa37b1cd4526b260d35a05f44f6d-601a0159eb34411186ab1bc1a75ec36b.xml` | 0 | False | 0.089 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/d4f6aa37b1cd4526b260d35a05f44f6d-790dee82350144289222dfc8427376e6.xml --timeout 120.000000` | 0 | False | 0.100 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d4f6aa37b1cd4526b260d35a05f44f6d-790dee82350144289222dfc8427376e6.xml` | 0 | False | 0.086 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/d4f6aa37b1cd4526b260d35a05f44f6d-fdf03621385b449c88461072ab08ab38.xml --timeout 120.000000` | 0 | False | 0.098 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d4f6aa37b1cd4526b260d35a05f44f6d-fdf03621385b449c88461072ab08ab38.xml` | 0 | False | 0.089 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/d4f6aa37b1cd4526b260d35a05f44f6d-8c7e487f74374304a2e7bfe0d8579269.xml --timeout 120.000000` | 0 | False | 0.109 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d4f6aa37b1cd4526b260d35a05f44f6d-8c7e487f74374304a2e7bfe0d8579269.xml` | 0 | False | 0.076 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.105 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.245 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.600 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.100 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.078 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/1c5632dc8cca4f2eb6f27918d2773af5-bce355a9067c4cfc923ece06f525c894.xml --timeout 120.000000` | 0 | False | 0.093 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/1c5632dc8cca4f2eb6f27918d2773af5-bce355a9067c4cfc923ece06f525c894.xml` | 0 | False | 0.077 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/1c5632dc8cca4f2eb6f27918d2773af5-f3cd2ffa3f4540e2bd37bc09d19d31e3.xml --timeout 120.000000` | 0 | False | 0.105 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/1c5632dc8cca4f2eb6f27918d2773af5-f3cd2ffa3f4540e2bd37bc09d19d31e3.xml` | 0 | False | 0.076 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/1c5632dc8cca4f2eb6f27918d2773af5-d1a5ab3407aa49efa953c3b0d4eea5e5.xml --timeout 120.000000` | 0 | False | 0.107 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/1c5632dc8cca4f2eb6f27918d2773af5-d1a5ab3407aa49efa953c3b0d4eea5e5.xml` | 0 | False | 0.080 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/1c5632dc8cca4f2eb6f27918d2773af5-ef6de216cc254d64820409f64bc03d29.xml --timeout 120.000000` | 0 | False | 0.102 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/1c5632dc8cca4f2eb6f27918d2773af5-ef6de216cc254d64820409f64bc03d29.xml` | 0 | False | 0.087 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
