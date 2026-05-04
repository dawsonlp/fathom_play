You are analyzing one Fathom meeting transcript.

Target: coaching_review

Runtime user: {{ username }}
Optional context: {{ context }}

Task:
Assess how the runtime user conducted the meeting. Focus on observable facilitation behaviors: framing, listening, summarizing, clarifying, interrupting, drawing people in, managing decisions, and closing next steps.

Small-model instructions:
- Do not coach the project plan. Coach the meeting conduct.
- Do not infer motives or personality.
- If you cannot tell which transcript speaker is the runtime user, say so in the summary and return low confidence.
- Return at most 5 coaching observations.
- Every observation must cite exact transcript evidence.
- Use careful language such as "appears", "suggests", or "in this moment" when appropriate.

Return only JSON matching this shape:

{
  "target": "coaching_review",
  "summary": "one short paragraph",
  "confidence": "high|medium|low",
  "findings": [
    {
      "claim": "specific coaching observation",
      "category": "strength|improvement_opportunity|follow_up_behavior|unclear_identity",
      "owner": "{{ username }}",
      "suggested_next_behavior": "specific behavior or null",
      "evidence": [
        {
          "speaker": "speaker name",
          "timestamp": "MM:SS",
          "excerpt": "short exact transcript quote"
        }
      ],
      "caveat": "carefulness qualifier"
    }
  ]
}

Transcript:
{{ transcript }}

