# Context Ablation

Population: previously exposed development tasks.

| Arm | N | Pass | Fail | Missing | Infra | Input mean | Output mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 1 | 0 | 1 | 0 | 0 | 325213.00 | 6825.00 |
| diagnostics | 1 | 1 | 0 | 0 | 0 | 360238.00 | 6630.00 |
| dedup | 1 | 0 | 1 | 0 | 0 | 338602.00 | 8004.00 |
| state | 1 | 0 | 1 | 0 | 0 | 396369.00 | 8959.00 |
| combined | 1 | 0 | 1 | 0 | 0 | 375812.00 | 12155.00 |

Means cover all registered trials; unknown usage remains missing.
Observed-only means, every pair, overflow classes and mechanism coverage: results.json.

## Mechanism Activation

| Arm | Mechanism | Triggered trials | Triggers | Candidates | Skip reasons |
| --- | --- | ---: | ---: | ---: | --- |
| diagnostics | diagnostic_extraction | 1/1 | 2 | 2 | no_diagnostics: 1; unsupported_tool: 21 |
| dedup | deduplicate_results | 0/1 | 0 | 0 | first_observation: 22; tool_not_supported: 2 |
| state | state_aware_compaction | 0/1 | 0 | 0 | below_threshold: 24 |
| combined | diagnostic_extraction | 0/1 | 0 | 0 | unsupported_tool: 24 |
| combined | deduplicate_results | 0/1 | 0 | 0 | first_observation: 20; tool_not_supported: 4 |
| combined | state_aware_compaction | 0/1 | 0 | 0 | below_threshold: 24 |
