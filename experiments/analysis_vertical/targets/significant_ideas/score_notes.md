# Score Notes: Significant Ideas

## Variant V1: Evidence Candidates

Purpose: determine whether `gemma4:e2b` can extract significant ideas and intentions from short transcript windows.

Prompt: `prompt_v1_evidence_candidates.md`

Success criteria:

- Returns exact evidence snippets.
- Avoids logistics and meeting mechanics.
- Captures ideas, intentions, principles, proposals, design directions, and strategic concerns.
- Does not collapse into a broad meeting summary.

## Runs

### Run: `significant_ideas-v1-slices-140341999-20260503-023715`

Initial manual score estimate: 13/19.

Strengths:

- Avoided generic summary mode.
- Returned evidence-rich outputs for substantive slices.
- Correctly returned empty evidence for early logistics-heavy slices.
- Produced useful raw material for synthesis.

Weaknesses:

- Included travel/logistics in one slice.
- Produced one malformed speaker field.
- Needs synthesis, deduplication, and exclusion of weak candidates.

Next tuning step:

- Add V2 synthesis over evidence candidates to group related ideas and exclude weak/logistical candidates.
