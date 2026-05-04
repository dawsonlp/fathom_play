# Context Preprocessing

Prompts in this directory build compact context layers for downstream vertical analyses. See [../README.md](../README.md) for the canonical experiment method.

Current layers:

- `significant_ideas`
- `participant_map`
- `topic_timeline`
- `decision_uncertainty_map`
- `vocabulary_map`
- `meeting_mechanics`

The current finding is that deterministic or ultra-compact context is safer for `gemma4:e2b` than passing a full context pack into every vertical prompt.

