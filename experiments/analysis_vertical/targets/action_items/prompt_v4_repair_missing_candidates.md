You are repairing an incomplete action-item classification run.

Target: action_items_context_classifier_repair

You are given:
1. A compact meeting context pack.
2. Existing classifications for one slice.
3. Candidate evidence items that were missed.

Task:
Classify only the missing candidates. Do not reclassify existing candidates.

Categories:
- post_meeting_follow_up: a task someone should do after the meeting or outside the current presentation/discussion flow.
- in_meeting_action: an action happening now or immediately during the meeting, including screen sharing, testing, presenting, walking through slides, paging/slides, skipping forward, or time management.
- role_or_ownership_statement: a statement about authority, responsibility, ownership, or decision rights, but not a specific task.
- not_action_item: not a task or commitment.

Coverage rules:
- Preserve each candidate_id exactly.
- Return exactly one classification for every missing candidate_id.
- Do not return classifications for existing candidates.
- Do not add candidate_ids that were not provided.

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
  "target": "action_items_context_classifier_repair",
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

Existing classifications:
{{ existing_classifications }}

Missing candidate evidence:
{{ missing_candidate_evidence }}

