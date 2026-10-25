# Verified native fmt target A/B

All 43 command-log hashes and 44 telemetry files verified; 30 frozen source files verified.
Four fixed CPU affinities: 0, 1, 2, 3. No model calls. Old pilot excluded.

| Variant | N | Median (s) | Range (s) |
| --- | ---: | ---: | --- |
| cache-fill | 1 | 60.782 | 60.782–60.782 |
| cache-warm-fresh-build | 3 | 2.449 | 1.488–2.647 |
| cold-make | 3 | 46.791 | 46.648–59.999 |
| cold-ninja | 3 | 38.358 | 38.138–59.134 |
| final-cold | 1 | 38.458 | 38.458–38.458 |
| incremental-unchanged | 3 | 0.506 | 0.418–0.679 |
| reference-reapplied | 1 | 0.585 | 0.585–0.585 |
| reference-reverted | 1 | 10.068 | 10.068–10.068 |

Cold Ninja to warm ccache reduction: 93.61%. Cold Ninja to unchanged incremental reduction: 98.68%.

This is target-level native timing, with current measurement overhead included. It is not full qualification, Agent repair latency or GitHub Job throughput.
