"""Query/Automation interface for local workflows."""

from __future__ import annotations

from pathlib import Path

from fathom_play.artifacts import ArtifactStore
from fathom_play.fathom_client import FathomHttpClient
from fathom_play.knowledge_base import ConversationKnowledgeBase
from fathom_play.model_adapter import ModelAdapter
from fathom_play.source_importer import FathomSourceImporter
from fathom_play.workflows import WorkflowRunner, WorkflowSummary


class ConversationAutomation:
    """Stable interface used by CLI and future local automation adapters."""

    def __init__(self, data_root: Path | None = None, with_source: bool = True, with_model: bool = True):
        self.artifacts = ArtifactStore(data_root)
        self.kb = ConversationKnowledgeBase(self.artifacts.db_path)
        source = None
        if with_source:
            source = FathomSourceImporter(FathomHttpClient())
        model = ModelAdapter() if with_model else None
        self.runner = WorkflowRunner(self.kb, self.artifacts, source_importer=source, model_adapter=model)

    def ingest(self) -> WorkflowSummary:
        return self.runner.ingest()

    def analyze(self, recording_id: int, username: str, context: str = "") -> int:
        return self.runner.analyze(recording_id, username=username, context=context)

    def query(self):
        return self.runner.query()

    def delete_local(self, recording_id: int) -> None:
        self.runner.delete_local(recording_id)
