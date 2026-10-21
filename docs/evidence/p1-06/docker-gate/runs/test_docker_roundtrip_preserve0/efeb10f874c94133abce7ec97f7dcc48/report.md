# ReproPatch run efeb10f874c94133abce7ec97f7dcc48

Status: **passed**
Docker isolated: True
Base commit: `35edae77877b9ae8573d54bb00eef24c5cc18469`
Reproduced: True; independently verified: True
Elapsed: 12.021 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.095 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.241 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.593 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.128 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.112 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/d065195ec7c146b8aa43ef228fd5d398-f75846f09b6a49c4bd2950e19b275386.xml --timeout 120.000000` | 8 | False | 0.151 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d065195ec7c146b8aa43ef228fd5d398-f75846f09b6a49c4bd2950e19b275386.xml` | 0 | False | 0.126 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/d065195ec7c146b8aa43ef228fd5d398-60084cfb7bc946f18dc46c5f294dfb22.xml --timeout 120.000000` | 0 | False | 0.109 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d065195ec7c146b8aa43ef228fd5d398-60084cfb7bc946f18dc46c5f294dfb22.xml` | 0 | False | 0.087 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/d065195ec7c146b8aa43ef228fd5d398-556920762b464e47a792f958c0c7aedc.xml --timeout 120.000000` | 0 | False | 0.123 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d065195ec7c146b8aa43ef228fd5d398-556920762b464e47a792f958c0c7aedc.xml` | 0 | False | 0.103 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/d065195ec7c146b8aa43ef228fd5d398-02c40fcaeb0b4a9eb89c2f212ab98497.xml --timeout 120.000000` | 0 | False | 0.094 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/d065195ec7c146b8aa43ef228fd5d398-02c40fcaeb0b4a9eb89c2f212ab98497.xml` | 0 | False | 0.069 |
| agent-check | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.107 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.286 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.583 |
| agent-check | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.155 |
| agent-check | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.106 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/bc7a8ff9a63446e890a3c5cdf6f75ad5-4f6ab0223d6d452c9229cb0cf68e8cf2.xml --timeout 120.000000` | 0 | False | 0.098 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/bc7a8ff9a63446e890a3c5cdf6f75ad5-4f6ab0223d6d452c9229cb0cf68e8cf2.xml` | 0 | False | 0.158 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/bc7a8ff9a63446e890a3c5cdf6f75ad5-69f24fe00400412cbe516a1715091afe.xml --timeout 120.000000` | 0 | False | 0.107 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/bc7a8ff9a63446e890a3c5cdf6f75ad5-69f24fe00400412cbe516a1715091afe.xml` | 0 | False | 0.101 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/bc7a8ff9a63446e890a3c5cdf6f75ad5-7bfbb5a928c14f62a79f89c7e8963ec4.xml --timeout 120.000000` | 0 | False | 0.117 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/bc7a8ff9a63446e890a3c5cdf6f75ad5-7bfbb5a928c14f62a79f89c7e8963ec4.xml` | 0 | False | 0.136 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/bc7a8ff9a63446e890a3c5cdf6f75ad5-83ad97d50cb442b08b4c6d769f822d20.xml --timeout 120.000000` | 0 | False | 0.088 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/bc7a8ff9a63446e890a3c5cdf6f75ad5-83ad97d50cb442b08b4c6d769f822d20.xml` | 0 | False | 0.118 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.147 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.241 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.616 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.174 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.121 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/b1f086143a81429498fb54256e75ea4f-a1d0c57481cb4916ac0281d406a81ff9.xml --timeout 120.000000` | 0 | False | 0.206 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b1f086143a81429498fb54256e75ea4f-a1d0c57481cb4916ac0281d406a81ff9.xml` | 0 | False | 0.090 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/b1f086143a81429498fb54256e75ea4f-75eb6bf58b9b4e58b134ad7161e44725.xml --timeout 120.000000` | 0 | False | 0.102 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b1f086143a81429498fb54256e75ea4f-75eb6bf58b9b4e58b134ad7161e44725.xml` | 0 | False | 0.089 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/b1f086143a81429498fb54256e75ea4f-c30000f0a8aa4102a9c3e78477febc6c.xml --timeout 120.000000` | 0 | False | 0.125 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b1f086143a81429498fb54256e75ea4f-c30000f0a8aa4102a9c3e78477febc6c.xml` | 0 | False | 0.127 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/b1f086143a81429498fb54256e75ea4f-cf39db047d2a4c07b7b3f2be2fc719de.xml --timeout 120.000000` | 0 | False | 0.085 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b1f086143a81429498fb54256e75ea4f-cf39db047d2a4c07b7b3f2be2fc719de.xml` | 0 | False | 0.154 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
