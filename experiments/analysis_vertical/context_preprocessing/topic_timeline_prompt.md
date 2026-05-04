You are reading one short slice of a meeting transcript.

Task:
Return a compact topic timeline entry for this slice.

Rules:
- Do not summarize the whole meeting.
- Distinguish substance from logistics.
- Use at most 3 topic labels.
- If the slice is mostly logistics or small talk, say so.
- Return only JSON.

JSON shape:
{
  "slice_id": "{{ slice_id }}",
  "primary_topic": "short label",
  "secondary_topics": ["short label"],
  "substance_level": "high|medium|low",
  "brief": "one sentence"
}

Transcript slice:
{{ transcript_slice }}

