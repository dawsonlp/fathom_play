You are reading evidence candidates extracted from a meeting.

Task:
Identify decisions, proposals, uncertainties, risks, assumptions, and open questions represented in this evidence.

Rules:
- Do not invent items.
- Preserve supporting evidence timestamps.
- Prefer "proposal" or "open_question" when not clearly settled.
- Return at most 8 items.
- Return only JSON.

JSON shape:
{
  "items": [
    {
      "claim": "succinct statement",
      "status": "decision|proposal|open_question|risk|assumption|unclear",
      "supporting_timestamps": ["MM:SS"],
      "caveat": "short caveat"
    }
  ]
}

Evidence candidates:
{{ evidence_candidates }}

