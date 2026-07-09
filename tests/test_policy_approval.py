"""Tests for the approval state machine (T04)."""

from __future__ import annotations

import pytest

from phycode.events.models import (
    PolicyDecision,
    PolicyDecisionEnum,
    ToolCall,
)
from phycode.policy.approval import (
    ApprovalAction,
    ApprovalMachine,
    ApprovalState,
)


def _pending() -> tuple[ApprovalMachine, ToolCall, PolicyDecision]:
    machine = ApprovalMachine()
    tc = ToolCall(tool_name="file.write", args={"path": "out.txt", "content": "x"})
    # Register the tool_call_id as pending approval (not yet user_prompted)
    machine._pending_ids.add(tc.id)
    decision = PolicyDecision(
        tool_call_id=tc.id,
        decision=PolicyDecisionEnum.ask,
        rule_id="default.risky_action",
        reason="risky",
        requires_user=True,
    )
    return machine, tc, decision


def test_pending_to_user_prompted_to_approved() -> None:
    machine, tc, decision = _pending()
    machine.request_user_prompt(tc.id)
    assert machine.state_of(tc.id) == ApprovalState.user_prompted
    machine.decide(tc.id, ApprovalAction.approve)
    assert machine.state_of(tc.id) == ApprovalState.approved


def test_rejected_blocks_tool_call() -> None:
    machine, tc, decision = _pending()
    machine.request_user_prompt(tc.id)
    machine.decide(tc.id, ApprovalAction.reject)
    assert machine.state_of(tc.id) == ApprovalState.blocked


def test_reapprove_required_after_reject() -> None:
    """After rejection, the same tool_call_id must be re-promoted before approving."""
    machine, tc, decision = _pending()
    machine.request_user_prompt(tc.id)
    machine.decide(tc.id, ApprovalAction.reject)
    assert machine.state_of(tc.id) == ApprovalState.blocked
    # User changed their mind: must call request_user_prompt again
    machine.request_user_prompt(tc.id)
    machine.decide(tc.id, ApprovalAction.approve)
    assert machine.state_of(tc.id) == ApprovalState.approved


def test_unknown_tool_call_id_raises() -> None:
    machine = ApprovalMachine()
    with pytest.raises(KeyError):
        machine.decide("nonexistent-id", ApprovalAction.approve)


def test_double_prompt_is_idempotent() -> None:
    """Calling request_user_prompt twice for the same id should not reset the chain."""
    machine, tc, decision = _pending()
    machine.request_user_prompt(tc.id)
    machine.request_user_prompt(tc.id)
    assert machine.state_of(tc.id) == ApprovalState.user_prompted
    machine.decide(tc.id, ApprovalAction.approve)
    assert machine.state_of(tc.id) == ApprovalState.approved


def test_approve_before_prompt_raises() -> None:
    """Cannot approve a tool call that has not yet been prompted to the user."""
    machine, tc, _ = _pending()
    with pytest.raises(ValueError):
        machine.decide(tc.id, ApprovalAction.approve)
