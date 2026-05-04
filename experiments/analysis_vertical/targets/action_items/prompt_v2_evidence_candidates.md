You are reading a short slice of a meeting transcript.

Target: action_items_evidence_candidates

Task:
Find exact transcript lines where someone commits to doing something, asks someone else to do something, or clearly accepts responsibility for a follow-up.

Rules:
- Do not summarize the meeting.
- Do not describe project themes.
- Do not infer tasks from topics.
- Do not include vague possibilities like "we could", "we might", or general planning discussion.
- If there are no commitments in this slice, return an empty evidence array.
- Return at most 3 evidence items.
- Use exact transcript excerpts only.

Positive example:
Transcript line: [03:12] Alice: I will send the updated plan tomorrow.
Valid evidence item:
{
  "speaker": "Alice",
  "timestamp": "03:12",
  "excerpt": "I will send the updated plan tomorrow.",
  "why_this_is_a_commitment": "Alice explicitly says she will send the plan."
}

Negative example:
Transcript line: [04:08] Bob: We should probably think about the rollout.
This is not an action item because nobody accepts responsibility.

Return only JSON:

{
  "target": "action_items_evidence_candidates",
  "slice_id": "{{ slice_id }}",
  "evidence": [
    {
      "speaker": "speaker name",
      "timestamp": "MM:SS",
      "excerpt": "short exact transcript quote",
      "why_this_is_a_commitment": "brief reason"
    }
  ]
}

Transcript slice:
{{ transcript_slice }}

