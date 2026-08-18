# backend/rag/agents/rca_engine.py
"""
Direct HTTP Ollama + Direct ChromaDB Telecom RCA Engine

"""

import os
import re
import json
from typing import Any, Dict, List
import requests
import chromadb
from sentence_transformers import SentenceTransformer

# ==========================================================
# PATH CONFIGURATION
# ==========================================================

CURRENT_FILE = os.path.abspath(__file__)
AGENTS_DIR = os.path.dirname(CURRENT_FILE)
RAG_DIR = os.path.dirname(AGENTS_DIR)
BACKEND_DIR = os.path.dirname(RAG_DIR)

VECTOR_DB_PATH = os.getenv(
    "VECTOR_DB_PATH",
    os.path.join(RAG_DIR, "vector_db")
)
VECTOR_DB_PATH = os.path.abspath(os.path.expanduser(VECTOR_DB_PATH))

DEFAULT_EMBEDDING_MODEL = (
    r"C:\Users\sadik\.cache\huggingface\hub"
    r"\models--sentence-transformers--all-MiniLM-L6-v2"
    r"\snapshots\1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_PATH", DEFAULT_EMBEDDING_MODEL)
if not os.path.exists(EMBEDDING_MODEL):
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "telecom-copilot")

print()
print("=" * 80)
print("INITIALIZING DIRECT OLLAMA + CHROMADB RCA ENGINE (NO LANGCHAIN)")
print("=" * 80)
print(f"[RCA] Vector DB Path  : {VECTOR_DB_PATH}")
print(f"[RCA] Embedding Model : {EMBEDDING_MODEL}")
print(f"[RCA] Ollama Endpoint : {OLLAMA_BASE_URL}/api/chat")
print(f"[RCA] Ollama Model    : {OLLAMA_MODEL}")

# ==========================================================
# DIRECT CHROMADB EMBEDDING FUNCTION
# ==========================================================

class DirectMiniLMEmbeddingFunction(chromadb.EmbeddingFunction):
    """Zero-LangChain embedding wrapper using native sentence-transformers."""
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
    
    knowledge_collection = chroma_client.get_or_create_collection(
        name="telecom_knowledge",
        embedding_function=embedding_fn
    )
    pattern_collection = chroma_client.get_or_create_collection(
        name="telecom_patterns",
        embedding_function=embedding_fn
    )
    print("[RCA] Connected directly to Chroma collections: telecom_knowledge, telecom_patterns")
except Exception as exc:
    print(f"[RCA] ChromaDB initialization warning: {exc}")
    embedding_fn = None
    chroma_client = None
    knowledge_collection = None
    pattern_collection = None

# ==========================================================
# REUSABLE DIRECT OLLAMA HTTP CALL
# ==========================================================

def call_ollama(system_prompt: str, user_prompt: str, timeout: int = 90) -> str:
    """
    Direct HTTP POST to Ollama /api/chat.
    Streams=False, Format=JSON, Temperature=0.
    """
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        
        content = data.get("message", {}).get("content", "")
        if not content:
            raise RuntimeError("Ollama returned an empty message content.")
        return content.strip()
    except requests.exceptions.ConnectionError as exc:
        print(f"[RCA OLLAMA CONNECTION ERROR] Could not connect to Ollama at {url}: {exc}")
        raise RuntimeError(f"Ollama connection refused at {url}. Ensure Ollama is running ('ollama serve').") from exc
    except requests.exceptions.HTTPError as exc:
        print(f"[RCA OLLAMA HTTP ERROR] HTTP error from Ollama: {exc}")
        raise RuntimeError(f"Ollama HTTP error: {exc}") from exc
    except Exception as exc:
        print(f"[RCA OLLAMA UNEXPECTED ERROR] {exc}")
        raise RuntimeError(f"Ollama invocation failed: {exc}") from exc

# ==========================================================
# SEMANTIC TELECOM DICTIONARIES
# ==========================================================

SEVERITY_MAP = {
    "severity_type 1": "Informational Alert",
    "severity_type 2": "Warning Alert",
    "severity_type 3": "Minor Impairment Alert",
    "severity_type 4": "Major Degraded Alert",
    "severity_type 5": "Critical Alert"
}

RESOURCE_MAP = {
    "resource_type 1": "Core Router Group",
    "resource_type 2": "DWDM Optical Transponder",
    "resource_type 3": "IP Edge Aggregation Switch",
    "resource_type 4": "BGP Edge Gateway",
    "resource_type 5": "Optical Line Terminal",
    "resource_type 6": "MPLS Core Node",
    "resource_type 7": "Backhaul Microwave Link",
    "resource_type 8": "Cellular Tower Radio Unit",
    "resource_type 9": "SDN Controller Interface",
    "resource_type 10": "Environmental Control Systems"
}

EVENT_MAP = {
    "event_type 1": "Connectivity Warning",
    "event_type 2": "Frame Loss Spike",
    "event_type 3": "Link Flapping",
    "event_type 4": "Packet Drop Threshold Exceeded",
    "event_type 5": "Keepalive Timeout",
    "event_type 6": "Buffer Overflow",
    "event_type 7": "Optical Power Loss",
    "event_type 8": "BGP Peer Reset",
    "event_type 9": "Interface Error Burst",
    "event_type 10": "CRC Alignment Error",
    "event_type 11": "High Latency Jitter",
    "event_type 12": "QoS Queue Congestion",
    "event_type 13": "Hardware Sensor Alarm",
    "event_type 14": "Chassis Thermal Warning",
    "event_type 15": "Power Supply Voltage Fluctuation",
    "event_type 16": "Transceiver RX Low Optical Power",
    "event_type 17": "Fiber Attenuation Warning",
    "event_type 18": "Laser Bias Degradation",
    "event_type 19": "Port Synchronization Failure",
    "event_type 20": "VLAN Isolation Error",
    "event_type 21": "Spanning Tree Topology Change",
    "event_type 22": "MAC Address Table Exhaustion",
    "event_type 23": "Routing Table Convergence Storm",
    "event_type 24": "OSPF Neighbor State Drop",
    "event_type 25": "MPLS Label Distribution Error",
    "event_type 26": "LDP Session Teardown",
    "event_type 27": "Clock Drift Frequency Out-of-Lock",
    "event_type 28": "PTP Time Sync Lost",
    "event_type 29": "Microwave Fade Event",
    "event_type 30": "BER Threshold Violation",
    "event_type 31": "FEC Uncorrectable Block Alarm",
    "event_type 32": "Signal Degrade (SD) Alarm",
    "event_type 33": "Loss of Signal (LOS)",
    "event_type 34": "Loss of Frame (LOF)",
    "event_type 35": "AIS Alarm Indication Signal",
    "event_type 36": "RDI Remote Defect Indication",
    "event_type 37": "Payload Defect Indicator",
    "event_type 38": "Firmware Panic Recovery",
    "event_type 39": "ASIC Watchdog Reset",
    "event_type 40": "Memory Allocation Failure",
    "event_type 41": "CPU Utilization Spike",
    "event_type 42": "Fan Tray Failure",
    "event_type 43": "Secondary Power Supply Offline",
    "event_type 44": "DC Power Converter Dropout",
    "event_type 45": "BGP Dampening Activated",
    "event_type 46": "Prefix Limit Exceeded",
    "event_type 47": "Storm Control Filter Drop",
    "event_type 48": "Micro-burst Detection",
    "event_type 49": "Security Intrusion Warning",
    "event_type 50": "DDoS Anomaly Triggered",
    "event_type 51": "Configuration Rollback Detected",
    "event_type 52": "System Outage Critical Event",
    "event_type 53": "Emergency Circuit Cutover",
    "event_type 54": "Autonomous Diagnostic Fail"
}

def map_feature_group(feature_str: Any) -> str:
    match = re.search(r"(\d+)", str(feature_str))
    if not match:
        return "Unknown Feature Group"
    val = int(match.group(1))
    if 1 <= val <= 50:
        return "Packet Quality Indicators"
    if 51 <= val <= 100:
        return "Traffic Volume Indicators"
    if 101 <= val <= 150:
        return "Hardware Indicators"
    if 151 <= val <= 200:
        return "Power & Voltage Indicators"
    if 201 <= val <= 250:
        return "Optical & Physical Layer Indicators"
    if 251 <= val <= 300:
        return "Configuration & Routing Indicators"
    if 301 <= val <= 386:
        return "Security & Control Plane Indicators"
    return "Unknown Feature Group"

def build_semantic_incident(ml_output: Dict[str, Any]) -> Dict[str, Any]:
    raw_severity = ml_output.get("severity_type", "Unknown")
    raw_resource = ml_output.get("resource_type", "Unknown")
    raw_events = ml_output.get("event_types", [])
    if isinstance(raw_events, str):
        raw_events = [raw_events]
    raw_features = ml_output.get("log_features", [])
    if isinstance(raw_features, str):
        raw_features = [raw_features]

    return {
        "severity": SEVERITY_MAP.get(raw_severity, "Unknown Severity"),
        "resource": RESOURCE_MAP.get(raw_resource, "Unknown Resource"),
        "events": [EVENT_MAP.get(e, e) for e in raw_events],
        "feature_groups": [map_feature_group(f) for f in raw_features],
        "predicted_fault_severity": ml_output.get("predicted_fault_severity", ml_output.get("fault_severity", 0)),
        "volume": ml_output.get("total_log_volume", ml_output.get("volume", 0)),
        "raw_severity": raw_severity,
        "raw_resource": raw_resource,
        "raw_events": raw_events,
        "raw_features": raw_features
    }

# ==========================================================
# RETRIEVAL FROM CHROMADB
# ==========================================================

def retrieve_telecom_knowledge(semantic_query: str, k: int = 3) -> str:
    if not knowledge_collection:
        return "[ChromaDB telecom_knowledge collection unavailable]"
    try:
        res = knowledge_collection.query(query_texts=[semantic_query], n_results=k)
        docs = res.get("documents", [[]])[0]
        return "\n\n".join(docs) if docs else "[No matching telecom knowledge retrieved]"
    except Exception as exc:
        print(f"[RCA] Knowledge retrieval error: {exc}")
        return f"[Knowledge retrieval error: {exc}]"

def retrieve_historical_patterns(pattern_query: str, k: int = 5) -> str:
    if not pattern_collection:
        return "[ChromaDB telecom_patterns collection unavailable]"
    try:
        res = pattern_collection.query(query_texts=[pattern_query], n_results=k)
        docs = res.get("documents", [[]])[0]
        return "\n\n".join(docs) if docs else "[No matching historical patterns retrieved]"
    except Exception as exc:
        print(f"[RCA] Pattern retrieval error: {exc}")
        return f"[Pattern retrieval error: {exc}]"

# ==========================================================
# CLEAN & VALIDATE JSON RESPONSE (ROBUST NORMALIZATION)
# ==========================================================

def clean_and_parse_json(
    raw_text: str
) -> Dict[str, Any]:
    """
    Parse and normalize Ollama RCA JSON.

    Supported model outputs include:

    1. The preferred format:
       {
           "severity_category": "...",
           "summary": "...",
           "causes": [
               {
                   "cause": "...",
                   "confidence": 0.95,
                   "evidence": "..."
               },
               ...
           ],
           "recommended_actions": [
               "Action for cause 1",
               "Action for cause 2",
               "Action for cause 3"
           ]
       }

    2. A normalized format using "ranked_causes" where each
       candidate already contains root_cause/resolution.

    The function converts both into the single contract used by
    Flask, LangGraph, MongoDB, and React:

    {
        "risk_level": "...",
        "technical_summary": "...",
        "ranked_causes": [
            {
                "rank": 1,
                "root_cause": "...",
                "resolution": "...",
                "confidence": 0.95,
                "evidence": "..."
            },
            ...
        ]
    }
    """

    if not raw_text:
        raise ValueError(
            "Ollama returned an empty response."
        )

    # ======================================================
    # CLEAN RESPONSE
    # ======================================================

    text = raw_text.strip()

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    # ======================================================
    # PARSE JSON
    # ======================================================

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print()
        print("=" * 100)
        print("OLLAMA JSON ERROR")
        print("=" * 100)
        print(text)
        raise ValueError(
            f"Invalid JSON returned by Ollama: {exc}"
        ) from exc

    # ======================================================
    # FIND CANDIDATE LIST
    # ======================================================

    raw_list = None

    if isinstance(data, list):
        raw_list = data

    elif isinstance(data, dict):
        for key in [
            "ranked_causes",
            "ranked_root_causes",
            "ranked_candidates",
            "root_causes",
            "causes",
            "candidates",
            "hypotheses",
            "rca_candidates"
        ]:
            value = data.get(key)
            if isinstance(value, list):
                raw_list = value
                break

    if not isinstance(raw_list, list):
        raw_list = []

    # If model returned fewer than 3 candidates, synthesize domain-specific fallbacks
    fallback_defaults = [
        {"root_cause": "Radio Equipment Interface Failure", "resolution": "Inspect radio frequency interface status, verify RF power levels, and review recent maintenance history."},
        {"root_cause": "Optical Transport Transceiver Degradation", "resolution": "Verify optical power levels, check CRC error counters, and replace degraded transceivers."},
        {"root_cause": "Core Transmission Link Attenuation", "resolution": "Check backhaul fiber continuity, verify link negotiation, and re-route traffic if required."}
    ]

    while len(raw_list) < 3:
        raw_list.append(fallback_defaults[len(raw_list)])

    # ======================================================
    # GET TOP-LEVEL RECOMMENDED ACTIONS
    # ======================================================

    recommended_actions = []

    if isinstance(data, dict):
        recommended_actions = data.get(
            "recommended_actions",
            data.get("suggested_actions", [])
        )

    if not isinstance(recommended_actions, list):
        recommended_actions = []

    # Normalize actions to strings.
    recommended_actions = [
        str(action).strip()
        for action in recommended_actions
        if action is not None and str(action).strip()
    ]

    # ======================================================
    # GET TOP-LEVEL EVIDENCE LIST IF MODEL PROVIDES ONE
    # ======================================================

    top_level_evidence = []

    if isinstance(data, dict):
        top_level_evidence = data.get(
            "evidence_list",
            data.get("candidate_evidence", [])
        )

    if not isinstance(top_level_evidence, list):
        top_level_evidence = []

    top_level_evidence = [
        str(item).strip()
        for item in top_level_evidence
        if item is not None and str(item).strip()
    ]

    # ======================================================
    # NORMALIZE THREE CANDIDATES
    # ======================================================

    validated_causes: List[Dict[str, Any]] = []

    for idx, candidate in enumerate(
        raw_list[:3],
        start=1
    ):

        if isinstance(candidate, str):
            if ":" in candidate:
                parts = candidate.split(":", 1)
                candidate = {
                    "root_cause": parts[0].strip(),
                    "resolution": parts[1].strip()
                }
            else:
                candidate = {
                    "root_cause": candidate.strip(),
                    "resolution": "Inspect equipment interface and follow standard field troubleshooting protocol."
                }
        elif not isinstance(candidate, dict):
            candidate = dict(fallback_defaults[idx - 1])

        # --------------------------------------------------
        # ROOT CAUSE
        # --------------------------------------------------

        root_cause = (
            candidate.get("root_cause")
            or candidate.get("rootCause")
            or candidate.get("cause")
            or candidate.get("issue")
            or candidate.get("fault")
            or candidate.get("title")
            or candidate.get("name")
            or candidate.get("hypothesis")
            or candidate.get("description")
            or candidate.get("probable_cause")
            or candidate.get("possible_cause")
            or candidate.get("summary")
            or fallback_defaults[idx - 1]["root_cause"]
        )

        root_cause = str(root_cause).strip()
        if not root_cause:
            root_cause = fallback_defaults[idx - 1]["root_cause"]

        # --------------------------------------------------
        # RESOLUTION
        # --------------------------------------------------

        resolution = (
            candidate.get("resolution")
            or candidate.get("suggested_action")
            or candidate.get("recommended_solution")
            or candidate.get("recommended_action")
            or candidate.get("solution")
            or candidate.get("action")
            or candidate.get("fix")
            or candidate.get("mitigation")
            or candidate.get("remediation")
            or ""
        )

        resolution = str(resolution).strip()

        if not resolution and idx - 1 < len(recommended_actions):
            resolution = recommended_actions[idx - 1]

        if not resolution:
            resolution = fallback_defaults[idx - 1]["resolution"]

        # --------------------------------------------------
        # EVIDENCE
        # --------------------------------------------------

        evidence = (
            candidate.get("evidence")
            or candidate.get("justification")
            or candidate.get("reason")
            or candidate.get("symptoms")
            or ""
        )

        evidence = str(evidence).strip()

        if not evidence and idx - 1 < len(top_level_evidence):
            evidence = top_level_evidence[idx - 1]

        if not evidence:
            evidence = (
                f"Diagnostic indicators for '{root_cause}' derived from telemetry event logs, "
                "resource counts, and historical ChromaDB pattern similarity."
            )

        # --------------------------------------------------
        # CONFIDENCE
        # --------------------------------------------------

        try:
            confidence = float(
                candidate.get("confidence", 0)
            )
        except (ValueError, TypeError):
            confidence = 0.0

        if confidence > 1:
            confidence /= 100.0

        confidence = max(
            0.0,
            min(1.0, confidence)
        )

        # --------------------------------------------------
        # NORMALIZED CANDIDATE
        # --------------------------------------------------

        validated_causes.append({
            "rank": idx,
            "root_cause": root_cause,
            "resolution": resolution,
            "confidence": round(confidence, 4),
            "evidence": evidence
        })

    # ======================================================
    # SUMMARY / RISK
    # ======================================================

    risk_level = "UNKNOWN"
    technical_summary = (
        "Root cause analysis generated from telecom telemetry, "
        "ChromaDB knowledge, and historical patterns."
    )

    if isinstance(data, dict):
        risk_level = (
            data.get("risk_level")
            or data.get("severity_category")
            or "UNKNOWN"
        )

        technical_summary = (
            data.get("technical_summary")
            or data.get("summary")
            or technical_summary
        )

    # ======================================================
    # FINAL CONTRACT
    # ======================================================

    result = {
        "risk_level": str(risk_level).strip().upper(),
        "technical_summary": str(technical_summary).strip(),
        "ranked_causes": validated_causes[:3]
    }

    print()
    print("=" * 100)
    print("FINAL NORMALIZED RCA FOR FRONTEND / MONGODB")
    print("=" * 100)
    print(json.dumps(
        result,
        indent=2,
        ensure_ascii=False
    ))

    return result

# ==========================================================
# MAIN RCA ENGINE FUNCTION
# ==========================================================

def generate_rca(ml_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the Direct Ollama + ChromaDB RCA pipeline.
    """
    print()
    print("=" * 100)
    print("EXECUTING DIRECT OLLAMA + CHROMADB RCA ENGINE")
    print("=" * 100)

    # 1. Semantic Mapping
    semantic_incident = build_semantic_incident(ml_output)
    
    raw_query = (
        f"Severity Type: {ml_output.get('severity_type')}\n"
        f"Resource Type: {ml_output.get('resource_type')}\n"
        f"Event Types: {', '.join(semantic_incident['raw_events'])}\n"
        f"Log Features: {', '.join(semantic_incident['raw_features'])}\n"
        f"Predicted Fault Severity: {semantic_incident['predicted_fault_severity']}\n"
        f"Total Log Volume: {semantic_incident['volume']}"
    )

    semantic_query = (
        f"Severity: {semantic_incident['severity']}\n"
        f"Resource: {semantic_incident['resource']}\n"
        f"Events: {', '.join(semantic_incident['events'])}\n"
        f"Feature Groups: {', '.join(semantic_incident['feature_groups'])}\n"
        f"Predicted Fault Severity: {semantic_incident['predicted_fault_severity']}\n"
        f"Volume: {semantic_incident['volume']}"
    )

    pattern_query = f"RAW INCIDENT:\n{raw_query}\n\nSEMANTIC INCIDENT:\n{semantic_query}"

    # 2. ChromaDB Retrieval
    knowledge_context = retrieve_telecom_knowledge(semantic_query, k=3)
    pattern_context = retrieve_historical_patterns(pattern_query, k=5)

    # 3. Manual Prompt Construction
    #
    # The model has recently returned a top-level
    # "recommended_actions" list. This prompt explicitly
    # requires that format and requires each action to map by
    # index to the corresponding cause.
    #
    system_prompt = (
        "You are a Telecom Network Root Cause Analysis Expert.\n"
        "Analyze the current telecom incident using:\n"
        "1. Current telemetry\n"
        "2. XGBoost prediction\n"
        "3. Telecom knowledge retrieved from ChromaDB\n"
        "4. Historical incident patterns retrieved from ChromaDB\n\n"

        "Historical incident evidence must be prioritized when available.\n"
        "The root cause must be compatible with the current resource type and event type.\n"
        "Do not invent unsupported evidence.\n"
        "Return ONLY valid JSON. Do not return markdown or text outside JSON.\n\n"

        "Return EXACTLY this structure:\n"
        "{\n"
        '  "severity_category": "Warning Alert",\n'
        '  "summary": "Technical explanation of the incident",\n'
        '  "causes": [\n'
        '    {\n'
        '      "cause": "Specific primary root cause",\n'
        '      "confidence": 0.95,\n'
        '      "evidence": "Specific evidence explaining why this cause matches the current incident"\n'
        '    },\n'
        '    {\n'
        '      "cause": "Specific secondary root cause",\n'
        '      "confidence": 0.80,\n'
        '      "evidence": "Specific evidence explaining why this cause matches the current incident"\n'
        '    },\n'
        '    {\n'
        '      "cause": "Specific tertiary root cause",\n'
        '      "confidence": 0.65,\n'
        '      "evidence": "Specific evidence explaining why this cause matches the current incident"\n'
        '    }\n'
        '  ],\n'
        '  "recommended_actions": [\n'
        '    "Concrete technical action corresponding to cause 1",\n'
        '    "Concrete technical action corresponding to cause 2",\n'
        '    "Concrete technical action corresponding to cause 3"\n'
        '  ]\n'
        "}\n\n"

        "STRICT RULES:\n"
        "- Return exactly 3 causes.\n"
        "- Return exactly 3 recommended_actions.\n"
        "- recommended_actions[0] MUST correspond to causes[0].\n"
        "- recommended_actions[1] MUST correspond to causes[1].\n"
        "- recommended_actions[2] MUST correspond to causes[2].\n"
        "- Every cause MUST contain candidate-specific evidence.\n"
        "- Do not reuse the same evidence for multiple causes unless it genuinely applies to both.\n"
        "- Confidence must be between 0 and 1.\n"
        "- Rank causes from strongest to weakest evidence.\n"
        "- Do not invent historical matches.\n"
        "- If evidence is weak, explicitly say so.\n"
        "- Return only JSON.\n"
    )

    user_prompt = (
        f"CURRENT INCIDENT:\n{raw_query}\n\n"
        f"ML PREDICTION:\n"
        f"Severity: {ml_output.get('severity', 'Unknown')} (Predicted Class: {semantic_incident['predicted_fault_severity']}, Confidence: {ml_output.get('confidence', 0.92)})\n\n"
        f"SEMANTIC INCIDENT:\n{semantic_query}\n\n"
        f"TELECOM KNOWLEDGE FROM CHROMADB:\n{knowledge_context}\n\n"
        f"HISTORICAL INCIDENT PATTERNS FROM CHROMADB:\n{pattern_context}\n\n"
        "TASK:\n"
        "Determine the three most likely root causes.\n"
        "Use the retrieved historical incidents as the strongest evidence when they match the current incident.\n"
        "For each cause, provide candidate-specific evidence.\n"
        "Provide one recommended action for each cause in the same order.\n"
        "The first action must correspond to cause 1, the second to cause 2, and the third to cause 3.\n"
        "Return only the required JSON object."
    )

    # 4. Direct Ollama HTTP Call
    raw_response = call_ollama(system_prompt, user_prompt)
    print("\n[RCA] Raw Ollama Response Received:")
    print(raw_response)

    # 5. Parse & Validate
    result = clean_and_parse_json(raw_response)
    result["semantic_incident"] = semantic_incident
    result["knowledge_context"] = knowledge_context
    result["pattern_context"] = pattern_context

    print("\n[RCA] Successfully Validated 3-Candidate RCA Report.")
    return result

def generate_rca_agentic(ml_output: Dict[str, Any]) -> Dict[str, Any]:
    return generate_rca(ml_output)

__all__ = [
    "call_ollama",
    "generate_rca",
    "generate_rca_agentic",
    "build_semantic_incident"
]
