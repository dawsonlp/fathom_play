"""Fathom source importer for local conversations."""

from __future__ import annotations

from dataclasses import dataclass

from fathom_play import fathom_mapper
from fathom_play.domain import Meeting, Transcript
from fathom_play.fathom_client import FathomHttpClient


@dataclass(frozen=True)
class SourceMeeting:
    meeting: Meeting
    raw: dict


@dataclass(frozen=True)
class SourceTranscript:
    transcript: Transcript
    raw: dict


class FathomSourceImporter:
    """Light source boundary over the Fathom API."""

    def __init__(self, client: FathomHttpClient):
        self.client = client

    def discover_meetings(self) -> list[SourceMeeting]:
        items: list[SourceMeeting] = []
        cursor: str | None = None
        while True:
            params = {"cursor": cursor} if cursor else {}
            resp = self.client.list_meetings(**params)
            meetings = {m.recording_id: m for m in fathom_mapper.to_meetings(resp.data)}
            for raw_item in resp.data.get("items", []):
                recording_id = raw_item["recording_id"]
                items.append(SourceMeeting(meeting=meetings[recording_id], raw=raw_item))
            cursor = fathom_mapper.next_cursor(resp.data)
            if not cursor:
                break
        return sorted(items, key=lambda item: item.meeting.start_time, reverse=True)

    def fetch_transcript(self, recording_id: int) -> SourceTranscript:
        resp = self.client.get_transcript(recording_id)
        return SourceTranscript(
            transcript=fathom_mapper.to_transcript(resp.data, recording_id),
            raw=resp.data,
        )
