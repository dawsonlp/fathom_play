# Vertical Analysis Rubric

Score each target run independently.

| Criterion | Score | Guidance |
| --- | ---: | --- |
| Valid schema | 0-2 | 2 means parseable and matches schema; 1 means recoverable; 0 means unusable. |
| Evidence completeness | 0-3 | 3 means every claim has speaker, timestamp, and excerpt. |
| Evidence accuracy | 0-3 | 3 means evidence clearly supports each claim. |
| Claim usefulness | 0-3 | 3 means findings would change follow-up behavior or improve understanding. |
| Claim carefulness | 0-2 | 2 means appropriately qualified and no overreach. |
| False positives | 0-3 | 3 means few or no invented/unsupported items. |
| Missing obvious items | 0-3 | 3 means few or no important omissions. |

Total interpretation:

- 15-19: strong enough to keep tuning.
- 10-14: promising but needs target-specific adjustment.
- 0-9: not good enough for the current model/input strategy.

Record failures explicitly. A run that returns only a summary should score low even if the prose sounds plausible.

