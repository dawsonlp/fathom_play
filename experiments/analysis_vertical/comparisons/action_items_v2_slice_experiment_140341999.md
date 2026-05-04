# Action Items V2 Slice Experiment: Recording 140341999

## Run

- Date: 2026-05-03
- Recording ID: `140341999`
- Experiment ID: `action_items-v2-slices-140341999-20260503-022458`
- Run root: `experiments/analysis_vertical/runs/140341999/action_items-v2-slices-140341999-20260503-022458/`
- Target: `action_items`
- Variant: `v2_evidence_candidates`
- Preprocessing: 5-minute time windows
- Model: Ollama `gemma4:e2b`, JSON mode, temperature `0`

## Result

This experiment was materially better than V1. The model did not ignore the prompt and did not produce a generic meeting summary. It returned JSON evidence candidates per slice, including speaker, timestamp, excerpt, and a short rationale.

## Slice Summary

| Slice | Window | Evidence Count | Initial Read |
| --- | --- | ---: | --- |
| 1 | 00:00-05:00 | 3 | Mostly screen-sharing and troubleshooting; likely false positives for follow-up action items. |
| 2 | 05:00-10:00 | 0 | Correctly returned empty evidence. |
| 3 | 10:00-15:00 | 1 | In-meeting offer to walk through slides; likely not a follow-up action item. |
| 4 | 15:00-20:00 | 2 | In-meeting presentation/feedback language; one may be useful but needs classification. |
| 5 | 20:00-25:00 | 0 | Correctly returned empty evidence. |
| 6 | 25:00-30:00 | 3 | Strongest slice; includes "We'll arrange that" and ownership/decision statements around Matt. Needs classification because some items are role ownership, not tasks. |
| 7 | 30:00-35:00 | 0 | Correctly returned empty evidence. |
| 8 | 35:00-40:00 | 2 | Time-management and slide navigation; likely false positives. |
| 9 | 40:00-45:00 | 2 | One immediate navigation action and one likely follow-up send/share commitment. |

## Strengths

- The model followed the narrow task on short context.
- It returned exact transcript coordinates.
- It returned empty evidence arrays on several slices instead of forcing findings.
- It surfaced potentially useful moments that can be classified in a second pass.

## Weaknesses

- It confuses any "I will" statement with a follow-up action item.
- It includes immediate in-meeting facilitation actions.
- It includes role/ownership descriptions as commitments.
- It needs a second-stage classifier before final action-item synthesis.

## Recommended Next Iteration

Add Action Items V3 as a candidate classifier:

- Input: evidence candidates from V2, not the full transcript.
- Output categories:
  - `post_meeting_follow_up`
  - `in_meeting_action`
  - `role_or_ownership_statement`
  - `not_action_item`
- Only `post_meeting_follow_up` should become final action items.
- Preserve original speaker, timestamp, and excerpt.
- Owner should be null unless stated or strongly implied by the evidence.

## Working Hypothesis

For this local model, action-item extraction should become a three-step iterative vertical workflow:

1. Slice transcript into small windows.
2. Extract candidate commitment evidence from each slice.
3. Classify and synthesize candidates into final action items.

