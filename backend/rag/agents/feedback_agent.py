# backend/rag/agents/feedback_agent.py
"""
Feedback Agent for Multi-Candidate Root Cause Hypothesis Loop.
100% LangChain-Free.
Dynamically handles 2, 3, or N ranked candidates.
"""

from typing import Any, Dict, List, Optional

STATUS_CLOSED = "CLOSED"
STATUS_RETRY = "RETRY"
STATUS_ESCALATE = "ESCALATE"

def process_feedback(
    ticket: Dict[str, Any],
    fixed: bool,
    selected_rank: Optional[int] = None,
    root_cause: str = "",
    resolution: str = "",
    notes: str = "",
    operator: str = "NOC Operator"
) -> Dict[str, Any]:
    """
    Controls the RCA hypothesis feedback loop:
    YES -> CLOSED (RESOLVED)
    NO (attempts < total_candidates) -> RETRY (with next candidate)
    NO (all candidates rejected) -> ESCALATE
    """
    if not isinstance(ticket, dict):
        raise TypeError("ticket must be a dictionary.")

    ranked_causes = ticket.get("ranked_causes", [])
    if not ranked_causes and "rca_report" in ticket:
        ranked_causes = ticket["rca_report"].get("ranked_causes", [])

    if not ranked_causes:
        raise ValueError("No ranked RCA candidates available in ticket state.")

    total_candidates = len(ranked_causes)

    # Determine rank being acted on
    try:
        current_attempt = int(ticket.get("attempt", 0))
    except (TypeError, ValueError):
        current_attempt = 0

    if selected_rank is not None:
        rank_idx = int(selected_rank)
    else:
        rank_idx = current_attempt + 1

    candidate = None
    for c in ranked_causes:
        if int(c.get("rank", 0)) == rank_idx:
            candidate = c
            break
    if not candidate:
        candidate = ranked_causes[min(current_attempt, total_candidates - 1)]

    chosen_root_cause = root_cause or candidate.get("root_cause", "")
    chosen_resolution = resolution or candidate.get("resolution", "")

    # Operator Confirmed YES
    if fixed:
        ticket["status"] = STATUS_CLOSED
        ticket["feedback_fixed"] = True
        ticket["confirmed_root_cause"] = chosen_root_cause
        ticket["confirmed_resolution"] = chosen_resolution
        ticket["operator"] = operator
        ticket["operator_notes"] = notes
        ticket["memory_candidate"] = {
            "rank": rank_idx,
            "root_cause": chosen_root_cause,
            "resolution": chosen_resolution,
            "operator": operator,
            "notes": notes
        }

        return {
            "status": STATUS_CLOSED,
            "fixed": True,
            "selected_rank": rank_idx,
            "confirmed_root_cause": chosen_root_cause,
            "confirmed_resolution": chosen_resolution,
            "operator": operator,
            "notes": notes,
            "memory_candidate": ticket["memory_candidate"],
            "should_escalate": False
        }

    # Operator Rejected NO
    ticket["feedback_fixed"] = False
    rejected_ranks = list(ticket.get("rejected_ranks", []))
    if rank_idx not in rejected_ranks:
        rejected_ranks.append(rank_idx)
    ticket["rejected_ranks"] = sorted(rejected_ranks)

    new_attempt = len(rejected_ranks)
    ticket["attempt"] = new_attempt

    # Find next un-rejected candidate
    next_candidate = None
    for c in ranked_causes:
        if int(c.get("rank", 0)) not in rejected_ranks:
            next_candidate = c
            break

    # If there is another candidate and not all candidates are rejected
    if next_candidate is not None and new_attempt < total_candidates:
        ticket["status"] = STATUS_RETRY
        ticket["next_candidate"] = next_candidate
        return {
            "status": STATUS_RETRY,
            "fixed": False,
            "attempt": new_attempt,
            "rejected_ranks": rejected_ranks,
            "rejected_candidate": candidate,
            "next_candidate": next_candidate,
            "should_escalate": False
        }

    # All candidates (2, 3, or N) have been rejected -> ESCALATE
    ticket["status"] = STATUS_ESCALATE
    ticket["next_candidate"] = None
    ticket["escalation_reason"] = f"All {total_candidates} ranked RCA recommendations rejected by operator."
    return {
        "status": STATUS_ESCALATE,
        "fixed": False,
        "attempt": new_attempt,
        "rejected_ranks": rejected_ranks,
        "rejected_candidate": candidate,
        "next_candidate": None,
        "should_escalate": True,
        "escalation_reason": ticket["escalation_reason"]
    }

__all__ = ["process_feedback"]