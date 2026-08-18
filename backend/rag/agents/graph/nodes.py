"""LangGraph nodes. Existing agents remain the domain implementation."""

from .state import AgentState
from ..dispatch_agent import assign_dispatch, load_reference_data
from ..escalation_agent import escalate
from ..feedback_agent import process_feedback
from ..memory_agent import save_resolution
from ..rca_engine import generate_rca_agentic


def rca_node(state: AgentState) -> dict:
    report = generate_rca_agentic(state["ml_output"])
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
    ml_output = state["ml_output"]
    candidate = state["current_candidate"]
    input_data = state["input_data"]
    fault = {
        "id": input_data["id"],
        "location": input_data["location"],
        "resource_type": input_data["resource_type"],
        "fault_severity": ml_output["predicted_fault_severity"],
        "root_cause": candidate["root_cause"],
        "recommended_solution": candidate["resolution"],
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
        "ranked_causes": state["ranked_causes"],
    }
    return {"fault": fault, "dispatch_result": result, "ticket": ticket, "status": "AWAITING_FEEDBACK"}


def feedback_node(state: AgentState) -> dict:
    # This node runs only after the API supplies feedback and resumes the graph.
    ticket = dict(state["ticket"])
    result = process_feedback(ticket, bool(state.get("feedback_fixed")))
    if result["status"] == "CLOSED":
        return {"ticket": ticket, "attempt": ticket["attempt"], "status": "CLOSED"}
    if result["status"] == "RETRY":
        return {
            "ticket": ticket,
            "attempt": ticket["attempt"],
            "current_candidate": result["next_candidate"],
            "status": "RETRY",
        }
    return {"ticket": ticket, "attempt": ticket["attempt"], "status": "ESCALATE"}


def memory_node(state: AgentState) -> dict:
    candidate = state["current_candidate"]
    save_resolution(
        ml_output=state["ml_output"],
        semantic_incident=state["semantic_incident"],
        root_cause=candidate["root_cause"],
        successful_action=candidate["resolution"],
    )
    return {"memory_saved": True, "status": "MEMORY_SAVED"}


def escalation_node(state: AgentState) -> dict:
    report = escalate(
        state.get("ticket", {"ticket_id": state["input_data"].get("id", "UNKNOWN")}),
        reason="No dispatch could be assigned or all ranked RCA resolutions failed.",
    )
    return {"escalation": report, "status": "ESCALATED"}
