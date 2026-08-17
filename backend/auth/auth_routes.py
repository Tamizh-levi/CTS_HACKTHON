import os
import re
import secrets
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
import pymongo

auth_bp = Blueprint("auth", __name__)

# ============================================================
# MONGODB CONFIGURATION
# ============================================================
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB_NAME", "cts_incident_management")

mongo_client = None
db = None
users_collection = None

# Comprehensive seed users in MongoDB with Encrypted Passwords
INITIAL_SEED_USERS = [
    {
        "username": "ganesh@gmail.com",
        "password": generate_password_hash("ganesh123", method="pbkdf2:sha256"),
        "name": "Senior NOC Controller",
        "role": "operator",
        "department": "Tier-2 NOC Core Transmission",
        "email": "[EMAIL_ADDRESS]",
        "is_encrypted": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "username": "aadhi@gmail.com",
        "password": generate_password_hash("aadhi123", method="pbkdf2:sha256"),
        "name": "Central NOC Engineer",
        "role": "operator",
        "department": "Tier-2 NOC Console",
        "email": "noc_operator@telecom-noc.com",
        "is_encrypted": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "username": "sakthi@gmail.com",
        "password": generate_password_hash("sakthi123", method="pbkdf2:sha256"),
        "name": "System Administrator",
        "role": "admin",
        "department": "NOC Operations",
        "email": "admin@telecom-noc.com",
        "is_encrypted": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "username": "tamilzh@gmail.com",
        "password": generate_password_hash("tamilzh123", method="pbkdf2:sha256"),
        "name": "NOC Commander",
        "role": "admin",
        "department": "Central Core Ops",
        "email": "commander@telecom-noc.com",
        "is_encrypted": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
   
]


def verify_password_secure(stored_hash_or_plain: str, provided_password: str) -> bool:
    """
    Verifies provided password against stored hash or plain password.
    Supports secure PBKDF2/scrypt/argon hashes and auto-detects legacy plain text.
    """
    if not stored_hash_or_plain or not provided_password:
        return False

    try:
        # Check standard werkzeug hash (e.g. pbkdf2:sha256:... or scrypt:...)
        if stored_hash_or_plain.startswith(("pbkdf2:", "scrypt:", "argon2:")):
            return check_password_hash(stored_hash_or_plain, provided_password)
    except Exception:
        pass

    # Direct match fallback for legacy plain text passwords
    return stored_hash_or_plain == provided_password


def get_mongo_connection():
    """Initializes MongoDB users collection, encrypts existing plain passwords and auto-seeds."""
    global mongo_client, db, users_collection

    if users_collection is not None:
        return users_collection

    try:
        mongo_client = pymongo.MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=3000
        )
        # Verify connection
        mongo_client.admin.command('ping')
        db = mongo_client[DB_NAME]
        users_collection = db["users"]

        # Ensure index on username
        try:
            users_collection.create_index("username", unique=True)
        except Exception:
            pass

        # Seed missing initial users into MongoDB
        for user_data in INITIAL_SEED_USERS:
            existing = users_collection.find_one({"username": user_data["username"]})
            if not existing:
                users_collection.insert_one(dict(user_data))
            else:
                # Upgrade legacy plain passwords to encrypted hashes
                current_pw = str(existing.get("password", ""))
                if not current_pw.startswith(("pbkdf2:", "scrypt:", "argon2:")):
                    encrypted_pw = generate_password_hash(current_pw, method="pbkdf2:sha256")
                    users_collection.update_one(
                        {"_id": existing["_id"]},
                        {"$set": {"password": encrypted_pw, "is_encrypted": True}}
                    )

        return users_collection

    except Exception as e:
        print(f"[AUTH MONGODB NOTICE] MongoDB connection check at {MONGO_URI}: {e}")
        return None


# Initialize on import
get_mongo_connection()


# ============================================================
# LOGIN ENDPOINT (Verified Against Encrypted MongoDB Passwords)
# ============================================================
@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json(silent=True) or {}
        raw_username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        role_hint = data.get("role", "operator").strip()

        # If empty username submitted, default to operator
        username_or_email = raw_username if raw_username else "operator"

        col = get_mongo_connection()

        if col is not None:
            # Query by username or email (case-insensitive)
            user_doc = col.find_one({
                "$or": [
                    {"username": {"$regex": f"^{re.escape(username_or_email)}$", "$options": "i"}},
                    {"email": {"$regex": f"^{re.escape(username_or_email)}$", "$options": "i"}}
                ]
            })

            # If user not found in MongoDB
            if not user_doc:
                return jsonify({
                    "success": False,
                    "message": f"Invalid User or Password"
                }), 404

            # Verify password against encrypted hash stored in MongoDB
            stored_password_hash = str(user_doc.get("password", ""))
            is_valid = verify_password_secure(stored_password_hash, password)

            if not is_valid:
                return jsonify({
                    "success": False,
                    "message": "Invalid password. Authentication failed against encrypted MongoDB credentials."
                }), 401

            # Upgrade plain password to encrypted hash if needed
            if not stored_password_hash.startswith(("pbkdf2:", "scrypt:", "argon2:")):
                new_encrypted = generate_password_hash(password, method="pbkdf2:sha256")
                col.update_one(
                    {"_id": user_doc["_id"]},
                    {"$set": {"password": new_encrypted, "is_encrypted": True}}
                )

            # Update last login timestamp in MongoDB
            now_iso = datetime.now(timezone.utc).isoformat()
            col.update_one(
                {"_id": user_doc["_id"]},
                {"$set": {"last_login_at": now_iso}}
            )

            # Generate secure session token
            token = f"token_mongo_{secrets.token_hex(16)}"

            return jsonify({
                "success": True,
                "token": token,
                "user": {
                    "id": str(user_doc.get("_id")),
                    "username": user_doc.get("username"),
                    "name": user_doc.get("name", user_doc.get("username", "").title()),
                    "role": user_doc.get("role", role_hint),
                    "department": user_doc.get("department", "NOC Operations"),
                    "email": user_doc.get("email", ""),
                    "last_login_at": now_iso,
                    "auth_source": "MongoDB (Encrypted Credentials)"
                },
                "message": "Authentication successful (Verified via Encrypted MongoDB)"
            })

        # Fallback if MongoDB is offline
        return jsonify({
            "success": False,
            "message": "MongoDB is currently unreachable. Ensure MongoDB is running on port 27017."
        }), 503

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Authentication processing error: {str(e)}"
        }), 500


# ============================================================
# REGISTER ENDPOINT (Encrypts Passwords Before Saving to MongoDB)
# ============================================================
@auth_bp.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json(silent=True) or {}
        username = data.get("username", "").strip()
        plain_password = data.get("password", "").strip()
        name = data.get("name", username.title()).strip()
        role = data.get("role", "operator").strip()
        department = data.get("department", "NOC Operations").strip()
        email = data.get("email", f"{username}@telecom-noc.com").strip()

        if not username or not plain_password:
            return jsonify({
                "success": False,
                "message": "Username and password are required"
            }), 400

        col = get_mongo_connection()
        if col is None:
            return jsonify({
                "success": False,
                "message": "MongoDB is offline"
            }), 503

        # Check if username already exists
        existing = col.find_one({"username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}})
        if existing:
            return jsonify({
                "success": False,
                "message": f"User '{username}' already exists in MongoDB"
            }), 409

        # ENCRYPT THE PASSWORD USING PBKDF2:SHA256
        encrypted_password = generate_password_hash(plain_password, method="pbkdf2:sha256")

        new_user = {
            "username": username.lower(),
            "password": encrypted_password,  # Stored as encrypted hash
            "name": name,
            "role": role,
            "department": department,
            "email": email,
            "is_encrypted": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        result = col.insert_one(new_user)

        return jsonify({
            "success": True,
            "message": f"User '{username}' registered with encrypted password in MongoDB.",
            "user_id": str(result.inserted_id)
        }), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ============================================================
# CURRENT USER INFO
# ============================================================
@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    return jsonify({
        "success": True,
        "user": {
            "username": "operator",
            "name": "Senior NOC Controller",
            "role": "operator",
            "department": "Tier-2 NOC Core Transmission",
            "auth_source": "MongoDB (Encrypted)"
        }
    })


# ============================================================
# GET ALL USERS (Admin Roster from MongoDB)
# ============================================================
@auth_bp.route("/users", methods=["GET"])
def get_all_users():
    try:
        col = get_mongo_connection()
        if col is None:
            return jsonify({
                "success": False,
                "message": "MongoDB is offline",
                "users": []
            }), 503

        users_list = []
        for doc in col.find({}, {"password": 0}):
            users_list.append({
                "id": str(doc.get("_id")),
                "username": doc.get("username", ""),
                "name": doc.get("name", doc.get("username", "").title()),
                "role": doc.get("role", "operator"),
                "department": doc.get("department", "NOC Operations"),
                "email": doc.get("email", ""),
                "last_login_at": doc.get("last_login_at", "Never"),
                "created_at": doc.get("created_at", "N/A"),
                "is_encrypted": doc.get("is_encrypted", True)
            })

        return jsonify({
            "success": True,
            "total": len(users_list),
            "users": users_list
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# MONGODB CONNECTION STATUS
# ============================================================
@auth_bp.route("/status", methods=["GET"])
def get_db_status():
    col = get_mongo_connection()
    if col is not None:
        count = col.count_documents({})
        return jsonify({
            "success": True,
            "status": "connected",
            "database": DB_NAME,
            "collection": "users",
            "total_users": count,
            "encryption": "pbkdf2:sha256"
        })
    return jsonify({
        "success": False,
        "status": "disconnected",
        "message": "Could not connect to MongoDB at " + MONGO_URI
    }), 503

