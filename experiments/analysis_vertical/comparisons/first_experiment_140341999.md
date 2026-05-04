# First Vertical Experiment: Recording 140341999

## Run

- Date: 2026-05-02
- Recording ID: `140341999`
- Variant: V1 full transcript, strict target-specific prompts
- Runtime user: `dawsonlp`
- Model: Ollama `gemma4:e2b`, JSON mode, temperature `0`
- Run root: `experiments/analysis_vertical/runs/140341999/`

## Summary

All seven vertical targets failed in the same way. The model returned valid JSON shape with `confidence: low`, zero findings, and a generic project-roadmap summary. The summary text was effectively identical across targets.

This is useful evidence. It means target separation alone does not overcome the local model's difficulty with the full transcript.

## Target Results

| Target | Findings | Evidence Status | Automated Score | Notes |
| --- | ---: | --- | ---: | --- |
| conversation_classification | 0 | incomplete | 2 | Generic summary, no classification findings. |
| action_items | 0 | incomplete | 2 | Generic summary, no action items. |
| decisions | 0 | incomplete | 2 | Generic summary, no decisions. |
| open_questions_and_risks | 0 | incomplete | 2 | Generic summary, no risks or questions. |
| coaching_review | 0 | incomplete | 2 | Generic project summary, no coaching observations. |
| people_dynamics | 0 | incomplete | 2 | Generic project summary, no dynamics observations. |
| working_styles | 0 | incomplete | 2 | Generic project summary, no working-style observations. |

## Interpretation

The model appears to compress the full transcript into a broad summary before satisfying the target-specific request. JSON mode and strict schema prevent malformed output, but they do not force useful target-specific reasoning.

## Recommended Next Experiment

Move from V1 strict schema to V2 evidence-first prompts:

- Ask for only evidence candidates first.
- Do not ask for final claims in the same call for the first tuning pass.
- Use target-specific trigger language:
  - action items: commitments, requests, "I will", "can you", "next step"
  - decisions: decided, agreed, confirmed, rejected, deferred
  - risks/questions: concern, unknown, dependency, blocker, assumption
  - coaching: framing, clarifying, summarizing, inviting input, closing
  - people dynamics: disagreement, repair, alignment, interruption, clarification

If evidence-first full-transcript prompts still fail, the next axis should be horizontal preprocessing with speaker-turn or time-window chunks.

