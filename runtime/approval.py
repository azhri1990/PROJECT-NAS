"""Action-bound human approval contracts for governed JARVIS execution."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from uuid import uuid4


def action_fingerprint(tool_name: str, version: str, payload: dict) -> str:
    """Return a stable fingerprint for the exact executable action."""
    canonical = json.dumps(
        {"tool": tool_name, "version": version, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class ApprovalRequired(PermissionError):
    """Raised when a human approval is required before execution."""

    def __init__(self, proposal_id: str) -> None:
        self.proposal_id = proposal_id
        super().__init__(f"explicit approval required for proposal {proposal_id}")


@dataclass(frozen=True)
class ActionProposal:
    proposal_id: str
    tool_name: str
    version: str
    payload: dict
    risk: str
    reason: str
    fingerprint: str


@dataclass(frozen=True)
class ApprovalReceipt:
    proposal_id: str
    fingerprint: str
    approval_id: str


class ApprovalManager:
    """In-process, one-shot approval store for consequential actions."""

    def __init__(self) -> None:
        self._proposals: dict[str, ActionProposal] = {}
        self._approved: dict[str, ApprovalReceipt] = {}
        self._consumed: set[str] = set()

    def propose(
        self,
        *,
        tool_name: str,
        version: str,
        payload: dict,
        risk: str,
        reason: str,
    ) -> ActionProposal:
        fingerprint = action_fingerprint(tool_name, version, payload)
        proposal = ActionProposal(
            proposal_id=uuid4().hex,
            tool_name=tool_name,
            version=version,
            payload=dict(payload),
            risk=risk,
            reason=reason,
            fingerprint=fingerprint,
        )
        self._proposals[proposal.proposal_id] = proposal
        return proposal

    def require(self, proposal_id: str) -> ActionProposal:
        try:
            return self._proposals[proposal_id]
        except KeyError as exc:
            raise ApprovalRequired(proposal_id) from exc

    def approve(self, proposal_id: str) -> ApprovalReceipt:
        proposal = self.require(proposal_id)
        receipt = ApprovalReceipt(
            proposal_id=proposal.proposal_id,
            fingerprint=proposal.fingerprint,
            approval_id=uuid4().hex,
        )
        self._approved[proposal.proposal_id] = receipt
        return receipt

    def consume(self, receipt: ApprovalReceipt, proposal: ActionProposal) -> bool:
        if receipt.proposal_id in self._consumed:
            return False
        approved = self._approved.get(receipt.proposal_id)
        if approved != receipt:
            return False
        if proposal.proposal_id != receipt.proposal_id:
            return False
        if proposal.fingerprint != receipt.fingerprint:
            return False
        self._consumed.add(receipt.proposal_id)
        return True

    def consume_for_action(
        self,
        receipt: ApprovalReceipt,
        *,
        tool_name: str,
        version: str,
        payload: dict,
    ) -> bool:
        """Consume approval only when it matches the exact current action."""
        proposal = self.require(receipt.proposal_id)
        if proposal.tool_name != tool_name or proposal.version != version:
            return False
        if action_fingerprint(tool_name, version, payload) != proposal.fingerprint:
            return False
        return self.consume(receipt, proposal)
