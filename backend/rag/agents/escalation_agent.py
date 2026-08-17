# agents/escalation_agent.py


def escalate(
    ticket,
    reason="Issue not resolved after all RCA recommendations."
):
    """
    Escalate unresolved incidents to the human
    NOC engineering team.
    """

    ticket_id = str(
        ticket.get(
            "ticket_id",
            "UNKNOWN"
        )
    )

    return {
        "ticket_id": ticket_id,
        "status": "ESCALATED",
        "reason": reason,
        "assigned_group": "NOC_ENGINEERING_TEAM"
    }