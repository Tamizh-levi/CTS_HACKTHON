# backend/rag/agents/memory_agent.py
"""
Direct ChromaDB + CSV Self-Learning Memory Agent

"""

import os
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer

# ==========================================================
# PATHS
# ==========================================================

CURRENT_FILE = os.path.abspath(__file__)
AGENTS_DIR = os.path.dirname(CURRENT_FILE)
RAG_DIR = os.path.dirname(AGENTS_DIR)

RESOLUTION_FILE = os.path.join(RAG_DIR, "resolution_history.csv")
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", os.path.join(RAG_DIR, "vector_db"))
VECTOR_DB_PATH = os.path.abspath(os.path.expanduser(VECTOR_DB_PATH))

DEFAULT_EMBEDDING_MODEL = (
    r"C:\Users\sadik\.cache\huggingface\hub"
    r"\models--sentence-transformers--all-MiniLM-L6-v2"
    r"\snapshots\1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_PATH", DEFAULT_EMBEDDING_MODEL)
if not os.path.exists(EMBEDDING_MODEL):
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

print()
print("=" * 80)
print("INITIALIZING DIRECT CHROMADB MEMORY AGENT (NO LANGCHAIN)")
print("=" * 80)
print(f"[MEMORY] Resolution File : {RESOLUTION_FILE}")
print(f"[MEMORY] Vector DB Path  : {VECTOR_DB_PATH}")

# ==========================================================
# DIRECT CHROMADB CLIENT
# ==========================================================

class DirectMiniLMEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self, model_path_or_name: str):
        self.model = SentenceTransformer(model_path_or_name)

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        if not input:
            return []
        embeddings = self.model.encode(list(input), convert_to_numpy=True)
        return embeddings.tolist()

try:
    embedding_fn = DirectMiniLMEmbeddingFunction(EMBEDDING_MODEL)
    chroma_client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    pattern_collection = chroma_client.get_or_create_collection(
        name="telecom_patterns",
        embedding_function=embedding_fn
    )
except Exception as exc:
    print(f"[MEMORY] ChromaDB memory init warning: {exc}")
    pattern_collection = None

# ==========================================================
# SAVE RESOLUTION (AFTER CONFIRMED YES)
# ==========================================================

def save_resolution(
    ml_output: Dict[str, Any],
    semantic_incident: Dict[str, Any],
    root_cause: str,
    successful_action: str,
    ticket_id: Any = None,
    operator: str = "NOC Operator",
    operator_notes: str = ""
) -> Dict[str, Any]:
    """
    Saves operator-confirmed root cause resolution into resolution_history.csv
    and embeds into ChromaDB telecom_patterns collection.
    """
    root_cause = str(root_cause or "").strip()
    successful_action = str(successful_action or "").strip()
    if not root_cause or not successful_action:
        raise ValueError("Cannot save resolution without root_cause and successful_action.")

    events_list = ml_output.get("event_types", [])
    if isinstance(events_list, list):
        events_str = ", ".join([str(e) for e in events_list])
    else:
        events_str = str(events_list)

    logs_list = ml_output.get("log_features", [])
    if isinstance(logs_list, list):
        logs_str = ", ".join([str(l) for l in logs_list])
    else:
        logs_str = str(logs_list)

    raw_sig = (
        f"Severity Type: {ml_output.get('severity_type')}\n"
        f"Resource Type: {ml_output.get('resource_type')}\n"
        f"Event Types: {events_str}\n"
        f"Log Features: {logs_str}"
    )

    sem_events = semantic_incident.get("events", [])
    sem_events_str = ", ".join([str(e) for e in sem_events]) if isinstance(sem_events, list) else str(sem_events)
    sem_features = semantic_incident.get("feature_groups", [])
    sem_features_str = ", ".join([str(f) for f in sem_features]) if isinstance(sem_features, list) else str(sem_features)

    sem_sig = (
        f"Severity: {semantic_incident.get('severity')}\n"
        f"Resource: {semantic_incident.get('resource')}\n"
        f"Events: {sem_events_str}\n"
        f"Feature Groups: {sem_features_str}"
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    doc_text = (
        f"RAW INCIDENT SIGNATURE:\n{raw_sig}\n\n"
        f"SEMANTIC INCIDENT SIGNATURE:\n{sem_sig}\n\n"
        f"Resolved Root Cause:\n{root_cause}\n\n"
        f"Successful Resolution:\n{successful_action}\n\n"
        f"Operator: {operator}\n"
        f"Confirmed At: {now_iso}"
    )

    # 1. Append to CSV
    row = pd.DataFrame([{
        "ticket_id": str(ticket_id or ""),
        "raw_incident_signature": raw_sig.replace("\n", " | "),
        "semantic_incident_signature": sem_sig.replace("\n", " | "),
        "root_cause": root_cause,
        "successful_resolution": successful_action,
        "operator": operator,
        "operator_notes": operator_notes,
        "confirmed_at": now_iso
    }])

    os.makedirs(os.path.dirname(RESOLUTION_FILE), exist_ok=True)
    if os.path.exists(RESOLUTION_FILE):
        updated = pd.concat([pd.read_csv(RESOLUTION_FILE), row], ignore_index=True)
    else:
        updated = row
    updated.to_csv(RESOLUTION_FILE, index=False)

    # 2. Add text directly to ChromaDB
    mem_key = hashlib.sha256(f"{raw_sig}|{root_cause}|{now_iso}".encode("utf-8")).hexdigest()
    if pattern_collection:
        try:
            pattern_collection.add(
                documents=[doc_text],
                metadatas=[{
                    "ticket_id": str(ticket_id or ""),
                    "severity_type": str(ml_output.get("severity_type", "")),
                    "resource_type": str(ml_output.get("resource_type", "")),
                    "root_cause": root_cause,
                    "source": "successful_resolution",
                    "operator": operator
                }],
                ids=[f"MEM-{mem_key[:16]}"]
            )
            print(f"[MEMORY] Successfully embedded resolution into ChromaDB: MEM-{mem_key[:16]}")
        except Exception as exc:
            print(f"[MEMORY] ChromaDB add error: {exc}")

    print()
    print("=" * 90)
    print("SELF-LEARNING MEMORY UPDATED (CONFIRMED OPERATOR YES)")
    print("=" * 90)
    print(doc_text)

    return {
        "saved": True,
        "ticket_id": ticket_id,
        "root_cause": root_cause,
        "resolution": successful_action,
        "confirmed_at": now_iso
    }

__all__ = ["save_resolution"]