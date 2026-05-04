You are analyzing one Fathom meeting transcript.

Target: conversation_classification

Task:
Classify what kind of conversation this was and identify the strongest themes. Use only transcript evidence. Do not infer from the meeting title unless transcript evidence supports the same conclusion.

Small-model instructions:
- First find evidence excerpts that reveal the purpose of the conversation.
- Then create at most 4 findings.
- Each finding must have at least 1 exact transcript excerpt.
- If you cannot find evidence for a classification, return an empty findings array and explain that in the summary.
- Keep claims broad and careful.

Return only JSON matching this shape:

{
  "target": "conversation_classification",
  "summary": "one short paragraph",
  "confidence": "high|medium|low",
  "findings": [
    {
      "claim": "This was primarily a ... conversation.",
      "category": "primary_type|secondary_theme",
      "owner": null,
      "evidence": [
        {
          "speaker": "speaker name",
          "timestamp": "MM:SS",
          "excerpt": "short exact transcript quote"
        }
      ],
      "caveat": "why this claim should be treated carefully"
    }
  ]
}

Transcript:
{{ transcript }}

