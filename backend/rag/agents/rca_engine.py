# agents/rca_engine.py

import json
import os
import re

from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama


load_dotenv()


# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

VECTOR_DB_PATH = os.path.join(
    BASE_DIR,
    "vector_db"
)


# ==========================================================
# EMBEDDINGS
# ==========================================================

EMBEDDING_MODEL = (
    r"C:\Users\sadik\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2\snapshots\1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
)

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL
)


# ==========================================================
# KNOWLEDGE VECTOR DB
# ==========================================================

knowledge_db = Chroma(
    collection_name="telecom_knowledge",
    persist_directory=VECTOR_DB_PATH,
    embedding_function=embeddings
)

knowledge_retriever = knowledge_db.as_retriever(
    search_kwargs={
        "k": 3
    }
)


# ==========================================================
# HISTORICAL PATTERN VECTOR DB
# ==========================================================

pattern_db = Chroma(
    collection_name="telecom_patterns",
    persist_directory=VECTOR_DB_PATH,
    embedding_function=embeddings
)

pattern_retriever = pattern_db.as_retriever(
    search_kwargs={
        "k": 5
    }
)


# ==========================================================
# OLLAMA
# ==========================================================

llm = ChatOllama(
    model="telecom-copilot",
    temperature=0,
    format="json"
)


# ==========================================================
# EXTRACT RESPONSE TEXT
# ==========================================================

def extract_text(response):

    if response is None:
        return ""

    content = getattr(
        response,
        "content",
        response
    )

    if content is None:
        return ""

    # Gemini-like / multimodal style response
    if isinstance(content, list):

        result = ""

        for block in content:

            if isinstance(block, dict):

                result += block.get(
                    "text",
                    ""
                )

            else:

                result += str(
                    block
                )

        return result.strip()

    return str(
        content
    ).strip()


# ==========================================================
# CLEAN JSON
# ==========================================================

def clean_json(
    text
):

    if not text:
        return ""

    text = text.strip()

    # Remove markdown fences if model still adds them.
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

    return text.strip()


# ==========================================================
# BUILD INCIDENT QUERY
# ==========================================================

def build_query(
    ml_output
):

    return f"""
Severity Type:
{ml_output['severity_type']}

Resource Type:
{ml_output['resource_type']}

Event Types:
{", ".join(ml_output['event_types'])}

Log Features:
{", ".join(ml_output['log_features'])}

Predicted Fault Severity:
{ml_output['predicted_fault_severity']}

Volume:
{ml_output['volume']}
""".strip()


# ==========================================================
# BUILD SEMANTIC INCIDENT
# ==========================================================

def build_semantic_incident(
    ml_output
):

    # These values correspond to the mapping KB
    # you created for the anonymized identifiers.

    severity_map = {
        "severity_type 1":
            "Informational Alert",

        "severity_type 2":
            "Minor Alert",

        "severity_type 3":
            "Moderate Alert",

        "severity_type 4":
            "Major Alert",

        "severity_type 5":
            "Critical Alert"
    }

    resource_map = {
        "resource_type 1":
            "Core Router Group",

        "resource_type 2":
            "Edge Router Group",

        "resource_type 3":
            "Access Switch Group",

        "resource_type 4":
            "Aggregation Switch Group",

        "resource_type 5":
            "Fiber Infrastructure",

        "resource_type 6":
            "Optical Transmission Equipment",

        "resource_type 7":
            "Base Station Controller",

        "resource_type 8":
            "Radio Access Equipment",

        "resource_type 9":
            "Power Supply Systems",

        "resource_type 10":
            "Environmental Control Systems"
    }

    event_map = {
        "event_type 1":
            "Connectivity Warning",

        "event_type 2":
            "Connectivity Failure",

        "event_type 3":
            "Link Instability Alert",

        "event_type 4":
            "Interface Failure Alert",

        "event_type 5":
            "Network Reachability Alert",

        "event_type 6":
            "Connection Reset Event",

        "event_type 7":
            "Packet Loss Alert",

        "event_type 8":
            "Session Failure Alert",

        "event_type 9":
            "Service Timeout Alert",

        "event_type 10":
            "Network Recovery Event",

        "event_type 11":
            "Traffic Congestion Alert",

        "event_type 12":
            "Queue Overflow Alert",

        "event_type 13":
            "Bandwidth Saturation Alert",

        "event_type 14":
            "High Latency Alert",

        "event_type 15":
            "Throughput Degradation Alert",

        "event_type 16":
            "Traffic Spike Alert",

        "event_type 17":
            "Backhaul Congestion Alert",

        "event_type 18":
            "Routing Delay Alert",

        "event_type 19":
            "Core Network Load Alert",

        "event_type 20":
            "Performance Degradation Alert",

        "event_type 21":
            "Routing Table Change",

        "event_type 22":
            "Route Instability Alert",

        "event_type 23":
            "Route Convergence Delay",

        "event_type 24":
            "BGP Peer Failure",

        "event_type 25":
            "OSPF Neighbor Failure",

        "event_type 26":
            "Route Advertisement Error",

        "event_type 27":
            "Route Policy Violation",

        "event_type 28":
            "Network Loop Detection",

        "event_type 29":
            "Gateway Failure",

        "event_type 30":
            "Traffic Rerouting Event",

        "event_type 31":
            "Hardware Health Warning",

        "event_type 32":
            "Device Failure Alert",

        "event_type 33":
            "Temperature Warning",

        "event_type 34":
            "Cooling Failure Alert",

        "event_type 35":
            "Power Instability Alert",

        "event_type 36":
            "Battery Failure Alert",

        "event_type 37":
            "Hardware Restart Event",

        "event_type 38":
            "Optical Signal Loss",

        "event_type 39":
            "Fiber Quality Warning",

        "event_type 40":
            "Physical Infrastructure Failure",

        "event_type 41":
            "Authentication Failure",

        "event_type 42":
            "Authorization Failure",

        "event_type 43":
            "DNS Resolution Failure",

        "event_type 44":
            "Application Service Failure",

        "event_type 45":
            "Database Service Failure",

        "event_type 46":
            "Configuration Error Alert",

        "event_type 47":
            "Firmware Error Alert",

        "event_type 48":
            "Security Threat Alert",

        "event_type 49":
            "Intrusion Detection Alert",

        "event_type 50":
            "DDoS Suspicion Alert",

        "event_type 51":
            "Anomaly Detection Alert",

        "event_type 52":
            "Critical Service Failure",

        "event_type 53":
            "System-Wide Outage Alert"
    }

    def map_feature(
        feature
    ):

        match = re.search(
            r"(\d+)",
            str(feature)
        )

        if not match:
            return "Unknown Feature Group"

        value = int(
            match.group(1)
        )

        if 1 <= value <= 50:
            return "Packet Quality Indicators"

        if 51 <= value <= 100:
            return "Traffic Indicators"

        if 101 <= value <= 150:
            return "Hardware Indicators"

        if 151 <= value <= 200:
            return "Power Indicators"

        if 201 <= value <= 250:
            return "Optical Indicators"

        if 251 <= value <= 300:
            return "Configuration Indicators"

        if 301 <= value <= 386:
            return "Security Indicators"

        return "Unknown Feature Group"

    return {
        "severity":
            severity_map.get(
                ml_output["severity_type"],
                "Unknown Severity"
            ),

        "resource":
            resource_map.get(
                ml_output["resource_type"],
                "Unknown Resource"
            ),

        "events": [
            event_map.get(
                event,
                "Unknown Event"
            )
            for event in ml_output["event_types"]
        ],

        "feature_groups": [
            map_feature(feature)
            for feature in ml_output["log_features"]
        ],

        "predicted_fault_severity":
            ml_output[
                "predicted_fault_severity"
            ],

        "volume":
            ml_output["volume"],

        "raw_severity":
            ml_output["severity_type"],

        "raw_resource":
            ml_output["resource_type"],

        "raw_events":
            ml_output["event_types"],

        "raw_features":
            ml_output["log_features"]
    }


# ==========================================================
# GENERATE AGENTIC RCA
# ==========================================================

def generate_rca_agentic(
    ml_output
):

    # ======================================================
    # STEP 1
    # ======================================================

    query = build_query(
        ml_output
    )

    semantic_incident = (
        build_semantic_incident(
            ml_output
        )
    )


    # ======================================================
    # STEP 2
    # KNOWLEDGE RETRIEVAL
    # ======================================================

    semantic_query = f"""
Severity:
{semantic_incident['severity']}

Resource:
{semantic_incident['resource']}

Events:
{", ".join(semantic_incident['events'])}

Feature Groups:
{", ".join(semantic_incident['feature_groups'])}

Predicted Fault Severity:
{semantic_incident['predicted_fault_severity']}

Volume:
{semantic_incident['volume']}
"""

    knowledge_docs = (
        knowledge_retriever.invoke(
            semantic_query
        )
    )

    knowledge_context = "\n\n".join(
        doc.page_content
        for doc in knowledge_docs
    )


    # ======================================================
    # STEP 3
    # HISTORICAL PATTERN RETRIEVAL
    # ======================================================

    # Use both raw and semantic information.
    # This is important because your newly learned
    # resolutions contain raw incident signatures.

    pattern_query = f"""
RAW INCIDENT:
{query}

SEMANTIC INCIDENT:
{semantic_query}
"""

    pattern_docs = (
        pattern_retriever.invoke(
            pattern_query
        )
    )

    pattern_context = "\n\n".join(
        doc.page_content
        for doc in pattern_docs
    )


    # ======================================================
    # SHOW RETRIEVAL
    # ======================================================

    print("\n")
    print("=" * 100)
    print("MAPPED INCIDENT")
    print("=" * 100)

    print(
        json.dumps(
            semantic_incident,
            indent=2
        )
    )


    print("\n")
    print("=" * 100)
    print("RETRIEVED TELECOM KNOWLEDGE")
    print("=" * 100)

    print(
        knowledge_context
    )


    print("\n")
    print("=" * 100)
    print("RETRIEVED HISTORICAL PATTERNS")
    print("=" * 100)

    print(
        pattern_context
    )


    # ======================================================
    # STEP 4
    # PATTERN ANALYST AGENT
    # ======================================================

    pattern_prompt = f"""
You are a Telecom Historical Incident Pattern Analyst.

Analyze ONLY the retrieved historical incidents.

CURRENT INCIDENT:
{semantic_query}

HISTORICAL INCIDENTS:
{pattern_context}

Identify the strongest historical evidence.

Return:

1. Most relevant historical root cause
2. Successful resolution
3. Why the historical incident matches
4. Confidence

Do not invent information.

If there is an exact incident-signature match,
explicitly mention it.

Do not produce generic telecom advice.
"""

    try:

        pattern_response = (
            llm.invoke(
                pattern_prompt
            )
        )

        pattern_analysis = (
            extract_text(
                pattern_response
            )
        )

    except Exception as exc:

        print(
            "\nPattern Agent Error:",
            exc
        )

        pattern_analysis = ""


    print("\n")
    print("=" * 100)
    print("PATTERN ANALYST AGENT")
    print("=" * 100)

    print(
        pattern_analysis
    )


    # ======================================================
    # STEP 5
    # FINAL RCA AGENT
    # ======================================================

    final_prompt = f"""
You are the Senior Telecom Root Cause Analysis Agent.

CURRENT INCIDENT
================

Raw identifiers:
{query}

Mapped telecom interpretation:
{semantic_query}

==================================================
DOMAIN KNOWLEDGE
==================================================

{knowledge_context}

==================================================
HISTORICAL PATTERN ANALYSIS
==================================================

{pattern_analysis}

==================================================
RAW HISTORICAL RECORDS
==================================================

{pattern_context}

==================================================
YOUR TASK
==================================================

Generate exactly THREE ranked root-cause hypotheses.

Use the historical evidence first.

If a historical record contains the same raw incident
signature and a validated successful resolution,
that should receive the strongest confidence.

However, do not claim that an event or resource
identifier alone mathematically proves a root cause.

Use the domain knowledge as supporting evidence.

Each candidate MUST:

- be a different root cause
- have exactly one resolution
- have a confidence between 0 and 1
- include evidence explaining the ranking

Return ONLY JSON.

Required format:

{{
  "ranked_causes": [
    {{
      "rank": 1,
      "root_cause": "",
      "resolution": "",
      "confidence": 0.0,
      "evidence": ""
    }},
    {{
      "rank": 2,
      "root_cause": "",
      "resolution": "",
      "confidence": 0.0,
      "evidence": ""
    }},
    {{
      "rank": 3,
      "root_cause": "",
      "resolution": "",
      "confidence": 0.0,
      "evidence": ""
    }}
  ],
  "technical_summary": "",
  "risk_level": ""
}}
"""

    try:

        final_response = (
            llm.invoke(
                final_prompt
            )
        )

        final_content = (
            extract_text(
                final_response
            )
        )

    except Exception as exc:

        print(
            "\nFinal RCA Ollama Error:",
            exc
        )

        raise RuntimeError(
            "Final RCA generation failed."
        ) from exc


    print("\n")
    print("=" * 100)
    print("RAW FINAL OLLAMA RESPONSE")
    print("=" * 100)

    print(
        repr(final_content)
    )


    # ======================================================
    # HANDLE EMPTY RESPONSE
    # ======================================================

    if not final_content:

        raise RuntimeError(
            "Ollama returned an empty final RCA response. "
            "The Pattern Analyst succeeded, but the final "
            "RCA generation returned no content."
        )


    # ======================================================
    # CLEAN JSON
    # ======================================================

    final_content = clean_json(
        final_content
    )


    # ======================================================
    # PARSE
    # ======================================================

    try:

        result = json.loads(
            final_content
        )

    except json.JSONDecodeError as exc:

        print("\nJSON PARSE ERROR:")
        print(exc)

        print(
            "\nFINAL CONTENT:"
        )

        print(
            final_content
        )

        raise RuntimeError(
            "Ollama returned non-JSON output "
            "for the final RCA."
        ) from exc


    # ======================================================
    # VALIDATE
    # ======================================================

    ranked_causes = result.get(
        "ranked_causes"
    )

    if not isinstance(
        ranked_causes,
        list
    ):

        raise RuntimeError(
            "Final RCA response does not contain "
            "ranked_causes."
        )


    if len(
        ranked_causes
    ) != 3:

        raise RuntimeError(
            f"Expected 3 RCA candidates, "
            f"received {len(ranked_causes)}."
        )


    for index, candidate in enumerate(
        ranked_causes,
        start=1
    ):

        candidate["rank"] = index

        candidate["root_cause"] = str(
            candidate.get(
                "root_cause",
                ""
            )
        ).strip()

        candidate["resolution"] = str(
            candidate.get(
                "resolution",
                ""
            )
        ).strip()

        candidate["evidence"] = str(
            candidate.get(
                "evidence",
                ""
            )
        ).strip()

        try:

            candidate["confidence"] = float(
                candidate.get(
                    "confidence",
                    0.0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            candidate["confidence"] = 0.0


    # ======================================================
    # FINAL RESULT
    # ======================================================

    return {
        "ranked_causes":
            ranked_causes,

        "technical_summary":
            str(
                result.get(
                    "technical_summary",
                    ""
                )
            ),

        "risk_level":
            str(
                result.get(
                    "risk_level",
                    "UNKNOWN"
                )
            ),

        "semantic_incident":
            semantic_incident,

        "pattern_analysis":
            pattern_analysis
    }


# ==========================================================
# BACKWARD COMPATIBILITY
# ==========================================================

def generate_rca(
    ml_output
):

    return generate_rca_agentic(
        ml_output
    )