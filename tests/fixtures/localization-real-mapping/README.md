# Real Localization Mapping Fixtures

The two complete `include/fmt/format.h` files are frozen at the upstream commits
in `provenance.json`. Their SHA-256 hashes and byte sizes match the prepared
repositories recorded in the qualification archive. Each snapshot includes its
upstream license, also verified against the qualification manifest.

Tests read the original reference patches and manifests from the checked-in
qualification archive. All fixture loading and scoring run offline. Source roots
contain only the reference-touched header; their tree hashes describe that local
subset. The fixtures exercise line mapping and scoring without compiling fmt.

| Instance | Old-line spans | Insertion anchors |
| --- | --- | --- |
| `fmtlib__fmt-2317` | 1311, 1314-1318, 1800 | None |
| `fmtlib__fmt-3713` | None | 4056-4057 |

```sh
PYTHONPATH=src:scripts python -m pytest tests/test_localization_real_mapping.py -q
```
