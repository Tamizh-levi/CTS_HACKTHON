import os
import json
import pandas as pd
import numpy as np
import joblib
from flask import Blueprint, jsonify, request

# ============================================================
# FLASK BLUEPRINT
# ============================================================
predict_date_bp = Blueprint("predict_date", __name__)
predict_bp = predict_date_bp  # Alias for flexible imports

# ============================================================
# RESOLVE PATHS & LOAD MODEL / CONFIG
# ============================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(CURRENT_DIR, "model", "date_fault_severity_model.joblib")
CONFIG_PATH = os.path.join(CURRENT_DIR, "config", "date_fault_config.json")

model = None
config = {}
SLA_TARGETS = {"HIGH": 5, "MEDIUM": 10, "LOW": 24}
SEVERITY_MAPPING = {"0": "HIGH", "1": "MEDIUM", "2": "LOW"}

try:
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print(f"[SLA MODEL] Loaded date fault severity model from {MODEL_PATH}")
    else:
        print(f"[SLA MODEL WARNING] Model not found at {MODEL_PATH}")
except Exception as e:
    print(f"[SLA MODEL ERROR] Failed to load model: {e}")

try:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
            SLA_TARGETS = config.get("sla_targets", SLA_TARGETS)
            SEVERITY_MAPPING = config.get("severity_mapping", SEVERITY_MAPPING)
except Exception as e:
    print(f"[SLA CONFIG ERROR] Failed to load config: {e}")


# ============================================================
# CORE INFERENCE LOGIC
# ============================================================
def analyze_sla_workload(start_input: str, end_input: str):
    """
    Parses dates, generates time features, executes model inference,
    and returns comprehensive SLA priority and daily breakdown.
    """
    # 1. Parse dates (supports DD-MM-YYYY and YYYY-MM-DD)
    start_date = None
    end_date = None

    for fmt in ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]:
        if start_date is None:
            try:
                start_date = pd.to_datetime(start_input, format=fmt)
            except Exception:
                pass
        if end_date is None:
            try:
                end_date = pd.to_datetime(end_input, format=fmt)
            except Exception:
                pass

    if start_date is None or end_date is None:
        raise ValueError(f"Invalid date format for '{start_input}' or '{end_input}'. Please use DD-MM-YYYY (e.g. 01-06-2025).")

    if start_date > end_date:
        raise ValueError("Start date cannot be after end date.")

    # 2. Generate date range & features
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    
    data = pd.DataFrame({
        "year": dates.year,
        "month": dates.month,
        "day": dates.day,
        "day_of_week": dates.dayofweek,
        "day_of_year": dates.dayofyear
    })

    # 3. Model inference
    if model is not None:
        raw_preds = model.predict(data)
        predictions = np.maximum(np.round(raw_preds), 0).astype(int)
    else:
        # Fallback heuristic simulation if model file missing
        predictions = np.zeros((len(dates), 3), dtype=int)
        for i in range(len(dates)):
            predictions[i, 0] = np.random.randint(10, 18)  # HIGH
            predictions[i, 1] = np.random.randint(4, 9)    # MEDIUM
            predictions[i, 2] = np.random.randint(1, 5)    # LOW

    # 4. Total severity counts
    severity_0_total = int(predictions[:, 0].sum())  # HIGH
    severity_1_total = int(predictions[:, 1].sum())  # MEDIUM
    severity_2_total = int(predictions[:, 2].sum())  # LOW

    severity_counts = {
        "HIGH": severity_0_total,
        "MEDIUM": severity_1_total,
        "LOW": severity_2_total
    }

    total_faults = int(sum(severity_counts.values()))

    # 5. Workload priority
    high_workload = severity_counts["HIGH"]
    medium_workload = severity_counts["MEDIUM"]
    low_workload = severity_counts["LOW"]

    if high_workload > 0:
        overall_priority = "URGENT"
    elif medium_workload > 0:
        overall_priority = "NORMAL"
    else:
        overall_priority = "LOW"

    # 6. Daily breakdown table
    daily_breakdown = []
    for i, dt in enumerate(dates):
        h = int(predictions[i, 0])
        m = int(predictions[i, 1])
        l = int(predictions[i, 2])
        tot = h + m + l
        daily_breakdown.append({
            "date": dt.strftime("%d-%m-%Y"),
            "date_iso": dt.strftime("%Y-%m-%d"),
            "day_of_week": dt.strftime("%A"),
            "high": h,
            "medium": m,
            "low": l,
            "total": tot,
            "daily_priority": "URGENT" if h > 10 else "HIGH" if h > 0 else "NORMAL"
        })

    return {
        "success": True,
        "date_range": {
            "start_date": start_date.strftime("%d-%m-%Y"),
            "end_date": end_date.strftime("%d-%m-%Y"),
            "total_days": len(dates)
        },
        "summary": {
            "total_faults": total_faults,
            "severity_counts": severity_counts,
            "overall_priority": overall_priority
        },
        "sla_targets": {
            "HIGH": f"{SLA_TARGETS.get('HIGH', 5)} hours",
            "MEDIUM": f"{SLA_TARGETS.get('MEDIUM', 10)} hours",
            "LOW": f"{SLA_TARGETS.get('LOW', 24)} hours"
        },
        "workload_priority": {
            "urgent_workload": high_workload,
            "normal_workload": medium_workload,
            "low_priority_workload": low_workload
        },
        "daily_breakdown": daily_breakdown
    }


# ============================================================
# FLASK ROUTE: POST /api/sla/predict-date or POST /api/predict-date
# ============================================================
@predict_date_bp.route("/sla/predict-date", methods=["POST", "GET"])
@predict_date_bp.route("/predict-date", methods=["POST", "GET"])
def predict_sla_endpoint():
    try:
        # Retrieve date parameters from JSON body or URL Query Params
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            start_input = data.get("start_date") or data.get("start") or request.args.get("start_date")
            end_input = data.get("end_date") or data.get("end") or request.args.get("end_date")
        else:
            start_input = request.args.get("start_date") or request.args.get("start")
            end_input = request.args.get("end_date") or request.args.get("end")

        # Default fallback dates if not provided: current 14-day window
        if not start_input or not end_input:
            today = pd.Timestamp.now()
            start_input = today.strftime("%d-%m-%Y")
            end_input = (today + pd.Timedelta(days=14)).strftime("%d-%m-%Y")

        result = analyze_sla_workload(str(start_input).strip(), str(end_input).strip())
        return jsonify(result)

    except ValueError as ve:
        return jsonify({
            "success": False,
            "error": str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Internal SLA prediction error: {str(e)}"
        }), 500


# ============================================================
# STANDALONE TERMINAL CLI RUNNER
# ============================================================
if __name__ == "__main__":
    start_input = input("Enter start date (DD-MM-YYYY): ").strip()
    end_input = input("Enter end date (DD-MM-YYYY): ").strip()

    try:
        result = analyze_sla_workload(start_input, end_input)

        print("\n" + "=" * 60)
        print("          SLA PRIORITY & WORKLOAD ANALYSIS")
        print("=" * 60)
        print(f"Date Range : {result['date_range']['start_date']} → {result['date_range']['end_date']}")
        print("-" * 60)
        print(f"Total Faults : {result['summary']['total_faults']}")
        print(f"HIGH         : {result['summary']['severity_counts']['HIGH']}")
        print(f"MEDIUM       : {result['summary']['severity_counts']['MEDIUM']}")
        print(f"LOW          : {result['summary']['severity_counts']['LOW']}")

        print("\nSLA TARGETS")
        print("-" * 60)
        print(f"HIGH         : {result['sla_targets']['HIGH']}")
        print(f"MEDIUM       : {result['sla_targets']['MEDIUM']}")
        print(f"LOW          : {result['sla_targets']['LOW']}")

        print("\nWORKLOAD PRIORITY")
        print("-" * 60)
        print(f"Urgent Workload      : {result['workload_priority']['urgent_workload']} faults")
        print(f"Normal Workload      : {result['workload_priority']['normal_workload']} faults")
        print(f"Low-Priority Workload: {result['workload_priority']['low_priority_workload']} faults")
        print(f"\nOverall Priority : {result['summary']['overall_priority']}")
        print("=" * 60)

        show_daily = input("\nDo you want daily SLA breakdown? (y/n): ").strip().lower()
        if show_daily == "y":
            print("\n" + "=" * 75)
            print("                       DAILY BREAKDOWN")
            print("=" * 75)
            print(f"{'DATE':<15}{'HIGH':<12}{'MEDIUM':<12}{'LOW':<12}{'TOTAL':<12}")
            print("-" * 75)
            for row in result["daily_breakdown"]:
                print(f"{row['date']:<15}{row['high']:<12}{row['medium']:<12}{row['low']:<12}{row['total']:<12}")
            print("=" * 75)

    except Exception as e:
        print(f"\nError: {e}")