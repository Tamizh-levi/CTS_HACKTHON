from agents.rca_engine import generate_rca_agentic

from agents.dispatch_agent import (
    load_reference_data,
    assign_dispatch
)

from agents.feedback_agent import (
    process_feedback
)

from agents.escalation_agent import (
    escalate
)

from agents.memory_agent import (
    save_resolution
)


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    # ======================================================
    # ML OUTPUT
    # ======================================================

    # Temporary test input.
    # Later this dictionary will come directly from
    # your ML prediction service/model.

    ml_output = {

        "predicted_fault_severity": 2,

        "severity_type":
            "severity_type 2",

        "resource_type":
            "resource_type 5",

        "event_types": [
            "event_type 10",
            "event_type 12",
            "event_type 14"
        ],

        "log_features": [
            "feature 64",
            "feature 82",
            "feature 91"
        ],

        "volume":
            250
    }


    # ======================================================
    # STEP 1: RCA AGENT
    # ======================================================

    rca_report = generate_rca_agentic(
        ml_output
    )


    print("\n")
    print("=" * 100)
    print("ROOT CAUSE ANALYSIS REPORT")
    print("=" * 100)


    print(
        "\nRisk Level:"
    )

    print(
        rca_report.get(
            "risk_level",
            "UNKNOWN"
        )
    )


    print(
        "\nTechnical Summary:"
    )

    print(
        rca_report.get(
            "technical_summary",
            ""
        )
    )


    print("\nRanked RCA Candidates:")


    ranked_causes = rca_report[
        "ranked_causes"
    ]


    for candidate in ranked_causes:

        print("\n")
        print(
            f"#{candidate['rank']}"
        )

        print(
            f"Root Cause  : "
            f"{candidate['root_cause']}"
        )

        print(
            f"Confidence   : "
            f"{candidate['confidence']}"
        )

        print(
            f"Resolution   : "
            f"{candidate['resolution']}"
        )


    # ======================================================
    # STEP 2: DISPATCH AGENT
    # ======================================================

    technicians, spare_parts = (
        load_reference_data()
    )


    # The dispatch agent needs the highest-ranked RCA
    # only as contextual information.
    top_candidate = ranked_causes[0]


    fault = {

        "id":
            "1001",

        "location":
            "location 2",

        "resource_type":
            ml_output[
                "resource_type"
            ],

        "fault_severity":
            ml_output[
                "predicted_fault_severity"
            ],

        "root_cause":
            top_candidate[
                "root_cause"
            ],

        "recommended_solution":
            top_candidate[
                "resolution"
            ]
    }


    dispatch_result = assign_dispatch(
        fault,
        technicians,
        spare_parts
    )


    print("\n")
    print("=" * 100)
    print("DISPATCH REPORT")
    print("=" * 100)


    print(
        f"Dispatch Status : "
        f"{dispatch_result['status']}"
    )


    # ======================================================
    # STEP 3: NO TECHNICIAN
    # ======================================================

    if (
        dispatch_result[
            "technician"
        ]
        is None
    ):

        print(
            "\nNo suitable technician "
            "was available."
        )


        if dispatch_result[
            "escalation"
        ]:

            escalation = (
                dispatch_result[
                    "escalation"
                ]
            )

            print(
                "\nEscalation:"
            )

            print(
                escalation
            )

        raise SystemExit


    # ======================================================
    # STEP 4: TECHNICIAN INFORMATION
    # ======================================================

    technician = (
        dispatch_result[
            "technician"
        ]
    )


    print(
        f"\nTechnician Name : "
        f"{technician['technician_name']}"
    )

    print(
        f"Technician ID   : "
        f"{technician['technician_id']}"
    )

    print(
        f"Technician Region : "
        f"{technician['region']}"
    )

    print(
        f"Skill           : "
        f"{technician['skill_type']}"
    )

    print(
        f"Current Load    : "
        f"{technician['current_load_after_assignment']}"
    )

    print(
        f"Cross Region    : "
        f"{technician['cross_region']}"
    )


    # ======================================================
    # STEP 5: SPARE PART
    # ======================================================

    spare = (
        dispatch_result[
            "spare_part"
        ]
    )


    print("\nSpare Part Information")

    print(
        f"Part Type       : "
        f"{spare['part_type']}"
    )

    print(
        f"Sourced Region  : "
        f"{spare['sourced_region']}"
    )

    print(
        f"Available       : "
        f"{spare['available']}"
    )


    # ======================================================
    # STEP 6: CREATE TICKET
    # ======================================================

    ticket = {

        "ticket_id":
            fault["id"],

        "location":
            fault["location"],

        "resource_type":
            fault["resource_type"],

        "fault_severity":
            fault["fault_severity"],

        "assigned_to":
            technician[
                "technician_name"
            ],

        "attempt":
            0,

        "status":
            "OPEN",

        "ranked_causes":
            ranked_causes
    }


    # ======================================================
    # STEP 7: FEEDBACK LOOP
    # ======================================================

    while True:

        # --------------------------------------------------
        # Current RCA hypothesis
        # --------------------------------------------------

        current_candidate = ticket[
            "ranked_causes"
        ][
            ticket["attempt"]
        ]


        current_root_cause = (
            current_candidate[
                "root_cause"
            ]
        )


        current_resolution = (
            current_candidate[
                "resolution"
            ]
        )


        current_confidence = (
            current_candidate[
                "confidence"
            ]
        )


        # --------------------------------------------------
        # Display attempt
        # --------------------------------------------------

        print("\n")
        print("=" * 80)

        print(
            f"ATTEMPT "
            f"{ticket['attempt'] + 1}"
        )

        print("=" * 80)


        print(
            f"Assigned Technician : "
            f"{ticket['assigned_to']}"
        )


        print(
            f"\nProbable Root Cause:"
        )

        print(
            current_root_cause
        )


        print(
            f"\nConfidence:"
        )

        print(
            current_confidence
        )


        print(
            f"\nRecommended Resolution:"
        )

        print(
            current_resolution
        )


        # --------------------------------------------------
        # NOC / Technician feedback
        # --------------------------------------------------

        feedback = input(
            "\nIssue Fixed? (yes/no): "
        ).strip().lower()


        # ==================================================
        # SUCCESS
        # ==================================================

        if feedback == "yes":

            ticket[
                "status"
            ] = "CLOSED"


            # ----------------------------------------------
            # Save successful resolution
            # ----------------------------------------------

            save_resolution(
                ml_output=ml_output,
                semantic_incident=rca_report["semantic_incident"],
                root_cause=current_root_cause,
                successful_action=current_resolution
            )


            print("\n")
            print("=" * 80)
            print("TICKET CLOSED")
            print("=" * 80)


            print(
                "Issue resolved successfully."
            )


            break


        # ==================================================
        # FAILURE
        # ==================================================

        result = process_feedback(
            ticket,
            fixed=False
        )


        # ==================================================
        # TRY NEXT RCA HYPOTHESIS
        # ==================================================

        if result[
            "status"
        ] == "RETRY":

            next_candidate = (
                result[
                    "next_candidate"
                ]
            )


            print("\n")
            print("=" * 80)
            print("PREVIOUS HYPOTHESIS FAILED")
            print("=" * 80)


            print(
                "Moving to next root-cause hypothesis:"
            )


            print(
                next_candidate[
                    "root_cause"
                ]
            )


            continue


        # ==================================================
        # ESCALATION AFTER 3 FAILURES
        # ==================================================

        if result[
            "status"
        ] == "ESCALATE":

            ticket[
                "status"
            ] = "ESCALATED"


            escalation_report = (
                escalate(
                    ticket,
                    reason=(
                        "All three ranked "
                        "RCA resolutions failed."
                    )
                )
            )


            print("\n")
            print("=" * 80)
            print("ESCALATION REPORT")
            print("=" * 80)


            print(
                f"Ticket ID : "
                f"{escalation_report['ticket_id']}"
            )


            print(
                f"Status    : "
                f"{escalation_report['status']}"
            )


            print(
                f"Reason    : "
                f"{escalation_report['reason']}"
            )


            print(
                f"Assigned Group : "
                f"{escalation_report['assigned_group']}"
            )


            break