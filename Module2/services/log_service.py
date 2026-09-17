from datetime import datetime, timezone
from google.cloud.firestore_v1.base_query import FieldFilter
from Module2.services.firebase_service import get_db

FORENSIC_LOGS_COLLECTION = "forensic_logs"


def save_forensic_log(data):
    """
    Saves a comprehensive verification/audit log into the 'forensic_logs' collection.

    Accepts structured fields such as:
        - action / event_type: str (e.g. "VERIFICATION", "MANUAL_REVIEW", "ENROLLMENT")
        - officer_email: str
        - role: str ("SSB", "Investigator", "Admin")
        - passport_no: str
        - national_id: str
        - second_doc_type: str
        - second_doc_no: str
        - scores: dict (document_score, cross_validation_score, fingerprint_score, face_score, risk_score, etc.)
        - verification_status: str ("VERIFIED", "NOT_VERIFIED", "FLAGGED", "SUSPICIOUS", etc.)
        - details: dict (complete process data, error reasons, biometric details, integrity check results)
        - timestamp: str (ISO format; generated if absent)

    Returns:
        tuple: (result_dict, status_code)
    """
    if not isinstance(data, dict):
        return {"success": False, "message": "Log payload must be a JSON object"}, 400

    db = get_db()

    # Normalize timestamp
    ts = data.get("timestamp")
    if not ts:
        ts = datetime.now(timezone.utc).isoformat()

    log_entry = {
        "event_type": data.get("event_type") or data.get("action") or "VERIFICATION",
        "officer_email": data.get("officer_email") or data.get("email") or "system",
        "role": data.get("role") or "SSB",
        "passport_no": data.get("passport_no") or "",
        "national_id": data.get("national_id") or "",
        "second_doc_type": data.get("second_doc_type") or "",
        "second_doc_no": data.get("second_doc_no") or "",
        "scores": data.get("scores") or {},
        "verification_status": (
            data.get("verification_status")
            or data.get("status")
            or data.get("final_status")
            or "UNKNOWN"
        ),
        "details": data.get("details") or {},
        "timestamp": ts,
        "created_at": ts
    }

    doc_ref = db.collection(FORENSIC_LOGS_COLLECTION).document()
    doc_ref.set(log_entry)

    saved_record = dict(log_entry)
    saved_record["id"] = doc_ref.id

    return {
        "success": True,
        "message": "Forensic log recorded successfully",
        "log_id": doc_ref.id,
        "log": saved_record
    }, 201


def get_forensic_logs(filters=None, limit=50):
    """
    Retrieves forensic logs for viewing by investigators and admins.
    Supports filtering by role, status, passport_no, etc.

    Parameters:
        filters (dict): Optional dict with keys like 'role', 'status', 'passport_no'
        limit (int): Maximum records to retrieve (default 50, max 200)

    Returns:
        tuple: (result_dict, status_code)
    """
    db = get_db()
    filters = filters or {}

    try:
        limit_val = min(max(int(limit), 1), 200)
    except (ValueError, TypeError):
        limit_val = 50

    query = db.collection(FORENSIC_LOGS_COLLECTION)

    # Optional simple filters
    role_filter = filters.get("role")
    if role_filter:
        query = query.where(filter=FieldFilter("role", "==", role_filter))

    status_filter = filters.get("status")
    if status_filter:
        query = query.where(filter=FieldFilter("verification_status", "==", status_filter))

    passport_filter = filters.get("passport_no")
    if passport_filter:
        query = query.where(filter=FieldFilter("passport_no", "==", str(passport_filter).strip().upper()))

    docs = query.limit(limit_val).stream()

    logs = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        logs.append(item)

    # Sort in memory by timestamp descending
    logs.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    return {
        "success": True,
        "count": len(logs),
        "logs": logs
    }, 200


def get_forensic_log_by_id(log_id):
    """
    Retrieves a single forensic log entry by its document ID.
    """
    if not log_id:
        return {"success": False, "message": "Log ID is required"}, 400

    db = get_db()
    doc_ref = db.collection(FORENSIC_LOGS_COLLECTION).document(log_id).get()

    if not doc_ref.exists:
        return {"success": False, "message": f"Log with ID '{log_id}' not found"}, 404

    data = doc_ref.to_dict()
    data["id"] = doc_ref.id

    return {
        "success": True,
        "log": data
    }, 200
