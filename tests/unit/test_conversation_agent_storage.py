import json
from datetime import UTC, datetime, timedelta

from fathom_play.artifacts import ArtifactStore, render_transcript_markdown
from fathom_play.domain import Meeting, Person, Transcript, Utterance
from fathom_play.knowledge_base import ConversationKnowledgeBase


def _meeting(recording_id: int = 1, title: str = "Test Meeting") -> Meeting:
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return Meeting(
        id=f"meeting-{recording_id}",
        recording_id=recording_id,
        title=title,
        start_time=start,
        end_time=start + timedelta(minutes=30),
        duration_seconds=1800,
        recorded_by=Person("Alice", "alice@example.com"),
        invitees=[Person("Bob", "bob@example.com")],
    )


def test_artifact_store_writes_transcript_outside_repo_root(tmp_path):
    store = ArtifactStore(tmp_path / "app-data")
    transcript = Transcript(
        recording_id=123,
        utterances=[Utterance(Person("Alice"), "Hello", 5000)],
    )

    ref = store.write_transcript_markdown(transcript)

    assert ref.path == tmp_path / "app-data" / "artifacts" / "fathom" / "recordings" / "123" / "transcript.md"
    assert "[00:05] **Alice:** Hello" in ref.path.read_text()


def test_render_transcript_markdown_is_deterministic():
    transcript = Transcript(
        recording_id=123,
        utterances=[Utterance(Person("Alice"), "Hello", 5000)],
    )

    assert render_transcript_markdown(transcript) == render_transcript_markdown(transcript)


def test_knowledge_base_upsert_and_processing_state(tmp_path):
    kb = ConversationKnowledgeBase(tmp_path / "conversations.db")
    meeting = _meeting()

    kb.upsert_conversation(meeting)

    unprocessed = kb.list_unprocessed_conversations()
    assert [item.recording_id for item in unprocessed] == [1]

    kb.mark_ingestion_completed(1)
    assert kb.list_unprocessed_conversations() == []


def test_knowledge_base_records_multiple_analysis_runs(tmp_path):
    kb = ConversationKnowledgeBase(tmp_path / "conversations.db")
    kb.upsert_conversation(_meeting())

    first = kb.create_analysis_run(1, "Alice", "", "ollama", "gemma4:e2b", "v1")
    second = kb.create_analysis_run(1, "Alice", "", "ollama", "gemma4:e2b", "v1")
    kb.mark_analysis_completed(first)
    kb.mark_analysis_completed(second)

    runs = kb.list_analysis_runs(1)
    assert [run.id for run in runs] == [second, first]


def test_artifact_reference_round_trip(tmp_path):
    kb = ConversationKnowledgeBase(tmp_path / "conversations.db")
    store = ArtifactStore(tmp_path)
    kb.upsert_conversation(_meeting())
    ref = store.write_transcript_json(1, {"transcript": []})
    kb.record_artifact(1, ref)

    path = kb.artifact_path(1, "transcript_json")

    assert path is not None
    assert json.loads(path.read_text()) == {"transcript": []}
