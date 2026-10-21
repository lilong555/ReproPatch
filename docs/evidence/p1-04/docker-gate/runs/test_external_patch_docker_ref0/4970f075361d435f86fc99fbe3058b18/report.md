# ReproPatch run 4970f075361d435f86fc99fbe3058b18

Status: **failed**
Docker isolated: True
Base commit: `01f348b23f7c36ae0f2cfe88f085e10b43dba855`
Reproduced: True; independently verified: False
Elapsed: 6.287 seconds
Model turns: 0; tool calls: 0

| Phase | Command | Exit | Timeout | Seconds |
| --- | --- | ---: | --- | ---: |
| baseline | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.087 |
| baseline | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.241 |
| baseline | `cmake --build /build --parallel 2` | 0 | False | 0.596 |
| baseline | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.078 |
| baseline | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.082 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/da01deba1c0547e68ecd754267467553-78a1a07f8efd403c9c802df822f14ddd.xml --timeout 120.000000` | 8 | False | 0.100 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/da01deba1c0547e68ecd754267467553-78a1a07f8efd403c9c802df822f14ddd.xml` | 0 | False | 0.082 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/da01deba1c0547e68ecd754267467553-9d252ce622a74d7db9d95b047029c8b9.xml --timeout 120.000000` | 0 | False | 0.084 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/da01deba1c0547e68ecd754267467553-9d252ce622a74d7db9d95b047029c8b9.xml` | 0 | False | 0.106 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/da01deba1c0547e68ecd754267467553-080032b40c5b45b49d4811ee67826a85.xml --timeout 120.000000` | 0 | False | 0.093 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/da01deba1c0547e68ecd754267467553-080032b40c5b45b49d4811ee67826a85.xml` | 0 | False | 0.090 |
| baseline | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/da01deba1c0547e68ecd754267467553-a8ad260045db4e159709f321553c0f51.xml --timeout 120.000000` | 0 | False | 0.090 |
| baseline | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/da01deba1c0547e68ecd754267467553-a8ad260045db4e159709f321553c0f51.xml` | 0 | False | 0.079 |
| independent | `/bin/sh -ec command -v cmake; command -v ctest; command -v c++; command -v cat; command -v timeout; /usr/bin/sleep --version; cmake --version; ctest --version; printf '\nREPROPATCH_CXX_VERSION\n'; c++ --version` | 0 | False | 0.106 |
| independent | `cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug` | 0 | False | 0.235 |
| independent | `cmake --build /build --parallel 2` | 0 | False | 0.647 |
| independent | `ctest --test-dir /build --show-only=json-v1` | 0 | False | 0.103 |
| independent | `/bin/sh -ec test ! -L /build/.repropatch-results && mkdir -p -- /build/.repropatch-results` | 0 | False | 0.082 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^negative_values$ --output-junit /build/.repropatch-results/27f62b77d1584b1fafd120c0e72ed4ac-c0a392b346954bb5b7ba21e707db7084.xml --timeout 120.000000` | 0 | False | 0.082 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/27f62b77d1584b1fafd120c0e72ed4ac-c0a392b346954bb5b7ba21e707db7084.xml` | 0 | False | 0.103 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^positive_values$ --output-junit /build/.repropatch-results/27f62b77d1584b1fafd120c0e72ed4ac-3c33b66302404dceac2cbf876b28243e.xml --timeout 120.000000` | 0 | False | 0.106 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/27f62b77d1584b1fafd120c0e72ed4ac-3c33b66302404dceac2cbf876b28243e.xml` | 0 | False | 0.088 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^empty_values$ --output-junit /build/.repropatch-results/27f62b77d1584b1fafd120c0e72ed4ac-2ab729aa26f14b118738b4cd4af5865f.xml --timeout 120.000000` | 0 | False | 0.085 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/27f62b77d1584b1fafd120c0e72ed4ac-2ab729aa26f14b118738b4cd4af5865f.xml` | 0 | False | 0.079 |
| independent | `ctest --test-dir /build --output-on-failure --no-tests=error -R ^mixed_values$ --output-junit /build/.repropatch-results/27f62b77d1584b1fafd120c0e72ed4ac-77f00541148b4ab7bd0cd6964b46ca92.xml --timeout 120.000000` | 8 | False | 0.095 |
| independent | `/bin/sh -ec test -f "$1" && test ! -L "$1" && test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1" repropatch-read /build/.repropatch-results/27f62b77d1584b1fafd120c0e72ed4ac-77f00541148b4ab7bd0cd6964b46ca92.xml` | 0 | False | 0.101 |

See patch.diff, events.jsonl and events.sqlite3 for evidence.
