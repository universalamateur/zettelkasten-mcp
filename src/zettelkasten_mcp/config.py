"""Pydantic settings for zettelkasten-mcp.

Loaded from environment variables (prefixed ``ZETTELKASTEN_``) with an optional
``.env`` file in the vault root or current working directory.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str | list[str]) -> list[str]:
    """Accept a comma-separated string or an already-split list."""
    if isinstance(value, list):
        return [v.strip() for v in value if v.strip()]
    return [part.strip() for part in value.split(",") if part.strip()]


class Settings(BaseSettings):
    """Runtime configuration for zettelkasten-mcp."""

    model_config = SettingsConfigDict(
        env_prefix="ZETTELKASTEN_",
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    vault_path: Path = Field(..., description="Root of the markdown vault.")
    chroma_path: Path = Field(
        default=Path("~/.local/share/zettelkasten-rag").expanduser(),
        description="ChromaDB persistence directory.",
    )
    ollama_url: str = Field(
        default="http://localhost:11434",
        description="Ollama HTTP API endpoint.",
    )
    embedding_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model name.",
    )
    index_dirs: list[str] = Field(
        default_factory=lambda: ["notes", "literature", "indexes"],
        description="Vault-relative directories to index.",
    )
    skip_dirs: list[str] = Field(
        default_factory=lambda: ["journals", "Customer", ".git", "artifacts"],
        description="Vault-relative directories to skip during ingest.",
    )

    @field_validator("vault_path", "chroma_path", mode="before")
    @classmethod
    def _expand_path(cls, value: str | Path) -> Path:
        return Path(str(value)).expanduser()

    @field_validator("index_dirs", "skip_dirs", mode="before")
    @classmethod
    def _parse_csv(cls, value: str | list[str]) -> list[str]:
        return _split_csv(value)


def get_settings() -> Settings:
    """Load settings from the environment."""
    return Settings()  # type: ignore[call-arg]  # fields populated from env
