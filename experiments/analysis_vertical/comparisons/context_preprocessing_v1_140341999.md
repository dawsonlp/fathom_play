# Context Preprocessing V1: Recording 140341999

## Run

- Date: 2026-05-03
- Recording ID: `140341999`
- Experiment ID: `context_pack-v1-140341999-20260503-030135`
- Run root: `experiments/analysis_vertical/runs/140341999/context_pack-v1-140341999-20260503-030135/`
- Input significant-ideas run: `significant_ideas-v1-slices-140341999-20260503-023715`
- Model: Ollama `gemma4:e2b`, JSON mode, temperature `0`

## Important Operational Note

Fathom returned `502` during this run. The runner fell back to local transcript slices from the significant-ideas experiment. This is a useful improvement because context experiments can now be repeated without live Fathom access once local transcript slices exist.

## Outputs

- `preprocessing_maps.json`: combined upstream maps.
- `deterministic_context_pack.json`: usable compact context pack assembled by code from the maps.
- `context_pack.json`: model-generated final pack; not reliable in this run.
- `context_pack/output.json`: raw model synthesis output.

## Result

The context preprocessing approach is useful, but the final synthesis should not be trusted to the model yet.

The model-generated `context_pack` failed:

- Wrong shape.
- Fenced JSON array instead of requested object.
- Hallucinated "logistics and supply chains" language not supported by the meeting context.

The deterministic context pack is usable and includes:

- Meeting purpose.
- Core ideas.
- Strategic intentions.
- Design principles.
- Open tensions.
- Participant context.
- Topic timeline.
- Domain vocabulary.
- Meeting mechanics/noise.
- Downstream guidance.

## Strong Signals

- Significant ideas should be built up front.
- Participant map should be deterministic.
- Meeting mechanics should be deterministic or mostly deterministic.
- Topic timeline can be model-assisted and appears useful.
- Final context packaging should be deterministic until the model is more reliable.

## Weak Signals

- Decision/uncertainty map generated malformed/noisy output.
- Vocabulary map generated partially useful but malformed output.
- Model-only final synthesis is unreliable.

## Recommended Next Step

Use `deterministic_context_pack.json` as context for the next downstream vertical experiment.

Best candidate: action-items V4 or decisions V2.

For action items, pass:

- deterministic context pack
- one transcript slice
- V2 evidence candidates for that slice

Then ask for only one narrow operation, such as classifying candidates with stronger temporal rules.

