"""Workflow runner for ingestion, analysis, query, and local deletion."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from fathom_play import fathom_mapper
from fathom_play.analysis_enricher import (
    ANALYSIS_VERSION,
    AnalysisEnricher,
    RuntimeContext,
)
from fathom_play.artifacts import ArtifactStore
from fathom_play.knowledge_base import ConversationKnowledgeBase
from fathom_play.model_adapter import ModelAdapter
from fathom_play.source_importer import FathomSourceImporter, SourceMeeting
from fathom_play.tools import ExplicitTool, make_tool


@dataclass(frozen=True)
class WorkflowSummary:
    discovered: int = 0
    skipped: int = 0
    completed: int = 0
    failed: int = 0


class IngestState(TypedDict, total=False):
    meetings: list[SourceMeeting]
    discovered: int
    skipped: int
    completed: int
    failed: int


class AnalysisState(TypedDict, total=False):
    recording_id: int
    username: str
    context: str
    transcript_data: dict[str, Any]
    analysis_run_id: int


class WorkflowRunner:
    """Coordinates approved workflows across component interfaces."""

    def __init__(
        self,
        knowledge_base: ConversationKnowledgeBase,
        artifact_store: ArtifactStore,
        source_importer: FathomSourceImporter | None = None,
        model_adapter: ModelAdapter | None = None,
    ):
        self.kb = knowledge_base
        self.artifacts = artifact_store
        self.source_importer = source_importer
        self.model_adapter = model_adapter
        self.tools = self._make_tools()
        self._ingest_graph = self._build_ingest_graph()
        self._analysis_graph = self._build_analysis_graph()

    def _make_tools(self) -> dict[str, ExplicitTool]:
        return {
            "record_artifact": make_tool(
                "record_artifact",
                "Records an artifact reference in the local knowledge base.",
                self.kb.record_artifact,
            ),
        }

    def _build_ingest_graph(self):
        graph = StateGraph(IngestState)
        graph.add_node("discover", self._ingest_discover)
        graph.add_node("process", self._ingest_process)
        graph.add_edge(START, "discover")
        graph.add_edge("discover", "process")
        graph.add_edge("process", END)
        return graph.compile()

    def _build_analysis_graph(self):
        graph = StateGraph(AnalysisState)
        graph.add_node("load_transcript", self._analysis_load_transcript)
        graph.add_node("create_run", self._analysis_create_run)
        graph.add_node("run_analysis", self._analysis_run)
        graph.add_edge(START, "load_transcript")
        graph.add_edge("load_transcript", "create_run")
        graph.add_edge("create_run", "run_analysis")
        graph.add_edge("run_analysis", END)
        return graph.compile()

    def _ingest_discover(self, _state: IngestState) -> IngestState:
        if self.source_importer is None:
            raise RuntimeError("Source importer is required for ingestion")

        meetings = sorted(
            self.source_importer.discover_meetings(),
            key=lambda item: item.meeting.start_time,
            reverse=True,
        )
        for source_meeting in meetings:
            self.kb.upsert_conversation(source_meeting.meeting)
        return {"meetings": meetings, "discovered": len(meetings), "skipped": 0, "completed": 0, "failed": 0}

    def _ingest_process(self, state: IngestState) -> IngestState:
        completed = failed = skipped = 0

        for source_meeting in state.get("meetings", []):
            meeting = source_meeting.meeting
            unprocessed_ids = {item.recording_id for item in self.kb.list_unprocessed_conversations()}
            if meeting.recording_id not in unprocessed_ids:
                skipped += 1
                continue
            try:
                self.kb.mark_ingestion_started(meeting.recording_id)
                meeting_ref = self.artifacts.write_meeting(meeting.recording_id, source_meeting.raw)
                self.kb.record_artifact(meeting.recording_id, meeting_ref)
                source_transcript = self.source_importer.fetch_transcript(meeting.recording_id)
                transcript_json_ref = self.artifacts.write_transcript_json(meeting.recording_id, source_transcript.raw)
                transcript_md_ref = self.artifacts.write_transcript_markdown(source_transcript.transcript)
                self.kb.record_artifact(meeting.recording_id, transcript_json_ref)
                self.kb.record_artifact(meeting.recording_id, transcript_md_ref)
                self.kb.mark_ingestion_completed(meeting.recording_id)
                completed += 1
            except Exception as exc:
                self.kb.mark_ingestion_failed(meeting.recording_id, str(exc))
                failed += 1
                raise

        return {"skipped": skipped, "completed": completed, "failed": failed}

    def ingest(self) -> WorkflowSummary:
        state = self._ingest_graph.invoke({})
        return WorkflowSummary(
            discovered=state.get("discovered", 0),
            skipped=state.get("skipped", 0),
            completed=state.get("completed", 0),
            failed=state.get("failed", 0),
        )

    def _analysis_load_transcript(self, state: AnalysisState) -> AnalysisState:
        recording_id = state["recording_id"]
        transcript_path = self.kb.artifact_path(recording_id, "transcript_json")
        if transcript_path is None:
            raise RuntimeError(f"No local transcript artifact for recording {recording_id}")

        transcript_data = json.loads(transcript_path.read_text(encoding="utf-8"))
        return {"transcript_data": transcript_data}

    def _analysis_create_run(self, state: AnalysisState) -> AnalysisState:
        if self.model_adapter is None:
            raise RuntimeError("Model adapter is required for analysis")

        model_info = self.model_adapter.info
        analysis_run_id = self.kb.create_analysis_run(
            recording_id=state["recording_id"],
            runtime_username=state["username"],
            runtime_context=state.get("context", ""),
            model_provider=model_info.provider,
            model_name=model_info.model,
            analysis_version=ANALYSIS_VERSION,
        )
        return {"analysis_run_id": analysis_run_id}

    def _analysis_run(self, state: AnalysisState) -> AnalysisState:
        if self.model_adapter is None:
            raise RuntimeError("Model adapter is required for analysis")

        recording_id = state["recording_id"]
        username = state["username"]
        context = state.get("context", "")
        analysis_run_id = state["analysis_run_id"]
        transcript = fathom_mapper.to_transcript(state["transcript_data"], recording_id)
        model_info = self.model_adapter.info
        try:
            enricher = AnalysisEnricher(self.model_adapter.chat_model())
            for output in enricher.analyze(transcript, RuntimeContext(username=username, context=context)):
                ref = self.artifacts.write_analysis_json(recording_id, analysis_run_id, output.name, output.payload)
                self.kb.record_artifact(recording_id, ref, analysis_run_id=analysis_run_id)
                self.kb.record_finding(analysis_run_id, recording_id, output.name, output.payload)
            context_ref = self.artifacts.write_analysis_json(
                recording_id,
                analysis_run_id,
                "analysis_context",
                {"username": username, "context": context, "model": model_info.model, "provider": model_info.provider},
            )
            self.kb.record_artifact(recording_id, context_ref, analysis_run_id=analysis_run_id)
            self.kb.mark_analysis_completed(analysis_run_id)
        except Exception as exc:
            self.kb.mark_analysis_failed(analysis_run_id, str(exc))
            raise
        return {}

    def analyze(self, recording_id: int, username: str, context: str = "") -> int:
        state = self._analysis_graph.invoke({"recording_id": recording_id, "username": username, "context": context})
        return state["analysis_run_id"]

    def query(self):
        return self.kb.list_conversations()

    def delete_local(self, recording_id: int) -> None:
        recording_dir = self.artifacts.recording_dir(recording_id)
        if recording_dir.exists():
            shutil.rmtree(recording_dir)
        self.kb.delete_conversation(recording_id)
