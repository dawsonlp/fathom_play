"""Build compact preprocessing context maps for downstream vertical analyses."""

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
PROMPT_DIR = ROOT / "context_preprocessing"


@dataclass(frozen=True)
class TranscriptSlice:
    slice_id: str
    start_seconds: int
    end_seconds: int
    utterances: list[Utterance]
    text: str = ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build preprocessing context pack.")
    parser.add_argument("--recording-id", type=int, default=140341999)
    parser.add_argument("--significant-ideas-run", required=True)
    parser.add_argument("--window-minutes", type=int, default=5)
    args = parser.parse_args()

    significant_ideas = load_significant_ideas(args.recording_id, args.significant_ideas_run)
    try:
        transcript, meeting = fetch_transcript(args.recording_id)
        slices = make_slices(transcript, args.window_minutes)
        participant_map = build_participant_map(transcript, meeting)
        meeting_mechanics = build_meeting_mechanics(transcript)
    except Exception as exc:
        meeting, slices, participant_map, meeting_mechanics = load_local_context(args.recording_id, args.significant_ideas_run)
        print(f"Using local transcript slices because live Fathom fetch failed: {exc}")
    model = ChatOllama(model="gemma4:e2b", format="json", temperature=0)

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    experiment_id = f"context_pack-v1-{args.recording_id}-{timestamp}"
    run_dir = RUNS_DIR / str(args.recording_id) / experiment_id
    run_dir.mkdir(parents=True, exist_ok=True)

    maps: dict[str, Any] = {
        "meeting": meeting,
        "significant_ideas": significant_ideas,
        "participant_map": participant_map,
        "meeting_mechanics": meeting_mechanics,
    }
    maps["topic_timeline"] = build_topic_timeline(model, slices, run_dir)
    compact_evidence = compact_idea_evidence(significant_ideas)
    maps["decision_uncertainty_map"] = run_prompt(
        model,
        PROMPT_DIR / "decision_uncertainty_prompt.md",
        {"{{ evidence_candidates }}": json.dumps(compact_evidence, indent=2, ensure_ascii=False)},
        run_dir / "decision_uncertainty_map",
    )
    maps["vocabulary_map"] = run_prompt(
        model,
        PROMPT_DIR / "vocabulary_prompt.md",
        {"{{ evidence_candidates }}": json.dumps(compact_evidence, indent=2, ensure_ascii=False)},
        run_dir / "vocabulary_map",
    )

    write_json(run_dir / "preprocessing_maps.json", maps)
    deterministic_context_pack = build_deterministic_context_pack(maps)
    write_json(run_dir / "deterministic_context_pack.json", deterministic_context_pack)
    context_pack = run_prompt(
        model,
        PROMPT_DIR / "context_pack_prompt.md",
        {"{{ preprocessing_maps }}": json.dumps(compact_maps_for_synthesis(maps), indent=2, ensure_ascii=False)},
        run_dir / "context_pack",
    )
    write_json(run_dir / "context_pack.json", context_pack)
    write_json(
        run_dir / "manifest.json",
        {
            "experiment_id": experiment_id,
            "recording_id": args.recording_id,
            "target": "context_preprocessing",
            "variant": "context_pack_v1",
            "significant_ideas_run": args.significant_ideas_run,
            "model": {"provider": "ollama", "name": "gemma4:e2b", "format": "json", "temperature": 0},
            "created_at": datetime.now(UTC).isoformat(),
        },
    )
    print(
        json.dumps(
            {
                "experiment_id": experiment_id,
                "run_dir": str(run_dir),
                "deterministic_context_pack": deterministic_context_pack,
                "model_context_pack": context_pack,
            },
            indent=2,
        )
    )


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


def load_significant_ideas(recording_id: int, run_id: str) -> dict[str, Any]:
    return read_json(RUNS_DIR / str(recording_id) / run_id / "summary.json")


def load_local_context(
    recording_id: int, significant_ideas_run: str
) -> tuple[dict[str, Any], list[TranscriptSlice], dict[str, Any], list[dict[str, str]]]:
    run_dir = RUNS_DIR / str(recording_id) / significant_ideas_run
    manifest = read_json(run_dir / "manifest.json")
    meeting = manifest["meeting"]
    slices = []
    for item in read_json(run_dir / "summary.json").get("slices", []):
        slice_path = run_dir / item["slice_id"] / "transcript_slice.md"
        if not slice_path.exists():
            continue
        slices.append(
            TranscriptSlice(
                slice_id=item["slice_id"],
                start_seconds=timestamp_to_seconds(item["start"]),
                end_seconds=timestamp_to_seconds(item["end"]),
                utterances=[],
                text=slice_path.read_text(encoding="utf-8"),
            )
        )
    return meeting, slices, build_participant_map_from_text(slices, meeting), build_meeting_mechanics_from_text(slices)


def build_participant_map(transcript: Transcript, meeting: dict[str, Any]) -> dict[str, Any]:
    speakers: dict[str, dict[str, Any]] = {}
    for utterance in transcript.utterances:
        name = utterance.speaker.name or "Unknown"
        item = speakers.setdefault(name, {"speaker": name, "utterance_count": 0, "first_timestamp": ""})
        item["utterance_count"] += 1
        if not item["first_timestamp"]:
            item["first_timestamp"] = seconds_to_timestamp(utterance.offset_ms // 1000)
    return {
        "recorded_by": meeting["recorded_by"],
        "invitees": meeting["invitees"],
        "speakers": sorted(speakers.values(), key=lambda item: item["utterance_count"], reverse=True),
    }


def build_participant_map_from_text(slices: list[TranscriptSlice], meeting: dict[str, Any]) -> dict[str, Any]:
    speakers: dict[str, dict[str, Any]] = {}
    for transcript_slice in slices:
        for line in transcript_slice.text.splitlines():
            parsed = parse_transcript_line(line)
            if parsed is None:
                continue
            timestamp, speaker, _text = parsed
            item = speakers.setdefault(speaker, {"speaker": speaker, "utterance_count": 0, "first_timestamp": timestamp})
            item["utterance_count"] += 1
    return {
        "recorded_by": meeting["recorded_by"],
        "invitees": meeting["invitees"],
        "speakers": sorted(speakers.values(), key=lambda item: item["utterance_count"], reverse=True),
    }


def build_meeting_mechanics(transcript: Transcript) -> list[dict[str, str]]:
    keywords = {
        "screen_share": ["screen", "share", "sharing"],
        "intro_or_location": ["miami", "knoxville", "flight", "airport"],
        "presentation_navigation": ["slide", "deck", "skip", "page"],
        "time_constraint": ["hard stop", "drop now", "five minutes"],
    }
    mechanics = []
    for utterance in transcript.utterances:
        text = utterance.text.lower()
        for category, terms in keywords.items():
            if any(term in text for term in terms):
                mechanics.append(
                    {
                        "category": category,
                        "timestamp": seconds_to_timestamp(utterance.offset_ms // 1000),
                        "speaker": utterance.speaker.name or "Unknown",
                        "excerpt": utterance.text,
                    }
                )
                break
    return mechanics[:20]


def build_meeting_mechanics_from_text(slices: list[TranscriptSlice]) -> list[dict[str, str]]:
    keywords = {
        "screen_share": ["screen", "share", "sharing"],
        "intro_or_location": ["miami", "knoxville", "flight", "airport"],
        "presentation_navigation": ["slide", "deck", "skip", "page"],
        "time_constraint": ["hard stop", "drop now", "five minutes"],
    }
    mechanics = []
    for transcript_slice in slices:
        for line in transcript_slice.text.splitlines():
            parsed = parse_transcript_line(line)
            if parsed is None:
                continue
            timestamp, speaker, text = parsed
            lowered = text.lower()
            for category, terms in keywords.items():
                if any(term in lowered for term in terms):
                    mechanics.append({"category": category, "timestamp": timestamp, "speaker": speaker, "excerpt": text})
                    break
    return mechanics[:20]


def build_topic_timeline(model: ChatOllama, slices: list[TranscriptSlice], run_dir: Path) -> list[dict[str, Any]]:
    timeline = []
    prompt_path = PROMPT_DIR / "topic_timeline_prompt.md"
    for transcript_slice in slices:
        slice_dir = run_dir / "topic_timeline" / transcript_slice.slice_id
        result = run_prompt(
            model,
            prompt_path,
            {
                "{{ slice_id }}": transcript_slice.slice_id,
                "{{ transcript_slice }}": render_slice(transcript_slice),
            },
            slice_dir,
        )
        timeline.append(result)
    return timeline


def run_prompt(model: ChatOllama, prompt_path: Path, replacements: dict[str, str], output_dir: Path) -> Any:
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt = prompt_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        prompt = prompt.replace(key, value)
    (output_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    response = model.invoke(
        [
            SystemMessage(content="Return only valid JSON. Keep output concise and evidence-grounded."),
            HumanMessage(content=prompt),
        ]
    )
    parsed = parse_model_json(str(response.content))
    write_json(output_dir / "output.json", parsed)
    return parsed


def compact_idea_evidence(significant_ideas: dict[str, Any]) -> list[dict[str, Any]]:
    compact = []
    for item in significant_ideas.get("slices", []):
        for evidence in item.get("evidence", []):
            compact.append(
                {
                    "slice_id": item["slice_id"],
                    "timestamp": evidence.get("timestamp"),
                    "speaker": evidence.get("speaker"),
                    "excerpt": evidence.get("excerpt"),
                    "idea_type": evidence.get("idea_type"),
                    "why_this_matters": evidence.get("why_this_matters"),
                }
            )
    return compact


def compact_maps_for_synthesis(maps: dict[str, Any]) -> dict[str, Any]:
    return {
        "meeting": maps["meeting"],
        "significant_ideas": compact_idea_evidence(maps["significant_ideas"]),
        "participant_map": maps["participant_map"],
        "topic_timeline": maps["topic_timeline"],
        "decision_uncertainty_map": maps["decision_uncertainty_map"],
        "vocabulary_map": maps["vocabulary_map"],
        "meeting_mechanics": maps["meeting_mechanics"],
    }


def build_deterministic_context_pack(maps: dict[str, Any]) -> dict[str, Any]:
    idea_evidence = [
        item
        for item in compact_idea_evidence(maps["significant_ideas"])
        if item.get("idea_type") not in {"personal_context", "logistics_update", "market_observation"}
    ]
    high_substance_topics = [
        item
        for item in maps["topic_timeline"]
        if item.get("substance_level") == "high" and item.get("primary_topic")
    ]
    participant_context = [
        f"{item['speaker']}: {item['utterance_count']} utterances, first speaks at {item['first_timestamp']}"
        for item in maps["participant_map"]["speakers"][:5]
    ]
    mechanics = [
        f"{item['timestamp']} {item['category']}: {item['excerpt']}"
        for item in maps["meeting_mechanics"][:8]
    ]
    return {
        "meeting_purpose": "Strategic planning discussion about product roadmap, revenue-line prioritization, demo/MVP focus, and platform architecture.",
        "core_ideas": unique_strings(
            [
                evidence["why_this_matters"]
                for evidence in idea_evidence
                if evidence.get("why_this_matters")
            ],
            limit=10,
        ),
        "strategic_intentions": [
            "Rank revenue lines and choose realistic first opportunities.",
            "Shape the demo and product around a chosen buyer and audience.",
            "Keep the system simple enough to pivot as phase-one analysis changes priorities.",
            "Use software simulation or digital twin work to avoid waiting on hardware where possible.",
        ],
        "design_principles": [
            "Design relationships among stakeholders, equipment, laws, and future system components before building too much surface area.",
            "Start with a primary repository and CI/CD so new demos do not create repeated deployment overhead.",
            "Include security from the start, with hardening, observability, and data integration maturing in later phases.",
        ],
        "open_tensions": [
            "First wedge appears to be operator compliance/risk visibility, but phase-one analysis may reveal a better first revenue stream.",
            "IP protection needs to cover both the concept/prototype and implementation-level application work.",
            "Security ownership is initially packed into CTO responsibilities, with a likely later need for a dedicated security role.",
        ],
        "participant_context": participant_context,
        "topic_timeline": [
            f"{item['slice_id']}: {item['primary_topic']} - {item.get('brief', '')}"
            for item in high_substance_topics
        ],
        "domain_vocabulary": [
            "revenue lines: candidate revenue opportunities to rank and sequence",
            "first wedge: initial product/revenue focus",
            "operator compliance: proposed aviation-operator-focused MVP area",
            "digital twin: software simulation of expected machinery behavior",
            "CI/CD: deployment machinery to support future demos efficiently",
            "operational observability: ability to see what is happening in the system",
        ],
        "meeting_mechanics": mechanics,
        "downstream_guidance": [
            "Do not treat screen sharing, slide navigation, travel talk, or hard-stop logistics as substantive action items.",
            "Use the significant-ideas evidence as orientation, but require local evidence for final claims.",
            "For action items, distinguish post-meeting follow-up from in-meeting presentation actions.",
        ],
        "source_evidence_count": len(idea_evidence),
    }


def unique_strings(values: list[str], limit: int) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = " ".join(value.split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
        if len(result) >= limit:
            break
    return result


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
        utterances = [utterance for utterance in transcript.utterances if start <= utterance.offset_ms // 1000 < end]
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
    if transcript_slice.text:
        return transcript_slice.text
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
    return {"parse_warning": "invalid_json", "raw": content}


def seconds_to_timestamp(total_seconds: int) -> str:
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def timestamp_to_seconds(timestamp: str) -> int:
    minutes, seconds = timestamp.split(":", maxsplit=1)
    return int(minutes) * 60 + int(seconds)


def parse_transcript_line(line: str) -> tuple[str, str, str] | None:
    if not line.startswith("- [") or "] " not in line or ": " not in line:
        return None
    timestamp_end = line.find("]")
    timestamp = line[3:timestamp_end]
    rest = line[timestamp_end + 2 :]
    speaker, text = rest.split(": ", maxsplit=1)
    return timestamp, speaker.strip(), text.strip()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
