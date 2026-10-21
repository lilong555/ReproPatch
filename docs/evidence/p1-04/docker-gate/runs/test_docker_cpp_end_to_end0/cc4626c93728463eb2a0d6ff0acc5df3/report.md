# ReproPatch run cc4626c93728463eb2a0d6ff0acc5df3

Status: **passed**
Docker isolated: True
Base commit: `ace858ba4759ea680c89d928b560e4ad7ab6382a`
Reproduced: True; independently verified: True
Elapsed: 9.922 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.184 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.299 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.704 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.108 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.095 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/4e0d99514d4a4d3cbe2d300b0345ee87-f5964b06eb834a7d9913b83c944257c5.xml --timeout 120.000000` | 8 | False | 0.106 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/4e0d99514d4a4d3cbe2d300b0345ee87-f5964b06eb834a7d9913b83c944257c5.xml` | 0 | False | 0.090 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/4e0d99514d4a4d3cbe2d300b0345ee87-f7137849519a44b5826f023ba31c0217.xml --timeout 120.000000` | 0 | False | 0.092 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/4e0d99514d4a4d3cbe2d300b0345ee87-f7137849519a44b5826f023ba31c0217.xml` | 0 | False | 0.085 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/4e0d99514d4a4d3cbe2d300b0345ee87-0dbee1b731164f1ba77c0ca1033e5b9e.xml --timeout 120.000000` | 0 | False | 0.094 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/4e0d99514d4a4d3cbe2d300b0345ee87-0dbee1b731164f1ba77c0ca1033e5b9e.xml` | 0 | False | 0.105 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/4e0d99514d4a4d3cbe2d300b0345ee87-f0c26996d2d741e8bde17960a97067e0.xml --timeout 120.000000` | 0 | False | 0.091 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/4e0d99514d4a4d3cbe2d300b0345ee87-f0c26996d2d741e8bde17960a97067e0.xml` | 0 | False | 0.086 |
| agent-check | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.114 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.229 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.639 |
| agent-check | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.109 |
| agent-check | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.096 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/7537512349f44ecca829a604e1b98558-5ac4a07f54ed4695b3f5e98f865f88bc.xml --timeout 120.000000` | 0 | False | 0.094 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/7537512349f44ecca829a604e1b98558-5ac4a07f54ed4695b3f5e98f865f88bc.xml` | 0 | False | 0.083 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/7537512349f44ecca829a604e1b98558-eefcabfca29747e2a66a31ea5d8e479f.xml --timeout 120.000000` | 0 | False | 0.104 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/7537512349f44ecca829a604e1b98558-eefcabfca29747e2a66a31ea5d8e479f.xml` | 0 | False | 0.088 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/7537512349f44ecca829a604e1b98558-35a26a8b81264e76800c020e13a3574e.xml --timeout 120.000000` | 0 | False | 0.085 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/7537512349f44ecca829a604e1b98558-35a26a8b81264e76800c020e13a3574e.xml` | 0 | False | 0.087 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/7537512349f44ecca829a604e1b98558-920186e85fa74674a5490d918de4597a.xml --timeout 120.000000` | 0 | False | 0.095 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/7537512349f44ecca829a604e1b98558-920186e85fa74674a5490d918de4597a.xml` | 0 | False | 0.104 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.096 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.224 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.600 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.099 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.084 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/6091ebe6f151430b939af0fa0b6698c8-424a712579c840f4adf590ce6469fc13.xml --timeout 120.000000` | 0 | False | 0.090 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/6091ebe6f151430b939af0fa0b6698c8-424a712579c840f4adf590ce6469fc13.xml` | 0 | False | 0.078 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/6091ebe6f151430b939af0fa0b6698c8-b006002835ef4f4499ecaa06be9a582a.xml --timeout 120.000000` | 0 | False | 0.105 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/6091ebe6f151430b939af0fa0b6698c8-b006002835ef4f4499ecaa06be9a582a.xml` | 0 | False | 0.082 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/6091ebe6f151430b939af0fa0b6698c8-922cc01c087d4bf48c44415a4b315914.xml --timeout 120.000000` | 0 | False | 0.104 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/6091ebe6f151430b939af0fa0b6698c8-922cc01c087d4bf48c44415a4b315914.xml` | 0 | False | 0.091 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/6091ebe6f151430b939af0fa0b6698c8-19e0e0d81e804354a783b0734ae78eba.xml --timeout 120.000000` | 0 | False | 0.094 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/6091ebe6f151430b939af0fa0b6698c8-19e0e0d81e804354a783b0734ae78eba.xml` | 0 | False | 0.095 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
