# Claude Sonnet vs Opus Comparison: Recording 142870463

## Runs

- Date: 2026-05-04
- Recording: `142870463` — AI Doc Recon - Weekly Status Sync (45 min, 5 active speakers)
- Candidate source run: `action_items-v2-slices-142870463-20260504-200837`
- Context source run: `context_pack-v1-142870463-20260504-201710`
- Pipeline: V4 context-aware action-item classifier (`prompt_v4_context_classifier.md`)
- Fathom API used: no (local artifacts only)

### Model Arms

| Arm | Experiment ID | Notes |
| --- | --- | --- |
| Sonnet (pre-fix) | `claude-model-comparison-142870463-20260504-202351` | Initial run, fences present |
| Opus | `claude-model-comparison-142870463-20260504-202351` | Same run as Sonnet pre-fix |
| Sonnet (post-fix) | `claude-model-comparison-142870463-20260504-210000` | After stronger no-fence instruction |

## Comparison Against gemma4:e2b Baseline

The gemma4 baseline is from recording 140341999 (different meeting). A direct numeric comparison is not valid, but the structural comparison is.

| Metric | gemma4:e2b (140341999, repaired) | claude-sonnet-4-6 | claude-opus-4-7 |
| --- | --- | --- | --- |
| Coverage failures | 2 of 6 slices | **0 of 8** | **0 of 8** |
| Repair passes needed | yes | **no** | **no** |
| Invalid slice count | 2 (pre-repair) | 0 | 0 |
| Fence strips needed | N/A | 4 (pre-fix), **0 (post-fix)** | **0** |
| Latency | ~15 min (local) | ~46–50s | ~50–52s |

## Sonnet vs Opus Detail

| Metric | claude-sonnet-4-6 (post-fix) | claude-opus-4-7 |
| --- | --- | --- |
| Slices processed | 8 | 8 |
| Coverage failures | 0 | 0 |
| Invalid slices | 0 | 0 |
| Fence strips | 0 | 0 |
| Promoted count | 10 | 12 |
| Total latency | 50.2s | 50.4s |

## Promoted Candidates

Ten candidates are common to both models. Opus promoted two additional items.

### Shared (10 items)

| Time | Speaker | Excerpt (truncated) |
| --- | --- | --- |
| 00:06 | Pamela Krol | "this would be getting Brett that information by end of day today" |
| 03:20 | Pamela Krol | "Larry, get all that set up..." (assigns Larry multiple setup tasks) |
| 14:35 | Pamela Krol | "we'll probably set up a separate session...while going through the user..." |
| 17:15 | Larry Dawson | "Yeah, let's add a ticket for that specifically." |
| 21:01 | Larry Dawson | "I'll extend this with more information about how to actually go about deploying..." |
| 22:37 | Larry Dawson | "If not, we'll do a walkthrough and show you how we deploy it on our environment..." |
| 30:18 | Pamela Krol | "we'll have this, there's a couple tweaks we need to make, and then we'll send..." |
| 30:33 | Pamela Krol | "next week, you guys can work together with Larry and with our team..." |
| 33:34 | Kari Cromer | "So as soon as I get that, I will shoot it to you." |
| 44:00 | Chris Calvert | "we are going to be switching over to read-only Production Service Titan shortly..." |

### Opus-only (2 additional items)

| Time | Speaker | Excerpt | Assessment |
| --- | --- | --- | --- |
| 18:00 | Larry Dawson | "And GitHub that I want to add in...we'll get you a updated packet and the Terraform code for it later today..." | Borderline. The first clause is in-meeting screen sharing; the second ("updated packet later today") is a genuine post-meeting delivery. Sonnet's rejection is arguably too conservative here. |
| 43:45 | Colin Rushton | "So we can start giving that a test on the sandbox and see what we..." | Legitimate post-meeting sandbox testing proposal. Sonnet missed this. Opus is correct. |

## JSON Compliance Finding

### Before fix

Sonnet wrapped output in ` ```json ` fences on 4 of 8 slices. Opus never did.

The original system prompt said: `"Do not add markdown fences or extra keys."` This did not land reliably for Sonnet.

### Fix applied

Changed the instruction to a positive constraint:

> "Your response must begin with `{` and end with `}`. Never use ` ```json `, ` ``` `, or any other code fence or wrapper."

After the fix: Sonnet produced clean raw JSON on all 8 slices. Zero fence strips required.

This change was applied to both the experiment runner (`SYSTEM_PROMPT`) and the production `analysis_enricher.py`.

**Rule:** For Claude models, a positive output constraint ("begin with `{`") is more reliable than a negative instruction ("no fences"). Apply this pattern wherever clean JSON output is required.

## Instrumentation Note: HARD_NEGATIVE_IDS

The `HARD_NEGATIVE_IDS` set in the experiment runner was copied from recording 140341999, where specific candidate IDs (e.g., `slice_01_00:00_05:00_candidate_01`) were confirmed false positives from that meeting's content.

For recording 142870463, these IDs coincidentally exist (same slice naming convention) but refer to entirely different candidates. The 1–2 "hard negative promotions" reported for both models in this experiment are not genuine false positives — the flagged candidates are legitimate action items in this meeting.

**Action required:** For future experiments on a new recording, either clear `HARD_NEGATIVE_IDS` or replace it with recording-specific IDs identified after reviewing the V2 candidate extraction output.

## Coverage Finding

Both models classified every candidate exactly once across all 8 slices. No repair pass was needed.

This contrasts with gemma4:e2b, which omitted candidates in 2 of 6 candidate-bearing slices in the prior recording and required a targeted repair runner. The repair requirement appears to be a gemma4 limitation rather than a pipeline requirement.

For production use with Claude, the repair pass can be treated as a safety net rather than a routine step.

## Latency Finding

Both models completed 8 slices in approximately 50 seconds (cloud API, not local inference).

- Sonnet: 50.2s total, avg ~6.3s/slice
- Opus: 50.4s total, avg ~6.3s/slice

The latency difference is negligible. The dominant cost difference between Sonnet and Opus is price per token, not wall-clock time.

## Conclusion

**Both models solve the coverage problem.** The pipeline no longer requires a mandatory repair pass when using Claude.

**Sonnet is the right default for this pipeline.** It achieves identical coverage and nearly identical promoted output to Opus, at lower cost. The two Opus-only promotions at 18:00 and 43:45 suggest Opus is marginally less conservative — useful to know, but not worth the cost difference for a classification task.

**Opus has one genuine quality advantage:** it never needed fences even before the prompt fix, while Sonnet required a prompt change. This suggests Opus has stronger instruction-following on output format constraints. After the fix, Sonnet is equivalent in this respect.

## Recommended Next Steps

- Use `claude-sonnet-4-6` as the default production model.
- Apply the positive JSON constraint (`"Your response must begin with {"`) to any new prompt that targets Claude models.
- Record-specific hard-negative IDs should be established per recording before running the comparison runner; clear the global set between recordings.
- Evaluate whether the 43:45 Opus promotion (sandbox testing) and 18:00 Opus promotion (Terraform packet) are correct by reviewing the raw transcript context. If both are genuine, this is signal that Sonnet may need a slightly more permissive promotion rule for conditional post-meeting commitments.
