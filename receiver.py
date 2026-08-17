from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any

import os
import sys
import traceback
from pathlib import Path

import pandas as pd
import numpy as np
import joblib
import xgboost as xgb
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================
# AGENT IMPORTS
# ============================================================

try:
    from ai_engine.agents.rca_engine import generate_rca_agentic
    from ai_engine.agents.dispatch_agent import load_reference_data, assign_dispatch
    from ai_engine.agents.feedback_agent import process_feedback
    from ai_engine.agents.escalation_agent import escalate
    from ai_engine.agents.memory_agent import save_resolution
except ModuleNotFoundError:
    from ai_engine.agents.rca_engine import generate_rca_agentic
    from ai_engine.agents.dispatch_agent import load_reference_data, assign_dispatch
    from ai_engine.agents.feedback_agent import process_feedback
    from ai_engine.agents.escalation_agent import escalate
    from ai_engine.agents.memory_agent import save_resolution


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# MODEL PATHS
# ============================================================

# First check project directory
PROJECT_MODEL_PATH = os.path.join(
    BASE_DIR,
    "experiment_37_best_xgboost.json"
)

PROJECT_PREPROCESSOR_PATH = os.path.join(
    BASE_DIR,
    "experiment_37_preprocessor.joblib"
)


# Fallback to original paths
OLD_MODEL_PATH = (
    r"C:\Users\sadik\best model"
    r"\experiment_37_results"
    r"\experiment_37_best_xgboost.json"
)

OLD_PREPROCESSOR_PATH = (
    r"C:\Users\sadik\best model"
    r"\experiment_37_results"
    r"\experiment_37_preprocessor.joblib"
)


# ============================================================
# RESOLVE FILE PATH
# ============================================================

def resolve_file(
    project_path,
    old_path
):

    if os.path.exists(
        project_path
    ):
        return project_path

    if os.path.exists(
        old_path
    ):
        return old_path

    raise FileNotFoundError(
        f"Required file not found.\n\n"
        f"Checked:\n"
        f"1. {project_path}\n"
        f"2. {old_path}"
    )


MODEL_PATH = resolve_file(
    PROJECT_MODEL_PATH,
    OLD_MODEL_PATH
)

PREPROCESSOR_PATH = resolve_file(
    PROJECT_PREPROCESSOR_PATH,
    OLD_PREPROCESSOR_PATH
)


# ============================================================
# SEVERITY NAMES
# ============================================================

SEVERITY_NAMES = {

    0: "Low Severity",

    1: "Medium Severity",

    2: "High Severity"
}


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(

    title="Telecom Fault Management API",

    description=(
        "Telecom ML prediction followed by "
        "Agentic RAG, dispatch, feedback, "
        "memory and escalation."
    ),

    version="4.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# LOAD XGBOOST MODEL
# ============================================================

print("\n")
print("=" * 80)
print("LOADING TELECOM FAULT SEVERITY MODEL")
print("=" * 80)

print(
    f"Model path:\n{MODEL_PATH}"
)

try:

    model = xgb.XGBClassifier()

    model.load_model(
        MODEL_PATH
    )

    print(
        "\nXGBoost model loaded successfully."
    )

except Exception as exc:

    print(
        "\nCRITICAL ERROR: "
        "Failed to load XGBoost model."
    )

    print(
        exc
    )

    raise RuntimeError(
        "Model loading failed."
    ) from exc


# ============================================================
# LOAD PREPROCESSOR
# ============================================================

print("\n")
print("=" * 80)
print("LOADING PREPROCESSOR")
print("=" * 80)

print(
    f"Preprocessor path:\n{PREPROCESSOR_PATH}"
)

try:

    preprocessor = joblib.load(
        PREPROCESSOR_PATH
    )

    print(
        "\nPreprocessor loaded successfully."
    )

except Exception as exc:

    print(
        "\nCRITICAL ERROR: "
        "Failed to load preprocessor."
    )

    print(
        exc
    )

    raise RuntimeError(
        "Preprocessor loading failed."
    ) from exc


# ============================================================
# EXPECTED FEATURES
# ============================================================

expected_features = list(
    preprocessor.feature_names_in_
)

print("\n")
print(
    f"Expected raw features: "
    f"{len(expected_features)}"
)

print(
    f"Encoded model feature count: "
    f"{model.n_features_in_}"
)


# ============================================================
# REQUEST SCHEMA
# ============================================================

class FaultData(BaseModel):

    # --------------------------------------------------------
    # Identity
    # --------------------------------------------------------

    id: int

    location: str

    severity_type: str

    resource_type: str

    # --------------------------------------------------------
    # Numerical ML features
    # --------------------------------------------------------

    event_count_x: float

    unique_event_count: float

    log_feature_count: float

    unique_log_features: float

    total_log_volume: float

    mean_log_volume: float

    max_log_volume: float

    min_log_volume: float

    event_count_y: float

    event_event_type_unique: float

    log_count: float

    log_log_feature_unique: float

    log_volume_unique: float

    resource_count: float

    resource_resource_type_unique: float

    log_count_ratio: float

    resource_count_ratio: float

    # --------------------------------------------------------
    # Interaction features
    # --------------------------------------------------------

    severity_resource: str

    severity_location: str

    resource_location: str

    # --------------------------------------------------------
    # RCA arrays
    # --------------------------------------------------------

    event_types: List[str] = Field(
        default_factory=list
    )

    log_features: List[str] = Field(
        default_factory=list
    )


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():

    return {

        "status":
            "online",

        "service":
            "Telecom Fault Management API",

        "pipeline":
            "Sender → XGBoost → Agentic RAG → Dispatch → Feedback"
    }


# ============================================================
# HEALTH ENDPOINT
# ============================================================

@app.get("/health")
def health():

    return {

        "status":
            "healthy",

        "model_loaded":
            True,

        "preprocessor_loaded":
            True,

        "agent_pipeline":
            "connected",

        "model_features":
            int(
                model.n_features_in_
            )
    }


# ============================================================
# XGBOOST ML PIPELINE
# ============================================================

def execute_ml_pipeline(
    data: FaultData
):

    # ========================================================
    # STEP 1 — REQUEST → DICTIONARY
    # ========================================================

    payload = data.model_dump()


    # ========================================================
    # STEP 2 — CHECK REQUIRED FEATURES
    # ========================================================

    received_features = set(
        payload.keys()
    )

    missing_features = [

        feature

        for feature in expected_features

        if feature not in received_features
    ]


    if missing_features:

        raise HTTPException(

            status_code=400,

            detail={

                "message":
                    "Missing required ML features",

                "missing_features":
                    missing_features
            }
        )


    # ========================================================
    # STEP 3 — DATAFRAME
    # ========================================================

    feature_df = pd.DataFrame(
        [payload]
    )


    # Use exact feature order from training
    feature_df = feature_df[
        expected_features
    ]


    # ========================================================
    # STEP 4 — CATEGORICAL FEATURES
    # ========================================================

    categorical_features = [

        "location",

        "severity_type",

        "resource_type",

        "severity_resource",

        "severity_location",

        "resource_location"
    ]


    for column in categorical_features:

        if column in feature_df.columns:

            feature_df[column] = (

                feature_df[column]

                .fillna(
                    "UNKNOWN"
                )

                .astype(str)
            )


    # ========================================================
    # STEP 5 — NUMERICAL FEATURES
    # ========================================================

    for column in feature_df.columns:

        if column not in categorical_features:

            feature_df[column] = (

                pd.to_numeric(
                    feature_df[column],
                    errors="coerce"
                )

                .replace(
                    [
                        np.inf,
                        -np.inf
                    ],
                    np.nan
                )

                .fillna(0)
            )


    # ========================================================
    # STEP 6 — PREPROCESS
    # ========================================================

    try:

        X = preprocessor.transform(
            feature_df
        )

    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail={

                "stage":
                    "Preprocessing",

                "error":
                    str(exc)
            }
        )


    print(
        "\nEncoded feature shape:",
        X.shape
    )


    # ========================================================
    # STEP 7 — FEATURE COUNT CHECK
    # ========================================================

    if X.shape[1] != model.n_features_in_:

        raise HTTPException(

            status_code=500,

            detail={

                "message":
                    "Feature count mismatch",

                "model_expected":
                    int(
                        model.n_features_in_
                    ),

                "received":
                    int(
                        X.shape[1]
                    )
            }
        )


    # ========================================================
    # STEP 8 — XGBOOST PREDICTION
    # ========================================================

    try:

        probabilities = (
            model.predict_proba(
                X
            )
        )


        prediction = int(

            np.argmax(
                probabilities,
                axis=1
            )[0]
        )


        severity = (
            SEVERITY_NAMES.get(
                prediction,
                "Unknown"
            )
        )


        confidence = float(
            np.max(
                probabilities[0]
            )
        )


    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail={

                "stage":
                    "XGBoost",

                "error":
                    str(exc)
            }
        )


    return {

        "fault_severity":
            prediction,

        "severity":
            severity,

        "confidence":
            round(
                confidence,
                4
            ),

        "probabilities": {

            "low":
                float(
                    probabilities[0][0]
                ),

            "medium":
                float(
                    probabilities[0][1]
                ),

            "high":
                float(
                    probabilities[0][2]
                )
        }
    }


# ============================================================
# BUILD EXACT ML OUTPUT
# ============================================================

def build_ml_output(
    data: FaultData,
    ml_result: Dict[str, Any]
):

    """
    This is the exact structure passed from
    the ML layer into the Agentic RAG layer.
    """

    return {

        "predicted_fault_severity":
            ml_result[
                "fault_severity"
            ],

        "severity_type":
            data.severity_type,

        "resource_type":
            data.resource_type,

        "event_types":
            list(
                data.event_types
            ),

        "log_features":
            list(
                data.log_features
            ),

        "volume":
            data.total_log_volume
    }


# ============================================================
# COMPLETE AGENTIC PIPELINE
# ============================================================

def run_agent_pipeline(
    ml_output,
    location,
    ticket_id
):

    # ========================================================
    # STEP 1 — AGENTIC RCA
    # ========================================================

    print("\n")
    print("=" * 100)
    print("ROOT CAUSE ANALYSIS")
    print("=" * 100)


    rca_report = (
        generate_rca_agentic(
            ml_output
        )
    )


    ranked_causes = (
        rca_report[
            "ranked_causes"
        ]
    )


    if len(
        ranked_causes
    ) != 3:

        raise RuntimeError(
            "RCA Agent did not return exactly 3 candidates."
        )


    # ========================================================
    # DISPLAY RCA
    # ========================================================

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


    print(
        "\nRanked RCA Candidates:"
    )


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


    # ========================================================
    # STEP 2 — DISPATCH
    # ========================================================

    print("\n")
    print("=" * 100)
    print("DISPATCH REPORT")
    print("=" * 100)


    technicians, spare_parts = (
        load_reference_data()
    )


    top_candidate = (
        ranked_causes[0]
    )


    fault = {

        "id":
            str(ticket_id),

        "location":
            location,

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


    print(
        f"Dispatch Status : "
        f"{dispatch_result['status']}"
    )


    # ========================================================
    # NO TECHNICIAN
    # ========================================================

    if (
        dispatch_result[
            "technician"
        ]
        is None
    ):

        print(
            "\nNo suitable technician available."
        )


        if dispatch_result[
            "escalation"
        ]:

            print("\n")
            print(
                "Escalated to Admin/NOC"
            )

            print(
                dispatch_result[
                    "escalation"
                ]
            )


        return {

            "status":
                "ESCALATED",

            "rca":
                rca_report,

            "dispatch":
                dispatch_result
        }


    # ========================================================
    # TECHNICIAN
    # ========================================================

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


    # ========================================================
    # SPARE PART
    # ========================================================

    spare = (
        dispatch_result[
            "spare_part"
        ]
    )


    print(
        "\nSpare Part Information"
    )


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


    # ========================================================
    # CREATE TICKET
    # ========================================================

    ticket = {

        "ticket_id":
            str(ticket_id),

        "location":
            location,

        "resource_type":
            ml_output[
                "resource_type"
            ],

        "fault_severity":
            ml_output[
                "predicted_fault_severity"
            ],

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


    # ========================================================
    # STEP 3 — FEEDBACK LOOP
    # ========================================================

    while True:

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
            "\nProbable Root Cause:"
        )

        print(
            current_root_cause
        )


        print(
            "\nConfidence:"
        )

        print(
            current_confidence
        )


        print(
            "\nRecommended Resolution:"
        )

        print(
            current_resolution
        )


        # ====================================================
        # OPERATOR FEEDBACK
        # ====================================================

        while True:

            feedback = input(
                "\nIssue Fixed? (yes/no): "
            ).strip().lower()


            if feedback in (
                "yes",
                "no"
            ):

                break


            print(
                "\nPlease enter "
                "'yes' or 'no'."
            )


        # ====================================================
        # SUCCESS
        # ====================================================

        if feedback == "yes":

            ticket[
                "status"
            ] = "CLOSED"


            # ------------------------------------------------
            # STORE ONLY SUCCESSFUL RESOLUTION
            # ------------------------------------------------

            save_resolution(

                ml_output=
                    ml_output,

                semantic_incident=
                    rca_report[
                        "semantic_incident"
                    ],

                root_cause=
                    current_root_cause,

                successful_action=
                    current_resolution
            )


            print("\n")
            print("=" * 90)
            print(
                "TICKET CLOSED"
            )
            print("=" * 90)


            print(
                "Issue resolved successfully."
            )


            return {

                "status":
                    "CLOSED",

                "rca":
                    rca_report,

                "dispatch":
                    dispatch_result,

                "ticket":
                    ticket,

                "successful_resolution": {

                    "root_cause":
                        current_root_cause,

                    "resolution":
                        current_resolution
                }
            }


        # ====================================================
        # FAILED
        # ====================================================

        result = process_feedback(

            ticket,

            fixed=False
        )


        # ====================================================
        # NEXT RCA HYPOTHESIS
        # ====================================================

        if (
            result[
                "status"
            ]
            == "RETRY"
        ):

            next_candidate = (
                result[
                    "next_candidate"
                ]
            )


            print("\n")
            print("=" * 80)

            print(
                "PREVIOUS HYPOTHESIS FAILED"
            )

            print("=" * 80)


            print(
                "Moving to next root-cause "
                "hypothesis:"
            )


            print(
                next_candidate[
                    "root_cause"
                ]
            )


            continue


        # ====================================================
        # ESCALATION
        # ====================================================

        if (
            result[
                "status"
            ]
            == "ESCALATE"
        ):

            ticket[
                "status"
            ] = "ESCALATED"


            escalation_report = escalate(

                ticket,

                reason=(
                    "All three ranked "
                    "RCA resolutions failed."
                )
            )


            print("\n")
            print("=" * 80)
            print(
                "ESCALATION REPORT"
            )
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


            return {

                "status":
                    "ESCALATED",

                "rca":
                    rca_report,

                "dispatch":
                    dispatch_result,

                "ticket":
                    ticket,

                "escalation":
                    escalation_report
            }


# ============================================================
# PREDICT ONLY
# ============================================================

@app.post("/predict")
def predict(
    data: FaultData
):

    print("\n")
    print("=" * 80)
    print(
        "SYSTEM 1 -> RECEIVER"
    )
    print(
        "XGBOOST PREDICTION ONLY"
    )
    print("=" * 80)


    prediction = (
        execute_ml_pipeline(
            data
        )
    )


    return {

        "status":
            "success",

        "ticket_id":
            data.id,

        "fault_prediction":
            prediction
    }


# ============================================================
# FULL END-TO-END ENDPOINT
# ============================================================

@app.post(
    "/predict-and-rca"
)
def predict_and_rca(
    data: FaultData
):

    print("\n")
    print("=" * 100)
    print(
        "SYSTEM 1 -> RECEIVER"
    )
    print(
        "FULL TELECOM INCIDENT PIPELINE"
    )
    print("=" * 100)


    # ========================================================
    # STEP 1 — XGBOOST
    # ========================================================

    print("\n")
    print("=" * 100)
    print(
        "STEP 1 - XGBOOST FAULT SEVERITY"
    )
    print("=" * 100)


    try:

        prediction = (
            execute_ml_pipeline(
                data
            )
        )


        print(
            "\nTicket ID:",
            data.id
        )

        print(
            "Fault Severity:",
            prediction[
                "fault_severity"
            ]
        )

        print(
            "Severity:",
            prediction[
                "severity"
            ]
        )

        print(
            "Confidence:",
            prediction[
                "confidence"
            ]
        )


    except Exception as exc:

        traceback.print_exc()


        if isinstance(
            exc,
            HTTPException
        ):

            raise


        raise HTTPException(

            status_code=500,

            detail={

                "stage":
                    "XGBoost",

                "error":
                    str(exc)
            }
        )


    # ========================================================
    # STEP 1.5 — ZERO SEVERITY GATE
    # ========================================================
    #
    # 0 = Low Severity / no actionable fault.
    #
    # Do NOT execute:
    #   - Mapping
    #   - RAG
    #   - Ollama
    #   - Dispatch
    #   - Feedback
    #   - Memory
    #   - Escalation
    #
    # ========================================================

    if (
        prediction[
            "fault_severity"
        ]
        == 0
    ):

        print("\n")
        print("=" * 100)
        print(
            "NO ACTIONABLE FAULT DETECTED"
        )
        print("=" * 100)


        print(
            "Fault severity is 0."
        )


        print(
            "Skipping Agentic RAG."
        )


        print(
            "No technician will be dispatched."
        )


        return {

            "status":
                "success",

            "ticket_id":
                data.id,

            "fault_prediction":
                prediction,

            "agent_pipeline": {

                "executed":
                    False,

                "reason":
                    "Fault severity is 0"
            }
        }


    # ========================================================
    # STEP 2 — BUILD EXACT ML OUTPUT
    # ========================================================

    print("\n")
    print("=" * 100)
    print(
        "STEP 2 - ML OUTPUT"
    )
    print("=" * 100)


    ml_output = (
        build_ml_output(
            data,
            prediction
        )
    )


    print(
        "\nML OUTPUT:"
    )

    print(
        ml_output
    )


    # ========================================================
    # STEP 3 — AGENTIC SYSTEM
    # ========================================================

    print("\n")
    print("=" * 100)
    print(
        "STEP 3 - AGENTIC RCA + OPERATIONS"
    )
    print("=" * 100)


    try:

        agent_result = (
            run_agent_pipeline(

                ml_output=
                    ml_output,

                location=
                    data.location,

                ticket_id=
                    str(data.id)
            )
        )


    except Exception as exc:

        print("\n")
        print(
            "AGENTIC PIPELINE ERROR"
        )

        traceback.print_exc()

        return {
            "status": "partial_success",
            "ticket_id": data.id,
            "ml_output": ml_output,
            "fault_prediction": prediction,
            "agent_pipeline": {
                "executed": False,
                "reason": "Agentic RCA pipeline failed",
                "error": str(exc),
            },
            "message": "ML prediction ran successfully, but the RCA/agent pipeline did not complete."
        }


    # ========================================================
    # STEP 4 — COMPLETE
    # ========================================================

    print("\n")
    print("=" * 100)
    print(
        "STEP 4 - COMPLETE"
    )
    print("=" * 100)


    return {

        "status":
            "success",

        "ticket_id":
            data.id,

        "ml_output":
            ml_output,

        "fault_prediction":
            prediction,

        "agent_result":
            agent_result
    }


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 100)
    print(
        "STARTING TELECOM FAULT MANAGEMENT SERVER"
    )
    print("=" * 100)


    print(
        "\nAPI:"
        " http://127.0.0.1:8001"
    )

    print(
        "Swagger:"
        " http://127.0.0.1:8001/docs"
    )

    print(
        "Predict:"
        " http://127.0.0.1:8001/predict"
    )

    print(
        "Predict + RCA:"
        " http://127.0.0.1:8001/predict-and-rca"
    )


    uvicorn.run(

        app,

        host="0.0.0.0",

        port=8001,

        reload=False
    )