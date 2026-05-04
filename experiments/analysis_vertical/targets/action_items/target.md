# Action Items

## Goal

Extract commitments and follow-up tasks for all participants.

## Best Initial Bet

Make the model classify only explicit or strongly implied commitments. This target should reject vague future possibilities. Owners and due dates should be null unless the transcript supports them.

## Strengths To Look For

- Separates commitments from discussion topics.
- Assigns owners only when supported.
- Leaves due dates null when absent.

## Weaknesses To Watch

- Turns generic next steps into action items.
- Invents owners from context.
- Treats proposals or options as commitments.

