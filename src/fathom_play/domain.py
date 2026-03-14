"""Domain objects for meeting data.

Provider-agnostic representations. No I/O, no infrastructure imports.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Person:
    """A named individual. Value object -- equality by name and email."""

    name: str
    email: str = ""


@dataclass(frozen=True)
class Meeting:
    """A recorded meeting event."""

    id: str
    recording_id: int
    title: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    recorded_by: Person
    invitees: list[Person]


@dataclass(frozen=True)
class Utterance:
    """A single spoken segment within a meeting. Value object."""

    speaker: Person
    text: str
    offset_ms: int


@dataclass(frozen=True)
class Transcript:
    """An ordered collection of utterances for a specific recording."""

    recording_id: int
    utterances: list[Utterance]


@dataclass(frozen=True)
class Summary:
    """A text summary of a specific recording."""

    recording_id: int
    markdown_text: str
