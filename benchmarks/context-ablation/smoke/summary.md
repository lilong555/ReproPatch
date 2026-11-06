# Context Ablation

Population: previously exposed development tasks.

| Arm | N | Pass | Fail | Missing | Infra | Input mean | Output mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 1 | 0 | 1 | 0 | 0 | 343181.00 | 12389.00 |
| diagnostics | 1 | 0 | 1 | 0 | 0 | 376386.00 | 19416.00 |
| dedup | 1 | 0 | 0 | 0 | 1 | missing | missing |
| state | 1 | 1 | 0 | 0 | 0 | 354016.00 | 18016.00 |
| combined | 1 | 0 | 1 | 0 | 0 | 356718.00 | 11068.00 |

Means cover all registered trials; unknown usage remains missing.
Observed-only means, every pair, overflow classes and mechanism coverage: results.json.
