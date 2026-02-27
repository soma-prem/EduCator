import os
import sys

from flask import Blueprint, jsonify

from services.firestore_service import FIREBASE_INIT_ERROR, get_firestore_db

diag_bp = Blueprint("diag", __name__)


@diag_bp.route("/api/diag/firebase", methods=["GET"])
def firebase_diag():
    info = {
        "python_executable": sys.executable,
        "firebase_admin_imported": get_firestore_db() is not None,
        "firebase_init_error": FIREBASE_INIT_ERROR,
        "service_account_path_env": os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", ""),
        "service_account_exists": False,
    }
    service_path = info["service_account_path_env"]
    if service_path:
        if not os.path.isabs(service_path):
            service_path = os.path.join(os.path.dirname(__file__), "..", service_path)
            service_path = os.path.normpath(service_path)
        info["service_account_exists"] = os.path.exists(service_path)
        info["service_account_path_resolved"] = service_path
    return jsonify(info)
