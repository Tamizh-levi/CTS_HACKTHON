# agents/feedback_agent.py


def process_feedback(
    ticket,
    fixed
):
    """
    Controls the RCA hypothesis feedback loop.

    Each failed attempt moves to the next
    ranked RCA hypothesis.

    After three failed hypotheses,
    escalation is triggered.
    """

    # ==================================================
    # SUCCESS
    # ==================================================

    if fixed:

        ticket["status"] = "CLOSED"

        return {
            "status": "CLOSED"
        }

    # ==================================================
    # FAILED ATTEMPT
    # ==================================================

    ticket["attempt"] += 1

    # ==================================================
    # MORE RCA HYPOTHESES AVAILABLE
    # ==================================================

    if ticket["attempt"] < len(
        ticket["ranked_causes"]
    ):

        next_candidate = ticket[
            "ranked_causes"
        ][ticket["attempt"]]

        return {
            "status": "RETRY",

            "next_candidate":
                next_candidate
        }

    # ==================================================
    # ALL HYPOTHESES FAILED
    # ==================================================

    ticket["status"] = "ESCALATED"

    return {
        "status": "ESCALATE"
    }