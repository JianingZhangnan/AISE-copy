"""Tests for the policy engine (T04 - core depth dimension)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from phycode.events.models import (
    PolicyDecisionEnum,
    RiskLevel,
    ToolCall,
    ToolSpec,
)
from phycode.policy.engine import PolicyContext, PolicyEngine


def _ws(tmp_path: Path) -> Path:
    """Return a workspace root inside tmp_path."""
    root = tmp_path / "workspace"
    root.mkdir()
    return root


def _read_tool() -> ToolSpec:
    return ToolSpec(
        name="file.read",
        description="Read a file",
        parameters={"path": "string"},
        risk_level=RiskLevel.safe,
    )


def _write_tool() -> ToolSpec:
    return ToolSpec(
        name="file.write",
        description="Write a file",
        parameters={"path": "string", "content": "string"},
        risk_level=RiskLevel.risky,
    )


def _shell_tool(risk: RiskLevel = RiskLevel.safe) -> ToolSpec:
    return ToolSpec(
        name="shell.run",
        description="Run shell command",
        parameters={"command": "string"},
        risk_level=risk,
    )


def _make_engine(project_overrides: dict[str, Any] | None = None) -> PolicyEngine:
    return PolicyEngine(project_overrides=project_overrides or {})


def test_safe_read_inside_workspace_allows(tmp_path: Path) -> None:
    """Reading a file inside the workspace with a safe tool -> allow."""
    root = _ws(tmp_path)
    target = root / "README.md"
    target.write_text("# hi", encoding="utf-8")
    engine = _make_engine()
    ctx = PolicyContext(
        workspace_root=root,
        allowlist=[],
        dry_run=False,
    )
    decision = engine.evaluate(
        ToolCall(tool_name="file.read", args={"path": str(target)}),
        _read_tool(),
        ctx,
    )
    assert decision.decision == PolicyDecisionEnum.allow
    assert decision.rule_id.startswith("default.")


def test_workspace_escape_denies(tmp_path: Path) -> None:
    """Writing to a path outside the workspace -> deny."""
    root = _ws(tmp_path)
    engine = _make_engine()
    ctx = PolicyContext(workspace_root=root, allowlist=[], dry_run=False)
    decision = engine.evaluate(
        ToolCall(tool_name="file.write", args={"path": "../etc/passwd", "content": "x"}),
        _write_tool(),
        ctx,
    )
    assert decision.decision == PolicyDecisionEnum.deny
    assert "escape" in decision.reason.lower() or "outside" in decision.reason.lower()


def test_credential_read_denied(tmp_path: Path) -> None:
    """Reading a credential file (.env) inside workspace -> deny."""
    root = _ws(tmp_path)
    (root / ".env").write_text("KEY=secret", encoding="utf-8")
    engine = _make_engine()
    ctx = PolicyContext(workspace_root=root, allowlist=[], dry_run=False)
    decision = engine.evaluate(
        ToolCall(tool_name="file.read", args={"path": str(root / ".env")}),
        _read_tool(),
        ctx,
    )
    assert decision.decision == PolicyDecisionEnum.deny
    assert decision.rule_id == "default.credential_files_blocked"


def test_credential_read_denied_pem(tmp_path: Path) -> None:
    """Reading a .pem file -> deny."""
    root = _ws(tmp_path)
    (root / "id_rsa.pem").write_text("priv", encoding="utf-8")
    engine = _make_engine()
    ctx = PolicyContext(workspace_root=root, allowlist=[], dry_run=False)
    decision = engine.evaluate(
        ToolCall(tool_name="file.read", args={"path": str(root / "id_rsa.pem")}),
        _read_tool(),
        ctx,
    )
    assert decision.decision == PolicyDecisionEnum.deny
    assert decision.rule_id == "default.credential_files_blocked"


def test_file_write_requires_approval(tmp_path: Path) -> None:
    """Writing a file inside workspace requires user approval (ask)."""
    root = _ws(tmp_path)
    engine = _make_engine()
    ctx = PolicyContext(workspace_root=root, allowlist=[], dry_run=False)
    decision = engine.evaluate(
        ToolCall(tool_name="file.write", args={"path": str(root / "out.txt"), "content": "x"}),
        _write_tool(),
        ctx,
    )
    assert decision.decision == PolicyDecisionEnum.ask
    assert decision.requires_user is True


def test_dangerous_shell_denied(tmp_path: Path) -> None:
    """A shell command matching dangerous patterns -> deny."""
    root = _ws(tmp_path)
    engine = _make_engine()
    ctx = PolicyContext(workspace_root=root, allowlist=[], dry_run=False)
    decision = engine.evaluate(
        ToolCall(tool_name="shell.run", args={"command": "rm -rf /"}),
        _shell_tool(),
        ctx,
    )
    assert decision.decision == PolicyDecisionEnum.deny
    assert decision.rule_id == "default.shell_dangerous_block"


def test_safe_shell_allows(tmp_path: Path) -> None:
    """A safe shell command with safe tool risk level -> allow."""
    root = _ws(tmp_path)
    engine = _make_engine()
    ctx = PolicyContext(workspace_root=root, allowlist=[], dry_run=False)
    decision = engine.evaluate(
        ToolCall(tool_name="shell.run", args={"command": "pytest -q"}),
        _shell_tool(risk=RiskLevel.safe),
        ctx,
    )
    assert decision.decision == PolicyDecisionEnum.allow


def test_project_override_beats_default(tmp_path: Path) -> None:
    """Project-level overrides should take precedence over default rules."""
    root = _ws(tmp_path)
    target = root / "README.md"
    target.write_text("# hi", encoding="utf-8")
    engine = _make_engine(
        project_overrides={
            "default.safe_allow": {
                "decision": "ask",
                "reason": "Project wants all reads approved",
            }
        }
    )
    ctx = PolicyContext(workspace_root=root, allowlist=[], dry_run=False)
    decision = engine.evaluate(
        ToolCall(tool_name="file.read", args={"path": str(target)}),
        _read_tool(),
        ctx,
    )
    assert decision.decision == PolicyDecisionEnum.ask
    assert decision.rule_id == "project.default.safe_allow"


def test_symlink_escape_denied(tmp_path: Path) -> None:
    """Reading a symlink that escapes workspace -> deny."""
    root = _ws(tmp_path)
    external = tmp_path / "external"
    external.mkdir()
    (external / "secret.txt").write_text("hush", encoding="utf-8")
    link = root / "link.txt"
    try:
        link.symlink_to(external / "secret.txt")
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported on this platform")
    engine = _make_engine()
    ctx = PolicyContext(workspace_root=root, allowlist=[], dry_run=False)
    decision = engine.evaluate(
        ToolCall(tool_name="file.read", args={"path": str(link)}),
        _read_tool(),
        ctx,
    )
    assert decision.decision == PolicyDecisionEnum.deny


def test_decision_includes_rule_id_and_reason(tmp_path: Path) -> None:
    """Every decision must include rule_id and reason (audit trail)."""
    root = _ws(tmp_path)
    engine = _make_engine()
    ctx = PolicyContext(workspace_root=root, allowlist=[], dry_run=False)
    decision = engine.evaluate(
        ToolCall(tool_name="file.read", args={"path": str(root / "x.txt")}),
        _read_tool(),
        ctx,
    )
    assert decision.rule_id
    assert decision.reason
