"""Configuration file loading with TOML + Pydantic validation."""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import Any

from phycode.config.models import ProjectConfig, UserConfig
from phycode.errors import ConfigError

logger = logging.getLogger(__name__)


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file, returning an empty dict if it doesn't exist."""
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as exc:
        raise ConfigError(f"Failed to parse TOML at {path}", cause=exc) from exc


def load_project_config(
    project_root: Path | None = None,
) -> ProjectConfig:
    """Load project-level config from `project_root/phycode.toml`.

    Unknown keys are logged as warnings but do NOT raise.
    """
    if project_root is None:
        project_root = Path.cwd()

    cfg_path = project_root / "phycode.toml"
    raw = _load_toml(cfg_path)

    # Warn about unknown fields
    known_fields = set(ProjectConfig.model_fields)
    for key in raw:
        if key not in known_fields:
            logger.warning("Unknown project config key '%s' in %s (ignored)", key, cfg_path)

    try:
        return ProjectConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigError(f"Invalid project config in {cfg_path}", cause=exc) from exc


def load_user_config(
    config_dir: Path | None = None,
) -> UserConfig:
    """Load user-level config from `config_dir/config.toml`."""
    if config_dir is None:
        import platformdirs

        config_dir = Path(platformdirs.user_config_dir("phycode", appauthor=False))

    cfg_path = config_dir / "config.toml"
    raw = _load_toml(cfg_path)

    try:
        return UserConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigError(f"Invalid user config in {cfg_path}", cause=exc) from exc
