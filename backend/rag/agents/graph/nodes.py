# backend/rag/agents/graph/nodes.py
"""LangGraph nodes. Existing agents remain the domain implementation."""

from .state import AgentState
from ..dispatch_agent import assign_dispatch, load_reference_data
from ..escalation_agent import escalate
from ..feedback_agent import process_feedback
from ..memory_agent import save_resolution
from ..rca_engine import generate_rca


def rca_node(state: AgentState) -> dict:
    ml_output = state.get("ml_output") or state.get("input_data", {})
    if not ml_output:
        return {"rca_report": {}, "ranked_causes": [], "status": "RCA_FAILED"}

    report = generate_rca(ml_output)
    causes = report.get("ranked_causes", [])
    if not causes:
        return {"rca_report": report, "ranked_causes": [], "status": "RCA_FAILED"}
    return {
        "rca_report": report,
        "semantic_incident": report.get("semantic_incident", {}),
        "knowledge_context": report.get("knowledge_context", []),
        "pattern_context": report.get("pattern_context", []),
        "ranked_causes": causes,
        "current_candidate": causes[0],
        "attempt": state.get("attempt", 0),
        "status": "RCA_COMPLETE",
    }


def dispatch_node(state: AgentState) -> dict:
    ml_output = state.get("ml_output") or {}
    candidate = state.get("current_candidate") or (state.get("ranked_causes", [{}])[0])
    input_data = state.get("input_data") or {}
    fault_sev = ml_output.get("predicted_fault_severity", ml_output.get("fault_severity", 0))

    fault = {
        "id": input_data.get("id"),
        "location": input_data.get("location"),
        "resource_type": input_data.get("resource_type"),
        "fault_severity": fault_sev,
        "root_cause": candidate.get("root_cause", ""),
        "recommended_solution": candidate.get("resolution", ""),
    }
    technicians, spare_parts = load_reference_data()
    result = assign_dispatch(fault, technicians, spare_parts)
    technician = result.get("technician")
    if technician is None:
        return {"fault": fault, "dispatch_result": result, "status": "ESCALATE"}
    
    ticket = {
        "ticket_id": str(fault["id"]),
        "location": fault["location"],
        "resource_type": fault["resource_type"],
        "fault_severity": fault["fault_severity"],
        "assigned_to": technician["technician_name"],
        "attempt": state.get("attempt", 0),
        "status": "OPEN",
        "ranked_causes": state.get("ranked_causes", []),
    }
    return {"fault": fault, "dispatch_result": result, "ticket": ticket, "status": "AWAITING_FEEDBACK"}


def feedback_node(state: AgentState) -> dict:
    ticket = dict(state.get("ticket") or {})
    if "ranked_causes" not in ticket and "ranked_causes" in state:
        ticket["ranked_causes"] = state["ranked_causes"]

    result = process_feedback(
        ticket=ticket,
        fixed=bool(state.get("feedback_fixed")),
        selected_rank=state.get("selected_rank"),
        root_cause=state.get("confirmed_root_cause", ""),
        resolution=state.get("confirmed_resolution", ""),
        notes=state.get("operator_notes", ""),
        operator=state.get("operator", "NOC Operator")
    )

    if result["status"] == "CLOSED":
        return {
            "ticket": ticket,
            "attempt": ticket.get("attempt", 0),
            "status": "CLOSED",
            "confirmed_root_cause": result.get("confirmed_root_cause", ""),
            "confirmed_resolution": result.get("confirmed_resolution", "")
        }
    if result["status"] == "RETRY":
        return {
            "ticket": ticket,
            "attempt": ticket.get("attempt", 1),
            "current_candidate": result.get("next_candidate"),
            "status": "RETRY",
        }
    return {
        "ticket": ticket,
        "attempt": ticket.get("attempt", 3),
        "status": "ESCALATE",
        "escalation_reason": result.get("escalation_reason", "All 3 automated RCA recommendations rejected.")
    }


def memory_node(state: AgentState) -> dict:
    candidate = state.get("current_candidate") or {}
    root_cause = state.get("confirmed_root_cause") or candidate.get("root_cause", "")
    resolution = state.get("confirmed_resolution") or candidate.get("resolution", "")
    ticket_id = state.get("input_data", {}).get("id") or state.get("ticket", {}).get("ticket_id")

    save_resolution(
        ml_output=state.get("ml_output") or {},
        semantic_incident=state.get("semantic_incident", {}),
        root_cause=root_cause,
        successful_action=resolution,
        ticket_id=ticket_id,
        operator=state.get("operator", "NOC Operator"),
        operator_notes=state.get("operator_notes", "")
    )
    return {"memory_saved": True, "status": "MEMORY_SAVED"}


def escalation_node(state: AgentState) -> dict:
    report = escalate(
        state.get("ticket", {"ticket_id": state.get("input_data", {}).get("id", "UNKNOWN")}),
        reason=state.get("escalation_reason", "No dispatch could be assigned or all 3 ranked RCA recommendations rejected.")
    )
    return {"escalation": report, "status": "ESCALATED"}
