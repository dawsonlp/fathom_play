"""SQLite-backed local conversation knowledge base."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fathom_play.artifacts import ArtifactRef
from fathom_play.domain import Meeting, Person

Status = Literal["pending", "in_progress", "completed", "failed"]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class ConversationRecord:
    recording_id: int
    meeting_id: str
    title: str
    start_time: str
    status: str


@dataclass(frozen=True)
class AnalysisRunRecord:
    id: int
    recording_id: int
    status: str
    model_provider: str
    model_name: str


class ConversationKnowledgeBase:
    """Owns local queryable conversation and analysis records."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    recording_id INTEGER PRIMARY KEY,
                    meeting_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    recorded_by_name TEXT NOT NULL,
                    recorded_by_email TEXT NOT NULL,
                    source_provider TEXT NOT NULL DEFAULT 'fathom',
                    ingestion_status TEXT NOT NULL DEFAULT 'pending',
                    analysis_status TEXT NOT NULL DEFAULT 'pending',
                    last_error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    UNIQUE(name, email)
                );

                CREATE TABLE IF NOT EXISTS conversation_participants (
                    recording_id INTEGER NOT NULL REFERENCES conversations(recording_id) ON DELETE CASCADE,
                    participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    UNIQUE(recording_id, participant_id, role)
                );

                CREATE TABLE IF NOT EXISTS artifact_refs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recording_id INTEGER NOT NULL REFERENCES conversations(recording_id) ON DELETE CASCADE,
                    analysis_run_id INTEGER,
                    kind TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS analysis_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recording_id INTEGER NOT NULL REFERENCES conversations(recording_id) ON DELETE CASCADE,
                    status TEXT NOT NULL,
                    runtime_username TEXT NOT NULL,
                    runtime_context TEXT NOT NULL,
                    model_provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    analysis_version TEXT NOT NULL,
                    last_error TEXT NOT NULL DEFAULT '',
                    started_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS analysis_findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_run_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
                    recording_id INTEGER NOT NULL REFERENCES conversations(recording_id) ON DELETE CASCADE,
                    finding_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evidence_refs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    finding_id INTEGER NOT NULL REFERENCES analysis_findings(id) ON DELETE CASCADE,
                    speaker_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    excerpt TEXT NOT NULL
                );
                """
            )

    def upsert_conversation(self, meeting: Meeting) -> None:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations (
                    recording_id, meeting_id, title, start_time, end_time, duration_seconds,
                    recorded_by_name, recorded_by_email, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(recording_id) DO UPDATE SET
                    meeting_id = excluded.meeting_id,
                    title = excluded.title,
                    start_time = excluded.start_time,
                    end_time = excluded.end_time,
                    duration_seconds = excluded.duration_seconds,
                    recorded_by_name = excluded.recorded_by_name,
                    recorded_by_email = excluded.recorded_by_email,
                    updated_at = excluded.updated_at
                """,
                (
                    meeting.recording_id,
                    meeting.id,
                    meeting.title,
                    meeting.start_time.isoformat(),
                    meeting.end_time.isoformat(),
                    meeting.duration_seconds,
                    meeting.recorded_by.name,
                    meeting.recorded_by.email,
                    now,
                    now,
                ),
            )
            self._link_participant(conn, meeting.recording_id, meeting.recorded_by, "recorded_by")
            for invitee in meeting.invitees:
                self._link_participant(conn, meeting.recording_id, invitee, "invitee")

    def _link_participant(self, conn: sqlite3.Connection, recording_id: int, person: Person, role: str) -> None:
        conn.execute(
            "INSERT OR IGNORE INTO participants (name, email) VALUES (?, ?)",
            (person.name, person.email),
        )
        row = conn.execute(
            "SELECT id FROM participants WHERE name = ? AND email = ?",
            (person.name, person.email),
        ).fetchone()
        participant_id = row["id"]
        conn.execute(
            """
            INSERT OR IGNORE INTO conversation_participants (recording_id, participant_id, role)
            VALUES (?, ?, ?)
            """,
            (recording_id, participant_id, role),
        )

    def record_artifact(self, recording_id: int, ref: ArtifactRef, analysis_run_id: int | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO artifact_refs (recording_id, analysis_run_id, kind, path, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (recording_id, analysis_run_id, ref.kind, str(ref.path), utc_now()),
            )

    def artifact_path(self, recording_id: int, kind: str) -> Path | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT path FROM artifact_refs
                WHERE recording_id = ? AND kind = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (recording_id, kind),
            ).fetchone()
        return Path(row["path"]) if row else None

    def mark_ingestion_started(self, recording_id: int) -> None:
        self._set_ingestion_status(recording_id, "in_progress")

    def mark_ingestion_completed(self, recording_id: int) -> None:
        self._set_ingestion_status(recording_id, "completed")

    def mark_ingestion_failed(self, recording_id: int, error: str) -> None:
        self._set_ingestion_status(recording_id, "failed", error)

    def _set_ingestion_status(self, recording_id: int, status: Status, error: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE conversations
                SET ingestion_status = ?, last_error = ?, updated_at = ?
                WHERE recording_id = ?
                """,
                (status, error, utc_now(), recording_id),
            )

    def list_unprocessed_conversations(self) -> list[ConversationRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT recording_id, meeting_id, title, start_time, ingestion_status AS status
                FROM conversations
                WHERE ingestion_status != 'completed'
                ORDER BY start_time DESC
                """
            ).fetchall()
        return [ConversationRecord(**dict(row)) for row in rows]

    def list_conversations(self) -> list[ConversationRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT recording_id, meeting_id, title, start_time, ingestion_status AS status
                FROM conversations
                ORDER BY start_time DESC
                """
            ).fetchall()
        return [ConversationRecord(**dict(row)) for row in rows]

    def create_analysis_run(
        self,
        recording_id: int,
        runtime_username: str,
        runtime_context: str,
        model_provider: str,
        model_name: str,
        analysis_version: str,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_runs (
                    recording_id, status, runtime_username, runtime_context,
                    model_provider, model_name, analysis_version, started_at
                )
                VALUES (?, 'in_progress', ?, ?, ?, ?, ?, ?)
                """,
                (
                    recording_id,
                    runtime_username,
                    runtime_context,
                    model_provider,
                    model_name,
                    analysis_version,
                    utc_now(),
                ),
            )
            conn.execute(
                "UPDATE conversations SET analysis_status = 'in_progress', updated_at = ? WHERE recording_id = ?",
                (utc_now(), recording_id),
            )
            return int(cursor.lastrowid)

    def record_finding(self, analysis_run_id: int, recording_id: int, finding_type: str, payload: dict) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_findings (analysis_run_id, recording_id, finding_type, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (analysis_run_id, recording_id, finding_type, json.dumps(payload, sort_keys=True), utc_now()),
            )
            finding_id = int(cursor.lastrowid)
            for evidence in payload.get("evidence", []):
                conn.execute(
                    """
                    INSERT INTO evidence_refs (finding_id, speaker_name, timestamp, excerpt)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        finding_id,
                        evidence.get("speaker", ""),
                        evidence.get("timestamp", ""),
                        evidence.get("excerpt", ""),
                    ),
                )
            return finding_id

    def mark_analysis_completed(self, analysis_run_id: int) -> None:
        self._set_analysis_status(analysis_run_id, "completed")

    def mark_analysis_failed(self, analysis_run_id: int, error: str) -> None:
        self._set_analysis_status(analysis_run_id, "failed", error)

    def _set_analysis_status(self, analysis_run_id: int, status: Status, error: str = "") -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT recording_id FROM analysis_runs WHERE id = ?",
                (analysis_run_id,),
            ).fetchone()
            if row is None:
                return
            conn.execute(
                """
                UPDATE analysis_runs
                SET status = ?, last_error = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, error, utc_now(), analysis_run_id),
            )
            conn.execute(
                "UPDATE conversations SET analysis_status = ?, updated_at = ? WHERE recording_id = ?",
                (status, utc_now(), row["recording_id"]),
            )

    def list_analysis_runs(self, recording_id: int | None = None) -> list[AnalysisRunRecord]:
        params: tuple[Any, ...] = ()
        where = ""
        if recording_id is not None:
            where = "WHERE recording_id = ?"
            params = (recording_id,)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, recording_id, status, model_provider, model_name
                FROM analysis_runs
                {where}
                ORDER BY id DESC
                """,
                params,
            ).fetchall()
        return [AnalysisRunRecord(**dict(row)) for row in rows]

    def delete_conversation(self, recording_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM conversations WHERE recording_id = ?", (recording_id,))
