"""Core Pydantic models for the PhyCode harness.

Schema version: 1
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Module-level schema version constant
SCHEMA_VERSION = "1"


class EventType(StrEnum):
    """All event types emitted by the agent loop (mirrors SPEC §5.4)."""

    assistant_commentary = "assistant_commentary"
    reasoning_summary = "reasoning_summary"
    tool_call_requested = "tool_call_requested"
    policy_decision = "policy_decision"
    tool_call_running = "tool_call_running"
    tool_call_output = "tool_call_output"
    feedback_signal = "feedback_signal"
    assistant_final = "assistant_final"
    error = "error"
    incomplete = "incomplete"
    user_interrupt = "user_interrupt"


class RiskLevel(StrEnum):
    """Risk classification for tools."""

    safe = "safe"
    risky = "risky"
    dangerous = "dangerous"


class PolicyDecisionEnum(StrEnum):
    """Policy enforcement decision."""

    allow = "allow"
    ask = "ask"
    deny = "deny"


class FeedbackKind(StrEnum):
    """Kinds of feedback signals from the feedback loop."""

    success = "success"
    command_failed = "command_failed"
    test_failed = "test_failed"
    policy_blocked = "policy_blocked"
    policy_requires_approval = "policy_requires_approval"
    invalid_tool_args = "invalid_tool_args"
    tool_error = "tool_error"
    timeout = "timeout"
    output_truncated = "output_truncated"
    repeat_stuck = "repeat_stuck"


class MemoryCategory(StrEnum):
    """Categories for memory entries."""

    decision = "decision"
    preference = "preference"
    project_fact = "project_fact"
    test_command = "test_command"


class SessionMode(StrEnum):
    """CLI session mode."""

    interactive = "interactive"
    non_interactive = "non_interactive"


class ToolSpec(BaseModel):
    """Specification for a registered tool."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for the tool's parameters
    risk_level: RiskLevel = RiskLevel.safe


class ToolCall(BaseModel):
    """A request to execute a tool."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result from a tool execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_call_id: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0


class PolicyDecision(BaseModel):
    """Decision made by the policy engine for a tool call."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_call_id: str
    decision: PolicyDecisionEnum
    rule_id: str
    reason: str
    requires_user: bool = False


# Kinds for which retryable=True by default (failure categories).
_RETRYABLE_ON_FAILURE = {
    FeedbackKind.command_failed,
    FeedbackKind.test_failed,
    FeedbackKind.tool_error,
    FeedbackKind.timeout,
}


class FeedbackSignal(BaseModel):
    """Signal from the feedback loop back to the agent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: FeedbackKind
    summary: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False
    suggested_next_step: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _default_retryable_from_kind(cls, data: Any) -> Any:
        # Resolve the _RETRYABLE_ON_FAILURE set using globals to avoid import
        # cycles (FeedbackKind is defined at module level before this class).
        retryable_kinds = {
            FeedbackKind.command_failed,
            FeedbackKind.test_failed,
            FeedbackKind.tool_error,
            FeedbackKind.timeout,
        }
        if isinstance(data, dict):
            if data.get("retryable") is None:
                kind_val = data.get("kind")
                if isinstance(kind_val, FeedbackKind) and kind_val in retryable_kinds:
                    data["retryable"] = True
        return data


class MemoryEntry(BaseModel):
    """An entry in the agent's memory store."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    category: MemoryCategory
    key: str
    value: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class AgentEvent(BaseModel):
    """A single event in the agent trace."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    trace_id: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class Session(BaseModel):
    """A complete agent session."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_root: str
    mode: SessionMode = SessionMode.interactive
    schema_version: str = SCHEMA_VERSION
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
