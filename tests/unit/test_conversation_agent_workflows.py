from datetime import UTC, datetime, timedelta

import pytest

from fathom_play.artifacts import ArtifactStore
from fathom_play.domain import Meeting, Person, Transcript, Utterance
from fathom_play.knowledge_base import ConversationKnowledgeBase
from fathom_play.source_importer import SourceMeeting, SourceTranscript
from fathom_play.workflows import WorkflowRunner


def _meeting(recording_id: int = 1) -> Meeting:
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return Meeting(
        id=f"meeting-{recording_id}",
        recording_id=recording_id,
        title=f"Meeting {recording_id}",
        start_time=start + timedelta(days=recording_id),
        end_time=start + timedelta(days=recording_id, minutes=10),
        duration_seconds=600,
        recorded_by=Person("Alice"),
        invitees=[],
    )


class FakeImporter:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.fetched: list[int] = []

    def discover_meetings(self):
        return [
            SourceMeeting(_meeting(1), {"recording_id": 1}),
            SourceMeeting(_meeting(2), {"recording_id": 2}),
        ]

    def fetch_transcript(self, recording_id: int):
        self.fetched.append(recording_id)
        if self.fail:
            raise RuntimeError("boom")
        return SourceTranscript(
            Transcript(recording_id, [Utterance(Person("Alice"), "Hello", 1000)]),
            {"transcript": [{"speaker": {"name": "Alice"}, "text": "Hello", "timestamp": "00:01"}]},
        )


def test_ingest_processes_newest_first_and_writes_artifacts(tmp_path):
    kb = ConversationKnowledgeBase(tmp_path / "conversations.db")
    store = ArtifactStore(tmp_path)
    importer = FakeImporter()
    runner = WorkflowRunner(kb, store, source_importer=importer)

    summary = runner.ingest()

    assert summary.discovered == 2
    assert summary.completed == 2
    assert importer.fetched == [2, 1]
    assert kb.list_unprocessed_conversations() == []
    assert (store.recording_dir(1) / "transcript.json").exists()


def test_ingest_fails_loudly_and_preserves_failure_state(tmp_path):
    kb = ConversationKnowledgeBase(tmp_path / "conversations.db")
    store = ArtifactStore(tmp_path)
    runner = WorkflowRunner(kb, store, source_importer=FakeImporter(fail=True))

    with pytest.raises(RuntimeError, match="boom"):
        runner.ingest()

    unprocessed = kb.list_unprocessed_conversations()
    assert {item.recording_id for item in unprocessed} == {1, 2}


def test_delete_local_removes_records_and_artifacts(tmp_path):
    kb = ConversationKnowledgeBase(tmp_path / "conversations.db")
    store = ArtifactStore(tmp_path)
    runner = WorkflowRunner(kb, store)
    kb.upsert_conversation(_meeting(1))
    ref = store.write_transcript_json(1, {"transcript": []})
    kb.record_artifact(1, ref)

    runner.delete_local(1)

    assert kb.list_conversations() == []
    assert not store.recording_dir(1).exists()
