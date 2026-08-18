# backend/rag/agents/dispatch_agent.py
"""
Proximity & Workload-Aware Telecom Dispatch Agent.
Calculates shortest circular topology distance across 10 regions.
Does NOT call escalate() directly; returns status 'ESCALATION_REQUIRED' for workflow orchestration.
"""

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

# ==========================================================
# CONFIGURATION & CSV PATHS
# ==========================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
RAG_DIR = os.path.dirname(CURRENT_DIR)
DATA_DIR = os.path.join(RAG_DIR, "data")

_TECH_CANDIDATES = [
    os.path.join(DATA_DIR, "technicians.csv"),
    r"E:\CTS_HACKTHON (3)\CTS_HACKTHON\backend\rag\data\technicians.csv",
    os.getenv("TECHNICIANS_CSV", "")
]

_SPARE_CANDIDATES = [
    os.path.join(DATA_DIR, "spare_parts.csv"),
    r"E:\CTS_HACKTHON (3)\CTS_HACKTHON\backend\rag\data\spare_parts.csv",
    os.getenv("SPARE_PARTS_CSV", "")
]

TECHNICIANS_CSV = next((p for p in _TECH_CANDIDATES if p and os.path.exists(p)), os.path.join(DATA_DIR, "technicians.csv"))
SPARE_PARTS_CSV = next((p for p in _SPARE_CANDIDATES if p and os.path.exists(p)), os.path.join(DATA_DIR, "spare_parts.csv"))
NUM_REGIONS = 10

# ==========================================================
# LOCATION & REGION MATH
# ==========================================================

def derive_region(location_str: str) -> str:
    """
    Extracts numeric location and maps to region_0 .. region_9 via (location_num % 10).
    """
    match = re.search(r"(\d+)", str(location_str))
    if not match:
        return "region_0"
    return f"region_{int(match.group(1)) % NUM_REGIONS}"

def _region_num(region_str: str) -> int:
    match = re.search(r"(\d+)", str(region_str))
    return int(match.group(1)) if match else 0

def _region_distance(region_a: str, region_b: str) -> int:
    a = _region_num(region_a)
    b = _region_num(region_b)
    direct = abs(a - b)
    circular = NUM_REGIONS - direct
    return min(direct, circular)

def _ordered_regions(home_region: str) -> List[str]:
    all_regs = [f"region_{i}" for i in range(NUM_REGIONS)]
    return sorted(all_regs, key=lambda r: _region_distance(r, home_region))

# ==========================================================
# REFERENCE DATA LOADING
# ==========================================================

def load_reference_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    if not os.path.exists(TECHNICIANS_CSV):
        raise FileNotFoundError(f"Technicians file not found: {TECHNICIANS_CSV}")
    if not os.path.exists(SPARE_PARTS_CSV):
        raise FileNotFoundError(f"Spare parts file not found: {SPARE_PARTS_CSV}")

    technicians = pd.read_csv(TECHNICIANS_CSV)
    spare_parts = pd.read_csv(SPARE_PARTS_CSV)

    if technicians["available"].dtype == object:
        technicians["available"] = (
            technicians["available"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "1": True, "yes": True, "false": False, "0": False, "no": False})
            .fillna(False)
        )
    else:
        technicians["available"] = technicians["available"].astype(bool)

    technicians["current_load"] = pd.to_numeric(technicians["current_load"], errors="coerce").fillna(0)
    spare_parts["stock_count"] = pd.to_numeric(spare_parts["stock_count"], errors="coerce").fillna(0)

    return technicians, spare_parts

# ==========================================================
# DISPATCH MATCHING
# ==========================================================

def part_in_stock(region: str, resource_type: str, spare_parts: pd.DataFrame) -> bool:
    mask = (spare_parts["region"] == region) & (spare_parts["part_type"] == resource_type)
    rows = spare_parts.loc[mask]
    return not rows.empty and int(rows.iloc[0]["stock_count"]) > 0

def reserve_part(region: str, resource_type: str, spare_parts: pd.DataFrame) -> bool:
    mask = (spare_parts["region"] == region) & (spare_parts["part_type"] == resource_type) & (spare_parts["stock_count"] > 0)
    if not spare_parts.loc[mask].empty:
        idx = spare_parts.loc[mask].index[0]
        spare_parts.loc[idx, "stock_count"] -= 1
        return True
    return False

def find_technician_in_region(region: str, resource_type: str, technicians: pd.DataFrame) -> Optional[pd.Series]:
    candidates = technicians[
        (technicians["region"] == region) &
        (technicians["skill_type"] == resource_type) &
        (technicians["available"] == True)
    ].sort_values("current_load")
    return candidates.iloc[0] if not candidates.empty else None

def find_best_dispatch(
    home_region: str,
    resource_type: str,
    technicians: pd.DataFrame,
    spare_parts: pd.DataFrame
) -> Tuple[Optional[pd.Series], Optional[str], bool, int]:
    search_order = _ordered_regions(home_region)

    # Pass 1: Region with available technician + in-stock spare
    for reg in search_order:
        tech = find_technician_in_region(reg, resource_type, technicians)
        if tech is not None and part_in_stock(reg, resource_type, spare_parts):
            dist = _region_distance(reg, home_region)
            return tech, reg, True, dist

    # Pass 2: Region with available technician (even if spare out of stock)
    for reg in search_order:
        tech = find_technician_in_region(reg, resource_type, technicians)
        if tech is not None:
            dist = _region_distance(reg, home_region)
            return tech, reg, False, dist

    # No technician available
    return None, None, False, 0

# ==========================================================
# MAIN DISPATCH ENTRY POINT
# ==========================================================

def assign_dispatch(
    fault: Dict[str, Any],
    technicians: pd.DataFrame,
    spare_parts: pd.DataFrame
) -> Dict[str, Any]:
    home_region = derive_region(str(fault.get("location", "")))
    resource_type = str(fault.get("resource_type", "")).strip()

    tech, source_region, part_avail, distance = find_best_dispatch(
        home_region, resource_type, technicians, spare_parts
    )

    if tech is None:
        return {
            "ticket_id": str(fault.get("id", "")),
            "location": fault.get("location"),
            "region": home_region,
            "resource_type": resource_type,
            "fault_severity": fault.get("fault_severity", 0),
            "root_cause": fault.get("root_cause", ""),
            "recommended_solution": fault.get("recommended_solution", ""),
            "status": "ESCALATION_REQUIRED",
            "technician": None,
            "spare_part": None,
            "escalation": {
                "required": True,
                "reason": f"No available technician with skill {resource_type} in any region.",
                "assigned_group": "NOC_ENGINEERING_TEAM"
            }
        }

    status = "assigned" if distance == 0 else "assigned_cross_region"
    if not part_avail:
        status = "part_shortage_flagged"

    # Increment workload
    tech_id = tech["technician_id"]
    technicians.loc[technicians["technician_id"] == tech_id, "current_load"] += 1

    # Reserve part if available
    part_reserved = False
    if part_avail and source_region:
        part_reserved = reserve_part(source_region, resource_type, spare_parts)

    current_load_after = int(technicians.loc[technicians["technician_id"] == tech_id, "current_load"].iloc[0])

    return {
        "ticket_id": str(fault.get("id", "")),
        "location": fault.get("location"),
        "region": home_region,
        "resource_type": resource_type,
        "fault_severity": fault.get("fault_severity", 0),
        "root_cause": fault.get("root_cause", ""),
        "recommended_solution": fault.get("recommended_solution", ""),
        "status": status,
        "technician": {
            "technician_id": str(tech["technician_id"]),
            "technician_name": str(tech["technician_name"]),
            "region": str(tech["region"]),
            "skill_type": str(tech["skill_type"]),
            "cross_region": bool(distance > 0),
            "distance_from_fault": int(distance),
            "current_load_after_assignment": current_load_after
        },
        "spare_part": {
            "part_type": resource_type,
            "sourced_region": source_region,
            "available": part_avail,
            "reserved": part_reserved
        },
        "escalation": None
    }

def dispatch_fault(fault: Dict[str, Any]) -> Dict[str, Any]:
    technicians, spare_parts = load_reference_data()
    return assign_dispatch(fault, technicians, spare_parts)

__all__ = [
    "derive_region",
    "load_reference_data",
    "assign_dispatch",
    "dispatch_fault"
]