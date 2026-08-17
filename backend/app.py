from flask import Flask, jsonify
from flask_cors import CORS

from auth.auth_routes import auth_bp
from rag.receiver import receiver_bp


# ============================================================
# FLASK APP
# ============================================================

app = Flask(
    __name__
)


# ============================================================
# CORS
# ============================================================

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": "*"
        }
    }
)


# ============================================================
# REGISTER AUTH BLUEPRINT
# ============================================================

app.register_blueprint(

    auth_bp,

    url_prefix="/api/auth"

)


# ============================================================
# REGISTER RECEIVER BLUEPRINT
# ============================================================

app.register_blueprint(

    receiver_bp,

    url_prefix="/api"

)


# ============================================================
# ROOT
# ============================================================

@app.route("/")
def root():

    return jsonify({

        "service":
            "Telecom Agentic Fault Management System",

        "status":
            "online",

        "framework":
            "Flask"

    })


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status":
            "healthy",

        "service":
            "CTS Backend"

    })


# ============================================================
# 404
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({

        "success":
            False,

        "message":
            "Endpoint not found"

    }), 404


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=8000,

        debug=True

    )