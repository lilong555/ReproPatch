# ReproPatch run c3dc5d167d3248f6962b65fc24ac5f31

Status: **failed**
Docker isolated: True
Base commit: `bc1feb86595b0010893ea215e26344cde9e873c4`
Reproduced: True; independently verified: False
Elapsed: 5.189 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.097 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.235 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.624 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.095 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.090 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/68cb2c05e8fd487e98292829ec919fb4-efb4232eff1947f99d6f3e3f60c6cc76.xml --timeout 120.000000` | 8 | False | 0.124 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/68cb2c05e8fd487e98292829ec919fb4-efb4232eff1947f99d6f3e3f60c6cc76.xml` | 0 | False | 0.089 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/68cb2c05e8fd487e98292829ec919fb4-3f678dd63f0145e5b1dab21e382b8aba.xml --timeout 120.000000` | 0 | False | 0.104 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/68cb2c05e8fd487e98292829ec919fb4-3f678dd63f0145e5b1dab21e382b8aba.xml` | 0 | False | 0.094 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/68cb2c05e8fd487e98292829ec919fb4-8224dbfc11c74ef78aed198f381f85d6.xml --timeout 120.000000` | 0 | False | 0.111 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/68cb2c05e8fd487e98292829ec919fb4-8224dbfc11c74ef78aed198f381f85d6.xml` | 0 | False | 0.094 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/68cb2c05e8fd487e98292829ec919fb4-513a144bce9f4e689572b24f0b7e6bb7.xml --timeout 120.000000` | 0 | False | 0.110 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/68cb2c05e8fd487e98292829ec919fb4-513a144bce9f4e689572b24f0b7e6bb7.xml` | 0 | False | 0.091 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.093 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.229 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.587 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.088 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
