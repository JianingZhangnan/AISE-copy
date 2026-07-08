"""Configuration data models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class UserConfig(BaseModel):
    """User-level configuration (from ~/.config/phycode/config.toml or similar)."""

    model_config = ConfigDict(frozen=True, extra="allow")

    default_provider: str = "openai"
    base_url: str | None = None
    model: str = "gpt-4o"
    api_key_env: str | None = None  # env var name holding the actual key


class ProjectConfig(BaseModel):
    """Project-level configuration (from ./phycode.toml)."""

    model_config = ConfigDict(frozen=True, extra="allow")

    workspace_root: str
    test_command: str = "uv run pytest"
    enabled_tools: list[str] | None = None
    allowlist: list[str] = []
    policy_overrides: dict[str, Any] | None = None
    feedback_overrides: dict[str, Any] | None = None
