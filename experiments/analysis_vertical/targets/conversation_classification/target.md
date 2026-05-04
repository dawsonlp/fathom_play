# Conversation Classification

## Goal

Identify the conversation type and the strongest themes using transcript evidence.

## Best Initial Bet

Ask the model to first select only transcript excerpts that reveal purpose, then classify from those excerpts. This target is likely one of the easier jobs for `gemma4:e2b`, but it may still overfit to the meeting title or produce generic project-planning language.

## Strengths To Look For

- Uses evidence from multiple parts of the meeting.
- Keeps classification broad when evidence is broad.
- Distinguishes meeting purpose from topic content.

## Weaknesses To Watch

- Infers too much from the title.
- Produces generic labels like `strategic discussion` without useful evidence.
- Uses themes that sound plausible but are not traceable to transcript excerpts.

