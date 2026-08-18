"""Explicit conditional routes for the telecom LangGraph workflow."""

from .state import AgentState


def route_after_rca(state: AgentState) -> str:
    return "dispatch" if state.get("status") == "RCA_COMPLETE" else "escalation"


def route_after_dispatch(state: AgentState) -> str:
    return "feedback" if state.get("status") == "AWAITING_FEEDBACK" else "escalation"


def route_after_feedback(state: AgentState) -> str:
    status = state.get("status")
    if status == "CLOSED":
        return "memory"
    if status == "RETRY":
        return "dispatch"
    return "escalation"
