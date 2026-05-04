You are building a compact context pack for downstream meeting analysis.

Task:
Use the supplied preprocessing maps to create a succinct context artifact. This will be passed to a small local model, so be concise and practical.

Rules:
- Do not write a report.
- Do not add facts that are not in the supplied maps.
- Prefer short bullets and compact phrasing.
- Keep the output useful for action-item, decision, risk, coaching, people-dynamics, and working-style analyses.
- Return only JSON.

JSON shape:
{
  "meeting_purpose": "one sentence",
  "core_ideas": ["short idea"],
  "strategic_intentions": ["short intention"],
  "design_principles": ["short principle"],
  "open_tensions": ["short tension or uncertainty"],
  "participant_context": ["short participant/role context"],
  "topic_timeline": ["time window: topic"],
  "domain_vocabulary": ["term: meaning"],
  "meeting_mechanics": ["short logistics/noise note"],
  "downstream_guidance": ["short instruction for future analyses"]
}

Preprocessing maps:
{{ preprocessing_maps }}

