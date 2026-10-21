# ReproPatch run 4aff8244777746d18a35a6561e6e1b13

Status: **passed**
Docker isolated: True
Base commit: `075a19d1b097d96df3550d2f08d20a0076705210`
Reproduced: True; independently verified: True
Elapsed: 6.566 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.115 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.225 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.659 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.070 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.083 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/308a64e6533c4c11bdf1f569efd7e5c1-7cade1fdbd934a4bb923d6aa2854cde8.xml --timeout 120.000000` | 8 | False | 0.111 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/308a64e6533c4c11bdf1f569efd7e5c1-7cade1fdbd934a4bb923d6aa2854cde8.xml` | 0 | False | 0.096 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/308a64e6533c4c11bdf1f569efd7e5c1-7459c70a643446da8b63e820dba7888e.xml --timeout 120.000000` | 0 | False | 0.068 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/308a64e6533c4c11bdf1f569efd7e5c1-7459c70a643446da8b63e820dba7888e.xml` | 0 | False | 0.068 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/308a64e6533c4c11bdf1f569efd7e5c1-083e58d05ba74963bb4aff70bfa39eb2.xml --timeout 120.000000` | 0 | False | 0.101 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/308a64e6533c4c11bdf1f569efd7e5c1-083e58d05ba74963bb4aff70bfa39eb2.xml` | 0 | False | 0.081 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/308a64e6533c4c11bdf1f569efd7e5c1-a6fda235a9a34c3f9f582e54457ffc95.xml --timeout 120.000000` | 0 | False | 0.088 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/308a64e6533c4c11bdf1f569efd7e5c1-a6fda235a9a34c3f9f582e54457ffc95.xml` | 0 | False | 0.096 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.093 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.228 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.604 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.077 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.101 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/9a084d04b47e4f8b9ee35d5baebf747a-bc04491cbdb34875a03bc27f96c3322c.xml --timeout 120.000000` | 0 | False | 0.117 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/9a084d04b47e4f8b9ee35d5baebf747a-bc04491cbdb34875a03bc27f96c3322c.xml` | 0 | False | 0.102 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/9a084d04b47e4f8b9ee35d5baebf747a-a723dbc7a992498182b3797b80f96aac.xml --timeout 120.000000` | 0 | False | 0.101 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/9a084d04b47e4f8b9ee35d5baebf747a-a723dbc7a992498182b3797b80f96aac.xml` | 0 | False | 0.098 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/9a084d04b47e4f8b9ee35d5baebf747a-13b49e559af44ce9b0af2e3d61eb2d67.xml --timeout 120.000000` | 0 | False | 0.091 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/9a084d04b47e4f8b9ee35d5baebf747a-13b49e559af44ce9b0af2e3d61eb2d67.xml` | 0 | False | 0.105 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/9a084d04b47e4f8b9ee35d5baebf747a-be3fd2365c324b4896a17c5ea1420497.xml --timeout 120.000000` | 0 | False | 0.102 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/9a084d04b47e4f8b9ee35d5baebf747a-be3fd2365c324b4896a17c5ea1420497.xml` | 0 | False | 0.096 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
