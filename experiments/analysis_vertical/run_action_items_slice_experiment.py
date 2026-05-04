"""Run action-item evidence extraction over short transcript slices."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from fathom_play import fathom_mapper
from fathom_play.domain import Transcript, Utterance
from fathom_play.fathom_client import FathomHttpClient

ROOT = Path(__file__).resolve().parent
RUNS_DIR = ROOT / "runs"
PROMPT_PATH = ROOT / "targets" / "action_items" / "prompt_v2_evidence_candidates.md"


@dataclass(frozen=True)
class TranscriptSlice:
    slice_id: str
    start_seconds: int
    end_seconds: int
    utterances: list[Utterance]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run sliced action-item evidence experiment.")
    parser.add_argument("--recording-id", type=int, default=140341999)
    parser.add_argument("--window-minutes", type=int, default=5)
    parser.add_argument("--max-slices", type=int, default=0, help="0 means all slices")
    args = parser.parse_args()

    transcript, meeting_metadata = fetch_transcript(args.recording_id)
    slices = make_slices(transcript, args.window_minutes)
    if args.max_slices:
        slices = slices[: args.max_slices]

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    experiment_id = f"action_items-v2-slices-{args.recording_id}-{timestamp}"
    run_dir = RUNS_DIR / str(args.recording_id) / experiment_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "experiment_id": experiment_id,
        "recording_id": args.recording_id,
        "target": "action_items",
        "vertical_variant": "v2_evidence_candidates",
        "preprocessing_variant": f"{args.window_minutes}_minute_time_windows",
        "prompt_path": str(PROMPT_PATH.relative_to(ROOT)),
        "model": {"provider": "ollama", "name": "gemma4:e2b", "format": "json", "temperature": 0},
        "meeting": meeting_metadata,
        "slice_count": len(slices),
        "created_at": datetime.now(UTC).isoformat(),
    }
    write_json(run_dir / "manifest.json", manifest)

    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    model = ChatOllama(model="gemma4:e2b", format="json", temperature=0)
    summaries = []
    for transcript_slice in slices:
        slice_dir = run_dir / transcript_slice.slice_id
        slice_dir.mkdir(parents=True, exist_ok=True)
        transcript_slice_text = render_slice(transcript_slice)
        prompt = (
            prompt_template.replace("{{ slice_id }}", transcript_slice.slice_id).replace(
                "{{ transcript_slice }}", transcript_slice_text
            )
        )
        (slice_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        (slice_dir / "transcript_slice.md").write_text(transcript_slice_text, encoding="utf-8")

        response = model.invoke(
            [
                SystemMessage(
                    content=(
                        "You extract action-item evidence from short transcript slices. "
                        "Return only valid JSON in the requested shape."
                    )
                ),
                HumanMessage(content=prompt),
            ]
        )
        raw_content = str(response.content)
        raw_output = parse_model_json(raw_content)
        normalized = normalize_output(raw_output, transcript_slice.slice_id)
        validation = validate_output(normalized)

        write_json(slice_dir / "raw_output.json", raw_output)
        write_json(slice_dir / "normalized_output.json", normalized)
        write_json(slice_dir / "validation.json", validation)

        summaries.append(
            {
                "slice_id": transcript_slice.slice_id,
                "start": seconds_to_timestamp(transcript_slice.start_seconds),
                "end": seconds_to_timestamp(transcript_slice.end_seconds),
                "utterance_count": len(transcript_slice.utterances),
                "evidence_count": len(normalized["evidence"]),
                "valid_shape": validation["valid_shape"],
                "warnings": validation["warnings"],
                "evidence": normalized["evidence"],
            }
        )

    summary = {"experiment_id": experiment_id, "run_dir": str(run_dir), "slices": summaries}
    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def fetch_transcript(recording_id: int) -> tuple[Transcript, dict[str, Any]]:
    with FathomHttpClient() as client:
        meetings_response = client.list_meetings()
        meetings = fathom_mapper.to_meetings(meetings_response.data)
        meeting = next((item for item in meetings if item.recording_id == recording_id), None)
        if meeting is None:
            raise SystemExit(f"Recording {recording_id} was not returned by the visible meetings list")

        transcript_response = client.get_transcript(recording_id)
        transcript = fathom_mapper.to_transcript(transcript_response.data, recording_id)

    return transcript, {
        "recording_id": meeting.recording_id,
        "title": meeting.title,
        "start_time": meeting.start_time.isoformat(),
        "end_time": meeting.end_time.isoformat(),
        "duration_seconds": meeting.duration_seconds,
        "recorded_by": meeting.recorded_by.name,
        "invitees": [person.name for person in meeting.invitees],
    }


def make_slices(transcript: Transcript, window_minutes: int) -> list[TranscriptSlice]:
    window_seconds = window_minutes * 60
    if not transcript.utterances:
        return []

    max_seconds = max(utterance.offset_ms // 1000 for utterance in transcript.utterances)
    slices = []
    start = 0
    index = 1
    while start <= max_seconds:
        end = start + window_seconds
        utterances = [
            utterance for utterance in transcript.utterances if start <= utterance.offset_ms // 1000 < end
        ]
        if utterances:
            slices.append(
                TranscriptSlice(
                    slice_id=f"slice_{index:02d}_{seconds_to_timestamp(start)}_{seconds_to_timestamp(end)}",
                    start_seconds=start,
                    end_seconds=end,
                    utterances=utterances,
                )
            )
            index += 1
        start = end
    return slices


def render_slice(transcript_slice: TranscriptSlice) -> str:
    lines = [
        f"# {transcript_slice.slice_id}",
        f"Window: {seconds_to_timestamp(transcript_slice.start_seconds)}-{seconds_to_timestamp(transcript_slice.end_seconds)}",
        "",
    ]
    for utterance in transcript_slice.utterances:
        timestamp = seconds_to_timestamp(utterance.offset_ms // 1000)
        speaker = utterance.speaker.name or "Unknown"
        lines.append(f"- [{timestamp}] {speaker}: {utterance.text}")
    lines.append("")
    return "\n".join(lines)


def parse_model_json(content: str) -> Any:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {"target": "action_items_evidence_candidates", "evidence": [], "parse_warning": "invalid_json"}


def normalize_output(payload: Any, slice_id: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {"target": "action_items_evidence_candidates", "slice_id": slice_id, "evidence": []}
    evidence = payload.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = []
    return {
        "target": str(payload.get("target") or "action_items_evidence_candidates"),
        "slice_id": str(payload.get("slice_id") or slice_id),
        "evidence": [item for item in (normalize_evidence(item) for item in evidence) if item],
    }


def normalize_evidence(item: Any) -> dict[str, str] | None:
    if not isinstance(item, dict):
        return None
    speaker = str(item.get("speaker", "")).strip()
    timestamp = str(item.get("timestamp", "")).strip()
    excerpt = str(item.get("excerpt", "")).strip()
    why = str(item.get("why_this_is_a_commitment", "")).strip()
    if not speaker or not timestamp or not excerpt:
        return None
    return {
        "speaker": speaker,
        "timestamp": timestamp,
        "excerpt": excerpt,
        "why_this_is_a_commitment": why,
    }


def validate_output(output: dict[str, Any]) -> dict[str, Any]:
    warnings = []
    if output["target"] != "action_items_evidence_candidates":
        warnings.append("unexpected target")
    if not isinstance(output["evidence"], list):
        warnings.append("evidence is not a list")
    if len(output["evidence"]) > 3:
        warnings.append("more than 3 evidence items returned")
    return {"valid_shape": not warnings, "warnings": warnings}


def seconds_to_timestamp(total_seconds: int) -> str:
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
