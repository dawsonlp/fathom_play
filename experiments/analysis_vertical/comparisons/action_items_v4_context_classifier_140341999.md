# Action Items V4 Context Classifier: Recording 140341999

## Run

- Date: 2026-05-03
- Recording ID: `140341999`
- Experiment ID: `action_items-v4-context-classifier-140341999-20260503-031430`
- Candidate source run: `action_items-v2-slices-140341999-20260503-022458`
- Context source run: `context_pack-v1-140341999-20260503-030135`
- Run root: `experiments/analysis_vertical/runs/140341999/action_items-v4-context-classifier-140341999-20260503-031430/`
- Fathom API used: no

## Result

This was a significant improvement over V3.

V3 promoted 11 candidates. V4 promoted 2 candidates:

- Brian C Winters at `03:39`: "Just text me and let me know and I'll stop what I'm doing and come over and fix it."
- Matt at `28:29`: "We'll arrange that."

Most false positives from V3 were correctly rejected:

- screen sharing/testing
- walking through slides
- hard-stop notice
- paging/skipping slides
- general role/ownership statements
- incomplete "I'll shoot you my..." commitment

## What Changed

The V4 prompt used:

- deterministic context pack
- hard negative rules
- local V2 candidate evidence
- no live Fathom fetch

This supports the hypothesis that upstream context plus narrow local evidence inputs can improve vertical quality.

## Remaining Weaknesses

- One slice had incomplete classification coverage: 2 candidates in, 1 classification out.
- The Brian item may be a real support commitment, but it is not necessarily an action item from the substantive meeting.
- The Matt item needs nearby context before final synthesis can safely phrase it.

## Recommended Next Step

Add validation that every input candidate must receive one classification. Then add final action-item synthesis over promoted candidates with access to:

- deterministic context pack
- promoted candidates
- local transcript slice text for promoted candidate slices

The final synthesizer should produce a concise action-item list or explicitly say that no substantive post-meeting action items were found.

