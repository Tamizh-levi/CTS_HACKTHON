import os

import pandas as pd

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


# ==========================================================
# CONFIG
# ==========================================================

RESOLUTION_FILE = "resolution_history.csv"

VECTOR_DB_PATH = "vector_db"

EMBEDDING_MODEL = (
    r"C:\Users\sadik\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2\snapshots\1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
)


# ==========================================================
# EMBEDDINGS
# ==========================================================

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL
)


# ==========================================================
# PATTERN DATABASE
# ==========================================================

pattern_db = Chroma(
    collection_name="telecom_patterns",
    persist_directory=VECTOR_DB_PATH,
    embedding_function=embeddings
)


# ==========================================================
# SAVE SUCCESSFUL RESOLUTION
# ==========================================================

def save_resolution(
    ml_output,
    semantic_incident,
    root_cause,
    successful_action
):

    raw_signature = (
        f"Severity Type: "
        f"{ml_output['severity_type']}\n"
        f"Resource Type: "
        f"{ml_output['resource_type']}\n"
        f"Event Types: "
        f"{','.join(ml_output['event_types'])}\n"
        f"Log Features: "
        f"{','.join(ml_output['log_features'])}"
    )

    semantic_signature = (
        f"Severity: "
        f"{semantic_incident['severity']}\n"
        f"Resource: "
        f"{semantic_incident['resource']}\n"
        f"Events: "
        f"{','.join(semantic_incident['events'])}\n"
        f"Feature Groups: "
        f"{','.join(semantic_incident['feature_groups'])}"
    )

    document = f"""
RAW INCIDENT SIGNATURE:
{raw_signature}

SEMANTIC INCIDENT SIGNATURE:
{semantic_signature}

Resolved Root Cause:
{root_cause}

Successful Resolution:
{successful_action}
""".strip()

    # ======================================================
    # SAVE CSV
    # ======================================================

    row = pd.DataFrame([
        {
            "raw_incident_signature":
                raw_signature.replace(
                    "\n",
                    " | "
                ),

            "semantic_incident_signature":
                semantic_signature.replace(
                    "\n",
                    " | "
                ),

            "root_cause":
                root_cause,

            "successful_resolution":
                successful_action
        }
    ])

    if os.path.exists(
        RESOLUTION_FILE
    ):

        existing = pd.read_csv(
            RESOLUTION_FILE
        )

        updated = pd.concat(
            [
                existing,
                row
            ],
            ignore_index=True
        )

        updated.to_csv(
            RESOLUTION_FILE,
            index=False
        )

    else:

        row.to_csv(
            RESOLUTION_FILE,
            index=False
        )

    # ======================================================
    # ADD TO PATTERN VECTOR DB
    # ======================================================

    pattern_db.add_texts(
        texts=[document],

        metadatas=[
            {
                "severity_type":
                    ml_output[
                        "severity_type"
                    ],

                "resource_type":
                    ml_output[
                        "resource_type"
                    ],

                "root_cause":
                    root_cause,

                "source":
                    "successful_resolution"
            }
        ]
    )

    print("\n")
    print("=" * 90)
    print("SELF-LEARNING MEMORY UPDATED")
    print("=" * 90)

    print(document)