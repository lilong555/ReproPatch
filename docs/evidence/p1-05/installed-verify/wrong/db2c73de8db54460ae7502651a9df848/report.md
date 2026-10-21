# ReproPatch run db2c73de8db54460ae7502651a9df848

Status: **failed**
Docker isolated: True
Base commit: `075a19d1b097d96df3550d2f08d20a0076705210`
Reproduced: True; independently verified: False
Elapsed: 6.597 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.098 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.213 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.595 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.091 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.071 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/3a3c407dcdd243a08fe69047f05616d6-912c8876138241cd84d853464e08ae12.xml --timeout 120.000000` | 8 | False | 0.097 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3a3c407dcdd243a08fe69047f05616d6-912c8876138241cd84d853464e08ae12.xml` | 0 | False | 0.090 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/3a3c407dcdd243a08fe69047f05616d6-3e44c1e5876c46608a2af4a1223fb091.xml --timeout 120.000000` | 0 | False | 0.078 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3a3c407dcdd243a08fe69047f05616d6-3e44c1e5876c46608a2af4a1223fb091.xml` | 0 | False | 0.085 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/3a3c407dcdd243a08fe69047f05616d6-c39358402c8c47298f7b9be25946e4b9.xml --timeout 120.000000` | 0 | False | 0.094 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3a3c407dcdd243a08fe69047f05616d6-c39358402c8c47298f7b9be25946e4b9.xml` | 0 | False | 0.097 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/3a3c407dcdd243a08fe69047f05616d6-2e31aa00cafa43cd9b6ac05b282eaab0.xml --timeout 120.000000` | 0 | False | 0.113 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3a3c407dcdd243a08fe69047f05616d6-2e31aa00cafa43cd9b6ac05b282eaab0.xml` | 0 | False | 0.089 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.113 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.238 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.629 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.093 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.076 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/684b397114754aa9957910c7f02473ca-e5ed93b76ef24c2fa0f85dfbe8320116.xml --timeout 120.000000` | 8 | False | 0.102 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/684b397114754aa9957910c7f02473ca-e5ed93b76ef24c2fa0f85dfbe8320116.xml` | 0 | False | 0.088 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/684b397114754aa9957910c7f02473ca-4065ba359d994017a506df4b609ddf1d.xml --timeout 120.000000` | 0 | False | 0.094 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/684b397114754aa9957910c7f02473ca-4065ba359d994017a506df4b609ddf1d.xml` | 0 | False | 0.070 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/684b397114754aa9957910c7f02473ca-57c13ae7682d4d25bebd5c9ac7091425.xml --timeout 120.000000` | 0 | False | 0.091 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/684b397114754aa9957910c7f02473ca-57c13ae7682d4d25bebd5c9ac7091425.xml` | 0 | False | 0.083 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/684b397114754aa9957910c7f02473ca-843816bcbdb2417b8a5245dadc53b80a.xml --timeout 120.000000` | 0 | False | 0.103 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/684b397114754aa9957910c7f02473ca-843816bcbdb2417b8a5245dadc53b80a.xml` | 0 | False | 0.101 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
