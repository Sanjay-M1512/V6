from flask import Blueprint, request, jsonify
from Module2.services.log_service import (
    save_forensic_log,
    get_forensic_logs,
    get_forensic_log_by_id
)

logs_bp = Blueprint("logs", __name__, url_prefix="/api")


@logs_bp.route("/logs", methods=["POST"])
@logs_bp.route("/forensic/logs", methods=["POST"])
def save_log_endpoint():
    """
    Endpoint for saving verification and forensic logs.
    Captures the whole process: scores, documents, biometrics, status, officer details.
    Accepts JSON or multipart/form-data.
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            # Fallback to form data
            data = request.form.to_dict()

        if not data:
            return jsonify({
                "success": False,
                "message": "Empty log payload provided"
            }), 400

        result, status_code = save_forensic_log(data)
        return jsonify(result), status_code

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "Failed to save forensic log",
            "error": str(e)
        }), 500


@logs_bp.route("/logs", methods=["GET"])
@logs_bp.route("/forensic/logs", methods=["GET"])
def get_logs_endpoint():
    """
    Endpoint for forensic investigators and admins to view audit and verification logs.
    Supports query parameters:
        - role: filter by role (e.g. 'Investigator', 'Admin', 'SSB')
        - status: filter by verification status (e.g. 'VERIFIED', 'NOT_VERIFIED')
        - passport_no: filter by passport number
        - limit: max number of logs to return (default 50)
    """
    try:
        filters = {}
        if request.args.get("role"):
            filters["role"] = request.args.get("role")
        if request.args.get("status"):
            filters["status"] = request.args.get("status")
        if request.args.get("passport_no"):
            filters["passport_no"] = request.args.get("passport_no")

        limit = request.args.get("limit", 50)

        result, status_code = get_forensic_logs(filters=filters, limit=limit)
        return jsonify(result), status_code

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "Failed to retrieve logs",
            "error": str(e)
        }), 500


@logs_bp.route("/logs/<log_id>", methods=["GET"])
@logs_bp.route("/forensic/logs/<log_id>", methods=["GET"])
def get_single_log_endpoint(log_id):
    """
    Endpoint for retrieving complete details of a single forensic log entry.
    """
    try:
        result, status_code = get_forensic_log_by_id(log_id)
        return jsonify(result), status_code

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Failed to retrieve log {log_id}",
            "error": str(e)
        }), 500

