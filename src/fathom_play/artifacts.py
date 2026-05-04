"""Filesystem artifact storage for conversations and analyses."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fathom_play.app_paths import default_data_root
from fathom_play.domain import Transcript


@dataclass(frozen=True)
class ArtifactRef:
    """Reference to a local artifact."""

    kind: str
    path: Path


class ArtifactStore:
    """Owns local artifact paths and file writes."""

    def __init__(self, root: Path | None = None):
        self.root = root or default_data_root()

    @property
    def db_path(self) -> Path:
        return self.root / "conversations.db"

    def recording_dir(self, recording_id: int) -> Path:
        return self.root / "artifacts" / "fathom" / "recordings" / str(recording_id)

    def analysis_dir(self, recording_id: int, analysis_run_id: int) -> Path:
        return self.recording_dir(recording_id) / "analyses" / str(analysis_run_id)

    def write_json(self, path: Path, data: Any) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")
        return path

    def write_text(self, path: Path, text: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def write_meeting(self, recording_id: int, data: dict) -> ArtifactRef:
        path = self.write_json(self.recording_dir(recording_id) / "meeting.json", data)
        return ArtifactRef(kind="meeting_json", path=path)

    def write_transcript_json(self, recording_id: int, data: dict) -> ArtifactRef:
        path = self.write_json(self.recording_dir(recording_id) / "transcript.json", data)
        return ArtifactRef(kind="transcript_json", path=path)

    def write_transcript_markdown(self, transcript: Transcript) -> ArtifactRef:
        path = self.write_text(
            self.recording_dir(transcript.recording_id) / "transcript.md",
            render_transcript_markdown(transcript),
        )
        return ArtifactRef(kind="transcript_md", path=path)

    def write_analysis_json(self, recording_id: int, analysis_run_id: int, name: str, data: Any) -> ArtifactRef:
        path = self.write_json(self.analysis_dir(recording_id, analysis_run_id) / f"{name}.json", data)
        return ArtifactRef(kind=f"analysis_{name}", path=path)

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")


def render_transcript_markdown(transcript: Transcript) -> str:
    """Render a deterministic transcript for human review and evidence lookup."""
    lines = [f"# Transcript {transcript.recording_id}", ""]
    for utterance in transcript.utterances:
        total_seconds = utterance.offset_ms // 1000
        minutes, seconds = divmod(total_seconds, 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"
        speaker = utterance.speaker.name or "Unknown"
        lines.append(f"- [{timestamp}] **{speaker}:** {utterance.text}")
    lines.append("")
    return "\n".join(lines)
