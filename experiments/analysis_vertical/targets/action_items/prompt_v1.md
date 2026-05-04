You are analyzing one Fathom meeting transcript.

Target: action_items

Task:
Extract only concrete commitments or follow-up tasks. A valid action item needs transcript evidence that someone agreed to do something, asked someone to do something, or clearly accepted responsibility.

Small-model instructions:
- Do not list discussion topics.
- Do not list possible future work unless someone committed to it.
- Use null for owner when no owner is stated or strongly implied.
- Use null for dates unless a date or timing is stated.
- Return at most 6 action items.
- Every action item must cite exact transcript evidence.

Return only JSON matching this shape:

{
  "target": "action_items",
  "summary": "one short paragraph describing action-item confidence",
  "confidence": "high|medium|low",
  "findings": [
    {
      "claim": "specific action item",
      "category": "commitment|request|follow_up",
      "owner": "person name or null",
      "due": "date/timing or null",
      "evidence": [
        {
          "speaker": "speaker name",
          "timestamp": "MM:SS",
          "excerpt": "short exact transcript quote"
        }
      ],
      "caveat": "what is uncertain, or empty string"
    }
  ]
}

Transcript:
{{ transcript }}

