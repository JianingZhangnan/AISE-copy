"""T01: Core Pydantic data model tests."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

import phycode.events.models as models_module
from phycode.events.models import (
    SCHEMA_VERSION,
    AgentEvent,
    EventType,
    FeedbackKind,
    FeedbackSignal,
    MemoryCategory,
    PolicyDecision,
    PolicyDecisionEnum,
    RiskLevel,
    Session,
    SessionMode,
    ToolCall,
    ToolResult,
    ToolSpec,
)


class TestAgentEvent:
    def test_agent_event_minimal_round_trip(self) -> None:
        event = AgentEvent(type=EventType.assistant_commentary)
        data = event.model_dump()
        restored = AgentEvent.model_validate(data)
        assert restored.id == event.id
        assert restored.type == event.type

    def test_agent_event_with_payload_round_trip(self) -> None:
        event = AgentEvent(type=EventType.tool_call_output, payload={"output": "hello world"})
        data = event.model_dump()
        restored = AgentEvent.model_validate(data)
        assert restored.payload == {"output": "hello world"}

    def test_agent_event_timestamp_auto_generated(self) -> None:
        event = AgentEvent(type=EventType.error)
        assert event.timestamp is not None
        assert event.timestamp.endswith("Z") or event.timestamp.endswith("+00:00")

    def test_agent_event_id_auto_generated(self) -> None:
        event = AgentEvent(type=EventType.feedback_signal)
        uuid.UUID(event.id)

    def test_agent_event_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            AgentEvent.model_validate({"type": "assistant_commentary", "unknown_field": True})

    def test_agent_event_required_type(self) -> None:
        with pytest.raises(ValidationError):
            AgentEvent.model_validate({})


class TestPolicyDecision:
    def test_policy_decision_allow(self) -> None:
        pd = PolicyDecision(
            tool_call_id="tc-001",
            decision=PolicyDecisionEnum.allow,
            rule_id="default.safe_allow",
            reason="tool is low risk",
        )
        assert pd.decision == PolicyDecisionEnum.allow
        assert pd.requires_user is False

    def test_policy_decision_deny(self) -> None:
        pd = PolicyDecision(
            tool_call_id="tc-001",
            decision=PolicyDecisionEnum.deny,
            rule_id="default.risky_action",
            reason="dangerous tool",
        )
        assert pd.decision == PolicyDecisionEnum.deny

    def test_policy_decision_ask(self) -> None:
        pd = PolicyDecision(
            tool_call_id="tc-001",
            decision=PolicyDecisionEnum.ask,
            rule_id="default.risky_action",
            reason="requires approval",
            requires_user=True,
        )
        assert pd.requires_user is True

    def test_policy_decision_requires_user_default_false(self) -> None:
        pd = PolicyDecision(
            tool_call_id="tc-001",
            decision=PolicyDecisionEnum.allow,
            rule_id="default.safe_allow",
            reason="ok",
        )
        assert pd.requires_user is False

    def test_policy_decision_round_trip(self) -> None:
        pd = PolicyDecision(
            tool_call_id="tc-001",
            decision=PolicyDecisionEnum.allow,
            rule_id="default.safe_allow",
            reason="ok",
        )
        data = pd.model_dump()
        restored = PolicyDecision.model_validate(data)
        assert restored.decision == pd.decision

    def test_policy_decision_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            PolicyDecision.model_validate(
                {
                    "tool_call_id": "tc-001",
                    "decision": "allow",
                    "rule_id": "default.safe_allow",
                    "reason": "ok",
                    "unknown_field": True,
                }
            )


class TestFeedbackSignal:
    def test_feedback_signal_success_defaults_retryable_false(self) -> None:
        fs = FeedbackSignal(kind=FeedbackKind.success, summary="All good")
        assert fs.retryable is False
        assert fs.suggested_next_step is None

    def test_feedback_signal_retryable_on_failure_kinds(self) -> None:
        for kind in (
            FeedbackKind.command_failed,
            FeedbackKind.test_failed,
            FeedbackKind.tool_error,
            FeedbackKind.timeout,
        ):
            fs = FeedbackSignal(kind=kind, summary="error")
            assert fs.retryable is True, f"{kind} should be retryable"

    def test_feedback_signal_non_retryable_kinds(self) -> None:
        for kind in (
            FeedbackKind.success,
            FeedbackKind.policy_blocked,
            FeedbackKind.policy_requires_approval,
            FeedbackKind.invalid_tool_args,
            FeedbackKind.output_truncated,
            FeedbackKind.repeat_stuck,
        ):
            fs = FeedbackSignal(kind=kind, summary="msg")
            assert fs.retryable is False, f"{kind} should not be retryable"

    def test_feedback_signal_round_trip(self) -> None:
        fs = FeedbackSignal(
            kind=FeedbackKind.command_failed,
            summary="ls failed",
            evidence={"exit_code": 1},
            suggested_next_step="check the command",
            retryable=True,
        )
        data = fs.model_dump()
        restored = FeedbackSignal.model_validate(data)
        assert restored.kind == fs.kind
        assert restored.retryable is True

    def test_feedback_kind_repeat_stuck_exists(self) -> None:
        assert hasattr(FeedbackKind, "repeat_stuck")


class TestToolSpec:
    def test_tool_spec_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ToolSpec.model_validate(
                {
                    "name": "bash",
                    "description": "run commands",
                    "parameters": {},
                    "risk_level": "safe",
                    "unknown_field": True,
                }
            )

    def test_tool_spec_risk_levels(self) -> None:
        for level in (RiskLevel.safe, RiskLevel.risky, RiskLevel.dangerous):
            spec = ToolSpec(
                name="bash", description="run commands", parameters={}, risk_level=level
            )
            assert spec.risk_level == level

    def test_tool_spec_default_risk_safe(self) -> None:
        spec = ToolSpec(name="ls", description="list files", parameters={})
        assert spec.risk_level == RiskLevel.safe

    def test_tool_spec_round_trip(self) -> None:
        spec = ToolSpec(
            name="bash",
            description="run commands",
            parameters={"type": "object", "properties": {}},
            risk_level=RiskLevel.risky,
        )
        data = spec.model_dump()
        restored = ToolSpec.model_validate(data)
        assert restored.name == spec.name


class TestToolCall:
    def test_tool_call_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ToolCall.model_validate({"tool_name": "bash", "args": {}, "unknown_extra": True})

    def test_tool_call_round_trip(self) -> None:
        tc = ToolCall(tool_name="bash", args={"command": "ls"})
        data = tc.model_dump()
        restored = ToolCall.model_validate(data)
        assert restored.tool_name == tc.tool_name
        assert restored.args == {"command": "ls"}

    def test_tool_call_id_auto_generated(self) -> None:
        tc = ToolCall(tool_name="bash", args={})
        uuid.UUID(tc.id)


class TestToolResult:
    def test_tool_result_success(self) -> None:
        result = ToolResult(tool_call_id="tc-001", stdout="hello world", exit_code=0)
        assert result.stdout == "hello world"
        assert result.exit_code == 0

    def test_tool_result_failure(self) -> None:
        result = ToolResult(tool_call_id="tc-001", stdout="", stderr="exit code 1", exit_code=1)
        assert result.exit_code == 1

    def test_tool_result_round_trip(self) -> None:
        tr = ToolResult(
            tool_call_id="tc-001", stdout="ok", stderr="", exit_code=0, duration_ms=123.4
        )
        data = tr.model_dump()
        restored = ToolResult.model_validate(data)
        assert restored.tool_call_id == tr.tool_call_id
        assert restored.duration_ms == 123.4

    def test_tool_result_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ToolResult.model_validate(
                {"tool_call_id": "tc-001", "stdout": "ok", "unknown_field": True}
            )


class TestSession:
    def test_session_requires_workspace_root(self) -> None:
        with pytest.raises(ValidationError):
            Session.model_validate({})

    def test_session_default_mode_interactive(self) -> None:
        session = Session(workspace_root="/tmp")
        assert session.mode == SessionMode.interactive

    def test_session_non_interactive_mode(self) -> None:
        session = Session(workspace_root="/tmp", mode=SessionMode.non_interactive)
        assert session.mode == SessionMode.non_interactive

    def test_session_schema_version(self) -> None:
        session = Session(workspace_root="/tmp")
        assert session.schema_version == SCHEMA_VERSION

    def test_session_round_trip(self) -> None:
        session = Session(workspace_root="/tmp", mode=SessionMode.interactive)
        data = session.model_dump()
        restored = Session.model_validate(data)
        assert restored.workspace_root == "/tmp"

    def test_session_id_auto_generated(self) -> None:
        session = Session(workspace_root="/tmp")
        uuid.UUID(session.id)

    def test_session_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            Session.model_validate({"workspace_root": "/tmp", "unknown_field": True})


class TestEventType:
    def test_event_type_has_all_required_values(self) -> None:
        required = {
            "assistant_commentary",
            "tool_call_requested",
            "policy_decision",
            "tool_call_running",
            "tool_call_output",
            "feedback_signal",
            "assistant_final",
            "error",
            "incomplete",
            "user_interrupt",
            "reasoning_summary",
        }
        members = {e.value for e in EventType}
        assert required.issubset(members), f"Missing: {required - members}"


class TestFeedbackKind:
    def test_feedback_kind_has_all_required_values(self) -> None:
        required = {
            "success",
            "command_failed",
            "test_failed",
            "tool_error",
            "timeout",
            "policy_blocked",
            "policy_requires_approval",
            "repeat_stuck",
            "invalid_tool_args",
            "output_truncated",
        }
        members = {e.value for e in FeedbackKind}
        assert required.issubset(members), f"Missing: {required - members}"


class TestMemoryCategory:
    def test_memory_category_has_required_values(self) -> None:
        required = {"decision", "preference", "project_fact", "test_command"}
        members = {e.value for e in MemoryCategory}
        assert required.issubset(members), f"Missing: {required - members}"


class TestRiskLevel:
    def test_risk_level_values(self) -> None:
        assert {e.value for e in RiskLevel} == {"safe", "risky", "dangerous"}


class TestSchemaVersion:
    def test_schema_version_exists(self) -> None:
        assert hasattr(models_module, "SCHEMA_VERSION")
        assert isinstance(SCHEMA_VERSION, str)

    def test_session_uses_schema_version(self) -> None:
        session = Session(workspace_root="/tmp")
        assert session.schema_version == SCHEMA_VERSION
