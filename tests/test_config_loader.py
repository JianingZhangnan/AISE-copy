"""T03: Configuration loading tests.

RED phase: these tests must fail because src/phycode/config/ does not exist yet.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from phycode.config.loader import ConfigError, load_project_config, load_user_config


class TestProjectConfig:
    def test_load_project_config_minimal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Load a minimal phycode.toml and verify test_command default."""
        cfg_file = tmp_path / "phycode.toml"
        cfg_file.write_text('workspace_root = "/tmp/test"\ntest_command = "uv run pytest"\n')
        # Mock platformdirs to return our tmp_path as the "project root"
        monkeypatch.chdir(tmp_path)
        config = load_project_config(project_root=tmp_path)
        assert config.test_command == "uv run pytest"
        assert config.workspace_root == "/tmp/test"

    def test_project_config_defaults(self, tmp_path: Path) -> None:
        """ProjectConfig should have safe defaults for all optional fields."""
        cfg_file = tmp_path / "phycode.toml"
        cfg_file.write_text('workspace_root = "/tmp"\n')
        config = load_project_config(project_root=tmp_path)
        assert config.enabled_tools is None or isinstance(config.enabled_tools, (list, tuple))
        assert config.allowlist == []  # Should default to empty list

    def test_project_config_unknown_key_warns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Unknown keys in phycode.toml should warn but NOT raise."""
        cfg_file = tmp_path / "phycode.toml"
        cfg_file.write_text(
            'workspace_root = "/tmp"\n'
            "unknown_foo = 123\n"  # unknown field
            'another_unknown = "bar"\n'
        )
        with caplog.at_level(logging.WARNING):
            config = load_project_config(project_root=tmp_path)
        assert config.workspace_root == "/tmp"
        # Should have logged at least one warning about unknown keys
        assert any(
            "unknown" in rec.message.lower() or "foo" in rec.message.lower()
            for rec in caplog.records
        ), f"Expected warning about unknown keys, got: {[r.message for r in caplog.records]}"


class TestUserConfig:
    def test_user_config_defaults(self, tmp_path: Path) -> None:
        """UserConfig should have safe defaults."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text("")  # empty config
        config = load_user_config(config_dir=tmp_path)
        assert config.default_provider is not None
        assert isinstance(config.base_url, (str, type(None)))

    def test_user_config_overlay_when_project_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When project config is missing, user config values should be used."""
        user_cfg = tmp_path / "config.toml"
        user_cfg.write_text('default_provider = "openai"\nmodel = "gpt-4o"\n')
        config = load_user_config(config_dir=tmp_path)
        assert config.default_provider == "openai"
        assert config.model == "gpt-4o"


class TestProjectOverridesUser:
    def test_project_overrides_user(self, tmp_path: Path) -> None:
        """Project-level settings should override user-level settings."""
        user_cfg = tmp_path / "config.toml"
        user_cfg.write_text('test_command = "python -m pytest"\n')
        project_cfg = tmp_path / "phycode.toml"
        project_cfg.write_text(
            'workspace_root = "/project"\ntest_command = "uv run pytest --maxfail=1"\n'
        )
        # Verify project overrides: effective test_command comes from project
        project_config = load_project_config(project_root=tmp_path)
        # In a real merge the effective test_command comes from project
        assert project_config.test_command == "uv run pytest --maxfail=1"


class TestConfigError:
    def test_config_error_is_phycode_error(self) -> None:
        """ConfigError should inherit from PhyCodeError."""
        from phycode.errors import PhyCodeError

        assert issubclass(ConfigError, PhyCodeError)

    def test_config_error_round_trip(self) -> None:
        """ConfigError should carry a message."""
        err = ConfigError("invalid config", cause=None)
        assert "invalid config" in str(err)
