You are reading a short slice of a meeting transcript.

Target: significant_ideas_evidence_candidates

Task:
Find exact transcript lines where participants express a significant idea, intention, proposal, principle, design direction, or strategic concern.

This is not action-item extraction. Do not look for tasks. Look for what the group is trying to understand, design, decide, or make possible.

Rules:
- Do not summarize the meeting.
- Do not list generic topics.
- Do not include small talk, logistics, screen sharing, or meeting navigation.
- Include only ideas that seem important to the substance of the meeting.
- If there are no significant ideas in this slice, return an empty evidence array.
- Return at most 4 evidence items.
- Use exact transcript excerpts only.

Positive example:
Transcript line: [12:10] Alice: The important thing is that the system has to preserve customer trust even when we automate the workflow.
Valid evidence item:
{
  "speaker": "Alice",
  "timestamp": "12:10",
  "excerpt": "The important thing is that the system has to preserve customer trust even when we automate the workflow.",
  "idea_type": "principle",
  "why_this_matters": "It states a design principle that should guide later choices."
}

Negative example:
Transcript line: [02:04] Bob: I can see your screen now.
This is not a significant idea because it is meeting logistics.

Return only JSON:

{
  "target": "significant_ideas_evidence_candidates",
  "slice_id": "{{ slice_id }}",
  "evidence": [
    {
      "speaker": "speaker name",
      "timestamp": "MM:SS",
      "excerpt": "short exact transcript quote",
      "idea_type": "intention|proposal|principle|design_direction|strategic_concern|assumption",
      "why_this_matters": "brief reason"
    }
  ]
}

Transcript slice:
{{ transcript_slice }}

