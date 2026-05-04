# Preprocessing Context Strategy

## What We Have Learned

The first broad full-transcript vertical experiment failed. `gemma4:e2b` returned valid JSON shape, but every vertical collapsed into nearly the same generic meeting summary and returned zero evidence-backed findings.

The action-items evidence-candidate experiment showed that the model can follow a narrow extraction task when the transcript is sliced into small windows. It returned exact speaker, timestamp, and excerpt fields. However, it over-included immediate in-meeting actions as action items.

The action-items classifier experiment showed that a second model pass over smaller evidence candidates can preserve structure, but the model still struggled with a subtle distinction: post-meeting follow-up versus immediate in-meeting action.

The significant-ideas experiment was the strongest result so far. It extracted useful evidence candidates from the substantive parts of the meeting and ignored early logistics in some slices. That suggests upstream context-building is a better fit for this local model than asking each vertical to rediscover meeting substance from the full transcript.

## New Working Model

Downstream vertical analyses should not begin with the full transcript alone. They should receive a succinct context pack built from several preprocessing perspectives:

- Significant ideas and intentions.
- Participant map.
- Topic timeline.
- Decision and uncertainty map.
- Vocabulary/domain map.
- Meeting mechanics/noise map.

These context layers should be lossy but traceable. They are allowed to compress the meeting, but any substantive statement should remain linked to transcript evidence or source timestamps.

## Why This Helps A Small Local Model

The local model appears to lose task instructions when the input is large and the requested analysis is broad. Preprocessing reduces cognitive load:

- Slices keep individual extraction tasks small.
- Context maps orient downstream prompts.
- Meeting mechanics can filter logistics and presentation flow.
- Significant ideas tell downstream analyses what the conversation is about.
- Topic timeline lets downstream analysis know where a local slice fits.

## Next Experiment

Build a `context_pack_v1` artifact for recording `140341999`.

The context pack should be compact enough to include in future vertical prompts. It should not try to be a final report. It should help another prompt understand the meeting quickly and avoid confusing logistics with substance.

