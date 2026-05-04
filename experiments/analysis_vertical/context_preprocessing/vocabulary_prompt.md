You are reading evidence candidates extracted from a meeting.

Task:
Extract domain vocabulary, project terms, entities, and important phrases that downstream analysis should understand.

Rules:
- Do not include ordinary business words unless they have specific meaning in this meeting.
- Include a short meaning inferred only from evidence.
- Preserve supporting timestamps.
- Return at most 12 terms.
- Return only JSON.

JSON shape:
{
  "terms": [
    {
      "term": "term or phrase",
      "meaning": "short inferred meaning",
      "category": "domain|project|technical|business|entity",
      "supporting_timestamps": ["MM:SS"]
    }
  ]
}

Evidence candidates:
{{ evidence_candidates }}

