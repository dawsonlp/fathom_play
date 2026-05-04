# Action Items V3 Candidate Classifier: Recording 140341999

## Run

- Date: 2026-05-03
- Recording ID: `140341999`
- Experiment ID: `action_items-v3-classifier-140341999-20260503-023352`
- Source run: `action_items-v2-slices-140341999-20260503-022458`
- Run root: `experiments/analysis_vertical/runs/140341999/action_items-v3-classifier-140341999-20260503-023352/`
- Model: Ollama `gemma4:e2b`, JSON mode, temperature `0`

## Result

The classifier preserved structure and did not collapse into a generic summary. However, it over-promoted candidates to `post_meeting_follow_up`.

It promoted 11 candidates. Manual inspection suggests many are false positives.

## What Worked

- It consumed the V2 candidates without needing the full transcript.
- It preserved speaker, timestamp, and excerpt.
- It correctly classified at least one immediate action:
  - `02:06` "I'll try that again now." as `in_meeting_action`.
- It correctly classified at least one role statement:
  - `29:00` "You own the final wage selection..." as `role_or_ownership_statement`.

## What Failed

The model still promoted obvious in-meeting or facilitation actions:

- `00:30` "Yeah, I'll test."
- `14:35` "I'll walk through the slide deck..."
- `37:22` hard stop notice.
- `37:26` paging quickly through slides.
- `41:43` skipping forward before dropping.

The failure mode is narrower than V1, but still important: the model is over-relying on "I will" wording and underusing temporal context.

## Next Tuning Options

Option A: V4 stricter classifier prompt.

- Add explicit negative examples for screen sharing, presenting, slide navigation, time management, and "now" actions.
- Require a post-meeting cue such as after, later, send, follow up, arrange, schedule, share, review, update, or get back.

Option B: deterministic prefilter before model classification.

- Mark candidates with obvious in-meeting cues as `in_meeting_action`.
- Send only ambiguous candidates to the model.

Option C: defer action-items synthesis and test another vertical.

- The significant-ideas/intentions path may be more naturally aligned with this meeting and may require less brittle classification.

