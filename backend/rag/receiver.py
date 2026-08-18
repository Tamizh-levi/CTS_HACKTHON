# backend/rag/receiver.py
"""
Telecom Fault Detection, RCA & Autonomous Dispatch API Gateway.
Coordinates XGBoost Machine Learning, LangGraph State Machine,
Direct ChromaDB + Ollama RCA Engine, MongoDB Incident & Decision Persistence.
Single source of truth: MongoDB Database.
"""

import os
import sys
import json
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from flask import Blueprint, jsonify, request
from pymongo import MongoClient

# ============================================================
# RESOLVE IMPORT PATHS
# ============================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

for path in [CURRENT_DIR, BACKEND_DIR, ROOT_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

# ============================================================
# LANGGRAPH WORKFLOW & DOMAIN AGENTS
# ============================================================

workflow = None
WORKFLOW_AVAILABLE = False

try:
    try:
        from backend.rag.agents.graph.workflow import workflow
    except ImportError:
        try:
            from rag.agents.graph.workflow import workflow
        except ImportError:
            from agents.graph.workflow import workflow
    WORKFLOW_AVAILABLE = workflow is not None
    print("[RECEIVER] LangGraph Checkpointed Workflow successfully loaded.")
except Exception as e:
    print(f"[RECEIVER WARNING] LangGraph workflow not loaded: {e}")
    workflow = None
    WORKFLOW_AVAILABLE = False

# ============================================================
# FLASK BLUEPRINT
# ============================================================

receiver_bp = Blueprint("receiver", __name__)

# ============================================================
# MONGODB CONFIGURATION & CLIENT
# ============================================================

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB_NAME = "cts_incident_management"
mongo_client = None
mongo_db = None

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    mongo_client.admin.command("ping")
    mongo_db = mongo_client[MONGO_DB_NAME]
    print(f"[RECEIVER] MongoDB Connected successfully to database '{MONGO_DB_NAME}'")
except Exception as e:
    print(f"[RECEIVER WARNING] MongoDB connection failed: {e}.")
    mongo_db = None

def get_mongo_db():
    global mongo_db, mongo_client
    if mongo_db is not None:
        return mongo_db
    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1000)
        mongo_db = mongo_client[MONGO_DB_NAME]
        return mongo_db
    except Exception:
        return None

# ============================================================
# ML ARTIFACT PATHS (EXPERIMENT 37 XGBOOST)
# ============================================================

_MODEL_DIR_CANDIDATES = [
    os.path.join(BACKEND_DIR, "models", "models"),
    os.path.join(CURRENT_DIR, "..", "models", "models"),
    os.path.join(ROOT_DIR, "backend", "models", "models"),
    r"E:\CTS_HACKTHON (3)\CTS_HACKTHON\backend\models\models",
    os.path.join(ROOT_DIR, "models", "models")
]

MODELS_DIR = next((d for d in _MODEL_DIR_CANDIDATES if os.path.exists(d)), os.path.join(BACKEND_DIR, "models", "models"))
PREPROCESSOR_PATH = os.path.join(MODELS_DIR, "experiment_37_preprocessor.joblib")
MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_fault_severity_model.json")

print("[RECEIVER] Preprocessor Path:", PREPROCESSOR_PATH)
print("[RECEIVER] Model Path       :", MODEL_PATH)

# ============================================================
# LOAD MACHINE LEARNING MODEL
# ============================================================

preprocessor = None
model = None
MODEL_AVAILABLE = False

try:
    if os.path.exists(PREPROCESSOR_PATH) and os.path.exists(MODEL_PATH):
        preprocessor = joblib.load(PREPROCESSOR_PATH)
        model = xgb.XGBClassifier()
        model.load_model(MODEL_PATH)
        MODEL_AVAILABLE = True
        print("[RECEIVER] ML Model & Preprocessor Loaded Successfully!")
    else:
        print(f"[RECEIVER WARNING] Model files missing: {PREPROCESSOR_PATH} or {MODEL_PATH}")
except Exception as e:
    print(f"[RECEIVER ERROR] Failed to load ML Model: {e}")

# ============================================================
# PAYLOAD VALIDATION
# ============================================================

REQUIRED_FIELDS = [
    "id", "location", "severity_type", "resource_type",
    "event_count_x", "unique_event_count", "log_feature_count",
    "unique_log_features", "event_count_y",
    "event_event_type_unique", "log_count", "log_log_feature_unique",
    "log_volume_unique", "resource_count", "resource_resource_type_unique",
    "log_count_ratio", "resource_count_ratio", "severity_resource",
    "severity_location", "resource_location"
]

def validate_fault_data(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    if not isinstance(data, dict):
        return False, {"error": "Invalid format: Payload must be a JSON object"}

    missing_fields = []
    for field in REQUIRED_FIELDS:
        if field not in data:
            missing_fields.append(field)

    # Check volume fields
    if "total_log_volume" not in data and "volume" not in data:
        missing_fields.append("total_log_volume")

    if missing_fields:
        return False, {
            "error": "Missing required fields",
            "missing_fields": missing_fields
        }

    return True, None

# ============================================================
# ML PREDICTION PIPELINE
# ============================================================

SEVERITY_LABELS = {
    0: "Low Severity",
    1: "Medium Severity",
    2: "High Severity"
}

def execute_ml_pipeline(data: Dict[str, Any]) -> Dict[str, Any]:
    if model is None or preprocessor is None:
        raise RuntimeError(
            "XGBoost model or preprocessor is not loaded. "
            "Cannot perform real fault prediction."
        )

    df = pd.DataFrame([data])
    if "total_log_volume" not in df.columns and "volume" in df.columns:
        df["total_log_volume"] = df["volume"]

    expected_features = getattr(preprocessor, "feature_names_in_", None)
    if expected_features is not None:
        for feat in expected_features:
            if feat not in df.columns:
                df[feat] = 0.0
        df = df[expected_features]

    X_transformed = preprocessor.transform(df)
    pred_class = int(model.predict(X_transformed)[0])
    pred_probs = model.predict_proba(X_transformed)[0]
    confidence = float(np.max(pred_probs))

    prob_dict = {
        "low": float(round(pred_probs[0], 4)) if len(pred_probs) > 0 else 0.0,
        "medium": float(round(pred_probs[1], 4)) if len(pred_probs) > 1 else 0.0,
        "high": float(round(pred_probs[2], 4)) if len(pred_probs) > 2 else 0.0,
    }

    return {
        "fault_severity": pred_class,
        "severity": SEVERITY_LABELS.get(pred_class, "Unknown Severity"),
        "confidence": float(round(confidence, 4)),
        "probabilities": prob_dict
    }

def build_rca_input(data: Dict[str, Any], ml_result: Dict[str, Any]) -> Dict[str, Any]:
    vol = data.get("total_log_volume", data.get("volume", 0))
    return {
        **data,
        "incident_id": data.get("id"),
        "predicted_fault_severity": ml_result.get("fault_severity", 2),
        "fault_severity": ml_result.get("fault_severity", 2),
        "severity": ml_result.get("severity", "High Severity"),
        "confidence": ml_result.get("confidence", 0.92),
        "volume": vol,
        "total_log_volume": vol,
    }

# ============================================================
# API ENDPOINT 1: PREDICT ONLY
# ============================================================

@receiver_bp.route("/predict", methods=["POST"])
def predict_only():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "message": "Request body must contain JSON data"}), 400

        valid, error = validate_fault_data(data)
        if not valid:
            return jsonify({"success": False, **error}), 400

        ml_result = execute_ml_pipeline(data)
        return jsonify({
            "success": True,
            "ticket_id": data.get("id"),
            "prediction": ml_result
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "Prediction failed", "error": str(e)}), 500

# ============================================================
# API ENDPOINT 2: PREDICT + RCA + DISPATCH (SINGLE ORCHESTRATION)
# ============================================================

def process_single_incident(data: Dict[str, Any]) -> Dict[str, Any]:
    valid, error = validate_fault_data(data)
    if not valid:
        raise ValueError(f"Validation error for record #{data.get('id')}: {error.get('missing_fields', error.get('error'))}")

    # Step 1: Execute Real ML Prediction
    ml_result = execute_ml_pipeline(data)

    # Step 2: Build RCA Input
    ml_output = build_rca_input(data, ml_result)

    # Step 3: Single LangGraph Orchestration Path
    if not WORKFLOW_AVAILABLE or workflow is None:
        raise RuntimeError("LangGraph workflow is unavailable.")

    config = {
        "configurable": {
            "thread_id": str(data["id"])
        }
    }

    graph_state = workflow.invoke(
        {
            "input_data": data,
            "ml_output": ml_output,
            "attempt": 0,
            "status": "STARTED",
            "feedback_fixed": None,
            "selected_rank": None,
            "confirmed_root_cause": "",
            "confirmed_resolution": "",
            "operator_notes": "",
            "operator": "SYSTEM",
            "memory_saved": False
        },
        config=config
    )

    rca_result = graph_state.get("rca_report")
    dispatch_result = graph_state.get("dispatch_result")
    workflow_status = graph_state.get("status", "AWAITING_FEEDBACK")

    if not rca_result:
        raise RuntimeError(f"Workflow completed without RCA result for #{data.get('id')}.")

    if not rca_result.get("ranked_causes"):
        raise RuntimeError(f"RCA result contains no ranked_causes for #{data.get('id')}.")

    # Step 4: Construct complete incident document
    new_inc = {
        **data,
        "id": f"INC-{data['id']}",
        "ticket_id": data["id"],
        "title": f"Telemetry Alert at {data.get('location', 'Node')} ({data.get('resource_type', 'Resource')})",
        "location": data.get("location", "Unknown Location"),
        "region": dispatch_result.get("region", "region_1") if dispatch_result else "region_1",
        "severity_type": data.get("severity_type", "severity_type 1"),
        "resource_type": data.get("resource_type", "resource_type 1"),
        "event_types": data.get("event_types", []),
        "log_features": data.get("log_features", []),
        "total_log_volume": data.get("total_log_volume", data.get("volume", 0)),
        "status": workflow_status,
        "severity": ml_result.get("severity", "High Severity"),
        "fault_severity": ml_result.get("fault_severity", 2),
        "confidence": ml_result.get("confidence", 0.92),
        "prediction": ml_result,
        "agent_result": rca_result,
        "dispatch_result": dispatch_result,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "assigned_to": (
            dispatch_result["technician"]["technician_name"]
            if dispatch_result and dispatch_result.get("technician")
            else "Pending Autonomous Dispatch"
        )
    }

    # Step 5: Save into MongoDB
    db_conn = get_mongo_db()
    if db_conn is not None:
        try:
            clean_doc = dict(new_inc)
            db_conn["incidents"].update_one(
                {"ticket_id": data["id"]},
                {"$set": clean_doc},
                upsert=True
            )
            print(f"[RECEIVER] Stored incident #{data['id']} in MongoDB 'incidents' collection.")
        except Exception as ex:
            print(f"[RECEIVER] MongoDB store error: {ex}")

    return {
        "success": True,
        "status": "success",
        "ticket_id": data["id"],
        "prediction": ml_result,
        "rca_status": "success",
        "agent_result": rca_result,
        "dispatch_result": dispatch_result
    }

# ============================================================
# API ENDPOINT 2: PREDICT + RCA + DISPATCH (SUPPORTS SINGLE & BATCH)
# ============================================================

@receiver_bp.route("/predict-and-rca", methods=["POST"])
def predict_and_rca():
    try:
        raw_body = request.get_json(silent=True)
        if not raw_body:
            return jsonify({"success": False, "message": "Request body must contain JSON data"}), 400

        # Handle batch or single payloads
        if isinstance(raw_body, dict) and "data" in raw_body and isinstance(raw_body["data"], list):
            records = raw_body["data"]
        elif isinstance(raw_body, list):
            records = raw_body
        elif isinstance(raw_body, dict):
            records = [raw_body]
        else:
            return jsonify({"success": False, "message": "Invalid JSON format"}), 400

        if not records:
            return jsonify({"success": False, "message": "No incident records found in payload"}), 400

        results = []
        for record in records:
            res = process_single_incident(record)
            results.append(res)

        if len(results) == 1:
            return jsonify(results[0])
        else:
            return jsonify({
                "success": True,
                "status": "success",
                "total_records": len(results),
                "results": results
            })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "status": "RCA_FAILED",
            "message": f"Processing failed: {str(e)}",
            "error": str(e)
        }), 500

# ============================================================
# API ENDPOINT 3: GET ALL INCIDENTS (DIRECT MONGODB QUERY)
# ============================================================

@receiver_bp.route("/incidents", methods=["GET"])
def get_all_incidents():
    db_conn = get_mongo_db()
    if db_conn is not None:
        try:
            docs = list(db_conn["incidents"].find({}, {"_id": 0}).sort("created_at", -1))
            return jsonify({"success": True, "incidents": docs, "count": len(docs)})
        except Exception as ex:
            print(f"[RECEIVER] MongoDB query error: {ex}")

    return jsonify({"success": True, "incidents": [], "count": 0})

# ============================================================
# API ENDPOINT 4: GET SINGLE INCIDENT (DIRECT MONGODB QUERY)
# ============================================================

@receiver_bp.route("/incidents/<ticket_id>", methods=["GET"])
def get_incident_by_id(ticket_id):
    clean_id_str = str(ticket_id).replace("INC-", "").strip()

    # Query MongoDB as single source of truth
    db_conn = get_mongo_db()
    if db_conn is not None:
        try:
            try:
                query_id: Any = int(clean_id_str)
            except ValueError:
                query_id = clean_id_str

            doc = db_conn["incidents"].find_one({
                "$or": [
                    {"ticket_id": query_id},
                    {"ticket_id": clean_id_str},
                    {"id": f"INC-{clean_id_str}"},
                    {"id": clean_id_str}
                ]
            }, {"_id": 0})

            if doc:
                return jsonify({"success": True, "incident": doc})
            else:
                return jsonify({
                    "success": False,
                    "message": f"Incident #{ticket_id} not found."
                }), 404
        except Exception as ex:
            print(f"[RECEIVER] MongoDB find error: {ex}")

    return jsonify({
        "success": False,
        "message": f"Incident #{ticket_id} not found."
    }), 404

# ============================================================
# API ENDPOINT 5: FEEDBACK & OPERATOR DECISION
# ============================================================

@receiver_bp.route("/feedback", methods=["POST"])
def submit_feedback():
    try:
        data = request.get_json(silent=True) or {}
        ticket_id = data.get("ticket_id")
        confirmed_raw = data.get("confirmed", True)
        confirmed = (
            confirmed_raw
            if isinstance(confirmed_raw, bool)
            else str(confirmed_raw).strip().lower() in {"true", "1", "yes"}
        )
        root_cause = data.get("root_cause", "")
        rank = data.get("rank", 1)
        notes = data.get("notes", "")
        operator = data.get("operator", "NOC Operator")
        resolution = data.get("resolution", "")

        status_value = "FINISHED (RESOLVED)" if confirmed else "RE_ANALYZING"
        commit_id = f"COMMIT-RCA-{ticket_id}-{int(datetime.now(timezone.utc).timestamp())}"
        now_iso = datetime.now(timezone.utc).isoformat()
        graph_state = None
        next_candidate = None
        memory_result = None
        escalation_result = None

        if not WORKFLOW_AVAILABLE or workflow is None:
            raise RuntimeError("LangGraph workflow is unavailable to process feedback.")

        if ticket_id is None:
            raise ValueError("ticket_id is required for feedback.")

        # Resume checkpointed LangGraph workflow
        thread_id = str(ticket_id).replace("INC-", "").strip()
        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Rehydrate LangGraph workflow state if lost (e.g. server restart)
            current_state = workflow.get_state(config)
            db_conn = get_mongo_db()
            inc_doc = None
            past_decisions = []
            if db_conn is not None:
                try:
                    clean_int = int(thread_id)
                except (ValueError, TypeError):
                    clean_int = None
                conds = [{"ticket_id": thread_id}, {"id": f"INC-{thread_id}"}, {"id": thread_id}]
                dec_conds = [{"ticket_id": thread_id}, {"ticket_id": str(ticket_id)}]
                if clean_int is not None:
                    conds.append({"ticket_id": clean_int})
                    dec_conds.append({"ticket_id": clean_int})

                inc_doc = db_conn["incidents"].find_one({"$or": conds})
                past_decisions = list(db_conn["decisions"].find({"$or": dec_conds}))

            # Extract rejected ranks from decisions table
            existing_rejected = list(set([
                int(d.get("selected_rank")) for d in past_decisions
                if (d.get("decision_type") == "REJECT_CANDIDATE" or not d.get("confirmed")) and d.get("selected_rank") is not None
            ]))

            if not current_state.values or "ml_output" not in current_state.values:
                if inc_doc:
                    ml_out = inc_doc.get("prediction") or build_rca_input(inc_doc, inc_doc.get("prediction", {}))
                    rca_rep = inc_doc.get("agent_result") or {}
                    r_causes = rca_rep.get("ranked_causes", [])
                    workflow.update_state(config, {
                        "input_data": inc_doc,
                        "ml_output": ml_out,
                        "semantic_incident": rca_rep.get("semantic_incident", {}),
                        "rca_report": rca_rep,
                        "ranked_causes": r_causes,
                        "current_candidate": r_causes[0] if r_causes else {},
                        "dispatch_result": inc_doc.get("dispatch_result", {}),
                        "ticket": {
                            "ticket_id": str(ticket_id),
                            "location": inc_doc.get("location"),
                            "resource_type": inc_doc.get("resource_type"),
                            "assigned_to": inc_doc.get("assigned_to"),
                            "ranked_causes": r_causes,
                            "attempt": len(existing_rejected),
                            "rejected_ranks": existing_rejected
                        },
                        "status": "AWAITING_FEEDBACK"
                    }, as_node="dispatch")

            workflow.update_state(config, {
                "feedback_fixed": bool(confirmed),
                "selected_rank": int(rank) if rank else 1,
                "confirmed_root_cause": root_cause,
                "confirmed_resolution": resolution,
                "operator_notes": notes,
                "operator": operator,
                "commit_id": commit_id if confirmed else None
            })
            graph_state = workflow.invoke(None, config=config)
            graph_status = graph_state.get("status")
            next_candidate = graph_state.get("current_candidate")
            memory_result = graph_state.get("memory_result")
            escalation_result = graph_state.get("escalation")

            if graph_status == "ESCALATED":
                status_value = "FINISHED (ESCALATED)"
            elif graph_status in {"CLOSED", "MEMORY_SAVED"}:
                status_value = "FINISHED (RESOLVED)"

            # Ensure escalation status if all candidates are rejected
            if not confirmed:
                all_rejected = set(existing_rejected)
                all_rejected.add(int(rank))
                total_candidates = len(inc_doc.get("agent_result", {}).get("ranked_causes", [])) if inc_doc and "agent_result" in inc_doc else 3
                if len(all_rejected) >= total_candidates or graph_status == "ESCALATED":
                    status_value = "FINISHED (ESCALATED)"
                    if not escalation_result:
                        escalation_result = {
                            "ticket_id": str(ticket_id),
                            "assigned_group": "NOC_ENGINEERING_TEAM (Tier-3)",
                            "reason": f"All {total_candidates} automated RCA recommendations rejected by operator. Issue escalated to Tier-3 Senior NOC Team."
                        }
        except Exception as exc:
            traceback.print_exc()
            return jsonify({
                "success": False,
                "status": "FEEDBACK_WORKFLOW_FAILED",
                "message": "Failed to resume LangGraph workflow.",
                "error": str(exc)
            }), 500

        # Save operator decision strictly in decisions collection (do not mutate incidents collection)
        if db_conn is not None:
            try:
                decision_type = "COMMIT_RESOLUTION" if confirmed else (
                    "ESCALATION_TO_TIER_3" if status_value == "FINISHED (ESCALATED)" else "REJECT_CANDIDATE"
                )

                decision_doc = {
                    "ticket_id": ticket_id,
                    "decision_type": decision_type,
                    "confirmed": confirmed,
                    "selected_rank": int(rank) if rank else 1,
                    "root_cause": root_cause,
                    "resolution": resolution,
                    "notes": notes,
                    "operator": operator,
                    "commit_id": commit_id if confirmed else None,
                    "status": status_value,
                    "timestamp": now_iso
                }
                db_conn["decisions"].insert_one(decision_doc)
                print(f"[RECEIVER] Saved decision for incident #{ticket_id} to 'decisions' collection: {decision_type} ({status_value}).")
            except Exception as ex:
                print(f"[RECEIVER] MongoDB decision write error: {ex}")

        return jsonify({
            "success": True,
            "status": status_value,
            "commit_id": commit_id if confirmed else None,
            "next_candidate": next_candidate,
            "memory_saved": graph_state.get("memory_saved", False) if graph_state else bool(confirmed),
            "memory_result": memory_result,
            "escalation_result": escalation_result or (graph_state.get("escalation") if graph_state else None)
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "Feedback failed", "error": str(e)}), 500

# ============================================================
# API ENDPOINT 6: ESCALATE (DIRECT ESCALATION FALLBACK)
# ============================================================

@receiver_bp.route("/escalate", methods=["POST"])
def direct_escalate():
    try:
        data = request.get_json(silent=True) or {}
        ticket_id = data.get("ticket_id")
        reason = data.get("reason", "Operator escalated to Tier-3 NOC team.")
        now_iso = datetime.now(timezone.utc).isoformat()

        # Save escalation strictly in decisions collection (do not mutate incidents collection)
        db_conn = get_mongo_db()
        if db_conn is not None:
            try:
                db_conn["decisions"].insert_one({
                    "ticket_id": ticket_id,
                    "decision_type": "ESCALATION_TO_TIER_3",
                    "reason": reason,
                    "operator": data.get("operator", "NOC Operator"),
                    "status": "FINISHED (ESCALATED)",
                    "timestamp": now_iso
                })
                print(f"[RECEIVER] Stored ESCALATION_TO_TIER_3 in 'decisions' collection for #{ticket_id}.")
            except Exception as ex:
                print(f"[RECEIVER] MongoDB escalation write error: {ex}")

        return jsonify({
            "success": True,
            "status": "FINISHED (ESCALATED)",
            "ticket_id": ticket_id,
            "reason": reason,
            "escalated_at": now_iso
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================
# API ENDPOINT 7: DECISIONS LOG (DIRECT MONGODB QUERY)
# ============================================================

@receiver_bp.route("/decisions", methods=["GET"])
def get_decisions_log():
    db_conn = get_mongo_db()
    if db_conn is not None:
        try:
            docs = list(db_conn["decisions"].find({}, {"_id": 0}).sort("timestamp", -1))
            return jsonify({"success": True, "decisions": docs, "count": len(docs)})
        except Exception as ex:
            print(f"[RECEIVER] Decisions query error: {ex}")

    return jsonify({"success": True, "decisions": [], "count": 0})

@receiver_bp.route("/decisions/<ticket_id>", methods=["GET"])
def get_decisions_by_ticket(ticket_id):
    clean_id_str = str(ticket_id).replace("INC-", "").strip()
    try:
        query_id: Any = int(clean_id_str)
    except ValueError:
        query_id = clean_id_str

    db_conn = get_mongo_db()
    if db_conn is not None:
        try:
            docs = list(db_conn["decisions"].find({
                "$or": [
                    {"ticket_id": query_id},
                    {"ticket_id": clean_id_str},
                    {"ticket_id": f"INC-{clean_id_str}"}
                ]
            }, {"_id": 0}).sort("timestamp", 1))
            return jsonify({"success": True, "ticket_id": ticket_id, "decisions": docs, "count": len(docs)})
        except Exception as ex:
            print(f"[RECEIVER] Single ticket decisions query error: {ex}")

    return jsonify({"success": True, "ticket_id": ticket_id, "decisions": [], "count": 0})

# ============================================================
# SYSTEM HEALTH & STATS
# ============================================================

@receiver_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "service": "Telecom Autonomous RCA & Dispatch Gateway",
        "ml_model_loaded": MODEL_AVAILABLE,
        "workflow_loaded": WORKFLOW_AVAILABLE,
        "mongodb_connected": mongo_db is not None
    })

@receiver_bp.route("/system-stats", methods=["GET"])
def system_stats():
    db_conn = get_mongo_db()
    total_count = 0
    if db_conn is not None:
        try:
            total_count = db_conn["incidents"].count_documents({})
        except Exception:
            pass

    return jsonify({
        "success": True,
        "total_incidents": total_count,
        "ml_model": "xgboost_fault_severity_model.json",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
