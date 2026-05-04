"""Run vertical analysis experiments against a Fathom recording.

This is experiment-only tooling. It writes generated outputs under
experiments/analysis_vertical/runs/, which is intentionally gitignored.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from fathom_play import fathom_mapper
from fathom_play.artifacts import render_transcript_markdown
from fathom_play.fathom_client import FathomHttpClient

ROOT = Path(__file__).resolve().parent
RUNS_DIR = ROOT / "runs"
REGISTRY_PATH = ROOT / "registry.json"
SCORING_TEMPLATE_PATH = ROOT / "shared" / "scoring_template.json"


@dataclass(frozen=True)
class TargetRun:
    target: str
    experiment_id: str
    run_dir: Path
    evidence_status: str
    finding_count: int
    complete_finding_count: int
    confidence: str
    summary: str
    warnings: list[str]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run vertical analysis experiment targets.")
    parser.add_argument("--recording-id", type=int, default=140341999)
    parser.add_argument("--username", default="dawsonlp")
    parser.add_argument("--context", default="")
    parser.add_argument("--target", action="append", help="Target ID to run. Defaults to all registry targets.")
    args = parser.parse_args()

    registry = read_json(REGISTRY_PATH)
    targets = registry["targets"]
    if args.target:
        wanted = set(args.target)
        targets = [target for target in targets if target["id"] in wanted]
        missing = wanted - {target["id"] for target in targets}
        if missing:
            raise SystemExit(f"Unknown target(s): {', '.join(sorted(missing))}")

    transcript_text, meeting_metadata = fetch_transcript(args.recording_id)
    model = ChatOllama(model=registry["model"]["name"], format="json", temperature=0)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

    results = []
    for target in targets:
        results.append(
            run_target(
                target=target,
                model=model,
                transcript_text=transcript_text,
                meeting_metadata=meeting_metadata,
                recording_id=args.recording_id,
                username=args.username,
                context=args.context,
                timestamp=timestamp,
            )
        )

    print(json.dumps({"recording_id": args.recording_id, "runs": [summarize_run(item) for item in results]}, indent=2))


def fetch_transcript(recording_id: int) -> tuple[str, dict[str, Any]]:
    with FathomHttpClient() as client:
        meetings_response = client.list_meetings()
        meetings = fathom_mapper.to_meetings(meetings_response.data)
        meeting = next((item for item in meetings if item.recording_id == recording_id), None)
        if meeting is None:
            raise SystemExit(f"Recording {recording_id} was not returned by the visible meetings list")

        transcript_response = client.get_transcript(recording_id)
        transcript = fathom_mapper.to_transcript(transcript_response.data, recording_id)

    return render_transcript_markdown(transcript), {
        "recording_id": meeting.recording_id,
        "title": meeting.title,
        "start_time": meeting.start_time.isoformat(),
        "end_time": meeting.end_time.isoformat(),
        "duration_seconds": meeting.duration_seconds,
        "recorded_by": meeting.recorded_by.name,
        "invitees": [person.name for person in meeting.invitees],
    }


def run_target(
    target: dict[str, Any],
    model: ChatOllama,
    transcript_text: str,
    meeting_metadata: dict[str, Any],
    recording_id: int,
    username: str,
    context: str,
    timestamp: str,
) -> TargetRun:
    target_id = target["id"]
    experiment_id = f"{target_id}-v1-{recording_id}-{timestamp}"
    run_dir = RUNS_DIR / str(recording_id) / experiment_id
    run_dir.mkdir(parents=True, exist_ok=True)

    prompt_template = (ROOT / target["prompt"]).read_text(encoding="utf-8")
    prompt = (
        prompt_template.replace("{{ transcript }}", transcript_text)
        .replace("{{ username }}", username)
        .replace("{{ context }}", context or "(none)")
    )
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    manifest = {
        "experiment_id": experiment_id,
        "recording_id": recording_id,
        "target": target_id,
        "vertical_variant": "v1",
        "preprocessing_variant": "none_full_transcript",
        "prompt_path": target["prompt"],
        "model": {"provider": "ollama", "name": "gemma4:e2b", "format": "json", "temperature": 0},
        "runtime": {"username": username, "context": context},
        "meeting": meeting_metadata,
        "created_at": datetime.now(UTC).isoformat(),
    }
    write_json(run_dir / "manifest.json", manifest)

    response = model.invoke(
        [
            SystemMessage(
                content=(
                    "You analyze meeting transcripts. Return only valid JSON. "
                    "Follow the requested schema exactly and cite exact transcript excerpts."
                )
            ),
            HumanMessage(content=prompt),
        ]
    )
    raw_content = str(response.content)
    raw_payload = parse_model_json(raw_content)
    write_json(run_dir / "raw_output.json", raw_payload)

    normalized = normalize_output(raw_payload, target_id)
    write_json(run_dir / "normalized_output.json", normalized)

    validation = validate_output(normalized)
    write_json(run_dir / "validation.json", validation)

    score = make_initial_score(experiment_id, recording_id, target_id, validation)
    write_json(run_dir / "score.json", score)
    (run_dir / "review.md").write_text(make_review_stub(target_id, validation), encoding="utf-8")

    findings = normalized["findings"]
    complete_finding_count = sum(1 for finding in findings if finding.get("evidence"))
    return TargetRun(
        target=target_id,
        experiment_id=experiment_id,
        run_dir=run_dir,
        evidence_status=validation["evidence_status"],
        finding_count=len(findings),
        complete_finding_count=complete_finding_count,
        confidence=normalized["confidence"],
        summary=normalized["summary"],
        warnings=validation["warnings"],
    )


def parse_model_json(content: str) -> Any:
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

    return {"summary": content, "confidence": "low", "findings": [], "parse_warning": "invalid_json"}


def normalize_output(payload: Any, target_id: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {"summary": str(payload), "confidence": "low", "findings": []}

    confidence = str(payload.get("confidence", "low")).lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"

    findings = payload.get("findings", [])
    if not isinstance(findings, list):
        findings = []

    normalized_findings = []
    for item in findings:
        if isinstance(item, str):
            item = {"claim": item, "category": "", "owner": None, "evidence": []}
        if not isinstance(item, dict):
            continue
        normalized_item = dict(item)
        normalized_item["claim"] = str(item.get("claim") or item.get("summary") or item.get("action") or "")
        normalized_item["category"] = str(item.get("category") or item.get("type") or "")
        normalized_item["owner"] = item.get("owner")
        normalized_item["evidence"] = normalize_evidence(item.get("evidence", []))
        normalized_findings.append(normalized_item)

    return {
        "target": str(payload.get("target") or target_id),
        "summary": str(payload.get("summary", "")),
        "confidence": confidence,
        "findings": normalized_findings,
    }


def normalize_evidence(evidence: Any) -> list[dict[str, str]]:
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


def validate_output(output: dict[str, Any]) -> dict[str, Any]:
    warnings = []
    findings = output.get("findings", [])
    if not findings:
        warnings.append("no findings returned")

    missing_evidence = [index for index, finding in enumerate(findings) if not finding.get("evidence")]
    if missing_evidence:
        warnings.append(f"findings missing evidence: {missing_evidence}")

    empty_claims = [index for index, finding in enumerate(findings) if not finding.get("claim")]
    if empty_claims:
        warnings.append(f"findings missing claims: {empty_claims}")

    return {
        "valid_json": True,
        "valid_common_shape": output.get("target") and isinstance(findings, list),
        "finding_count": len(findings),
        "complete_evidence_count": len(findings) - len(missing_evidence),
        "evidence_status": "complete" if findings and not missing_evidence else "incomplete",
        "warnings": warnings,
    }


def make_initial_score(experiment_id: str, recording_id: int, target: str, validation: dict[str, Any]) -> dict[str, Any]:
    score = read_json(SCORING_TEMPLATE_PATH)
    score["experiment_id"] = experiment_id
    score["recording_id"] = recording_id
    score["target"] = target
    score["scores"]["valid_schema"] = 2 if validation["valid_common_shape"] else 0
    score["scores"]["evidence_completeness"] = 3 if validation["evidence_status"] == "complete" else 0
    score["total"] = sum(score["scores"].values())
    score["reviewer_notes"] = "Initial automated score only. Evidence accuracy and usefulness require manual review."
    score["weaknesses"] = validation["warnings"]
    return score


def make_review_stub(target: str, validation: dict[str, Any]) -> str:
    return (
        f"# Review: {target}\n\n"
        "## Automated Validation\n\n"
        f"- Evidence status: `{validation['evidence_status']}`\n"
        f"- Finding count: `{validation['finding_count']}`\n"
        f"- Complete evidence count: `{validation['complete_evidence_count']}`\n"
        f"- Warnings: `{', '.join(validation['warnings']) or 'none'}`\n\n"
        "## Manual Review\n\n"
        "- Evidence accuracy:\n"
        "- Claim usefulness:\n"
        "- False positives:\n"
        "- Missing obvious items:\n"
        "- Next tuning step:\n"
    )


def summarize_run(run: TargetRun) -> dict[str, Any]:
    data = asdict(run)
    data["run_dir"] = str(run.run_dir)
    return data


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
