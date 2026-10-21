# ReproPatch run 16a05324fb8647a1ab9f0badbb2bce31

Status: **passed**
Docker isolated: True
Base commit: `075a19d1b097d96df3550d2f08d20a0076705210`
Reproduced: True; independently verified: True
Elapsed: 6.507 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.219 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.349 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.684 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.093 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.103 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/a8a948eaef744d35b08981a84926eefb-3237d54785f942e68e0d680b7f58d48c.xml --timeout 120.000000` | 8 | False | 0.104 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a8a948eaef744d35b08981a84926eefb-3237d54785f942e68e0d680b7f58d48c.xml` | 0 | False | 0.094 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/a8a948eaef744d35b08981a84926eefb-963baf39641b48e3bb6369d8d84590bd.xml --timeout 120.000000` | 0 | False | 0.099 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a8a948eaef744d35b08981a84926eefb-963baf39641b48e3bb6369d8d84590bd.xml` | 0 | False | 0.085 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/a8a948eaef744d35b08981a84926eefb-eafa5ae6632247589dab014b051491ef.xml --timeout 120.000000` | 0 | False | 0.100 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a8a948eaef744d35b08981a84926eefb-eafa5ae6632247589dab014b051491ef.xml` | 0 | False | 0.093 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/a8a948eaef744d35b08981a84926eefb-7ba81f4a692544d6b7d0d1c28b9ea907.xml --timeout 120.000000` | 0 | False | 0.095 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/a8a948eaef744d35b08981a84926eefb-7ba81f4a692544d6b7d0d1c28b9ea907.xml` | 0 | False | 0.077 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.102 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.224 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.632 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.096 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.087 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/858fa1acd5814acabe79b983cf36509f-053ec066d71e41e88a2b8b1ca9120f9d.xml --timeout 120.000000` | 0 | False | 0.086 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/858fa1acd5814acabe79b983cf36509f-053ec066d71e41e88a2b8b1ca9120f9d.xml` | 0 | False | 0.089 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/858fa1acd5814acabe79b983cf36509f-fb238ad5a72149ddb59523bb608752a9.xml --timeout 120.000000` | 0 | False | 0.101 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/858fa1acd5814acabe79b983cf36509f-fb238ad5a72149ddb59523bb608752a9.xml` | 0 | False | 0.091 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/858fa1acd5814acabe79b983cf36509f-9b47663e87b546e6a3defe0668a3121c.xml --timeout 120.000000` | 0 | False | 0.096 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/858fa1acd5814acabe79b983cf36509f-9b47663e87b546e6a3defe0668a3121c.xml` | 0 | False | 0.097 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/858fa1acd5814acabe79b983cf36509f-2cafdc9382a943f085a342233a694554.xml --timeout 120.000000` | 0 | False | 0.092 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/858fa1acd5814acabe79b983cf36509f-2cafdc9382a943f085a342233a694554.xml` | 0 | False | 0.081 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
