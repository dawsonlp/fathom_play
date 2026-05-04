You are classifying candidate action-item evidence from a meeting.

Target: action_items_context_classifier

You are given:
1. A compact meeting context pack.
2. Candidate evidence items previously extracted from one transcript slice.

Task:
Classify each candidate. Only promote true post-meeting follow-up tasks.

Coverage rules:
- Preserve each candidate_id exactly.
- Return exactly one classification for every input candidate_id.
- Do not add candidate_ids that were not provided.

Categories:
- post_meeting_follow_up: a task someone should do after the meeting or outside the current presentation/discussion flow.
- in_meeting_action: an action happening now or immediately during the meeting, including screen sharing, testing, presenting, walking through slides, paging/slides, skipping forward, or time management.
- role_or_ownership_statement: a statement about authority, responsibility, ownership, or decision rights, but not a specific task.
- not_action_item: not a task or commitment.

Hard negative rules:
- If the candidate is about screen sharing or testing meeting technology, classify as in_meeting_action.
- If the candidate is about walking through slides, paging slides, skipping forward, or showing material during the meeting, classify as in_meeting_action.
- If the candidate is about a hard stop or time remaining, classify as in_meeting_action or not_action_item.
- If the candidate describes what someone owns generally, classify as role_or_ownership_statement.
- The words "I will", "I'll", or "we'll" are not enough. Use the surrounding meaning.

Promote only if:
- classification is post_meeting_follow_up, and
- the action clearly happens after the meeting or outside the immediate meeting flow.

Return only JSON:

{
  "target": "action_items_context_classifier",
  "slice_id": "{{ slice_id }}",
  "classifications": [
    {
      "candidate_id": "candidate id",
      "speaker": "speaker name",
      "timestamp": "MM:SS",
      "excerpt": "exact candidate excerpt",
      "classification": "post_meeting_follow_up|in_meeting_action|role_or_ownership_statement|not_action_item",
      "owner": "person name or null",
      "promote_to_action_item": false,
      "classification_reason": "brief reason"
    }
  ]
}

Context pack:
{{ context_pack }}

Candidate evidence:
{{ candidate_evidence }}
