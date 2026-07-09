"""Deterministic policy engine for PhyCode tool calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from phycode.events.models import (
    PolicyDecision,
    PolicyDecisionEnum,
    ToolCall,
    ToolSpec,
)
from phycode.policy.rules import DEFAULT_RULES


@dataclass(frozen=True)
class PolicyContext:
    workspace_root: Path
    allowlist: list[Path] = field(default_factory=list)
    policy_overrides: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False


class PolicyEngine:
    """Evaluate tool calls against layered rules."""

    def __init__(
        self,
        project_overrides: dict[str, Any] | None = None,
        runtime_overrides: dict[str, Any] | None = None,
    ) -> None:
        self._project_overrides = dict(project_overrides or {})
        self._runtime_overrides = dict(runtime_overrides or {})

    def evaluate(
        self,
        tool_call: ToolCall,
        tool_spec: ToolSpec,
        ctx: PolicyContext,
    ) -> PolicyDecision:
        for rid, override in self._runtime_overrides.items():
            if _rule_matches_override(rid, tool_call, tool_spec, ctx):
                return _build_override_decision(tool_call, rid, override, prefix="runtime")
        for rid, override in self._project_overrides.items():
            if _rule_matches_override(rid, tool_call, tool_spec, ctx):
                return _build_override_decision(tool_call, rid, override, prefix="project")
        for name, matcher, decision, reason in DEFAULT_RULES:
            if matcher(tool_call, tool_spec, ctx):
                return PolicyDecision(
                    tool_call_id=tool_call.id,
                    decision=decision,
                    rule_id=f"default.{name}",
                    reason=reason,
                    requires_user=decision == PolicyDecisionEnum.ask,
                )
        if tool_spec.risk_level.value == "safe":
            return PolicyDecision(
                tool_call_id=tool_call.id,
                decision=PolicyDecisionEnum.allow,
                rule_id="default.safe_allow",
                reason="Safe-risk tool with no other rule matched",
                requires_user=False,
            )
        return PolicyDecision(
            tool_call_id=tool_call.id,
            decision=PolicyDecisionEnum.ask,
            rule_id="default.unmatched_risky",
            reason="No rule matched but tool is risky",
            requires_user=True,
        )


def _build_override_decision(
    tool_call: ToolCall,
    rule_id: str,
    override: dict[str, Any],
    prefix: str,
) -> PolicyDecision:
    dec = PolicyDecisionEnum(override["decision"])
    return PolicyDecision(
        tool_call_id=tool_call.id,
        decision=dec,
        rule_id=f"{prefix}.{rule_id}",
        reason=str(override.get("reason", f"{prefix.title()} override")),
        requires_user=dec == PolicyDecisionEnum.ask,
    )


def _rule_matches_override(
    rule_id: str,
    tool_call: ToolCall,
    tool_spec: ToolSpec,
    ctx: PolicyContext,
) -> bool:
    """An override key matches a default rule if its matcher fires."""
    target = rule_id.split(".")[-1]
    for name, matcher, _, _ in DEFAULT_RULES:
        if name == target:
            return matcher(tool_call, tool_spec, ctx)
    return False
