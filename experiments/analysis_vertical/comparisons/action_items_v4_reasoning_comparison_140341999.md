# Action Items V4 Reasoning Comparison: Recording 140341999

## Run

- Date: 2026-05-03
- Experiment ID: `action_items-v4-context-reasoning-140341999-20260503-171609`
- Candidate source run: `action_items-v2-slices-140341999-20260503-022458`
- Context source run: `context_pack-v1-140341999-20260503-030135`
- Model: `gemma4:e2b`
- Settings: JSON mode, temperature `0`, `reasoning=True`
- Fathom API used: no

## Comparison Baselines

- Non-reasoning invalid run: `action_items-v4-context-classifier-140341999-20260503-032103`
- Repaired non-reasoning run: `action_items-v4-repaired-140341999-20260503-165550`

## Result

Reasoning mode did not solve candidate coverage.

The reasoning-enabled run still had:

- `invalid_slice_count: 2`
- missing `slice_04_15:00_20:00_candidate_02`
- missing `slice_08_35:00_40:00_candidate_02`

This matches the non-reasoning V4 failure pattern.

## What Improved

Reasoning mode made one useful semantic improvement:

- `slice_04_15:00_20:00_candidate_01`
- Excerpt: "But I'll give you a quick look and at least you'll get a heads up first."
- Non-reasoning rerun promoted it as `post_meeting_follow_up`.
- Reasoning mode classified it as `not_action_item`.

That is probably better.

## What Did Not Improve

Reasoning mode still promoted:

- Brian support/fix commitment at `03:39`.
- Matt "We'll arrange that" at `28:29`.
- Larry assigning Matt input/recommendation responsibility at `28:51`.

The third remains questionable as a final action item; it is arguably a role/participation need rather than a concrete task.

## Reasoning Trace Handling

The runner saved reasoning traces separately as `reasoning.txt` inside each slice directory. The final JSON content remained parseable and did not include thinking tags.

Reasoning traces are useful for debugging, but they should not be stored as final evidence or passed downstream as meeting facts.

## Conclusion

`reasoning=True` is worth keeping as an experimental setting, but it is not a substitute for:

- candidate IDs
- completeness validation
- targeted repair
- final synthesis/review over promoted candidates

The next useful model-settings experiment should compare:

- reasoning off/on
- shorter prompts
- smaller context pack
- explicit "classify all candidates first, then decide promotion" output shape

The next pipeline experiment should keep repair as a required stage.

