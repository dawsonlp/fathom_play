You are analyzing one Fathom meeting transcript.

Target: open_questions_and_risks

Task:
Extract unresolved questions, blockers, risks, assumptions, and dependencies that the participants discussed. Include only items that matter for follow-up.

Small-model instructions:
- Do not invent generic risks.
- Do not call something a blocker unless the transcript supports blocker-level language.
- Use low or medium severity unless the transcript clearly indicates high severity.
- Return at most 6 findings.
- Every finding must cite exact transcript evidence.

Return only JSON matching this shape:

{
  "target": "open_questions_and_risks",
  "summary": "one short paragraph describing unresolved items",
  "confidence": "high|medium|low",
  "findings": [
    {
      "claim": "specific unresolved question, risk, assumption, or dependency",
      "category": "open_question|risk|blocker|assumption|dependency",
      "owner": "person name or null",
      "severity": "high|medium|low|null",
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

