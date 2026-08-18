# backend/rag/agents/escalation_agent.py
"""
Tier-3 NOC Engineering Escalation Agent.
100% LangChain-Free.
"""

from datetime import datetime, timezone
from typing import Any, Dict

def escalate(
    ticket: Dict[str, Any],
    reason: str = "All 3 automated RCA recommendations rejected by operator."
) -> Dict[str, Any]:
    """
    Escalate unresolved incident to the human Tier-3 NOC engineering team.
    """
    if not isinstance(ticket, dict):
        raise TypeError("ticket must be a dictionary.")

    ticket_id = str(ticket.get("ticket_id", ticket.get("id", "UNKNOWN")))
    now_iso = datetime.now(timezone.utc).isoformat()

    return {
        "ticket_id": ticket_id,
        "status": "ESCALATED",
        "reason": reason,
        "assigned_group": "NOC_ENGINEERING_TEAM",
        "priority": "HIGH",
        "escalated_at": now_iso
    }

__all__ = ["escalate"]