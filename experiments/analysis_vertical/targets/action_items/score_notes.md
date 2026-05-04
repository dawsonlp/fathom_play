# Score Notes: Action Items

## Runs

No reviewed runs yet.

## Tuning Ideas

- If it invents action items, add negative examples: discussion topic, proposal, unresolved question.
- If it misses commitments, ask for evidence candidates containing "I will", "we should", "can you", "I'll", and similar phrases before final output.

## Variant V2: Evidence Candidates

Purpose: determine whether `gemma4:e2b` can follow a narrow extraction task on short transcript slices before asking it to synthesize final action items.

Prompt: `prompt_v2_evidence_candidates.md`

Success criteria:

- Returns `{"evidence": []}` for slices without commitments.
- Returns exact speaker/timestamp/excerpt for slices with explicit commitments.
- Does not summarize the meeting.
- Does not infer action items from planning topics.

### Run: `action_items-v2-slices-140341999-20260503-022458`

Initial manual score estimate: 10/19.

Strengths:

- Followed the narrow instruction on 5-minute slices.
- Returned structured evidence candidates with timestamps.
- Returned empty evidence arrays for several slices.

Weaknesses:

- High false positives.
- Included immediate in-meeting actions and facilitation moves.
- Included role/ownership statements as if they were tasks.

Next tuning step:

- Add a V3 classifier over evidence candidates before final action-item synthesis.

## Variant V3: Candidate Classifier

Purpose: classify V2 evidence candidates before final action-item synthesis.

Prompt: `prompt_v3_candidate_classifier.md`

Success criteria:

- Preserves original candidate evidence.
- Separates post-meeting follow-ups from in-meeting actions.
- Separates role/ownership statements from actionable tasks.
- Produces `promote_to_action_item: true` only for `post_meeting_follow_up`.

## Variant V4: Context-Aware Classifier

Purpose: test whether a deterministic context pack plus stronger temporal negative rules helps reject in-meeting actions.

Prompt: `prompt_v4_context_classifier.md`

Success criteria:

- Rejects screen sharing, slide walkthroughs, slide navigation, hard-stop notices, and immediate presentation actions.
- Preserves candidate evidence.
- Promotes only true post-meeting follow-up tasks.
- Does not require a live Fathom API fetch.
