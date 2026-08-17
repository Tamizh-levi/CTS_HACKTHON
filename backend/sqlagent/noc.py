"""
NL Query Agent — plain-English questions over MongoDB incidents.

Pipeline:
    question -> Gemini (MongoDB aggregation generation) -> clean/parse
             -> validate (stage/operator/field whitelist)
             -> execute (read-only aggregation)
             -> Gemini (explain) -> answer

MongoDB collection:
    database: cts_incident_management
    collection: incidents

Install:
    pip install google-generativeai pymongo python-dotenv

Environment variables:
    GEMINI_API_KEY
    MONGODB_URI   (example: mongodb://localhost:27017)
    MONGODB_DB    (default: cts_incident_management)
    MONGODB_COLLECTION (default: incidents)
"""

from dotenv import load_dotenv
import json
import os
import re
import sys
import difflib
from typing import Any

from flask import Blueprint, jsonify, request
import google.generativeai as genai
from pymongo import MongoClient

# ----------------------------------------------------------------------------
# 0. Config & Environment
# ----------------------------------------------------------------------------

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)

for p in [CURRENT_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

load_dotenv(os.path.join(CURRENT_DIR, ".env"))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

GEMINI_MODEL = None
for model_candidate in ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
    try:
        GEMINI_MODEL = genai.GenerativeModel(model_candidate)
        break
    except Exception:
        continue

if GEMINI_MODEL is None:
    GEMINI_MODEL = genai.GenerativeModel("gemini-1.5-flash")

MONGODB_URI = os.environ.get("MONGODB_URI", os.environ.get("MONGO_URI", "mongodb://localhost:27017"))
MONGODB_DB = os.environ.get("MONGODB_DB", os.environ.get("MONGO_DB_NAME", "cts_incident_management"))
INCIDENTS_COLLECTION = os.environ.get("MONGODB_INCIDENTS_COLLECTION", "incidents")
USERS_COLLECTION = os.environ.get("MONGODB_USERS_COLLECTION", "users")

MAX_ROWS = 100

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]
incidents_collection = db[INCIDENTS_COLLECTION]
users_collection = db[USERS_COLLECTION]

# Flask Blueprint
noc_bp = Blueprint("noc", __name__)
sqlagent_bp = noc_bp  # Alias for flexibility


# ----------------------------------------------------------------------------
# 1. MongoDB schema
# ----------------------------------------------------------------------------
# This reflects the uploaded incidents JSON. Nested paths are explicitly
# whitelisted so generated queries cannot access arbitrary MongoDB fields.

SCHEMA = {
    "_id",
    "ticket_id",
    "assigned_to",
    "confidence",
    "created_at",
    "dispatch_result",
    "event_count_x",
    "event_count_y",
    "event_event_type_unique",
    "event_types",
    "fault_severity",
    "finished_at",
    "id",
    "location",
    "log_count",
    "log_count_ratio",
    "log_feature_count",
    "log_features",
    "log_log_feature_unique",
    "log_volume_unique",
    "max_log_volume",
    "mean_log_volume",
    "min_log_volume",
    "prediction",
    "prediction.fault_severity",
    "prediction.severity",
    "prediction.confidence",
    "prediction.probabilities",
    "prediction.probabilities.low",
    "prediction.probabilities.medium",
    "prediction.probabilities.high",
    "region",
    "resource_count",
    "resource_count_ratio",
    "resource_location",
    "resource_resource_type_unique",
    "resource_type",
    "severity",
    "severity_location",
    "severity_resource",
    "severity_type",
    "status",
    "title",
    "total_log_volume",
    "unique_event_count",
    "unique_log_features",
    "commit_id",
    "confirmed_root_cause",
    "last_updated_at",
    "resolution_type",

    "agent_result",
    "agent_result.ranked_causes",
    "agent_result.ranked_causes.rank",
    "agent_result.ranked_causes.root_cause",
    "agent_result.ranked_causes.resolution",
    "agent_result.ranked_causes.confidence",
    "agent_result.ranked_causes.evidence",
    "agent_result.technical_summary",
    "agent_result.risk_level",
    "agent_result.semantic_incident",
    "agent_result.semantic_incident.severity",
    "agent_result.semantic_incident.resource",
    "agent_result.semantic_incident.events",
    "agent_result.semantic_incident.feature_groups",
    "agent_result.semantic_incident.predicted_fault_severity",
    "agent_result.semantic_incident.volume",
    "agent_result.semantic_incident.raw_severity",
    "agent_result.semantic_incident.raw_resource",
    "agent_result.semantic_incident.raw_events",
    "agent_result.semantic_incident.raw_features",
    "agent_result.pattern_analysis",
}

USERS_SCHEMA = {
    "_id", "username", "name", "role", "department", "email",
    "is_encrypted", "created_at", "last_login_at",
}

TOP_LEVEL_FIELDS = {x for x in SCHEMA if "." not in x}


def schema_text() -> str:
    return """
MongoDB database: cts_incident_management

Collection: incidents
Fields:
- ticket_id: integer
- id: string such as INC-14122
- location: string
- region: string
- resource_type: string
- severity: string, e.g. "High Severity"
- severity_type: string
- fault_severity: integer: 0 low, 1 medium, 2 high
- status: string, e.g. "FINISHED (RESOLVED)", "FINISHED (ESCALATED)"
- assigned_to: string
- confidence: number
- created_at, finished_at, last_updated_at: ISO/date-like strings in the supplied data
- confirmed_root_cause: string
- resolution_type: string
- event_types: array of strings
- log_features: array of strings
- total_log_volume: number
- unique_event_count: integer
- unique_log_features: integer
- prediction: object containing fault_severity, severity, confidence,
  and probabilities.low/medium/high
- agent_result.semantic_incident: object containing severity, resource,
  events, feature_groups, predicted_fault_severity, volume, raw_* fields
- agent_result.ranked_causes: array of objects with rank, root_cause,
  resolution, confidence, evidence

Collection: users
Fields:
- username, name, role, department, email
- is_encrypted, created_at, last_login_at

Rules:
- Incident questions use incidents.
- User/account/operator questions use users.
- Do not query or expose password/password-hash fields.
- Do not use $lookup, $unionWith, or other cross-collection stages.
"""


# ----------------------------------------------------------------------------
# 2. Question normalization / typo tolerance
# ----------------------------------------------------------------------------

# Common NOC vocabulary and alternate names. These are intentionally broad:
# they help with spelling mistakes, abbreviations, and natural wording before
# Gemini generates the MongoDB pipeline.
QUESTION_ALIASES = {
    "incidents": [
        "incident", "incidents", "ticket", "tickets", "fault", "faults",
        "alerts", "alarm", "alarms", "issues", "issue", "problems", "problem",
    ],
    "users": [
        "user", "users", "operator", "operators", "engineer", "engineers",
        "admin", "admins", "administrator", "administrators", "staff",
        "account", "accounts", "noc member", "noc members",
    ],
    "resolved": [
        "resolved", "resolve", "fixed", "closed", "completed", "finished",
        "recovered", "solved",
    ],
    "escalated": [
        "escalated", "escalate", "escalation", "tier 3", "tier-3",
        "tier3", "senior engineering",
    ],
    "high_severity": [
        "high severity", "high-severity", "critical", "critical severity",
        "severe", "high priority", "priority high",
    ],
    "open": [
        "open", "pending", "active", "unresolved", "not resolved",
        "in progress", "ongoing",
    ],
    "location": [
        "location", "site", "place", "area", "region location",
    ],
    "technician": [
        "technician", "tech", "engineer", "assigned engineer", "assignee",
        "assigned to", "noc engineer",
    ],
    "root_cause": [
        "root cause", "root-cause", "cause", "reason", "fault cause",
        "confirmed cause",
    ],
    "department": [
        "department", "team", "division", "unit", "group",
    ],
}

# Frequent keyboard/spelling mistakes seen in natural-language questions.
COMMON_TYPOS = {
    "severty": "severity",
    "severety": "severity",
    "severtiy": "severity",
    "severirty": "severity",
    "incidnt": "incident",
    "incidentses": "incidents",
    "ticet": "ticket",
    "tiket": "ticket",
    "tckets": "tickets",
    "escaleted": "escalated",
    "escalatd": "escalated",
    "resloved": "resolved",
    "resovled": "resolved",
    "resolveed": "resolved",
    "technican": "technician",
    "technitian": "technician",
    "locaton": "location",
    "locaton": "location",
    "regoin": "region",
    "opreator": "operator",
    "operater": "operator",
    "admn": "admin",
    "adimn": "admin",
    "departmant": "department",
    "deparment": "department",
    "confguration": "configuration",
    "congestionn": "congestion",
    "howmany": "how many",
}

def normalize_question(question: str) -> str:
    """Fix obvious spelling mistakes and normalize common NOC wording."""
    q = str(question or "").strip()
    if not q:
        return q

    # Normalize punctuation/spacing without changing the user's meaning.
    q = re.sub(r"\s+", " ", q)
    q = re.sub(r"[“”]", '"', q)
    q = re.sub(r"[‘’]", "'", q)

    # Apply exact common typo corrections.
    for wrong, right in COMMON_TYPOS.items():
        q = re.sub(rf"\b{re.escape(wrong)}\b", right, q, flags=re.IGNORECASE)

    # Fuzzy-correct individual words when they are very close to known NOC
    # vocabulary. This catches previously unseen errors such as "severiti".
    vocabulary = set(COMMON_TYPOS.values())
    for aliases in QUESTION_ALIASES.values():
        vocabulary.update(a for a in aliases if " " not in a)

    words = q.split()
    corrected = []
    for word in words:
        prefix = re.match(r"^([^\w]*)(.*?)([^\w]*)$", word)
        if not prefix:
            corrected.append(word)
            continue

        left, core, right = prefix.groups()
        if len(core) >= 5:
            match = difflib.get_close_matches(
                core.lower(),
                vocabulary,
                n=1,
                cutoff=0.84,
            )
            if match and match[0] != core.lower():
                core = match[0]
        corrected.append(left + core + right)

    return " ".join(corrected)


def question_hints(question: str) -> str:
    """Provide explicit semantic hints for alternate names/phrasing."""
    q = question.lower()
    hints = []

    for concept, aliases in QUESTION_ALIASES.items():
        if any(alias in q for alias in aliases):
            hints.append(f"{concept}: {', '.join(aliases[:8])}")

    return (
        "Recognized semantic hints: " + "; ".join(hints)
        if hints else
        "No predefined semantic hint matched; infer the user's intent from context."
    )


def looks_like_password_request(question: str) -> bool:
    q = question.lower()
    password_terms = [
        "password", "passwd", "pass word", "password hash",
        "credential", "credentials", "login secret",
    ]
    return any(term in q for term in password_terms)


# ----------------------------------------------------------------------------
# 2. Prompt builder + MongoDB aggregation generation
# ----------------------------------------------------------------------------

MONGO_GEN_PROMPT = """You are a MongoDB aggregation-pipeline generator for a telecom
fault/incident management system.

Database schema:
{schema}

Return ONLY one valid JSON object:
{"collection": "incidents" or "users", "pipeline": [...]}

Rules:
- Output no markdown, backticks, comments, or explanation.
- The output must be a JSON object containing collection and pipeline.
- The user's question may contain spelling mistakes, abbreviations,
  slang, alternate names, incomplete grammar, or unusual wording.
- Infer the intended meaning instead of rejecting the question.
- Treat synonyms such as "fixed/closed/solved" as resolved incidents,
  "critical/severe/high priority" as high severity when context supports it,
  "tech/engineer/assignee" as technician/assigned_to, and
  "site/place/area" as location.
- If the wording is imperfect but the intent is reasonably clear, still
  generate the best matching query.
- Do not output markdown, backticks, comments, or explanation.
- READ ONLY: never generate $out, $merge, $function, $accumulator, or writes.
- Use only fields belonging to the selected collection.
- Incident questions must select "incidents".
- User/account/operator questions must select "users".
- Never query or expose password/password hashes.
- Do not use $lookup, $unionWith, $graphLookup, or other cross-collection stages.
- Prefer simple aggregation stages: $match, $group, $sort, $limit,
  $count, $project, $unwind, $set, and $addFields.
- Do not use JavaScript or server-side code.
- For case-insensitive text matching, use $regex with "$options": "i".
- "open" incidents means status matching "assigned" or "retry" only.
- "resolved" means status "FINISHED (RESOLVED)".
- "escalated" means status "FINISHED (ESCALATED)".
- High severity can be queried using fault_severity: 2 or severity: "High Severity".
- Return at most {max_rows} result documents unless the query is a $count/$group
  query whose result is naturally small.
- Use field paths exactly as they appear, with a leading "$" only where MongoDB
  expressions require it.

Examples:

Q: How many open tickets
A: [
  {{"$match": {{"status": {{"$in": ["assigned", "retry"]}}}}}},
  {{"$count": "open_tickets"}}
]

Q: Which technician resolved the most high-severity tickets?
A: [
  {{"$match": {{
    "status": "FINISHED (RESOLVED)",
    "fault_severity": 2
  }}}},
  {{"$group": {{
    "_id": "$assigned_to",
    "resolved_count": {{"$sum": 1}}
  }}}},
  {{"$sort": {{"resolved_count": -1}}}},
  {{"$limit": 1}},
  {{"$project": {{
    "_id": 0,
    "technician": "$_id",
    "resolved_count": 1
  }}}}
]

Q: How many escalated tickets per location?
A: [
  {{"$match": {{"status": "FINISHED (ESCALATED)"}}}},
  {{"$group": {{
    "_id": "$location",
    "escalated_count": {{"$sum": 1}}
  }}}},
  {{"$sort": {{"escalated_count": -1}}}},
  {{"$limit": {max_rows}}},
  {{"$project": {{
    "_id": 0,
    "location": "$_id",
    "escalated_count": 1
  }}}}
]

Question: {question}
A:"""


QUESTION_NORMALIZE_PROMPT = """You normalize natural-language NOC questions.

The user may have:
- spelling mistakes ("severty", "resloved", "incidnt")
- alternate names ("critical", "fixed", "tech", "site", "assignee")
- poor grammar ("how much high severity")
- abbreviated wording ("no of admins", "resolved tickets count")
- mixed singular/plural forms

Rewrite the question into one clear, short English question while preserving
the user's intent. Do NOT answer it. Do NOT invent missing constraints.

Examples:
"how many high severty ticets" -> "How many high severity tickets are there?"
"who fixed most incidents" -> "Which technician resolved the most incidents?"
"count critical faults" -> "How many high severity incidents are there?"
"no of opreators" -> "How many operator users are there?"
"which site has most escalated" -> "Which location has the most escalated incidents?"

Question:
{question}

Return ONLY the normalized question.
"""

def normalize_with_gemini(question: str) -> str:
    if not GEMINI_MODEL:
        return normalize_question(question)

    response = GEMINI_MODEL.generate_content(
        QUESTION_NORMALIZE_PROMPT.format(question=question),
        generation_config={
            "temperature": 0.0,
            "max_output_tokens": 120,
        },
    )

    normalized = response.text.strip()
    normalized = re.sub(r"^```.*?\n", "", normalized, flags=re.DOTALL)
    normalized = re.sub(r"\n```$", "", normalized).strip()

    return normalized or normalize_question(question)


def generate_query(question: str) -> dict[str, Any]:
    # First repair spelling/phrasing, then generate the MongoDB query.
    local_normalized = normalize_question(question)

    try:
        normalized = normalize_with_gemini(local_normalized)
    except Exception:
        normalized = local_normalized

    prompt = MONGO_GEN_PROMPT.format(
        schema=schema_text(),
        question=(
            f"Original user question: {question}\n"
            f"Normalized question: {normalized}\n"
            f"{question_hints(normalized)}"
        ),
        max_rows=MAX_ROWS,
    )

    response = GEMINI_MODEL.generate_content(
        prompt,
        generation_config={
            "temperature": 0.0,
            "max_output_tokens": 700,
        },
    )

    return clean_query(response.text)


# ----------------------------------------------------------------------------
# 3. Clean / parse generated JSON
# ----------------------------------------------------------------------------

def clean_query(raw: str) -> dict[str, Any]:
    text = raw.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*```$", "", text)

    text = re.sub(
        r"^(json|pipeline|query)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    try:
        query = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Generated output is not valid JSON: {exc}")

    if not isinstance(query, dict):
        raise ValidationError("MongoDB query must be a JSON object.")

    if query.get("collection") not in {"incidents", "users"}:
        raise ValidationError("Unknown MongoDB collection.")

    if not isinstance(query.get("pipeline"), list):
        raise ValidationError("MongoDB pipeline must be a JSON array.")

    return query


# ----------------------------------------------------------------------------
# 4. Validation — safety net
# ----------------------------------------------------------------------------

class ValidationError(Exception):
    pass


ALLOWED_STAGES = {
    "$match",
    "$group",
    "$sort",
    "$limit",
    "$count",
    "$project",
    "$unwind",
    "$set",
    "$addFields",
}

FORBIDDEN_OPERATORS = {
    "$out",
    "$merge",
    "$function",
    "$accumulator",
    "$where",
    "$expr",       # deliberately disallowed to keep validation simple
    "$lookup",     # no cross-collection access
    "$graphLookup",
    "$unionWith",
}


def field_is_allowed(path: str, collection_name: str) -> bool:
    """Validate a Mongo field path against the selected collection."""
    if not isinstance(path, str) or path.startswith("$$"):
        return False

    clean = path[1:] if path.startswith("$") else path
    allowed = SCHEMA if collection_name == "incidents" else USERS_SCHEMA

    if clean == "_id" or clean in allowed:
        return True

    return any(
        clean.startswith(known + ".")
        for known in allowed
        if "." in known
    )


def validate_value(
    value: Any,
    *,
    collection_name: str,
    key_context: str | None = None,
) -> None:
    """Recursively validate fields/operators in generated Mongo JSON."""

    if isinstance(value, dict):
        for key, child in value.items():
            if key.startswith("$"):
                if key in FORBIDDEN_OPERATORS:
                    raise ValidationError(
                        f"MongoDB operator is not allowed: {key}"
                    )
                if key not in {
                    "$in", "$nin", "$eq", "$ne", "$gt", "$gte", "$lt", "$lte",
                    "$regex", "$options", "$exists", "$not",
                    "$sum", "$avg", "$min", "$max",
                    "$first", "$last",
                    "$push", "$addToSet",
                    "$cond", "$literal",
                }:
                    raise ValidationError(
                        f"MongoDB operator is not whitelisted: {key}"
                    )
            else:
                # Keys such as "_id", "count", "location", aliases, etc.
                # are allowed inside aggregation stage bodies.
                if key_context == "$match":
                    if not field_is_allowed(key, collection_name):
                        raise ValidationError(
                            f"Unknown match field: {key}"
                        )
                elif key_context in {"$project", "$sort"}:
                    if key.startswith("_"):
                        pass
                    elif "." in key and not field_is_allowed(key, collection_name):
                        raise ValidationError(
                            f"Unknown field: {key}"
                        )

            validate_value(
                child,
                collection_name=collection_name,
                key_context=key_context,
            )

    elif isinstance(value, list):
        for item in value:
            validate_value(
                item,
                collection_name=collection_name,
                key_context=key_context,
            )

    elif isinstance(value, str):
        # Strings beginning with '$' are aggregation field references.
        if value.startswith("$") and not field_is_allowed(value, collection_name):
            raise ValidationError(
                f"Unknown field reference: {value}"
            )


def validate_pipeline(
    pipeline: list[dict[str, Any]],
    collection_name: str,
) -> list[dict[str, Any]]:
    if not pipeline:
        raise ValidationError("Empty MongoDB pipeline.")

    if len(pipeline) > 12:
        raise ValidationError("Pipeline is too long.")

    for stage in pipeline:
        if not isinstance(stage, dict) or len(stage) != 1:
            raise ValidationError(
                "Each pipeline stage must be a single JSON object."
            )

        stage_name, stage_body = next(iter(stage.items()))

        if stage_name not in ALLOWED_STAGES:
            raise ValidationError(
                f"Pipeline stage is not allowed: {stage_name}"
            )

        if stage_name == "$limit":
            if not isinstance(stage_body, int) or stage_body < 1:
                raise ValidationError("$limit must be a positive integer.")
            if stage_body > MAX_ROWS:
                stage_body = MAX_ROWS
                stage[stage_name] = stage_body

        if stage_name == "$count":
            if not isinstance(stage_body, str) or not stage_body:
                raise ValidationError("$count requires a result field name.")

        validate_value(
            stage_body,
            collection_name=collection_name,
            key_context=stage_name,
        )

    # Add a hard result cap if the model forgot one.
    has_limit = any("$limit" in stage for stage in pipeline)
    has_count = any("$count" in stage for stage in pipeline)

    if not has_limit and not has_count:
        pipeline.append({"$limit": MAX_ROWS})

    return pipeline


# ----------------------------------------------------------------------------
# 5. Execute MongoDB aggregation
# ----------------------------------------------------------------------------

def json_safe(value: Any) -> Any:
    """Convert BSON values to JSON-safe values for the LLM/UI."""
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "__str__") and value.__class__.__name__ == "ObjectId":
        return str(value)
    return value


def execute_pipeline(
    pipeline: list[dict[str, Any]],
    collection_name: str,
) -> list[dict[str, Any]]:
    target = (
        incidents_collection
        if collection_name == "incidents"
        else users_collection
    )
    rows = list(target.aggregate(pipeline, maxTimeMS=5000))
    return [json_safe(row) for row in rows]


# ----------------------------------------------------------------------------
# 6. Result explanation
# ----------------------------------------------------------------------------

EXPLAIN_PROMPT = """A NOC engineer asked: "{question}"

MongoDB returned this aggregation result:
{result}

Explain the answer in 1-2 plain, friendly English sentences.
State numbers exactly. Do not invent information.
If the result is empty, say no matching records were found."""


def explain_result(question: str, rows: list[dict[str, Any]]) -> str:
    result_json = json.dumps(rows[:20], default=str)

    response = GEMINI_MODEL.generate_content(
        EXPLAIN_PROMPT.format(
            question=question,
            result=result_json,
        ),
        generation_config={
            "temperature": 0.2,
            "max_output_tokens": 200,
        },
    )

    answer = response.text.strip()
    return answer or "No matching records were found."


# ----------------------------------------------------------------------------
# 7. Offline fallback — useful when Gemini is unavailable
# ----------------------------------------------------------------------------

CANNED_EXAMPLES = {
    "open tickets": {
        "collection": "incidents",
        "pipeline": [
            {"$match": {"status": {"$in": ["assigned", "retry"]}}},
            {"$count": "open_tickets"},
        ],
        "answer_template": (
            "There are currently {n} open tickets "
            "(assigned or in retry)."
        ),
    },
    "escalated": {
        "collection": "incidents",
        "pipeline": [
            {"$match": {"status": "FINISHED (ESCALATED)"}},
            {"$count": "escalated"},
        ],
        "answer_template": (
            "{n} tickets have been escalated to a NOC engineer."
        ),
    },
    "resolved": {
        "collection": "incidents",
        "pipeline": [
            {"$match": {"status": "FINISHED (RESOLVED)"}},
            {"$count": "resolved"},
        ],
        "answer_template": "{n} tickets have been resolved so far.",
    },
    "admins": {
        "collection": "users",
        "pipeline": [
            {"$match": {"role": "admin"}},
            {"$count": "admins"},
        ],
        "answer_template": "There are {n} admin users.",
    },
    "operators": {
        "collection": "users",
        "pipeline": [
            {"$match": {"role": "operator"}},
            {"$count": "operators"},
        ],
        "answer_template": "There are {n} operator users.",
    },
}


def fallback_answer(question: str):
    q = question.lower()

    for keyword, entry in CANNED_EXAMPLES.items():
        if keyword in q:
            try:
                rows = execute_pipeline(
                    entry["pipeline"],
                    entry["collection"],
                )
                n = list(rows[0].values())[0] if rows else 0
                return (
                    entry["collection"],
                    entry["pipeline"],
                    entry["answer_template"].format(n=n),
                )
            except Exception:
                pass

    return None, None, (
        "The AI service is unreachable right now. Try one of the demo "
        "questions: 'How many open tickets?', "
        "'How many escalated tickets?', or 'How many resolved tickets?'"
    )


# ----------------------------------------------------------------------------
# 8. Main agent
# ----------------------------------------------------------------------------

def ask(question: str) -> dict:
    """Main entry point. Handles imperfect natural language gracefully."""

    conversational = conversational_fallback(question)
    if conversational:
        return {
            "question": question,
            "collection": None,
            "pipeline": None,
            "rows": [],
            "answer": conversational,
            "error": None,
        }

    if looks_like_password_request(question):
        return {
            "question": question,
            "collection": "users",
            "pipeline": None,
            "rows": [],
            "answer": (
                "For security, I can't retrieve or expose passwords, password "
                "hashes, or credentials. I can provide safe user/account "
                "information such as name, role, department, or login time."
            ),
            "error": None,
        }

    out = {
        "question": question,
        "collection": None,
        "pipeline": None,
        "rows": None,
        "answer": None,
        "error": None,
    }

    # Step 1: generate MongoDB pipeline.
    try:
        generated = generate_query(question)
    except Exception as exc:
        out["error"] = f"gemini_unavailable: {exc}"
        (
            out["collection"],
            out["pipeline"],
            out["answer"],
        ) = fallback_answer(question)
        return out

    # Step 2: validate before execution.
    try:
        out["collection"] = generated["collection"]
        safe_pipeline = validate_pipeline(
            generated["pipeline"],
            generated["collection"],
        )
        out["pipeline"] = safe_pipeline
    except ValidationError as exc:
        # Retry once using a normalized question. This handles malformed
        # generation as well as badly phrased user input.
        try:
            retry_question = normalize_question(question)
            if retry_question and retry_question != question.strip():
                retry_generated = generate_query(retry_question)
                out["collection"] = retry_generated["collection"]
                safe_pipeline = validate_pipeline(
                    retry_generated["pipeline"],
                    retry_generated["collection"],
                )
                out["pipeline"] = safe_pipeline
            else:
                raise
        except Exception:
            out["error"] = f"validation_failed: {exc}"
            out["answer"] = (
                "I could not confidently understand that question. "
                "Try asking about incidents, severity, status, locations, "
                "root causes, technicians, or users."
            )
            return out

    # Step 3: execute read-only aggregation.
    try:
        out["rows"] = execute_pipeline(safe_pipeline, out["collection"])
    except Exception as exc:
        # One repair/retry pass for queries that are syntactically valid JSON
        # but incompatible with the actual MongoDB data/types.
        try:
            retry_question = normalize_question(question)
            retry_generated = generate_query(retry_question)
            retry_pipeline = validate_pipeline(
                retry_generated["pipeline"],
                retry_generated["collection"],
            )
            out["collection"] = retry_generated["collection"]
            out["pipeline"] = retry_pipeline
            out["rows"] = execute_pipeline(
                retry_pipeline,
                retry_generated["collection"],
            )
        except Exception:
            out["error"] = f"db_error: {exc}"
            out["answer"] = (
                "I understood the question, but the generated query could "
                "not be executed safely against the available data."
            )
            return out

    # Step 4: explain result.
    try:
        out["answer"] = explain_result(question, out["rows"])
    except Exception:
        out["answer"] = (
            f"Raw result ({len(out['rows'])} rows): "
            f"{json.dumps(out['rows'][:10], default=str)}"
        )

    return out


# ----------------------------------------------------------------------------
# 9. Conversational fallback
# ----------------------------------------------------------------------------

def conversational_fallback(question: str) -> str | None:
    """Answer simple non-database messages without generating a query."""
    q = normalize_question(question).lower().strip()

    if q in {"hi", "hello", "hey", "hii", "good morning", "good evening"}:
        return (
            "Hello! I can help you query incidents and users. "
            "For example: 'how many high severity incidents?'"
        )

    if any(x in q for x in ["what can you do", "help me", "help"]):
        return (
            "I can answer questions about incidents and users, including "
            "severity, status, locations, root causes, technicians, "
            "operators, admins, and departments."
        )

    if q in {"thanks", "thank you", "thx", "thank u"}:
        return "You're welcome!"

    return None


# ----------------------------------------------------------------------------
# 9. Optional JSON -> MongoDB import
# ----------------------------------------------------------------------------

def import_json_file(
    json_path: str,
    collection_name: str,
    drop_existing: bool = False,
):
    """Import a JSON array into either incidents or users."""
    if collection_name not in {"incidents", "users"}:
        raise ValueError("collection_name must be 'incidents' or 'users'.")

    with open(json_path, "r", encoding="utf-8") as f:
        documents = json.load(f)

    if not isinstance(documents, list):
        raise ValueError("Expected the JSON file to contain an array.")

    target = (
        incidents_collection
        if collection_name == "incidents"
        else users_collection
    )

    if drop_existing:
        target.delete_many({})

    if documents:
        result = target.insert_many(documents)
        return len(result.inserted_ids)

    return 0


# ----------------------------------------------------------------------------
# 10. Flask Blueprint Routes
# ----------------------------------------------------------------------------

@noc_bp.route("/noc/query", methods=["POST", "GET"])
@noc_bp.route("/noc/ask", methods=["POST", "GET"])
@noc_bp.route("/noc", methods=["POST", "GET"])
@noc_bp.route("/sqlagent/query", methods=["POST", "GET"])
@noc_bp.route("/sqlagent/ask", methods=["POST", "GET"])
@noc_bp.route("/sqlagent", methods=["POST", "GET"])
def handle_noc_query():
    """Endpoint for natural language query execution against incidents/users collections."""
    try:
        question = None
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            question = data.get("question") or data.get("query") or data.get("prompt") or data.get("message")
        
        if not question:
            question = request.args.get("question") or request.args.get("query") or request.args.get("prompt") or request.args.get("message")

        if not question or not str(question).strip():
            return jsonify({
                "success": False,
                "error": "Question parameter is required in request body (JSON) or URL query parameter.",
                "sample_questions": [
                    "Which location has the most escalated incidents?",
                    "How many open tickets?'",
                    "Which technician resolved the most high-severity tickets?",
                    "How many escalated tickets per location?",
                    "How many resolved tickets?"
                ]
            }), 400

        result = ask(str(question).strip())
        is_success = bool(result.get("answer") and not result.get("error"))

        return jsonify({
            "success": is_success,
            **result,
            "query": result.get("pipeline"),  # Frontend compatibility
            "normalized_question": normalize_question(str(question).strip())
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"NOC agent query error: {str(e)}"
        }), 500


@noc_bp.route("/noc/examples", methods=["GET"])
@noc_bp.route("/sqlagent/examples", methods=["GET"])
def get_noc_examples():
    """Returns sample questions and schema information."""
    return jsonify({
        "success": True,
        "database": MONGODB_DB,
        "collections": [INCIDENTS_COLLECTION, USERS_COLLECTION],
        "canned_queries": list(CANNED_EXAMPLES.keys()),
        "sample_questions": [
            "Which location has the most escalated incidents?",
            "How many open tickets?",
            "Which technician resolved the most high-severity tickets?",
            "How many escalated tickets per location?",
            "How many admin users are there?"
        ]
    }), 200


@noc_bp.route("/noc/health", methods=["GET"])
@noc_bp.route("/sqlagent/health", methods=["GET"])
def get_noc_health():
    """Health check for NOC NL Query Agent."""
    return jsonify({
        "status": "online",
        "service": "NOC NL Query Agent",
        "database": MONGODB_DB,
        "collections": [INCIDENTS_COLLECTION, USERS_COLLECTION]
    }), 200


# ----------------------------------------------------------------------------
# 11. CLI demo loop
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    print("NL Query Agent — MongoDB")
    print(f"Database:   {MONGODB_DB}")
    print(f"Collections: {INCIDENTS_COLLECTION}, {USERS_COLLECTION}")
    print("Ctrl+C to quit.")

    while True:
        try:
            q = input("\nAsk about incidents > ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not q:
            continue

        result = ask(q)

        if result["collection"]:
            print(f"\n[Collection] {result['collection']}")

        if result["pipeline"]:
            print("\n[MongoDB Pipeline]")
            print(json.dumps(result["pipeline"], indent=2))

        print(f"\n[Answer] {result['answer']}")

        if result["rows"] is not None:
            print(f"[Rows]   {len(result['rows'])}")

        if result["error"]:
            print(f"[Note]   {result['error']}")
