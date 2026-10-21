# ReproPatch run 21872e5f4b184269b09f048887cda279

Status: **budget_exhausted**
Docker isolated: True
Base commit: `58d75e865ce6e6f648fc2ed34c04d53a95f10a0c`
Reproduced: True; independently verified: False
Elapsed: 3.397 seconds
Model turns: 1; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.105 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.235 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.625 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.085 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.096 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/ea2765f1acf34283a0d7955c6bfd7936-430f0c1649f4479d956fdd28204ea7b1.xml --timeout 120.000000` | 8 | False | 0.119 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/ea2765f1acf34283a0d7955c6bfd7936-430f0c1649f4479d956fdd28204ea7b1.xml` | 0 | False | 0.099 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/ea2765f1acf34283a0d7955c6bfd7936-5df44700a2064f8098baa8a8537fdc39.xml --timeout 120.000000` | 0 | False | 0.104 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/ea2765f1acf34283a0d7955c6bfd7936-5df44700a2064f8098baa8a8537fdc39.xml` | 0 | False | 0.103 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/ea2765f1acf34283a0d7955c6bfd7936-c6f5cf5d117f478b913ccb11b6ef3afb.xml --timeout 120.000000` | 0 | False | 0.086 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/ea2765f1acf34283a0d7955c6bfd7936-c6f5cf5d117f478b913ccb11b6ef3afb.xml` | 0 | False | 0.094 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/ea2765f1acf34283a0d7955c6bfd7936-7db6d17f345346909d001b027f0aaa92.xml --timeout 120.000000` | 0 | False | 0.097 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/ea2765f1acf34283a0d7955c6bfd7936-7db6d17f345346909d001b027f0aaa92.xml` | 0 | False | 0.094 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
