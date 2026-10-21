# ReproPatch run 8dcce9740e7c4207866fc3bcd887548b

Status: **passed**
Docker isolated: True
Base commit: `d7d1558579dcd5ba82a140c5ef1b0423a50be997`
Reproduced: True; independently verified: True
Elapsed: 6.709 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.149 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.221 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.588 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.213 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.170 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\[value\]\+edge$ --output-junit /build/.repropatch-results/2b39c5bb2b7648c0a991c13dea6068f4-e484294df7b449809c24f4927bce9567.xml --timeout 120.000000` | 8 | False | 0.142 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2b39c5bb2b7648c0a991c13dea6068f4-e484294df7b449809c24f4927bce9567.xml` | 0 | False | 0.146 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/2b39c5bb2b7648c0a991c13dea6068f4-6c4f99c527f0412c97f69bcc39a54c7c.xml --timeout 120.000000` | 0 | False | 0.161 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2b39c5bb2b7648c0a991c13dea6068f4-6c4f99c527f0412c97f69bcc39a54c7c.xml` | 0 | False | 0.128 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/2b39c5bb2b7648c0a991c13dea6068f4-b7ba5afd52a2498bb80b1a8b15891d4e.xml --timeout 120.000000` | 0 | False | 0.083 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2b39c5bb2b7648c0a991c13dea6068f4-b7ba5afd52a2498bb80b1a8b15891d4e.xml` | 0 | False | 0.081 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/2b39c5bb2b7648c0a991c13dea6068f4-2bcfd768cead4c38bd9ae99ad00bb045.xml --timeout 120.000000` | 0 | False | 0.091 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2b39c5bb2b7648c0a991c13dea6068f4-2bcfd768cead4c38bd9ae99ad00bb045.xml` | 0 | False | 0.073 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.089 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.228 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.581 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.100 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.074 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\[value\]\+edge$ --output-junit /build/.repropatch-results/3700a55db72c47dd87a463367e3bc080-ae1ad3f54b3a482f8797865b5076cfdd.xml --timeout 120.000000` | 0 | False | 0.084 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3700a55db72c47dd87a463367e3bc080-ae1ad3f54b3a482f8797865b5076cfdd.xml` | 0 | False | 0.069 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/3700a55db72c47dd87a463367e3bc080-2a6e942099d5477782cfbfcb54895945.xml --timeout 120.000000` | 0 | False | 0.097 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3700a55db72c47dd87a463367e3bc080-2a6e942099d5477782cfbfcb54895945.xml` | 0 | False | 0.080 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/3700a55db72c47dd87a463367e3bc080-23e86451488d4b829147f963d6ca091c.xml --timeout 120.000000` | 0 | False | 0.088 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3700a55db72c47dd87a463367e3bc080-23e86451488d4b829147f963d6ca091c.xml` | 0 | False | 0.097 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/3700a55db72c47dd87a463367e3bc080-43920c90ea30415f990abee53dc27d5a.xml --timeout 120.000000` | 0 | False | 0.102 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3700a55db72c47dd87a463367e3bc080-43920c90ea30415f990abee53dc27d5a.xml` | 0 | False | 0.084 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
