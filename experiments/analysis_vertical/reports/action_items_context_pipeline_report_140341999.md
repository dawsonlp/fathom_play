# Action Items Context Pipeline Report: Recording 140341999

## Purpose

Report the results of the action-items experiment sequence using local artifacts, significant-ideas/context preprocessing, candidate validation, and targeted repair.

## Recording

- Recording ID: `140341999`
- Meeting title: `Regroup - Larry / Matt / Brian / Jake`
- Source transcript: already captured in local experiment artifacts
- Live Fathom API used in final classification/repair steps: no

## Experiment Sequence

### V1: Full-Transcript Vertical Prompt

Run: `action_items-v1-140341999-20260502-204446`

Result: failed.

The model returned a generic project-roadmap summary and zero action-item findings. This matched the failure pattern across all full-transcript vertical prompts.

### V2: Slice Evidence Candidates

Run: `action_items-v2-slices-140341999-20260503-022458`

Result: promising but noisy.

The model successfully followed a narrow evidence-candidate extraction prompt over 5-minute transcript slices. It returned structured evidence with speaker, timestamp, excerpt, and rationale. However, it over-included immediate in-meeting actions.

### V3: Candidate Classifier

Run: `action_items-v3-classifier-140341999-20260503-023352`

Result: mixed.

The model preserved structure but promoted 11 candidates as post-meeting follow-ups. Many were false positives, including screen sharing, slide walkthroughs, hard-stop management, and slide navigation.

### Context Pack V1

Run: `context_pack-v1-140341999-20260503-030135`

Result: mixed overall, useful as deterministic context.

The model-generated final context pack hallucinated and used the wrong shape. The deterministic context pack built from validated maps was useful. It captured meeting purpose, significant ideas, strategic intentions, design principles, open tensions, participant context, topic timeline, domain vocabulary, and meeting mechanics.

### V4: Context-Aware Candidate Classifier

Run: `action_items-v4-context-classifier-140341999-20260503-031430`

Result: promising.

The deterministic context pack plus hard negative rules reduced promotions from 11 to 2. The model correctly rejected screen sharing, slide walkthroughs, hard-stop notices, slide navigation, and role/ownership statements.

### V4 Validation Rerun

Run: `action_items-v4-context-classifier-140341999-20260503-032103`

Result: validation worked.

Candidate IDs exposed a model omission: two slices were missing one classification each. The run correctly reported `invalid_slice_count: 2`.

### V4 Repair

Run: `action_items-v4-repaired-140341999-20260503-165550`

Result: repaired and complete.

The targeted repair pass processed only the two missing candidates and merged the results. Final repaired output had:

- `invalid_slice_count: 0`
- complete candidate coverage for all six candidate-bearing slices
- no missing, extra, or duplicate candidate IDs

## Final Promoted Candidates

The repaired run promoted four candidates:

| Time | Speaker | Excerpt | Initial Assessment |
| --- | --- | --- | --- |
| `03:39` | Brian C Winters | "Just text me and let me know and I'll stop what I'm doing and come over and fix it." | Likely real support commitment, but probably meeting-logistics/support rather than substantive follow-up. |
| `15:08` | Larry Dawson | "But I'll give you a quick look and at least you'll get a heads up first." | Possibly presentation-flow commitment; needs surrounding context before final action item. |
| `28:29` | Matt | "We'll arrange that." | Plausible follow-up, but needs nearby context to know what "that" refers to. |
| `28:51` | Larry Dawson | "I definitely need input from you, Matt..." | Model promoted this as a task for Matt, but this may be closer to role/participation need than a concrete task. |

## What Worked

- Local artifacts are sufficient for iterative downstream experiments after transcript capture.
- Full-transcript vertical prompting is weak for this model.
- Small slice evidence extraction works.
- Deterministic context packing helps.
- Candidate IDs are necessary for reliable multi-step workflows.
- Validation and targeted repair are effective.
- Hard negative rules improve temporal/action classification.

## What Did Not Work

- Broad model synthesis remains unreliable.
- The model still needs help distinguishing substantive follow-up tasks from vague or contextual commitments.
- Even with explicit coverage rules, the model can omit candidates.
- Promotion still needs a final synthesis/review step with local slice context.

## Current Recommended Pipeline Shape

For action items:

1. Slice transcript.
2. Extract candidate evidence.
3. Build deterministic context pack from preprocessing maps.
4. Classify candidates with context and hard negative rules.
5. Validate candidate coverage.
6. Repair only invalid slices.
7. Run final synthesis over promoted candidates plus local slice text.
8. Store final action items only if evidence and context support them.

## Implications For System Design

The local store should become the center of experimentation and analysis. Fathom should be used to ingest source artifacts once. Later analysis iterations should read local transcript, slice, candidate, context, and validation artifacts.

The system should treat model output as one stage in a validated pipeline, not as a trusted final answer.

## Next Experiment Direction

The next experiment should examine whether `gemma4:e2b` has provider/model-specific prompting requirements, especially around "thinking mode." If the model expects a particular system prompt or template behavior, we should test whether that improves:

- candidate coverage compliance
- classification accuracy
- resistance to generic summaries
- final synthesis quality

## Model Settings Follow-Up

Local `ollama show gemma4:e2b` reports that the installed model has the `thinking` capability. Ollama's API documentation exposes thinking through a request-level `think` field rather than only through system-prompt wording. The installed `langchain-ollama` package exposes this as the `reasoning` parameter on `ChatOllama`.

A local smoke test with:

```python
ChatOllama(model="gemma4:e2b", format="json", temperature=0, reasoning=True)
```

returned clean JSON in `content` and a separate reasoning trace in `additional_kwargs["reasoning_content"]`.

Next model-settings experiment:

- Repeat the V4 context classifier with `reasoning=True`.
- Keep the same local candidate/context inputs.
- Compare against `action_items-v4-repaired-140341999-20260503-165550`.
- Score candidate coverage, promotion count, false positives, and semantic consistency.
- Preserve reasoning traces as separate artifacts for review, but do not pass them downstream as facts.

