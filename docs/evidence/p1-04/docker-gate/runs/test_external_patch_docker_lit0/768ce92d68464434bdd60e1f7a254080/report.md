# ReproPatch run 768ce92d68464434bdd60e1f7a254080

Status: **passed**
Docker isolated: True
Base commit: `a12b1bdfd7aa93af0342420de131eea922f4ee9d`
Reproduced: True; independently verified: True
Elapsed: 6.441 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.130 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.264 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.670 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.110 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.092 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\[value\]\+edge$ --output-junit /build/.repropatch-results/9e7e297771af471f9ce444dc8f0e98b9-06e57b5c3a4e42f3b46989c721106021.xml --timeout 120.000000` | 8 | False | 0.084 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/9e7e297771af471f9ce444dc8f0e98b9-06e57b5c3a4e42f3b46989c721106021.xml` | 0 | False | 0.100 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/9e7e297771af471f9ce444dc8f0e98b9-119a1f27b53a4ea6b3c305e8af85e271.xml --timeout 120.000000` | 0 | False | 0.097 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/9e7e297771af471f9ce444dc8f0e98b9-119a1f27b53a4ea6b3c305e8af85e271.xml` | 0 | False | 0.094 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/9e7e297771af471f9ce444dc8f0e98b9-36d6e48295784e17831981269d22c59d.xml --timeout 120.000000` | 0 | False | 0.082 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/9e7e297771af471f9ce444dc8f0e98b9-36d6e48295784e17831981269d22c59d.xml` | 0 | False | 0.092 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/9e7e297771af471f9ce444dc8f0e98b9-cef1407b8c684c2b9c093f30bff87108.xml --timeout 120.000000` | 0 | False | 0.080 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/9e7e297771af471f9ce444dc8f0e98b9-cef1407b8c684c2b9c093f30bff87108.xml` | 0 | False | 0.083 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.105 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.224 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.578 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.090 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.076 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^parse\[value\]\+edge$ --output-junit /build/.repropatch-results/6e75389e606d4e01b06df29d77a10d03-f82cae8ebcdb492f86c0021b14c31cf5.xml --timeout 120.000000` | 0 | False | 0.096 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/6e75389e606d4e01b06df29d77a10d03-f82cae8ebcdb492f86c0021b14c31cf5.xml` | 0 | False | 0.086 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/6e75389e606d4e01b06df29d77a10d03-59d9e30206c246e19535668dc8e07423.xml --timeout 120.000000` | 0 | False | 0.083 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/6e75389e606d4e01b06df29d77a10d03-59d9e30206c246e19535668dc8e07423.xml` | 0 | False | 0.093 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/6e75389e606d4e01b06df29d77a10d03-5bc1b646a5d2496e8b1a4380b38ef806.xml --timeout 120.000000` | 0 | False | 0.096 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/6e75389e606d4e01b06df29d77a10d03-5bc1b646a5d2496e8b1a4380b38ef806.xml` | 0 | False | 0.102 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/6e75389e606d4e01b06df29d77a10d03-80fd33192c0b40d2af3d8ffe870f5e4f.xml --timeout 120.000000` | 0 | False | 0.099 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/6e75389e606d4e01b06df29d77a10d03-80fd33192c0b40d2af3d8ffe870f5e4f.xml` | 0 | False | 0.087 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
