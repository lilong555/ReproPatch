# ReproPatch run 449a21c40a384a98bd87d933fd93329d

Status: **passed**
Docker isolated: True
Base commit: `075a19d1b097d96df3550d2f08d20a0076705210`
Reproduced: True; independently verified: True
Elapsed: 8.663 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.264 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.225 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.640 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.151 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.119 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/62cf7713b1424cad85798c35d15b4925-5e2395cc8672476fb1c60dd7fea89fc7.xml --timeout 120.000000` | 8 | False | 0.162 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/62cf7713b1424cad85798c35d15b4925-5e2395cc8672476fb1c60dd7fea89fc7.xml` | 0 | False | 0.165 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/62cf7713b1424cad85798c35d15b4925-98cf157de7d846b4a16d836a6991ce00.xml --timeout 120.000000` | 0 | False | 0.109 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/62cf7713b1424cad85798c35d15b4925-98cf157de7d846b4a16d836a6991ce00.xml` | 0 | False | 0.090 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/62cf7713b1424cad85798c35d15b4925-427c6f9ed45e40d782efa069fe689d33.xml --timeout 120.000000` | 0 | False | 0.129 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/62cf7713b1424cad85798c35d15b4925-427c6f9ed45e40d782efa069fe689d33.xml` | 0 | False | 0.181 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/62cf7713b1424cad85798c35d15b4925-50369ad5e88140138f4a177fa5145622.xml --timeout 120.000000` | 0 | False | 0.098 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/62cf7713b1424cad85798c35d15b4925-50369ad5e88140138f4a177fa5145622.xml` | 0 | False | 0.131 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.133 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.225 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.660 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.168 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.113 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/0e5dc3c1ca844b85994ad9df34ae6d5d-97c36ab2205040709f9a666bf4df1d48.xml --timeout 120.000000` | 0 | False | 0.096 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/0e5dc3c1ca844b85994ad9df34ae6d5d-97c36ab2205040709f9a666bf4df1d48.xml` | 0 | False | 0.124 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/0e5dc3c1ca844b85994ad9df34ae6d5d-d351c08366ba473f8f3a4cae3559c3ae.xml --timeout 120.000000` | 0 | False | 0.136 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/0e5dc3c1ca844b85994ad9df34ae6d5d-d351c08366ba473f8f3a4cae3559c3ae.xml` | 0 | False | 0.105 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/0e5dc3c1ca844b85994ad9df34ae6d5d-e8afcd69e8384d32945e9eb264dc0127.xml --timeout 120.000000` | 0 | False | 0.125 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/0e5dc3c1ca844b85994ad9df34ae6d5d-e8afcd69e8384d32945e9eb264dc0127.xml` | 0 | False | 0.107 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/0e5dc3c1ca844b85994ad9df34ae6d5d-4134d376fe7245d6b12b879ccec23b34.xml --timeout 120.000000` | 0 | False | 0.093 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/0e5dc3c1ca844b85994ad9df34ae6d5d-4134d376fe7245d6b12b879ccec23b34.xml` | 0 | False | 0.129 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
