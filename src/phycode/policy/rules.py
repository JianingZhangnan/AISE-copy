"""Default policy rules for the policy engine."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from phycode.events.models import (
    PolicyDecisionEnum,
    ToolCall,
    ToolSpec,
)

if TYPE_CHECKING:
    from phycode.policy.engine import PolicyContext

MatchFn = Callable[[ToolCall, ToolSpec, "PolicyContext"], bool]

PATH_TOOLS = {
    "file.read",
    "file.write",
    "file.edit",
    "config.read",
    "config.write",
    "memory.read",
    "memory.write",
    "workspace.status",
}

CREDENTIAL_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".pem",
    ".key",
}
CREDENTIAL_GLOBS = (
    "id_rsa",
    "id_dsa",
    "id_ed25519",
    "credentials",
)


def _resolved_path(tool_call: ToolCall, ctx: PolicyContext) -> Path | None:
    arg = tool_call.args.get("path")
    if not isinstance(arg, str):
        arg = tool_call.args.get("file_path")
    if not isinstance(arg, str):
        return None
    candidate = Path(arg)
    if not candidate.is_absolute():
        candidate = ctx.workspace_root / candidate
    try:
        return candidate.resolve(strict=False)
    except OSError:
        return candidate


def _is_within_workspace(path: Path, ctx: PolicyContext) -> bool:
    try:
        root = ctx.workspace_root.resolve(strict=False)
        target = path.resolve(strict=False)
        return target.is_relative_to(root)
    except (OSError, ValueError):
        return False


def _is_credential_path(path: Path) -> bool:
    name = path.name.lower()
    if name in {n.lower() for n in CREDENTIAL_NAMES}:
        return True
    for token in CREDENTIAL_GLOBS:
        if token in name:
            return True
    return name.endswith(".pem") or name.endswith(".key")


def rule_credential_files_blocked(
    tool_call: ToolCall, tool_spec: ToolSpec, ctx: PolicyContext
) -> bool:
    if tool_spec.name not in {"file.read", "file.write", "file.edit"}:
        return False
    path = _resolved_path(tool_call, ctx)
    if path is None:
        return False
    return _is_credential_path(path)


def rule_symlink_escape(tool_call: ToolCall, tool_spec: ToolSpec, ctx: PolicyContext) -> bool:
    if tool_spec.name not in PATH_TOOLS:
        return False
    path = _resolved_path(tool_call, ctx)
    if path is None or not path.exists():
        return False
    if not path.is_symlink():
        return False
    try:
        root = ctx.workspace_root.resolve(strict=False)
        real = path.resolve(strict=False)
        return not real.is_relative_to(root)
    except (OSError, ValueError):
        return True


def rule_write_outside_workspace(
    tool_call: ToolCall, tool_spec: ToolSpec, ctx: PolicyContext
) -> bool:
    if tool_spec.name not in {"file.write", "file.edit"}:
        return False
    path = _resolved_path(tool_call, ctx)
    if path is None:
        return False
    if _is_credential_path(path):
        return False
    return not _is_within_workspace(path, ctx)


def rule_path_in_workspace(tool_call: ToolCall, tool_spec: ToolSpec, ctx: PolicyContext) -> bool:
    if tool_spec.name not in PATH_TOOLS:
        return False
    path = _resolved_path(tool_call, ctx)
    if path is None:
        return False
    return not _is_within_workspace(path, ctx)


def rule_shell_safe(tool_call: ToolCall, tool_spec: ToolSpec, ctx: PolicyContext) -> bool:
    if tool_spec.name != "shell.run":
        return False
    if tool_spec.risk_level.value != "safe":
        return False
    cmd = tool_call.args.get("command")
    if not isinstance(cmd, str):
        return False
    from phycode.policy.dangerous_patterns import is_dangerous_command

    return not is_dangerous_command(cmd)


def rule_shell_dangerous(tool_call: ToolCall, tool_spec: ToolSpec, ctx: PolicyContext) -> bool:
    if tool_spec.name != "shell.run":
        return False
    cmd = tool_call.args.get("command")
    if not isinstance(cmd, str):
        return False
    from phycode.policy.dangerous_patterns import is_dangerous_command

    return is_dangerous_command(cmd)


def rule_safe_allow(tool_call: ToolCall, tool_spec: ToolSpec, ctx: PolicyContext) -> bool:
    return tool_spec.risk_level.value == "safe"


def rule_risky_action(tool_call: ToolCall, tool_spec: ToolSpec, ctx: PolicyContext) -> bool:
    return tool_spec.risk_level.value == "risky"


RuleEntry = tuple[str, MatchFn, PolicyDecisionEnum, str]

# Order matters: more specific/specific rules come before general ones.
# Dangerous patterns must be checked BEFORE safe_allow to block dangerous commands.
DEFAULT_RULES: list[RuleEntry] = [
    (
        "shell_dangerous_block",
        rule_shell_dangerous,
        PolicyDecisionEnum.deny,
        "Command matches a dangerous-pattern blacklist",
    ),
    (
        "credential_files_blocked",
        rule_credential_files_blocked,
        PolicyDecisionEnum.deny,
        "Reading or modifying credential files is denied by policy",
    ),
    (
        "symlink_safe",
        rule_symlink_escape,
        PolicyDecisionEnum.deny,
        "Symlink points outside the workspace",
    ),
    (
        "write_outside_workspace",
        rule_write_outside_workspace,
        PolicyDecisionEnum.deny,
        "Target path is outside the workspace",
    ),
    (
        "path_in_workspace",
        rule_path_in_workspace,
        PolicyDecisionEnum.deny,
        "Path argument is outside the workspace",
    ),
    (
        "shell_safe",
        rule_shell_safe,
        PolicyDecisionEnum.allow,
        "Safe-shell command with no dangerous patterns",
    ),
    (
        "safe_allow",
        rule_safe_allow,
        PolicyDecisionEnum.allow,
        "Safe-risk tool with no other rule matched",
    ),
    (
        "risky_action",
        rule_risky_action,
        PolicyDecisionEnum.ask,
        "Risk-bearing tool action requires approval",
    ),
]
