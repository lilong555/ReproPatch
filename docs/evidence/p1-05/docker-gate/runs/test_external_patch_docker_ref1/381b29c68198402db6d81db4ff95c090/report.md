# ReproPatch run 381b29c68198402db6d81db4ff95c090

Status: **failed**
Docker isolated: True
Base commit: `803d0f794b5a8082ae05981883225f548680efe3`
Reproduced: True; independently verified: False
Elapsed: 5.199 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.096 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.222 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.587 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.090 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.068 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/ab3464e775d04f6a9ab843f747423bba-ddad6e16232f4a888b01c4567bc09d81.xml --timeout 120.000000` | 8 | False | 0.097 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/ab3464e775d04f6a9ab843f747423bba-ddad6e16232f4a888b01c4567bc09d81.xml` | 0 | False | 0.088 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/ab3464e775d04f6a9ab843f747423bba-c5afea9c98e144b69940afb75cc58ff2.xml --timeout 120.000000` | 0 | False | 0.094 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/ab3464e775d04f6a9ab843f747423bba-c5afea9c98e144b69940afb75cc58ff2.xml` | 0 | False | 0.086 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/ab3464e775d04f6a9ab843f747423bba-84a78f16978f43fca8a59543c117d3e7.xml --timeout 120.000000` | 0 | False | 0.096 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/ab3464e775d04f6a9ab843f747423bba-84a78f16978f43fca8a59543c117d3e7.xml` | 0 | False | 0.092 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/ab3464e775d04f6a9ab843f747423bba-52e94e9592234f1a9eee99b979c0e48f.xml --timeout 120.000000` | 0 | False | 0.091 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/ab3464e775d04f6a9ab843f747423bba-52e94e9592234f1a9eee99b979c0e48f.xml` | 0 | False | 0.094 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.115 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.233 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.602 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.093 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
