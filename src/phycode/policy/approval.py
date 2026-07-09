"""Approval state machine for ask policy decisions."""

from __future__ import annotations

from enum import StrEnum


class ApprovalAction(StrEnum):
    approve = "approve"
    reject = "reject"


class ApprovalState(StrEnum):
    pending = "pending"
    user_prompted = "user_prompted"
    approved = "approved"
    blocked = "blocked"


class ApprovalMachine:
    """In-memory approval state map keyed by tool_call_id."""

    def __init__(self) -> None:
        self._states: dict[str, ApprovalState] = {}
        self._pending_ids: set[str] = set()  # track IDs that entered approval flow

    def state_of(self, tool_call_id: str) -> ApprovalState:
        if tool_call_id not in self._states:
            return ApprovalState.pending
        return self._states[tool_call_id]

    def request_user_prompt(self, tool_call_id: str) -> None:
        self._states[tool_call_id] = ApprovalState.user_prompted
        self._pending_ids.add(tool_call_id)

    def decide(self, tool_call_id: str, action: ApprovalAction) -> None:
        if tool_call_id not in self._pending_ids:
            raise KeyError(f"No pending approval for tool_call_id={tool_call_id!r}")
        current = self.state_of(tool_call_id)
        if current not in {ApprovalState.user_prompted, ApprovalState.blocked}:
            raise ValueError(
                f"Cannot decide on tool_call_id={tool_call_id} "
                f"in state {current.value!r}; must request_user_prompt first"
            )
        if action == ApprovalAction.approve:
            self._states[tool_call_id] = ApprovalState.approved
        else:
            self._states[tool_call_id] = ApprovalState.blocked
