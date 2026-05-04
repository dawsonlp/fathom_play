# Conversation Analysis Experiments

## Purpose

This directory is the experimental workbench for learning how to analyze Fathom transcripts reliably before promoting behavior into the production LangGraph workflows.

The experiments are meant to answer three practical questions:

- Which analysis tasks can a small local model perform reliably?
- What preprocessing and validation are required before downstream vertical analyses become useful?
- Which model/provider settings are worth using for each stage, including local Gemma and future cloud models such as Anthropic?

The current evidence shows that `gemma4:e2b` is not reliable when asked to analyze a full transcript broadly. It performs better when the workflow is split into small, validated stages: slice, extract evidence, build compact context, classify or synthesize narrowly, validate, and repair.

## Structure

```text
experiments/analysis_vertical/
  README.md                         # canonical guide
  RUNBOOK.md                        # short command checklist
  TRACKING.md                       # current status and next work
  registry.json                     # target/model registry
  context_preprocessing/            # reusable context-building prompts
  shared/                           # common schemas, rubrics, templates
  targets/                          # target-specific prompt families
  comparisons/                      # reviewed observations from individual runs
  reports/                          # higher-level experiment reports
  runs/                             # generated outputs, gitignored
```

Commit prompts, schemas, rubrics, runners, reports, and reviewed comparison notes. Do not commit generated run artifacts under `runs/` unless there is a deliberate review reason.

## Current Findings

Durable findings are summarized in:

- [action_items_context_pipeline_report_140341999.md](reports/action_items_context_pipeline_report_140341999.md)
- [gemma4_strategy_experiments_140341999.md](reports/gemma4_strategy_experiments_140341999.md)
- [preprocessing_context_strategy.md](comparisons/preprocessing_context_strategy.md)

The short version:

- Full-transcript vertical prompts collapse into generic summaries.
- Slice-level evidence extraction works much better.
- Significant-ideas extraction is the strongest current context-building layer.
- Deterministic or ultra-compact context helps; full context can distract the local model.
- Candidate IDs, coverage validation, and targeted repair are required.
- `reasoning=True` is useful to test, but should not be globally enabled. It adds latency and can reduce coverage in larger prompts.
- Final synthesis must be constrained and validated; free-form synthesis is unreliable.

## Experiment Model

Experiments are organized as pipelines, not one-shot prompts.

Common stages:

1. **Source artifact**: local transcript or prior run output.
2. **Preprocessing**: slices, significant ideas, participant map, topic timeline, mechanics/noise, vocabulary, or uncertainty maps.
3. **Vertical task**: action items, decisions, risks, coaching, people dynamics, working styles, or significant ideas.
4. **Validation**: JSON shape, candidate coverage, evidence presence, IDs, duplicates, and semantic consistency.
5. **Repair**: rerun only invalid or missing pieces.
6. **Synthesis**: produce final meeting-level outputs from filtered evidence only.
7. **Report**: record what changed, what worked, what failed, and the next experiment.

## Local Store Policy

Once a transcript or slice artifact exists locally, experiments should use local artifacts instead of refetching from Fathom. Fathom is the source ingestion boundary, not the repeated experiment boundary.

Generated experiment outputs live under:

```text
experiments/analysis_vertical/runs/{recording_id}/{experiment_id}/
```

These outputs are gitignored. A run should usually write:

- `manifest.json`
- `prompt.txt`
- `raw_output.json` or `output.json`
- `normalized_output.json` when applicable
- `validation.json`
- `summary.json`
- `reasoning.txt` when reasoning is enabled

Reviewed results should be summarized in `comparisons/` or `reports/`.

## Adding A New Experiment

Use this checklist for local Gemma, Anthropic, Bedrock, or any future provider.

1. Define the question.
   - Example: "Does Claude improve final synthesis over filtered evidence?"
   - Example: "Does Gemma reasoning improve classification only for ambiguous candidates?"

2. Pick fixed inputs.
   - Prefer local artifacts from `runs/`.
   - Record source run IDs in the new run manifest.
   - Avoid changing transcript, prompt, model, and context all at once.

3. Create or update the target prompt.
   - Put target prompts under `targets/{target}/`.
   - Put preprocessing prompts under `context_preprocessing/`.
   - Keep prompts narrow and evidence-first.

4. Add a runner.
   - Use a new runner when the experiment introduces a new pipeline shape.
   - Make provider/model settings explicit in `manifest.json`.
   - Save raw output, normalized output, validation, and reasoning traces separately.

5. Include reasoning/provider variants deliberately.
   - Treat reasoning as an experimental factor, not a default.
   - Compare reasoning on/off per stage.
   - For cloud models, compare provider/model value against latency, cost, and quality.

6. Validate before interpreting.
   - Candidate IDs must round-trip.
   - Every candidate should be classified exactly once.
   - Final claims must cite evidence IDs or transcript coordinates.
   - Invalid output is a result, not a failure to hide.

7. Write a comparison or report.
   - Use `comparisons/` for one-run observations.
   - Use `reports/` for cross-run conclusions.
   - Link the run directory and source artifacts.

8. Update `TRACKING.md`.
   - Keep it concise: current status, best run, next step.
   - Do not duplicate full reports there.

## Adding A Cloud Model Experiment

Cloud models should use the same artifact and validation discipline as local models.

Required manifest fields:

```json
{
  "provider": "anthropic|bedrock|ollama",
  "model": "model id",
  "reasoning": "off|on|provider-specific setting",
  "temperature": 0,
  "source_runs": ["..."],
  "uses_fathom_api": false
}
```

Guidelines:

- Never send more transcript than the experiment requires.
- Prefer filtered local evidence and compact context packs.
- Record cost-relevant metadata when available.
- Do not compare cloud output only on prose quality; compare schema validity, evidence traceability, false positives, coverage, latency, and repair rate.
- Keep provider-specific prompting isolated in the runner or model adapter so target prompts remain portable where possible.

## Promotion Criteria

Promote an experimental behavior into production design only when it:

- Works on more than one recording or has a clear reason to be specialized.
- Produces evidence-backed findings.
- Preserves local artifact traceability.
- Fails visibly when output is incomplete.
- Has a documented reasoning/provider setting decision.
- Has tests or validation checks that protect the observed failure modes.

