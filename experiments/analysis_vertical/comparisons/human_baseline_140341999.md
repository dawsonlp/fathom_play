# Human Comparison Baseline: Recording 140341999

## Meeting

- Recording ID: `140341999`
- Title: `Regroup - Larry / Matt / Brian / Jake`
- Time: `2026-04-22T22:17:45+00:00`
- Duration: about 44 minutes

## Prior Local-Model Behavior

Broad full-transcript analysis with `gemma4:e2b` produced plausible but weak summaries. After stricter schema validation and Ollama JSON mode, the model still returned summary-only outputs for all broad perspectives. The system correctly marked those outputs as incomplete because they lacked evidence-backed findings.

## Human Comparison Point

This meeting appears to be a strategic regroup or planning discussion. The model consistently described it as involving roadmap, phases, data/system architecture, integration, resources, scope, and planning. Those themes may be directionally right, but they must be verified against transcript excerpts before being accepted as findings.

## Expected Improvement From Vertical Experiments

For this recording, a useful vertical target run should produce a small number of claims with exact evidence. It is better to return two supported findings than six plausible unsupported ones.

## Known Weakness To Watch

The local model tends to collapse every target into the same generic project-roadmap summary. A successful target prompt should prevent that by making the requested output narrow and evidence-first.

