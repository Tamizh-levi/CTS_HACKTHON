# agents/dispatch_agent.py

import os
import re
from datetime import datetime, timezone

import pandas as pd

try:
    import psycopg2
except ImportError:
    psycopg2 = None

from agents.escalation_agent import escalate


# ==========================================================
# FILE PATHS
# ==========================================================

TECHNICIANS_CSV = (
    r"E:\github\CTS-batch-1\RAG\data\technicians.csv"
    
)

SPARE_PARTS_CSV = (
    r"E:\github\CTS-batch-1\RAG\data\spare_parts.csv"
)


# ==========================================================
# POSTGRES CONFIGURATION
# ==========================================================

PG_CONFIG = {
    "host": os.getenv(
        "PGHOST",
        "localhost"
    ),

    "port": os.getenv(
        "PGPORT",
        "5432"
    ),

    "dbname": os.getenv(
        "PGDATABASE",
        "telecom_fault_prediction"
    ),

    "user": os.getenv(
        "PGUSER",
        "postgres"
    ),

    "password": os.getenv(
        "PGPASSWORD",
        ""
    )
}


# ==========================================================
# REGION CONFIGURATION
# ==========================================================

NUM_REGIONS = 10


# ==========================================================
# LOCATION → REGION
# ==========================================================

def derive_region(
    location: str
) -> str:
    """
    Current synthetic mapping:

        location 118 -> region_8
        location 662 -> region_2

    because:

        location_number % 10
    """

    match = re.search(
        r"\d+",
        str(location)
    )

    if not match:

        raise ValueError(
            f"Could not extract location number "
            f"from: {location}"
        )

    location_num = int(
        match.group()
    )

    return (
        f"region_{location_num % NUM_REGIONS}"
    )


# ==========================================================
# LOAD TECHNICIANS + SPARES
# ==========================================================

def load_reference_data():

    technicians = pd.read_csv(
        TECHNICIANS_CSV
    )

    spare_parts = pd.read_csv(
        SPARE_PARTS_CSV
    )

    # Normalize booleans in case CSV has strings.
    if technicians["available"].dtype == object:

        technicians["available"] = (
            technicians["available"]
            .astype(str)
            .str.lower()
            .map(
                {
                    "true": True,
                    "false": False
                }
            )
            .fillna(False)
        )

    return (
        technicians,
        spare_parts
    )


# ==========================================================
# REGION DISTANCE
# ==========================================================

def _region_num(
    region: str
) -> int:

    return int(
        region.split("_")[1]
    )


def _regions_by_distance(
    home_region: str
):

    home = _region_num(
        home_region
    )

    regions = [
        f"region_{i}"
        for i in range(NUM_REGIONS)
    ]

    return sorted(
        regions,
        key=lambda region: min(
            abs(
                _region_num(region)
                - home
            ),
            NUM_REGIONS -
            abs(
                _region_num(region)
                - home
            )
        )
    )


# ==========================================================
# FIND TECHNICIAN
# ==========================================================

def find_technician_in_region(
    region,
    resource_type,
    technicians
):
    """
    Matching priority:

    1. Region
    2. Skill
    3. Available
    4. Lowest current load
    """

    candidates = technicians[
        (technicians["region"] == region)
        &
        (
            technicians[
                "skill_type"
            ]
            == resource_type
        )
        &
        (
            technicians[
                "available"
            ]
            == True
        )
    ].sort_values(
        "current_load"
    )

    if candidates.empty:
        return None

    return candidates.iloc[0]


# ==========================================================
# CHECK SPARE
# ==========================================================

def part_in_stock(
    region,
    resource_type,
    spare_parts
):

    mask = (
        (spare_parts["region"] == region)
        &
        (
            spare_parts["part_type"]
            == resource_type
        )
    )

    rows = spare_parts.loc[
        mask
    ]

    if rows.empty:
        return False

    return (
        float(
            rows.iloc[0]["stock_count"]
        )
        > 0
    )


# ==========================================================
# RESERVE SPARE
# ==========================================================

def reserve_part(
    region,
    resource_type,
    spare_parts
):

    mask = (
        (spare_parts["region"] == region)
        &
        (
            spare_parts["part_type"]
            == resource_type
        )
    )

    spare_parts.loc[
        mask,
        "stock_count"
    ] -= 1


# ==========================================================
# BEST DISPATCH
# ==========================================================

def find_best_dispatch(
    home_region,
    resource_type,
    technicians,
    spare_parts
):
    """
    Pass 1:
        Search for technician + spare together.

    Pass 2:
        If no region has both,
        find technician even if spare is unavailable.
    """

    search_order = (
        _regions_by_distance(
            home_region
        )
    )

    # ------------------------------------------------------
    # PASS 1
    # ------------------------------------------------------

    for region in search_order:

        technician = (
            find_technician_in_region(
                region,
                resource_type,
                technicians
            )
        )

        if (
            technician is not None
            and
            part_in_stock(
                region,
                resource_type,
                spare_parts
            )
        ):

            distance = min(
                abs(
                    _region_num(region)
                    -
                    _region_num(home_region)
                ),
                NUM_REGIONS -
                abs(
                    _region_num(region)
                    -
                    _region_num(home_region)
                )
            )

            return (
                technician,
                region,
                True,
                distance
            )

    # ------------------------------------------------------
    # PASS 2
    # ------------------------------------------------------

    for region in search_order:

        technician = (
            find_technician_in_region(
                region,
                resource_type,
                technicians
            )
        )

        if technician is not None:

            distance = min(
                abs(
                    _region_num(region)
                    -
                    _region_num(home_region)
                ),
                NUM_REGIONS -
                abs(
                    _region_num(region)
                    -
                    _region_num(home_region)
                )
            )

            return (
                technician,
                region,
                False,
                distance
            )

    return (
        None,
        None,
        False,
        None
    )


# ==========================================================
# ASSIGN DISPATCH
# ==========================================================

def assign_dispatch(
    fault,
    technicians,
    spare_parts
):

    home_region = derive_region(
        fault["location"]
    )

    resource_type = (
        fault["resource_type"]
    )

    (
        technician,
        source_region,
        part_available,
        distance
    ) = find_best_dispatch(
        home_region,
        resource_type,
        technicians,
        spare_parts
    )

    escalation = None

    # ======================================================
    # NO TECHNICIAN
    # ======================================================

    if technician is None:

        escalation = escalate(
            {
                "ticket_id":
                    str(fault["id"])
            },

            reason=(
                "No available technician "
                "with matching skill "
                f"({resource_type}) "
                "in any region."
            )
        )

        status = (
            "ESCALATED"
        )

    # ======================================================
    # TECHNICIAN FOUND BUT NO SPARE
    # ======================================================

    elif not part_available:

        status = (
            "part_shortage_flagged"
        )

    # ======================================================
    # FULL DISPATCH
    # ======================================================

    else:

        status = (
            "assigned"
            if distance == 0
            else "assigned_cross_region"
        )

        # Increase technician workload.
        technicians.loc[
            technicians["technician_id"]
            ==
            technician["technician_id"],
            "current_load"
        ] += 1

        # Reserve the part.
        reserve_part(
            source_region,
            resource_type,
            spare_parts
        )

    # ======================================================
    # BASE RESULT
    # ======================================================

    result = {

        "ticket_id":
            str(fault["id"]),

        "location":
            fault["location"],

        "region":
            home_region,

        "resource_type":
            resource_type,

        "fault_severity":
            int(
                fault[
                    "fault_severity"
                ]
            ),

        "root_cause":
            fault.get(
                "root_cause"
            ),

        "recommended_solution":
            fault.get(
                "recommended_solution"
            ),

        "status":
            status,

        "technician":
            None,

        "spare_part":
            None,

        "escalation":
            escalation
    }

    # ======================================================
    # TECHNICIAN DETAILS
    # ======================================================

    if technician is not None:

        result["technician"] = {

            "technician_id":
                technician[
                    "technician_id"
                ],

            "technician_name":
                technician[
                    "technician_name"
                ],

            "region":
                technician[
                    "region"
                ],

            "cross_region":
                (
                    distance is not None
                    and
                    distance > 0
                ),

            "distance_from_fault":
                (
                    int(distance)
                    if distance is not None
                    else None
                ),

            "skill_type":
                technician[
                    "skill_type"
                ],

            "current_load_after_assignment":
                int(
                    technician[
                        "current_load"
                    ]
                    +
                    (
                        1
                        if status.startswith(
                            "assigned"
                        )
                        else 0
                    )
                )
        }

    # ======================================================
    # SPARE DETAILS
    # ======================================================

    result["spare_part"] = {

        "part_type":
            resource_type,

        "sourced_region":
            source_region,

        "available":
            part_available
    }

    return result


# ==========================================================
# OPTIONAL POSTGRES INITIALIZATION
# ==========================================================

def init_db():

    if psycopg2 is None:

        raise RuntimeError(
            "psycopg2 is not installed."
        )

    conn = psycopg2.connect(
        **PG_CONFIG
    )

    with conn.cursor() as cur:

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dispatch_records (
                ticket_id TEXT PRIMARY KEY,
                location TEXT,
                region TEXT,
                resource_type TEXT,
                severity INTEGER,
                technician_id TEXT,
                part_status TEXT,
                status TEXT,
                kb_entry_id TEXT,
                attempt_number INTEGER DEFAULT 0,
                source TEXT,
                created_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ
            )
            """
        )

    conn.commit()

    return conn


# ==========================================================
# OPTIONAL POSTGRES SAVE
# ==========================================================

def save_to_postgres(
    record,
    conn
):

    now = datetime.now(
        timezone.utc
    )

    with conn.cursor() as cur:

        cur.execute(
            """
            INSERT INTO dispatch_records
            (
                ticket_id,
                location,
                region,
                resource_type,
                severity,
                technician_id,
                part_status,
                status,
                kb_entry_id,
                attempt_number,
                source,
                created_at,
                updated_at
            )
            VALUES
            (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s
            )
            ON CONFLICT (ticket_id)
            DO UPDATE SET
                region = EXCLUDED.region,
                resource_type = EXCLUDED.resource_type,
                severity = EXCLUDED.severity,
                technician_id = EXCLUDED.technician_id,
                part_status = EXCLUDED.part_status,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
            """,
            (
                record["ticket_id"],
                record["location"],
                record["region"],
                record["resource_type"],
                record["fault_severity"],

                (
                    record["technician"][
                        "technician_id"
                    ]
                    if record["technician"]
                    else None
                ),

                (
                    "in_stock"
                    if record[
                        "spare_part"
                    ]["available"]
                    else "out_of_stock"
                ),

                record["status"],
                None,
                0,
                "dispatch_agent",
                now,
                now
            )
        )

    conn.commit()


# ==========================================================
# DISPATCH REPORT
# ==========================================================

def print_dispatch_report(
    results
):

    line = "=" * 70

    print(line)
    print(
        "DISPATCH REPORT".center(70)
    )
    print(line)

    for record in results:

        print(
            f"\nTicket #{record['ticket_id']}"
        )

        print(
            f"Location       : "
            f"{record['location']}"
        )

        print(
            f"Fault Region   : "
            f"{record['region']}"
        )

        print(
            f"Resource Type  : "
            f"{record['resource_type']}"
        )

        print(
            f"Severity       : "
            f"{record['fault_severity']}"
        )

        print(
            f"Status         : "
            f"{record['status']}"
        )

        technician = (
            record["technician"]
        )

        if technician is not None:

            print(
                f"Technician     : "
                f"{technician['technician_name']}"
                f" ({technician['technician_id']})"
            )

            print(
                f"Technician Region : "
                f"{technician['region']}"
            )

            print(
                f"Skill          : "
                f"{technician['skill_type']}"
            )

            print(
                f"Current Load   : "
                f"{technician['current_load_after_assignment']}"
            )

            print(
                f"Cross Region   : "
                f"{technician['cross_region']}"
            )

        else:

            print(
                "Technician     : NONE"
            )

        spare = record[
            "spare_part"
        ]

        print(
            f"Spare Part     : "
            f"{spare['part_type']}"
        )

        print(
            f"Spare Region   : "
            f"{spare['sourced_region']}"
        )

        print(
            f"Spare Available: "
            f"{spare['available']}"
        )

        if record["escalation"]:

            print(
                f"Escalation     : "
                f"{record['escalation']['reason']}"
            )

    print(line)


# ==========================================================
# BATCH RUNNER
# ==========================================================

def run_dispatch_batch(
    faults
):

    technicians, spare_parts = (
        load_reference_data()
    )

    faults_sorted = sorted(
        faults,
        key=lambda fault:
            fault["fault_severity"],
        reverse=True
    )

    return [
        assign_dispatch(
            fault,
            technicians,
            spare_parts
        )
        for fault in faults_sorted
    ]