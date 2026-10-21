# ReproPatch run 531718e75b4841aeb3f986718814255f

Status: **failed**
Docker isolated: True
Base commit: `8207277b20d029c353699ed29f11e371bfc84768`
Reproduced: True; independently verified: False
Elapsed: 6.050 seconds
Model turns: 2; tool calls: 1

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.106 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.208 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.593 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.099 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.091 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/989a686ba25d401e87c8cd30215f811e-144e5da04d914abe9be1c5e521438acc.xml --timeout 120.000000` | 8 | False | 0.087 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/989a686ba25d401e87c8cd30215f811e-144e5da04d914abe9be1c5e521438acc.xml` | 0 | False | 0.097 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/989a686ba25d401e87c8cd30215f811e-ca4e7fbfa638402a8837ddb780ad9ebe.xml --timeout 120.000000` | 0 | False | 0.092 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/989a686ba25d401e87c8cd30215f811e-ca4e7fbfa638402a8837ddb780ad9ebe.xml` | 0 | False | 0.090 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/989a686ba25d401e87c8cd30215f811e-2943c0210cb245b5a93cf18b2df6b3a7.xml --timeout 120.000000` | 0 | False | 0.098 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/989a686ba25d401e87c8cd30215f811e-2943c0210cb245b5a93cf18b2df6b3a7.xml` | 0 | False | 0.103 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/989a686ba25d401e87c8cd30215f811e-f6e66d454a564ca48ef30650adb51902.xml --timeout 120.000000` | 0 | False | 0.086 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/989a686ba25d401e87c8cd30215f811e-f6e66d454a564ca48ef30650adb51902.xml` | 0 | False | 0.077 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.100 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.242 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.594 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.094 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.075 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/3410ef7c2668466ba7e19bd7efb7c5bf-72c5db8584f6461e9edba388274bc511.xml --timeout 120.000000` | 8 | False | 0.091 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3410ef7c2668466ba7e19bd7efb7c5bf-72c5db8584f6461e9edba388274bc511.xml` | 0 | False | 0.089 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/3410ef7c2668466ba7e19bd7efb7c5bf-bcef44d44bc34ad8b94b085f2524d867.xml --timeout 120.000000` | 0 | False | 0.096 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3410ef7c2668466ba7e19bd7efb7c5bf-bcef44d44bc34ad8b94b085f2524d867.xml` | 0 | False | 0.098 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/3410ef7c2668466ba7e19bd7efb7c5bf-4b5737d2277d49a79219aeb20bda1303.xml --timeout 120.000000` | 0 | False | 0.099 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3410ef7c2668466ba7e19bd7efb7c5bf-4b5737d2277d49a79219aeb20bda1303.xml` | 0 | False | 0.090 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/3410ef7c2668466ba7e19bd7efb7c5bf-73a596f009ef46e88a85a9aa466a81ab.xml --timeout 120.000000` | 0 | False | 0.096 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/3410ef7c2668466ba7e19bd7efb7c5bf-73a596f009ef46e88a85a9aa466a81ab.xml` | 0 | False | 0.086 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
