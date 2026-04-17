"""Pydantic models for notes, search results, and index reports.

Field names and the ``NoteType`` enum follow ``.rag/schema.yaml`` in the vault.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class NoteType(str, Enum):
    """Allowed values for a note's ``type`` frontmatter field."""

    PERMANENT = "permanent"
    LITERATURE = "literature"
    PROJECT = "project"
    INDEX = "index"


class Note(BaseModel):
    """A parsed markdown note with frontmatter + body text."""

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(..., description="Kebab-case identifier; matches filename without .md.")
    type: NoteType
    tags: list[str] = Field(..., min_length=1)
    created: date
    source: str = Field(..., description="Journal path, project number, or URL.")
    updated: date | None = None
    related: list[str] = Field(default_factory=list)
    body: str = Field(..., description="Markdown-stripped body text used for embedding.")
    path: Path = Field(..., description="Absolute path to the source file.")
    content_hash: str = Field(..., description="Hash of raw file content for change detection.")


class SearchResult(BaseModel):
    """One row returned by the ``search`` MCP tool."""

    id: str
    type: str
    tags: list[str]
    score: float = Field(..., description="Lower is closer (ChromaDB distance).")
    snippet: str
    path: str


class IngestReport(BaseModel):
    """Summary returned by the ``ingest`` MCP tool."""

    indexed: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)


class CoverageGap(BaseModel):
    """A single problem found during ``status`` reporting."""

    path: str
    reason: str = Field(..., description="missing-frontmatter | unknown-tags | unindexed | invalid-type")


class StatusReport(BaseModel):
    """Summary returned by the ``status`` MCP tool."""

    total_indexed: int = 0
    last_ingest: datetime | None = None
    by_type: dict[str, int] = Field(default_factory=dict)
    by_tag: dict[str, int] = Field(default_factory=dict)
    coverage_gaps: list[CoverageGap] = Field(default_factory=list)
