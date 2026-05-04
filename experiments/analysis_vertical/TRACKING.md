# Experiment Tracking

This file tracks current status only. Detailed observations belong in `comparisons/` and `reports/`; see [README.md](README.md) for the experiment method.

## Current Status

| Area | Best / Latest Run | Status | Next Step |
| --- | --- | --- | --- |
| Full-transcript vertical prompts | `*-v1-140341999-20260502-204446` | failed | Do not use broad full-transcript prompts as the primary strategy. |
| Significant ideas extraction | `significant_ideas-v1-slices-140341999-20260503-023715` | promising | Add constrained bucketed synthesis over evidence candidates. |
| Context preprocessing | `context_pack-v1-140341999-20260503-030135` | mixed | Use deterministic or ultra-compact context; avoid model-only final context synthesis. |
| Action-item pipeline | `action_items-v4-repaired-140341999-20260503-165550` | promising | Add final synthesis plus semantic consistency validation. |
| Action-item reasoning mode | `action_items-v4-context-reasoning-140341999-20260503-171609` | mixed | Use reasoning only for targeted ambiguity tests, not globally. |
| Gemma4 strategy comparison | `gemma4-strategy-experiments-140341999-20260503-200313` | informative | Test ultra-compact slice-local classifier and fixed-bucket idea synthesis. |

## Current Working Hypothesis

For `gemma4:e2b`, the strongest pattern is:

1. Use local transcript artifacts.
2. Slice the transcript.
3. Extract evidence candidates with narrow prompts.
4. Build deterministic or ultra-compact context.
5. Classify small batches.
6. Validate candidate coverage.
7. Repair invalid pieces.
8. Synthesize only from filtered evidence.

## Next Experiments

- Ultra-compact action classifier by slice, reasoning off by default.
- Mechanics/noise negative filter before action classification.
- Significant-ideas synthesis with fixed buckets.
- Anthropic/cloud comparison using the same local artifacts and validation metrics.
