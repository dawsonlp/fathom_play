You are classifying candidate action-item evidence from a meeting transcript.

Target: action_items_candidate_classification

Task:
Classify each candidate as one of:

- post_meeting_follow_up: someone is committing to do something after the meeting or outside the current in-meeting flow.
- in_meeting_action: someone is doing or about to do something during the meeting, such as screen sharing, presenting, navigating slides, or managing time.
- role_or_ownership_statement: someone describes responsibility, authority, or ownership, but not a specific follow-up task.
- not_action_item: the candidate is not a task or commitment.

Rules:
- Preserve each candidate's original speaker, timestamp, and excerpt.
- Do not add new evidence.
- Do not summarize the meeting.
- Be conservative. If the action happens inside the meeting, classify it as in_meeting_action.
- Only post_meeting_follow_up candidates should be promoted to final action items later.

Return only JSON:

{
  "target": "action_items_candidate_classification",
  "slice_id": "{{ slice_id }}",
  "classifications": [
    {
      "speaker": "speaker name",
      "timestamp": "MM:SS",
      "excerpt": "exact candidate excerpt",
      "candidate_reason": "original candidate reason",
      "classification": "post_meeting_follow_up|in_meeting_action|role_or_ownership_statement|not_action_item",
      "owner": "person name or null",
      "promote_to_action_item": true,
      "classification_reason": "brief reason"
    }
  ]
}

Candidate evidence:
{{ candidate_evidence }}

