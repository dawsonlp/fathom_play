# Experiment Runbook

Use [README.md](README.md) as the canonical guide. This file is only the short operator checklist.

## Before Running

- Confirm the input transcript or prior run artifact exists under `runs/`.
- Confirm the experiment question changes one main variable.
- Confirm generated outputs will stay under `runs/{recording_id}/{experiment_id}/`.

## Run

Use the runner matching the experiment shape, for example:

```bash
uv run --extra dev python experiments/analysis_vertical/run_action_items_context_classifier.py \
  --recording-id 140341999 \
  --candidate-run action_items-v2-slices-140341999-20260503-022458 \
  --context-run context_pack-v1-140341999-20260503-030135
```

## Review

- Check `summary.json`.
- Check validation fields before judging quality.
- Inspect `reasoning.txt` only for debugging; it is not meeting evidence.
- Write durable observations to `comparisons/` or `reports/`.
- Update `TRACKING.md` with only status and next step.

