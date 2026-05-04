# Action Items V4 Completeness Validation: Recording 140341999

## Run

- Date: 2026-05-03
- Recording ID: `140341999`
- Experiment ID: `action_items-v4-context-classifier-140341999-20260503-032103`
- Candidate source run: `action_items-v2-slices-140341999-20260503-022458`
- Context source run: `context_pack-v1-140341999-20260503-030135`
- Fathom API used: no

## Change

The V4 runner now assigns stable `candidate_id` values to each input candidate and validates:

- every expected candidate is classified exactly once
- no unknown candidate IDs are returned
- no duplicate candidate IDs are returned
- promoted candidates are only `post_meeting_follow_up`

## Result

The validation caught incomplete model output.

Invalid slices:

- `slice_04_15:00_20:00`: 2 candidates in, 1 classification out.
- `slice_08_35:00_40:00`: 2 candidates in, 1 classification out.

This is exactly the class of failure that previously would have been easy to miss.

## Interpretation

The classification quality improved with context and hard negative rules, but the workflow still needs a repair mechanism. The model can omit items even when directly instructed to classify every candidate.

## Recommended Next Step

Add a local repair pass:

- Read the invalid V4 run.
- For each invalid slice, send only missing candidates plus existing classifications.
- Require output for the missing candidate IDs only.
- Merge repaired classifications into the original run or write a repaired run artifact.

This keeps the workflow local and avoids rerunning valid slices.

