# Fathom Conversation Agent Analysis Experiment Plan

## Purpose

Define a practical experiment plan for improving transcript analysis quality before committing to a larger analysis architecture. The current evidence shows that a single broad full-transcript analysis pass is too weak with the initial local model. This plan separates analysis quality questions so each approach can be tested, compared, and tuned independently.

## Current Observation

The current implementation can ingest a Fathom transcript, store artifacts, run a LangGraph analysis workflow, and persist structured outputs. A live run against recording `140341999` showed that the local `gemma4:e2b` model can produce plausible summaries but does not reliably produce evidence-backed findings when asked to perform broad analysis over the full transcript.

After tightening the schema and enabling Ollama JSON mode, the system correctly marked unsupported outputs as incomplete. That is the right correctness behavior, but it does not yet produce useful enough analysis.

## Hypothesis

Analysis quality will improve if the workflow is split along two axes:

- Vertical target separation: ask narrower analysis questions independently instead of asking one broad model pass to do everything.
- Horizontal context reduction: preprocess the transcript into smaller, signal-preserving inputs before running target-specific analysis.

The experiment sequence should start with vertical target separation because it is simpler to conceive, easier to evaluate, and less likely to hide signal. Preprocessing should be introduced only after the vertical targets have clear expected outputs and evaluation criteria.

## Experiment Principles

- Preserve the original transcript as the source of truth.
- Do not treat model output as complete unless claims tie back to evidence.
- Tune one variable at a time where practical.
- Store raw model output, normalized output, prompt version, model metadata, runtime context, and validation result for every run.
- Prefer repeatable comparison against a small fixed corpus before changing the general ingestion workflow.
- Failed or incomplete analysis is a useful result and should be recorded explicitly.

## Fixed Test Corpus

Initial experiments should use a small repeatable corpus:

| Recording | Purpose |
| --- | --- |
| `140341999` | Known latest visible conversation; useful baseline because previous broad runs produced weak summary-only outputs. |
| 1-2 short operational meetings | Tests whether short transcripts work without preprocessing. |
| 1 planning or architecture meeting | Tests decisions, action items, and technical disagreement extraction. |
| 1 coaching-heavy or facilitation-heavy meeting | Tests user-specific coaching analysis. |
| 1 meeting with obvious conflict or disagreement | Tests careful people-dynamics extraction. |

The first iteration may use only `140341999`. Additional recordings should be added once the experiment harness can compare outputs consistently.

## Baseline To Preserve

The baseline is the current broad full-transcript approach:

- Input: full transcript.
- Prompt: broad perspective-specific prompt.
- Output: JSON summary, confidence, findings, evidence status.
- Observed behavior: plausible summary, no useful evidence-backed findings.

This baseline should remain runnable so future changes can be compared against it.

## Vertical Analysis Targets

Each vertical target should be tested as an independent prompt and output contract. Targets should not share model output with each other during the first experiment phase.

### 1. Conversation Classification

Goal:

- Identify the type of conversation and the main themes.

Expected output:

- Conversation type.
- Secondary labels if useful.
- Main themes.
- Confidence.
- Evidence for each label or theme.

Evaluation questions:

- Does the model distinguish planning, status, coaching, conflict-resolution, sales, and technical-design conversations?
- Are labels supported by transcript evidence rather than inferred from title alone?
- Does the output avoid over-specific classification when evidence is thin?

### 2. Action Items

Goal:

- Extract commitments and follow-up tasks for all participants.

Expected output:

- Claim/action.
- Owner when stated or strongly implied.
- Due date only when stated.
- Status if discussed.
- Evidence.

Evaluation questions:

- Are actual commitments separated from vague possibilities?
- Are owners correctly assigned?
- Are due dates invented or left null when absent?
- Are action items supported by exact transcript excerpts?

### 3. Decisions

Goal:

- Extract decisions made or confirmed during the meeting.

Expected output:

- Decision.
- Decider or agreeing participants when visible.
- Alternatives considered, if present.
- Open caveats.
- Evidence.

Evaluation questions:

- Does the model distinguish decisions from proposals?
- Does it capture caveats or conditions?
- Does it avoid turning unresolved discussion into decisions?

### 4. Open Questions And Risks

Goal:

- Identify unresolved questions, risks, blockers, and assumptions.

Expected output:

- Risk/question/blocker.
- Category.
- Owner if assigned.
- Severity or priority if clearly implied.
- Evidence.

Evaluation questions:

- Does the model surface useful uncertainties?
- Does it avoid generic project-management filler?
- Are risks tied to actual remarks?

### 5. Coaching Review

Goal:

- Assess how the runtime user conducted the meeting.

Expected output:

- Coaching observation.
- Positive behavior or improvement opportunity.
- Suggested next behavior.
- Evidence.
- Carefulness qualifier.

Evaluation questions:

- Does the model focus on the supplied username?
- Does it identify facilitation moves, interruptions, framing, listening, summarizing, and decision management?
- Does it stay useful without becoming performative or personality-judgmental?

### 6. People Dynamics

Goal:

- Identify collaboration patterns, tension, conflict, working-style signals, and participant approaches.

Expected output:

- Observation.
- Participants involved.
- Dynamic category.
- Carefulness qualifier.
- Evidence.

Evaluation questions:

- Does the model distinguish observable behavior from psychological claims?
- Does it use careful language?
- Does it identify real tension or alignment rather than generic collaboration comments?

### 7. Working Styles

Goal:

- Identify participant preferences and approaches visible in the transcript.

Expected output:

- Participant.
- Observed working-style signal.
- Strength of signal.
- Evidence.
- Caveat.

Evaluation questions:

- Does the model avoid personality typing?
- Are observations grounded in repeated or strong transcript signals?
- Does it separate communication style from inferred motive?

## Vertical Experiment Matrix

For each target, run these variants first:

| Variant | Input | Prompt Style | Expected Learning |
| --- | --- | --- | --- |
| V1 | Full transcript | Strict schema only | Whether target separation alone improves output. |
| V2 | Full transcript | Schema plus 2-3 examples | Whether examples improve evidence compliance. |
| V3 | Full transcript | Two-step within target: evidence list then claims | Whether explicitly harvesting evidence first improves quality without external preprocessing. |
| V4 | Full transcript | Claims prohibited unless evidence first | Whether ordering constraints reduce unsupported summaries. |

The initial winner for each vertical target should be selected before introducing preprocessing variants.

## Evaluation Rubric

Each run should be scored per target:

| Criterion | Score |
| --- | --- |
| Valid schema | 0-2 |
| Evidence completeness | 0-3 |
| Evidence accuracy | 0-3 |
| Claim usefulness | 0-3 |
| Claim carefulness | 0-2 |
| False positives | 0-3, where 3 means few or none |
| Missing obvious items | 0-3, where 3 means few or none |

Recommended interpretation:

- 15-19: strong enough to keep tuning.
- 10-14: promising but needs target-specific adjustment.
- 0-9: not good enough for the current model/input strategy.

Manual review is expected at this stage. Automated validators can check schema and evidence presence, but they cannot yet judge whether evidence actually supports the claim.

## Horizontal Preprocessing Experiments

Preprocessing should be tested after vertical prompt variants have clear baselines. The concern is valid: preprocessing can hide signal. Each preprocessing strategy must preserve traceability to the original transcript and should be evaluated against the best full-transcript vertical variant.

### Preprocessing Strategy A: Time Windows

Split transcript into fixed time windows, such as 5 or 10 minutes.

Pros:

- Simple.
- Repeatable.
- Low implementation complexity.

Risks:

- Topic boundaries may be cut awkwardly.
- Cross-window commitments or conflicts may be missed.

### Preprocessing Strategy B: Speaker-Turn Windows

Split transcript by a fixed number of utterances or speaker turns.

Pros:

- Predictable token size.
- Preserves conversational exchange structure better than pure time.

Risks:

- Long monologues can dominate a window.
- Topic transitions may still be split.

### Preprocessing Strategy C: Topic Segmentation

Ask a preprocessing pass to identify topic segments with boundaries.

Pros:

- More semantically meaningful.
- Likely better for decisions, risks, and people dynamics.

Risks:

- The segmenter can lose or distort signal.
- Bad segmentation can bias all downstream analysis.

### Preprocessing Strategy D: Evidence Candidate Harvesting

Run a preprocessing pass that extracts candidate evidence only, not final claims.

Pros:

- Keeps downstream target analysis smaller.
- Maintains direct transcript traceability.
- Avoids asking preprocessing to synthesize too much.

Risks:

- The evidence harvester may omit subtle but important signals.
- Different vertical targets may need different evidence types.

## Horizontal Experiment Matrix

Once a vertical target has a best prompt variant, test it against:

| Variant | Input To Target Analyzer | Expected Learning |
| --- | --- | --- |
| H0 | Full transcript | Baseline for that target. |
| H1 | Time-window evidence candidates | Whether simple chunking is enough. |
| H2 | Speaker-turn evidence candidates | Whether conversation-shape chunks help. |
| H3 | Topic segments | Whether semantic segmentation improves target quality. |
| H4 | Target-specific evidence candidates | Whether each vertical target needs its own preprocessing filter. |

Do not compare preprocessing globally. Compare it per vertical target. Action items may benefit from different preprocessing than people dynamics.

## Recommended Experiment Sequence

1. Freeze the current broad full-transcript result as baseline.
2. Implement experiment harness support for named prompt variants and run metadata.
3. Run vertical target V1 against `140341999`.
4. Review outputs manually using the rubric.
5. Add examples or evidence-first prompting only for weak targets.
6. Select the best full-transcript variant per target.
7. Add preprocessing Strategy A or D as the first horizontal experiment.
8. Compare each vertical target against full-transcript and preprocessed inputs.
9. Promote only target/preprocessing combinations that improve evidence accuracy and usefulness.

## Experiment Harness Requirements

The harness should support:

- Fixed recording ID input.
- Named experiment ID.
- Named target.
- Named prompt variant.
- Named preprocessing variant.
- Model provider/name.
- Prompt/schema version.
- Raw model output artifact.
- Normalized output artifact.
- Validation result.
- Manual score fields or a separate score file.

The harness should not replace the production analysis workflow at first. It should be a parallel operator workflow used for learning.

## Data Model Additions For Experiments

The current database can store analysis runs and findings, but experiments would benefit from additional metadata. These can initially be JSON artifacts before becoming durable tables.

Recommended experiment artifact layout:

```text
artifacts/
  fathom/
    recordings/
      {recording_id}/
        experiments/
          {experiment_id}/
            manifest.json
            {target}/
              {variant}/
                prompt.txt
                raw_output.json
                normalized_output.json
                validation.json
                score.json
```

Required manifest fields:

- Recording ID.
- Experiment ID.
- Target.
- Vertical variant.
- Preprocessing variant.
- Model metadata.
- Prompt/schema version.
- Runtime username/context.
- Transcript artifact reference.
- Created timestamp.

## Promotion Criteria

A prompt or preprocessing strategy should be promoted into the main analysis workflow only if:

- It improves evidence completeness without materially reducing evidence accuracy.
- It produces useful findings, not just compliant JSON.
- It avoids unsupported psychological or interpersonal claims.
- It works on at least two different recordings of the relevant type, unless intentionally specialized.
- It preserves traceability to transcript speaker, timestamp, and excerpt.

## Open Questions

- Should experiment scoring live in SQLite, JSON artifacts, or both?
- Should the first experiment harness be a CLI command or a standalone developer script?
- Should examples be hand-authored from real transcripts, synthetic transcripts, or both?
- Should preprocessing be shared across targets or target-specific from the start?
- Should weak local-model targets be allowed to route to a stronger configured model later, or should all targets stay on `gemma4:e2b` until the local approach is exhausted?

