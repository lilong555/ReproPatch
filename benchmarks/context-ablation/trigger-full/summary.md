# Context Ablation

Population: previously exposed development tasks.

| Arm | N | Pass | Fail | Missing | Infra | Input mean | Output mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 38 | 32 | 6 | 0 | 0 | 276489.08 | 7371.03 |
| diagnostics | 38 | 33 | 5 | 0 | 0 | 287610.08 | 7587.50 |
| dedup | 38 | 32 | 6 | 0 | 0 | 276773.55 | 6932.63 |
| state | 38 | 35 | 3 | 0 | 0 | 272726.50 | 6817.89 |
| combined | 38 | 27 | 11 | 0 | 0 | 284349.39 | 7286.63 |

Means cover all registered trials; unknown usage remains missing.
Observed-only means, every pair, overflow classes and mechanism coverage: results.json.

## Mechanism Activation

| Arm | Mechanism | Triggered trials | Triggers | Candidates | Skip reasons |
| --- | --- | ---: | ---: | ---: | --- |
| diagnostics | diagnostic_extraction | 7/38 | 9 | 19 | insufficient_savings: 8; no_diagnostics: 76; output_limit: 2; unsupported_tool: 593 |
| dedup | deduplicate_results | 0/38 | 0 | 0 | first_observation: 581; incomplete_output: 2; tool_not_supported: 96 |
| state | state_aware_compaction | 0/38 | 0 | 0 | below_threshold: 710 |
| combined | diagnostic_extraction | 6/38 | 8 | 16 | insufficient_savings: 6; no_diagnostics: 66; output_limit: 2; superseded_by_dedup: 1; unsupported_tool: 632 |
| combined | deduplicate_results | 1/38 | 1 | 1 | first_observation: 600; incomplete_output: 3; tool_error: 1; tool_not_supported: 110 |
| combined | state_aware_compaction | 0/38 | 0 | 0 | below_threshold: 738 |
