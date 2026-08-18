"""Build the resumable State -> Nodes -> Conditional Edges workflow."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .nodes import dispatch_node, escalation_node, feedback_node, memory_node, rca_node
from .router import route_after_dispatch, route_after_feedback, route_after_rca
from .state import AgentState


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("rca", rca_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("feedback", feedback_node)
    graph.add_node("memory", memory_node)
    graph.add_node("escalation", escalation_node)
    graph.set_entry_point("rca")
    graph.add_conditional_edges("rca", route_after_rca, {"dispatch": "dispatch", "escalation": "escalation"})
    graph.add_conditional_edges("dispatch", route_after_dispatch, {"feedback": "feedback", "escalation": "escalation"})
    graph.add_conditional_edges("feedback", route_after_feedback, {"memory": "memory", "dispatch": "dispatch", "escalation": "escalation"})
    graph.add_edge("memory", END)
    graph.add_edge("escalation", END)
    return graph.compile(checkpointer=MemorySaver(), interrupt_before=["feedback"])
