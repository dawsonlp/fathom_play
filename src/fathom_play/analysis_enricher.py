"""Evidence-grounded transcript analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from fathom_play.artifacts import render_transcript_markdown
from fathom_play.domain import Transcript

ANALYSIS_VERSION = "conversation-agent-v1"
ANALYSIS_SCHEMA_VERSION = "evidence-grounded-v1"

PERSPECTIVE_INSTRUCTIONS = {
    "conversation classification": (
        "Classify the meeting type and list the strongest observed themes. "
        "Every finding must cite transcript evidence."
    ),
    "all-participant action item extraction": (
        "Extract action items, owners when stated or strongly implied, and due dates only when stated. "
        "If owner or due date is not stated, use null. Every action item must cite the utterance that supports it."
    ),
    "meeting coaching review": (
        "Evaluate how the named user conducted the meeting. Use careful coaching language and cite specific moments."
    ),
    "people dynamics review": (
        "Identify problems, conflicts, collaboration patterns, and information about approaches or personalities. "
        "Avoid diagnosis or overclaiming. Every finding must cite transcript evidence."
    ),
}


@dataclass(frozen=True)
class RuntimeContext:
    username: str
    context: str = ""


@dataclass(frozen=True)
class AnalysisOutput:
    name: str
    payload: dict[str, Any]


class AnalysisEnricher:
    """Runs required analysis perspectives over a transcript."""

    def __init__(self, model: BaseChatModel):
        self.model = model

    def analyze(self, transcript: Transcript, runtime: RuntimeContext) -> list[AnalysisOutput]:
        transcript_text = render_transcript_markdown(transcript)
        return [
            AnalysisOutput("conversation_type", self._run_json("conversation classification", transcript_text, runtime)),
            AnalysisOutput("action_items", self._run_json("all-participant action item extraction", transcript_text, runtime)),
            AnalysisOutput("coaching", self._run_json("meeting coaching review", transcript_text, runtime)),
            AnalysisOutput("people_dynamics", self._run_json("people dynamics review", transcript_text, runtime)),
        ]

    def _run_json(self, perspective: str, transcript_text: str, runtime: RuntimeContext) -> dict[str, Any]:
        messages = [
            SystemMessage(
                content=(
                    "You analyze meeting transcripts. Return only valid JSON. "
                    "Use careful evidence-grounded language. Include evidence arrays with "
                    "speaker, timestamp, and excerpt when making meaningful claims."
                )
            ),
            HumanMessage(
                content=(
                    f"Perspective: {perspective}\n"
                    f"Specific instruction: {PERSPECTIVE_INSTRUCTIONS[perspective]}\n"
                    f"User for coaching analysis: {runtime.username}\n"
                    f"Optional context: {runtime.context or '(none)'}\n\n"
                    f"Transcript:\n{transcript_text}\n\n"
                    "Return only a JSON object, with no Markdown fences. Use this exact shape:\n"
                    "{\n"
                    '  "summary": "one careful paragraph",\n'
                    '  "confidence": "high|medium|low",\n'
                    '  "findings": [\n'
                    "    {\n"
                    '      "claim": "specific claim or action item",\n'
                    '      "category": "short category",\n'
                    '      "owner": "person name or null",\n'
                    '      "evidence": [\n'
                    '        {"speaker": "speaker name", "timestamp": "MM:SS", "excerpt": "short exact transcript quote"}\n'
                    "      ]\n"
                    "    }\n"
                    "  ]\n"
                    "}\n"
                    "Do not include claims that cannot be tied to evidence. "
                    "Keep excerpts short and exact."
                )
            ),
        ]
        response = self.model.invoke(messages)
        content = str(response.content)
        parsed = self._parse_json(content)
        return self._normalize_payload(parsed)

    def _parse_json(self, content: str) -> Any:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            try:
                return json.loads("\n".join(lines))
            except json.JSONDecodeError:
                pass

        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                pass

        return {
            "summary": content,
            "findings": [],
            "evidence": [],
            "confidence": "low",
            "parse_warning": "Model did not return valid JSON",
        }

    def _normalize_payload(self, parsed: Any) -> dict[str, Any]:
        if not isinstance(parsed, dict):
            parsed = {"summary": str(parsed), "findings": [], "confidence": "low"}

        findings = self._normalize_findings(parsed.get("findings", []))
        warnings = list(parsed.get("schema_warnings", []))
        if not isinstance(parsed.get("findings", []), list):
            warnings.append("findings must be a list")

        evidence_complete = bool(findings) and all(finding["evidence"] for finding in findings)
        if not evidence_complete:
            warnings.append("one or more findings are missing transcript evidence")

        confidence = str(parsed.get("confidence", "low")).lower()
        if confidence not in {"high", "medium", "low"}:
            warnings.append("confidence must be high, medium, or low")
            confidence = "low"
        if not evidence_complete:
            confidence = "low"

        normalized = dict(parsed)
        normalized["schema_version"] = ANALYSIS_SCHEMA_VERSION
        normalized["summary"] = str(parsed.get("summary", ""))
        normalized["confidence"] = confidence
        normalized["findings"] = findings
        normalized["evidence_status"] = "complete" if evidence_complete else "incomplete"
        if warnings:
            normalized["schema_warnings"] = warnings
        return normalized

    def _normalize_findings(self, findings: Any) -> list[dict[str, Any]]:
        if not isinstance(findings, list):
            return []

        normalized = []
        for item in findings:
            if isinstance(item, str):
                item = {"claim": item, "category": "", "owner": None, "evidence": []}
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "claim": str(item.get("claim") or item.get("summary") or item.get("action") or ""),
                    "category": str(item.get("category") or item.get("type") or ""),
                    "owner": item.get("owner"),
                    "evidence": self._normalize_evidence(item.get("evidence", [])),
                }
            )
        return normalized

    def _normalize_evidence(self, evidence: Any) -> list[dict[str, str]]:
        if not isinstance(evidence, list):
            return []

        normalized = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            speaker = str(item.get("speaker", "")).strip()
            timestamp = str(item.get("timestamp", "")).strip()
            excerpt = str(item.get("excerpt", "")).strip()
            if speaker and timestamp and excerpt:
                normalized.append({"speaker": speaker, "timestamp": timestamp, "excerpt": excerpt})
        return normalized
