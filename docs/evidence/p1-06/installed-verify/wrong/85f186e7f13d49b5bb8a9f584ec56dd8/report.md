# ReproPatch run 85f186e7f13d49b5bb8a9f584ec56dd8

Status: **failed**
Docker isolated: True
Base commit: `075a19d1b097d96df3550d2f08d20a0076705210`
Reproduced: True; independently verified: False
Elapsed: 5.946 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.103 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.220 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.601 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.090 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.082 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/f18735e4a9574bcd8648fcd42937e9c4-c934c23efbf84a0fabe8bc4c4637a9b5.xml --timeout 120.000000` | 8 | False | 0.095 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f18735e4a9574bcd8648fcd42937e9c4-c934c23efbf84a0fabe8bc4c4637a9b5.xml` | 0 | False | 0.090 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/f18735e4a9574bcd8648fcd42937e9c4-4100f0ad0b08433894f51cbcb3b47df3.xml --timeout 120.000000` | 0 | False | 0.080 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f18735e4a9574bcd8648fcd42937e9c4-4100f0ad0b08433894f51cbcb3b47df3.xml` | 0 | False | 0.091 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/f18735e4a9574bcd8648fcd42937e9c4-077ccc4bb7c0430aac1ed4ea96f36b35.xml --timeout 120.000000` | 0 | False | 0.089 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f18735e4a9574bcd8648fcd42937e9c4-077ccc4bb7c0430aac1ed4ea96f36b35.xml` | 0 | False | 0.084 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/f18735e4a9574bcd8648fcd42937e9c4-af95aa9523b34b4bbc98dc5cf1b7b75e.xml --timeout 120.000000` | 0 | False | 0.095 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f18735e4a9574bcd8648fcd42937e9c4-af95aa9523b34b4bbc98dc5cf1b7b75e.xml` | 0 | False | 0.084 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.099 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.236 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.620 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.099 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.086 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/e81bb3ebed254b7e867ecc908ee703f9-19cdb08363e241eab3162e27cb534c3c.xml --timeout 120.000000` | 8 | False | 0.110 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/e81bb3ebed254b7e867ecc908ee703f9-19cdb08363e241eab3162e27cb534c3c.xml` | 0 | False | 0.109 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/e81bb3ebed254b7e867ecc908ee703f9-5444ba9b8086433bb011f1999a459208.xml --timeout 120.000000` | 0 | False | 0.089 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/e81bb3ebed254b7e867ecc908ee703f9-5444ba9b8086433bb011f1999a459208.xml` | 0 | False | 0.087 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/e81bb3ebed254b7e867ecc908ee703f9-5710778c2ed64c2f8d497b84a60d6529.xml --timeout 120.000000` | 0 | False | 0.095 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/e81bb3ebed254b7e867ecc908ee703f9-5710778c2ed64c2f8d497b84a60d6529.xml` | 0 | False | 0.084 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/e81bb3ebed254b7e867ecc908ee703f9-69c427baf51f4986a657f5a87fbe91f5.xml --timeout 120.000000` | 0 | False | 0.097 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/e81bb3ebed254b7e867ecc908ee703f9-69c427baf51f4986a657f5a87fbe91f5.xml` | 0 | False | 0.086 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
