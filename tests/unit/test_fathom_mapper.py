"""Tests for fathom_mapper -- JSON to domain object translation."""

import json
from pathlib import Path

import pytest

from fathom_play import fathom_mapper
from fathom_play.domain import Person

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class TestToMeetings:
    def test_parses_meetings_from_list_response(self):
        data = _load_fixture("fathom_meetings.json")
        meetings = fathom_mapper.to_meetings(data)

        assert len(meetings) == 2
        m = meetings[0]
        assert m.id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert m.recording_id == 9990001
        assert m.title == "Alice / Bob"
        assert m.duration_seconds == 1763
        assert m.recorded_by == Person(name="Alice Testerson", email="alice@example.com")
        assert len(m.invitees) == 2

    def test_meeting_has_parsed_datetimes(self):
        data = _load_fixture("fathom_meetings.json")
        m = fathom_mapper.to_meetings(data)[0]

        assert m.start_time.year == 2025
        assert m.start_time.month == 3
        assert m.start_time.day == 13

    def test_empty_invitees_produces_empty_list(self):
        data = _load_fixture("fathom_meetings.json")
        m = fathom_mapper.to_meetings(data)[1]

        assert m.invitees == []

    def test_ignores_inline_transcript_data(self):
        data = _load_fixture("fathom_meetings_with_transcript.json")
        meetings = fathom_mapper.to_meetings(data)

        assert len(meetings) == 1
        assert not hasattr(meetings[0], "transcript")


class TestToTranscripts:
    def test_extracts_transcripts_from_inline_data(self):
        data = _load_fixture("fathom_meetings_with_transcript.json")
        transcripts = fathom_mapper.to_transcripts(data)

        assert len(transcripts) == 1
        t = transcripts[0]
        assert t.recording_id == 9990001
        assert len(t.utterances) == 3

    def test_returns_empty_list_when_no_transcript_data(self):
        data = _load_fixture("fathom_meetings.json")
        transcripts = fathom_mapper.to_transcripts(data)

        assert transcripts == []

    def test_utterance_speaker_is_person(self):
        data = _load_fixture("fathom_meetings_with_transcript.json")
        t = fathom_mapper.to_transcripts(data)[0]

        assert t.utterances[0].speaker == Person(name="Alice Testerson", email="alice@example.com")
        assert t.utterances[1].speaker == Person(name="Bob Mockwell", email="bob@example.com")


class TestToSummaries:
    def test_extracts_summaries_from_inline_data(self):
        data = _load_fixture("fathom_meetings_with_transcript.json")
        summaries = fathom_mapper.to_summaries(data)

        assert len(summaries) == 1
        s = summaries[0]
        assert s.recording_id == 9990001
        assert "Alice" in s.markdown_text

    def test_returns_empty_list_when_no_summary_data(self):
        data = _load_fixture("fathom_meetings.json")
        summaries = fathom_mapper.to_summaries(data)

        assert summaries == []


class TestToTranscript:
    def test_parses_standalone_transcript_response(self):
        data = _load_fixture("fathom_transcript.json")
        t = fathom_mapper.to_transcript(data, recording_id=9990001)

        assert t.recording_id == 9990001
        assert len(t.utterances) == 3

    def test_utterance_offset_parsed_correctly(self):
        data = _load_fixture("fathom_transcript.json")
        t = fathom_mapper.to_transcript(data, recording_id=9990001)

        assert t.utterances[0].offset_ms == 5000
        assert t.utterances[1].offset_ms == 12000
        assert t.utterances[2].offset_ms == 13000


class TestToSummary:
    def test_parses_standalone_summary_response(self):
        data = _load_fixture("fathom_summary.json")
        s = fathom_mapper.to_summary(data, recording_id=9990001)

        assert s.recording_id == 9990001
        assert "Alice" in s.markdown_text


class TestNextCursor:
    def test_returns_cursor_when_present(self):
        data = _load_fixture("fathom_meetings.json")
        cursor = fathom_mapper.next_cursor(data)

        assert cursor is not None
        assert len(cursor) > 0

    def test_returns_none_when_no_cursor(self):
        data = _load_fixture("fathom_meetings_with_transcript.json")
        cursor = fathom_mapper.next_cursor(data)

        assert cursor is None


class TestTimestampParsing:
    @pytest.mark.parametrize(
        "ts,expected_ms",
        [
            ("00:00", 0),
            ("00:05", 5000),
            ("01:30", 90000),
            ("29:22", 1762000),
            ("1:05:30", 3930000),
        ],
    )
    def test_various_timestamp_formats(self, ts, expected_ms):
        assert fathom_mapper._parse_timestamp_ms(ts) == expected_ms
