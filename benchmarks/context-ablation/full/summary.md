# Context Ablation

Population: previously exposed development tasks.

| Arm | N | Pass | Fail | Missing | Infra | Input mean | Output mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 38 | 34 | 4 | 0 | 0 | 263291.92 | 6531.71 |
| diagnostics | 38 | 31 | 7 | 0 | 0 | 283292.05 | 6826.92 |
| dedup | 38 | 33 | 5 | 0 | 0 | 275897.63 | 7162.63 |
| state | 38 | 32 | 6 | 0 | 0 | 270666.89 | 7005.55 |
| combined | 38 | 30 | 8 | 0 | 0 | 297453.66 | 7395.95 |

Means cover all registered trials; unknown usage remains missing.
Observed-only means, every pair, overflow classes and mechanism coverage: results.json.
