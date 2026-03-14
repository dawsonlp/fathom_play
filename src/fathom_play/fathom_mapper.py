"""Fathom JSON -> domain object mapper.

Composable pure functions. No I/O, no HTTP knowledge.
Operates on the .data field of an ApiResponse.
"""

from datetime import datetime

from fathom_play.domain import Meeting, Person, Summary, Transcript, Utterance


def _parse_timestamp_ms(ts: str) -> int:
    """Parse Fathom timestamp string to milliseconds from recording start.

    Fathom uses "MM:SS" format (e.g., "00:05", "29:22").
    """
    parts = ts.strip().split(":")
    if len(parts) == 2:
        minutes, seconds = int(parts[0]), int(parts[1])
        return (minutes * 60 + seconds) * 1000
    if len(parts) == 3:
        hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
        return (hours * 3600 + minutes * 60 + seconds) * 1000
    return 0


def _parse_datetime(iso_str: str) -> datetime:
    """Parse ISO 8601 datetime string."""
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


def _to_person(data: dict) -> Person:
    """Convert a Fathom person-like dict to a Person."""
    return Person(
        name=data.get("display_name") or data.get("name") or "Unknown",
        email=data.get("email") or data.get("matched_calendar_invitee_email") or "",
    )


def _to_utterance(data: dict) -> Utterance:
    """Convert a Fathom transcript item dict to an Utterance."""
    speaker_data = data.get("speaker") or {}
    return Utterance(
        speaker=_to_person(speaker_data),
        text=data.get("text", ""),
        offset_ms=_parse_timestamp_ms(data.get("timestamp", "00:00")),
    )


# --- Public composable functions ---


def to_meetings(data: dict) -> list[Meeting]:
    """Extract Meeting objects from a /meetings response.

    Ignores inline transcript/summary data.
    """
    items = data.get("items", [])
    meetings = []
    for item in items:
        recorded_by_data = item.get("recorded_by") or {}
        invitees_data = item.get("calendar_invitees") or []

        start = _parse_datetime(item["recording_start_time"])
        end = _parse_datetime(item["recording_end_time"])
        duration = item.get("duration_seconds") or int((end - start).total_seconds())

        meetings.append(
            Meeting(
                id=item.get("id", ""),
                recording_id=item["recording_id"],
                title=item.get("title") or item.get("meeting_title") or "(untitled)",
                start_time=start,
                end_time=end,
                duration_seconds=duration,
                recorded_by=_to_person(recorded_by_data),
                invitees=[_to_person(inv) for inv in invitees_data],
            )
        )
    return meetings


def to_transcripts(data: dict) -> list[Transcript]:
    """Extract Transcript objects from a /meetings response with include_transcript=true.

    Returns empty list if transcript data was not included.
    """
    items = data.get("items", [])
    transcripts = []
    for item in items:
        transcript_data = item.get("transcript")
        if not transcript_data:
            continue
        transcripts.append(
            Transcript(
                recording_id=item["recording_id"],
                utterances=[_to_utterance(u) for u in transcript_data],
            )
        )
    return transcripts


def to_summaries(data: dict) -> list[Summary]:
    """Extract Summary objects from a /meetings response with include_summary=true.

    Returns empty list if summary data was not included.
    """
    items = data.get("items", [])
    summaries = []
    for item in items:
        summary_data = item.get("default_summary")
        if not summary_data:
            continue
        markdown = summary_data.get("markdown_formatted", "")
        if markdown:
            summaries.append(
                Summary(
                    recording_id=item["recording_id"],
                    markdown_text=markdown,
                )
            )
    return summaries


def to_transcript(data: dict, recording_id: int) -> Transcript:
    """Convert a standalone /recordings/{id}/transcript response."""
    transcript_data = data.get("transcript", [])
    return Transcript(
        recording_id=recording_id,
        utterances=[_to_utterance(u) for u in transcript_data],
    )


def to_summary(data: dict, recording_id: int) -> Summary:
    """Convert a standalone /recordings/{id}/summary response."""
    summary_data = data.get("summary", {})
    return Summary(
        recording_id=recording_id,
        markdown_text=summary_data.get("markdown_formatted", ""),
    )


def next_cursor(data: dict) -> str | None:
    """Extract the pagination cursor from a list response."""
    cursor = data.get("next_cursor")
    return cursor if cursor else None
