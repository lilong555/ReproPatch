# ReproPatch run 1ae36356f23f484ba87a0d5f263217e4

Status: **passed**
Docker isolated: True
Base commit: `70898f53ae0f5693dd7868b8ff8e70378e428366`
Reproduced: True; independently verified: True
Elapsed: 8.573 seconds
Model turns: 3; tool calls: 2

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.109 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.224 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.580 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.084 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.089 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/bb9a4eba45f647b89b638cea203d7220-11681ddc18af43efba3f4cf27abdf45d.xml --timeout 120.000000` | 8 | False | 0.094 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/bb9a4eba45f647b89b638cea203d7220-11681ddc18af43efba3f4cf27abdf45d.xml` | 0 | False | 0.083 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/bb9a4eba45f647b89b638cea203d7220-fb620dd0476e463ba76e298b4a03e091.xml --timeout 120.000000` | 0 | False | 0.092 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/bb9a4eba45f647b89b638cea203d7220-fb620dd0476e463ba76e298b4a03e091.xml` | 0 | False | 0.084 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/bb9a4eba45f647b89b638cea203d7220-59d1869ecddc42e59a8b5ec0db45048a.xml --timeout 120.000000` | 0 | False | 0.112 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/bb9a4eba45f647b89b638cea203d7220-59d1869ecddc42e59a8b5ec0db45048a.xml` | 0 | False | 0.090 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/bb9a4eba45f647b89b638cea203d7220-7c62b1cb06b54077a0859a5af2a0c52d.xml --timeout 120.000000` | 0 | False | 0.106 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/bb9a4eba45f647b89b638cea203d7220-7c62b1cb06b54077a0859a5af2a0c52d.xml` | 0 | False | 0.080 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.111 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.227 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.614 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.098 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.102 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/67e5c2f6e566406cadd12d8d54a4ef7c-d446da7330904befbca85de372956338.xml --timeout 120.000000` | 0 | False | 0.101 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/67e5c2f6e566406cadd12d8d54a4ef7c-d446da7330904befbca85de372956338.xml` | 0 | False | 0.100 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/67e5c2f6e566406cadd12d8d54a4ef7c-90b98db6db2a4a8ab82d9e72be1b061f.xml --timeout 120.000000` | 0 | False | 0.109 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/67e5c2f6e566406cadd12d8d54a4ef7c-90b98db6db2a4a8ab82d9e72be1b061f.xml` | 0 | False | 0.085 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/67e5c2f6e566406cadd12d8d54a4ef7c-fe8b4031c8ed4357963f01bbcf09025a.xml --timeout 120.000000` | 0 | False | 0.110 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/67e5c2f6e566406cadd12d8d54a4ef7c-fe8b4031c8ed4357963f01bbcf09025a.xml` | 0 | False | 0.092 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/67e5c2f6e566406cadd12d8d54a4ef7c-35ab6df70cad4769bfcab734a39ae94a.xml --timeout 120.000000` | 0 | False | 0.092 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/67e5c2f6e566406cadd12d8d54a4ef7c-35ab6df70cad4769bfcab734a39ae94a.xml` | 0 | False | 0.103 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
