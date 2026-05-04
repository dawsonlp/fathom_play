# Gemma4 Strategy Experiments: Recording 140341999

## Purpose

Compare three experiment sets for analyzing a Fathom transcript with the local `gemma4:e2b` model:

1. Prompt shape and reasoning mode.
2. Context pack composition and reasoning mode.
3. Iterative slice-to-meeting synthesis.

All runs used local artifacts only. No Fathom API calls were made.

## Inputs

- Recording ID: `140341999`
- Action candidate run: `action_items-v2-slices-140341999-20260503-022458`
- Context pack run: `context_pack-v1-140341999-20260503-030135`
- Repaired action baseline: `action_items-v4-repaired-140341999-20260503-165550`
- Significant ideas run: `significant_ideas-v1-slices-140341999-20260503-023715`

Primary run directory:

```text
experiments/analysis_vertical/runs/140341999/gemma4-strategy-experiments-140341999-20260503-200313/
```

## Operational Note

The first full matrix was stopped after running longer than was useful as a single batch. It had completed Experiment 1 and part of Experiment 2. The remaining high-value context variants and synthesis cases were run in a reduced follow-up batch and written into the same run directory.

That is itself a result: reasoning-enabled matrix runs are expensive enough that future experiments should run fewer variants or isolate reasoning comparisons carefully.

## Experiment 1: Prompt Shape And Reasoning Matrix

Goal: compare prompt shape and reasoning mode for classifying all action-item candidates in one call.

| Variant | Reasoning | Complete Coverage | Missing Candidates | Promotions | Hard-Negative Promotions |
| --- | --- | --- | ---: | ---: | ---: |
| full rules | off | no | 6 | 1 | 0 |
| full rules | on | no | 13 | 0 | 0 |
| short rules | off | no | 6 | 0 | 0 |
| short rules | on | no | 13 | 0 | 0 |
| two phase | off | no | 13 | 0 | 0 |
| two phase | on | no | 13 | 0 | 0 |

### Interpretation

Prompt shape alone did not solve coverage when all candidates were classified in one large call. Reasoning mode made coverage worse in this setup: reasoning-on variants frequently returned no usable candidate classifications.

Best signal:

- Full/short rules with reasoning off partially classified candidates.

Worst signal:

- Reasoning on for the all-candidate prompt shape caused complete coverage failure.

### Conclusion

For candidate classification, do not batch all candidates into one broad prompt. Keep classification slice-local or use smaller candidate batches. Do not enable reasoning by default for candidate coverage tasks.

## Experiment 2: Context Pack Size And Composition

Goal: compare whether context helps classification, and whether reasoning changes that value.

| Context Variant | Reasoning | Complete Coverage | Missing Candidates | Promotions | Hard-Negative Promotions |
| --- | --- | --- | ---: | ---: | ---: |
| no context | off | yes | 0 | 2 | 0 |
| no context | on | no | 13 | 0 | 0 |
| mechanics only | off | yes | 0 | 0 | 0 |
| mechanics only | on | yes | 0 | 0 | 0 |
| significant only | off | yes | 0 | 0 | 0 |
| significant only | on | yes | 0 | 0 | 0 |
| full context | off | no | 6 | 0 | 0 |
| full context | on | no | 13 | 0 | 0 |
| ultra compact | off | yes | 0 | 2 | 0 |
| ultra compact | on | yes | 0 | 2 | 0 |

### Interpretation

The full deterministic context pack was too large or distracting for the all-candidate classification prompt. It harmed candidate coverage. Smaller targeted context worked much better.

Best coverage:

- mechanics only
- significant only
- ultra compact
- no context with reasoning off

Best precision signal:

- mechanics-only and significant-only promoted zero candidates. That is conservative, possibly too conservative, but it avoided false positives.
- ultra-compact promoted two candidates with complete coverage.

Reasoning value:

- Reasoning did not improve the best context variants.
- Reasoning broke no-context and full-context runs.
- Reasoning did not harm mechanics-only, significant-only, or ultra-compact coverage, but it did not materially improve them either.

### Conclusion

Context should be small and purpose-built. For action-item classification, the most valuable context is likely:

- meeting mechanics/noise rules
- ultra-compact task guidance

The full context pack should not be passed wholesale into small-model verticals.

## Experiment 3: Iterative Slice-To-Meeting Synthesis

Goal: test final synthesis from reduced artifacts rather than from the full transcript.

| Case | Reasoning | Valid JSON | Item Count | Shape Followed | Initial Quality |
| --- | --- | --- | ---: | --- | --- |
| final action items from promoted candidates | off | yes | 4 | yes | usable but over-includes weak/vague items |
| final action items from promoted candidates | on | yes | 4 | yes | cleaner prose but overconfident |
| final action items from all candidates | off | yes | 7 | yes | too many false positives |
| final action items from all candidates | on | yes | 11 | yes | much worse; promotes many false positives |
| significant ideas synthesis | off | yes | 0 by expected key | no | wrong shape, generic product-analysis output |
| significant ideas synthesis | on | yes | 0 by expected key | no | same wrong shape |

### Interpretation

Action-item synthesis works structurally if it receives already-filtered candidates, but it still needs a final validator because it phrases weak candidates as concrete tasks.

Synthesis from all candidates is unsafe. Reasoning-on made it worse by promoting more false positives.

Significant-ideas synthesis failed the requested output shape and produced generic categories such as constraints, design principles, key decisions, risks, and success metrics. That is not acceptable as final synthesis, even though the earlier significant-ideas evidence extraction was strong.

### Conclusion

Final synthesis is a separate hard problem. It should be deterministic or heavily constrained:

- Use filtered evidence, not all candidates.
- Preserve evidence IDs.
- Validate output shape.
- Reject unsupported generic strategy-report sections.

Reasoning does not currently improve final synthesis enough to justify default use.

## Overall Reasoning-Mode Assessment

Reasoning mode should not be globally enabled.

Observed value:

- It can improve individual semantic judgments.
- It returns reasoning traces separately, which is useful for debugging.

Observed cost:

- Much higher latency.
- Worse candidate coverage in larger classification prompts.
- More false positives when synthesizing from all candidates.
- No improvement for significant-ideas synthesis shape compliance.

Recommended policy:

- Default reasoning off.
- Consider reasoning only for targeted ambiguity repair or one-item review.
- Always validate coverage and shape regardless of reasoning mode.
- Save reasoning traces for debugging only; never treat them as meeting evidence.

## Current Best Pattern

For `gemma4:e2b`, the most effective transcript analysis pattern is:

1. Ingest once into local storage.
2. Slice transcript into small windows.
3. Extract evidence candidates with narrow prompts.
4. Build deterministic or very compact context maps.
5. Run slice-local or small-batch classification.
6. Validate candidate IDs and coverage.
7. Repair missing candidates only.
8. Synthesize final outputs from filtered evidence only.
9. Validate final shape and evidence references.

## Recommended Next Experiments

### 1. Ultra-Compact Action Classifier By Slice

Run slice-local classification using only ultra-compact context and reasoning off.

Purpose:

- Determine whether the ultra-compact context can replace the fuller V4 prompt/context while preserving quality.

### 2. Mechanics-Only Negative Filter

Run a deterministic or model-assisted negative filter before action classification.

Purpose:

- Remove screen sharing, slide navigation, hard stops, and presentation flow before any action-item promotion.

### 3. Significant Ideas Synthesis With Fixed Buckets

Do not ask for free-form synthesis. Instead, group significant-ideas evidence into fixed buckets:

- revenue strategy
- MVP/wedge
- architecture/platform
- security/observability
- IP/legal
- risks/open questions

Purpose:

- Test whether constrained grouping succeeds where broad synthesis failed.

