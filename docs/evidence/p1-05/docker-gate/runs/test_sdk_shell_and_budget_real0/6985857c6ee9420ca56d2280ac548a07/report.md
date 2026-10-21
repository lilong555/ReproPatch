# ReproPatch run 6985857c6ee9420ca56d2280ac548a07

Status: **passed**
Docker isolated: True
Base commit: `56f7a1c1cf86004eb7dc3d479bfe5a25887969c0`
Reproduced: True; independently verified: True
Elapsed: 7.648 seconds
Model turns: 3; tool calls: 2

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.104 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.244 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.626 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.099 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.095 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/2c4d82587be64f2bad233fe11bb166cc-0741162ce3c6465b868f4972fdb458cd.xml --timeout 120.000000` | 8 | False | 0.114 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2c4d82587be64f2bad233fe11bb166cc-0741162ce3c6465b868f4972fdb458cd.xml` | 0 | False | 0.097 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/2c4d82587be64f2bad233fe11bb166cc-46f678d0da5849a284b4846af62bacc7.xml --timeout 120.000000` | 0 | False | 0.086 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2c4d82587be64f2bad233fe11bb166cc-46f678d0da5849a284b4846af62bacc7.xml` | 0 | False | 0.085 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/2c4d82587be64f2bad233fe11bb166cc-6ee2ea7d924643fe9b262990496d12bc.xml --timeout 120.000000` | 0 | False | 0.095 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2c4d82587be64f2bad233fe11bb166cc-6ee2ea7d924643fe9b262990496d12bc.xml` | 0 | False | 0.098 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/2c4d82587be64f2bad233fe11bb166cc-b4701ceaf5724364bafc971c19882979.xml --timeout 120.000000` | 0 | False | 0.100 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2c4d82587be64f2bad233fe11bb166cc-b4701ceaf5724364bafc971c19882979.xml` | 0 | False | 0.088 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.094 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.229 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.588 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.091 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.079 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/2f2400fe893641d4919da7180e83a822-2ba8ed8ff4eb48a08fa1452551cba242.xml --timeout 120.000000` | 0 | False | 0.086 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2f2400fe893641d4919da7180e83a822-2ba8ed8ff4eb48a08fa1452551cba242.xml` | 0 | False | 0.084 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/2f2400fe893641d4919da7180e83a822-3d28950306134a6b93db9e4b50c51695.xml --timeout 120.000000` | 0 | False | 0.100 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2f2400fe893641d4919da7180e83a822-3d28950306134a6b93db9e4b50c51695.xml` | 0 | False | 0.089 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/2f2400fe893641d4919da7180e83a822-0516c34cf1da4033a46a42c6f950df8f.xml --timeout 120.000000` | 0 | False | 0.097 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2f2400fe893641d4919da7180e83a822-0516c34cf1da4033a46a42c6f950df8f.xml` | 0 | False | 0.099 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/2f2400fe893641d4919da7180e83a822-84d5402413d148d09838a61457fc6b30.xml --timeout 120.000000` | 0 | False | 0.103 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/2f2400fe893641d4919da7180e83a822-84d5402413d148d09838a61457fc6b30.xml` | 0 | False | 0.083 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
