"""The shared state passed between every telecom workflow node."""

from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    input_data: Dict[str, Any]
    ml_output: Dict[str, Any]
    semantic_incident: Dict[str, Any]
    knowledge_context: List[str]
    pattern_context: List[str]
    rca_report: Dict[str, Any]
    ranked_causes: List[Dict[str, Any]]
    current_candidate: Dict[str, Any]
    fault: Dict[str, Any]
    dispatch_result: Dict[str, Any]
    ticket: Dict[str, Any]
    feedback_fixed: Optional[bool]
    attempt: int
    status: str
    memory_saved: bool
    escalation: Dict[str, Any]
