from dataclasses import dataclass

from fathom_play.analysis_enricher import AnalysisEnricher, RuntimeContext
from fathom_play.domain import Person, Transcript, Utterance


@dataclass(frozen=True)
class FakeResponse:
    content: str


class FakeModel:
    def __init__(self, content: str):
        self.content = content

    def invoke(self, _messages):
        return FakeResponse(self.content)


def _transcript() -> Transcript:
    return Transcript(
        recording_id=1,
        utterances=[Utterance(Person("Alice"), "I will send the plan tomorrow.", 1000)],
    )


def test_analysis_enricher_parses_fenced_json_and_keeps_complete_evidence():
    content = """
```json
{
  "summary": "Alice owns the next planning step.",
  "confidence": "high",
  "findings": [
    {
      "claim": "Alice will send the plan.",
      "category": "action_item",
      "owner": "Alice",
      "evidence": [
        {"speaker": "Alice", "timestamp": "00:01", "excerpt": "I will send the plan tomorrow."}
      ]
    }
  ]
}
```
"""

    payload = AnalysisEnricher(FakeModel(content))._run_json(
        "all-participant action item extraction", "", runtime=RuntimeContext("Alice")
    )

    assert payload["confidence"] == "high"
    assert payload["evidence_status"] == "complete"
    assert payload["findings"][0]["evidence"][0]["speaker"] == "Alice"


def test_analysis_enricher_marks_missing_evidence_incomplete():
    content = '{"summary": "A plan exists.", "confidence": "high", "findings": [{"claim": "There is a plan."}]}'

    outputs = AnalysisEnricher(FakeModel(content)).analyze(_transcript(), RuntimeContext("Alice"))

    payload = outputs[0].payload
    assert payload["confidence"] == "low"
    assert payload["evidence_status"] == "incomplete"
    assert "one or more findings are missing transcript evidence" in payload["schema_warnings"]
