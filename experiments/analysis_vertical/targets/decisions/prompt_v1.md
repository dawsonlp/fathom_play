You are analyzing one Fathom meeting transcript.

Target: decisions

Task:
Extract decisions made, confirmed, or explicitly deferred. A decision requires evidence that participants selected, accepted, confirmed, rejected, or deferred a course of action.

Small-model instructions:
- Do not report proposals as decisions.
- Do not report a topic as a decision.
- Include caveats when the decision depends on conditions.
- Return at most 5 decisions.
- Every decision must cite exact transcript evidence.

Return only JSON matching this shape:

{
  "target": "decisions",
  "summary": "one short paragraph describing whether clear decisions were present",
  "confidence": "high|medium|low",
  "findings": [
    {
      "claim": "specific decision or explicit deferral",
      "category": "decision|confirmed_decision|deferred_decision|rejected_option",
      "owner": "person or group responsible, or null",
      "evidence": [
        {
          "speaker": "speaker name",
          "timestamp": "MM:SS",
          "excerpt": "short exact transcript quote"
        }
      ],
      "caveat": "conditions, uncertainty, or empty string"
    }
  ]
}

Transcript:
{{ transcript }}

