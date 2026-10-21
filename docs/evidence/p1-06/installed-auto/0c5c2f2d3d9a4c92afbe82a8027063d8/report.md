# ReproPatch run 0c5c2f2d3d9a4c92afbe82a8027063d8

Status: **passed**
Docker isolated: True
Base commit: `075a19d1b097d96df3550d2f08d20a0076705210`
Reproduced: True; independently verified: True
Elapsed: 8.590 seconds
Model turns: 5; tool calls: 4

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.101 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.225 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.581 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.090 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.087 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/f599bd113eaf48918c57906f93e3693d-6cb64a49a9424378a3c21414b6e5b75a.xml --timeout 120.000000` | 8 | False | 0.103 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f599bd113eaf48918c57906f93e3693d-6cb64a49a9424378a3c21414b6e5b75a.xml` | 0 | False | 0.076 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/f599bd113eaf48918c57906f93e3693d-a100188f643e4557a30f724d2aea8bb8.xml --timeout 120.000000` | 0 | False | 0.094 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f599bd113eaf48918c57906f93e3693d-a100188f643e4557a30f724d2aea8bb8.xml` | 0 | False | 0.086 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/f599bd113eaf48918c57906f93e3693d-77b53193109b48378cb4ad59f8b7dee6.xml --timeout 120.000000` | 0 | False | 0.083 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f599bd113eaf48918c57906f93e3693d-77b53193109b48378cb4ad59f8b7dee6.xml` | 0 | False | 0.081 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/f599bd113eaf48918c57906f93e3693d-215b5eb18c2a44298ff058aaedadf593.xml --timeout 120.000000` | 0 | False | 0.082 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/f599bd113eaf48918c57906f93e3693d-215b5eb18c2a44298ff058aaedadf593.xml` | 0 | False | 0.084 |
| agent-check | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.085 |
| agent-check | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.212 |
| agent-check | `cmake --build /build --parallel 2` | 0 | False | 0.584 |
| agent-check | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.090 |
| agent-check | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.066 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/b84b2bfe7fb94dccb9e307a653631f46-1415a8b4ac1d4bb7ad95fd38caee0668.xml --timeout 120.000000` | 0 | False | 0.090 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b84b2bfe7fb94dccb9e307a653631f46-1415a8b4ac1d4bb7ad95fd38caee0668.xml` | 0 | False | 0.101 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/b84b2bfe7fb94dccb9e307a653631f46-fe17cdc884ea4aa198ebe1f9b41dd03f.xml --timeout 120.000000` | 0 | False | 0.093 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b84b2bfe7fb94dccb9e307a653631f46-fe17cdc884ea4aa198ebe1f9b41dd03f.xml` | 0 | False | 0.074 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/b84b2bfe7fb94dccb9e307a653631f46-d287c11a0938450b8a53c2efcf5bd06a.xml --timeout 120.000000` | 0 | False | 0.085 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b84b2bfe7fb94dccb9e307a653631f46-d287c11a0938450b8a53c2efcf5bd06a.xml` | 0 | False | 0.079 |
| agent-check | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/b84b2bfe7fb94dccb9e307a653631f46-804c960519954d4cbfd2fe907dcca091.xml --timeout 120.000000` | 0 | False | 0.093 |
| agent-check | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/b84b2bfe7fb94dccb9e307a653631f46-804c960519954d4cbfd2fe907dcca091.xml` | 0 | False | 0.072 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.113 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.232 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.562 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.097 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.076 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/94b996d6141f413ea52a21e8baae174f-b63c4c57f70b4f43964c66de0f80d630.xml --timeout 120.000000` | 0 | False | 0.080 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/94b996d6141f413ea52a21e8baae174f-b63c4c57f70b4f43964c66de0f80d630.xml` | 0 | False | 0.087 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/94b996d6141f413ea52a21e8baae174f-0047fa83357042738089599c6c82b554.xml --timeout 120.000000` | 0 | False | 0.094 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/94b996d6141f413ea52a21e8baae174f-0047fa83357042738089599c6c82b554.xml` | 0 | False | 0.096 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/94b996d6141f413ea52a21e8baae174f-c7c0c2767f91411b9ef9cb57941a65dc.xml --timeout 120.000000` | 0 | False | 0.090 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/94b996d6141f413ea52a21e8baae174f-c7c0c2767f91411b9ef9cb57941a65dc.xml` | 0 | False | 0.087 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/94b996d6141f413ea52a21e8baae174f-98c5c0460cbb4e3199e0414ffb825034.xml --timeout 120.000000` | 0 | False | 0.090 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/94b996d6141f413ea52a21e8baae174f-98c5c0460cbb4e3199e0414ffb825034.xml` | 0 | False | 0.085 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
