from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import hashlib
import json

from Module2.services.firebase_service import create_enrollment
from Module2.services.firpiv_service import extract_fingerprint_template
from Module2.services.pinata_service import upload_to_ipfs


enrollment_bp = Blueprint(
    "enrollment",
    __name__,
    url_prefix="/api"
)


# ============================================================
# NATIONAL ID GENERATION
# ============================================================

def generate_national_id(aadhaar=None, driving_license=None):
    """
    Generate an 8-character uppercase National ID using SHA-256.

    Rules:
        Aadhaar + DL  →  sha256(aadhaar|dl|TRUST-ID-V1)[:8]
        Aadhaar only  →  sha256(aadhaar|TRUST-ID-V1)[:8]
        DL only       →  sha256(dl|TRUST-ID-V1)[:8]
    """

    CONSTANT = "TRUST-ID-V1"

    if not aadhaar and not driving_license:
        return None

    if aadhaar and driving_license:
        raw = f"{aadhaar}|{driving_license}|{CONSTANT}"
    elif aadhaar:
        raw = f"{aadhaar}|{CONSTANT}"
    else:
        raw = f"{driving_license}|{CONSTANT}"

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest().upper()[:8]


# ============================================================
# SIMULATED BLOCKCHAIN HASH
# ============================================================

def generate_record_hash(data):
    """
    SHA-256 integrity hash over key enrollment fields.
    Simulates a blockchain record hash (no actual chain yet).
    """

    raw = (
        f"{data.get('passport_no', '')}|"
        f"{data.get('national_id', '')}|"
        f"{data.get('fingerprint_template', '')[:64]}"
    )

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ============================================================
# POST /api/enroll
# ============================================================

@enrollment_bp.route("/enroll", methods=["POST"])
def enroll():

    try:

        # --------------------------------------------------------
        # 1. Read form fields
        # --------------------------------------------------------

        name        = request.form.get("name",        "").strip()
        dob         = request.form.get("dob",         "").strip()
        contact_no  = request.form.get("contact_no",  "").strip()
        passport_no = request.form.get("passport_no", "").strip()
        nationality = request.form.get("nationality", "").strip()


        # --------------------------------------------------------
        # 2. Parse documents JSON string
        # --------------------------------------------------------

        try:
            documents = json.loads(
                request.form.get("documents", "[]")
            )
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Invalid documents JSON"
            }), 400

        if not isinstance(documents, list):
            return jsonify({
                "success": False,
                "message": "documents must be a JSON array"
            }), 400


        # --------------------------------------------------------
        # 3. Validate required text fields
        # --------------------------------------------------------

        missing = [
            field for field, val in {
                "name":        name,
                "dob":         dob,
                "contact_no":  contact_no,
                "passport_no": passport_no,
                "nationality": nationality
            }.items() if not val
        ]

        if missing:
            return jsonify({
                "success": False,
                "message": "Missing required fields",
                "missing_fields": missing
            }), 400


        # --------------------------------------------------------
        # 4. Validate fingerprint file
        # --------------------------------------------------------

        firpiv_file = request.files.get("fingerprint_file")

        if not firpiv_file or not firpiv_file.filename:
            return jsonify({
                "success": False,
                "message": "fingerprint_file (.firpiv) is required"
            }), 400

        if not firpiv_file.filename.lower().endswith(".firpiv"):
            return jsonify({
                "success": False,
                "message": "Only .firpiv fingerprint files are accepted"
            }), 400


        # --------------------------------------------------------
        # 5. Read file bytes ONCE
        #    (stream can only be read once)
        # --------------------------------------------------------

        fingerprint_bytes = firpiv_file.read()

        if not fingerprint_bytes:
            return jsonify({
                "success": False,
                "message": "Fingerprint file is empty"
            }), 400


        # --------------------------------------------------------
        # 6. Extract fingerprint template from FIRPIV bytes
        # --------------------------------------------------------

        fingerprint_template = extract_fingerprint_template(
            fingerprint_bytes
        )


        # --------------------------------------------------------
        # 7. Upload original FIRPIV bytes to Pinata / IPFS
        # --------------------------------------------------------

        ipfs_result = upload_to_ipfs(
            file_bytes=fingerprint_bytes,
            filename=firpiv_file.filename
        )


        # --------------------------------------------------------
        # 8. Find Aadhaar / Driving License numbers from documents
        # --------------------------------------------------------

        aadhaar_number         = None
        driving_license_number = None

        for doc in documents:

            if not isinstance(doc, dict):
                continue

            doc_type   = doc.get("type",   "").strip().lower()
            doc_number = doc.get("number", "").strip()

            if not doc_number:
                continue

            if doc_type == "aadhaar":
                aadhaar_number = doc_number

            elif doc_type in ("driving license", "driving licence"):
                driving_license_number = doc_number


        # --------------------------------------------------------
        # 9. At least one ID document is mandatory
        # --------------------------------------------------------

        if not aadhaar_number and not driving_license_number:
            return jsonify({
                "success": False,
                "message": (
                    "At least one of Aadhaar or "
                    "Driving License is required in documents"
                )
            }), 400


        # --------------------------------------------------------
        # 10. Generate National ID
        # --------------------------------------------------------

        national_id = generate_national_id(
            aadhaar=aadhaar_number,
            driving_license=driving_license_number
        )


        # --------------------------------------------------------
        # 11. Build enrollment record
        # --------------------------------------------------------

        timestamp = datetime.now(timezone.utc).isoformat()

        enrollment_record = {

            "name":        name,
            "dob":         dob,
            "contact_no":  contact_no,
            "passport_no": passport_no,
            "nationality": nationality,
            "national_id": national_id,

            "documents": documents,

            # Extracted WSQ template for future biometric matching
            "fingerprint_template": fingerprint_template,

            # IPFS reference — raw .firpiv is NOT stored in Firestore
            "fingerprint_file": {
                "file_name": firpiv_file.filename,
                "ipfs_cid":  ipfs_result["cid"],
                "ipfs_url":  ipfs_result["url"]
            },

            "created_at": timestamp
        }


        # --------------------------------------------------------
        # 12. Generate simulated blockchain integrity hash
        # --------------------------------------------------------

        record_hash = generate_record_hash(enrollment_record)
        enrollment_record["hash"] = record_hash


        # --------------------------------------------------------
        # 13. Store in Firestore
        # --------------------------------------------------------

        firebase_id = create_enrollment(enrollment_record)


        # --------------------------------------------------------
        # 14. Return response
        # --------------------------------------------------------

        return jsonify({

            "success": True,
            "message": "Enrollment successful",

            "data": {
                "firebase_id": firebase_id,
                "national_id": national_id,
                "fingerprint": {
                    "file_name": firpiv_file.filename,
                    "ipfs_cid":  ipfs_result["cid"],
                    "ipfs_url":  ipfs_result["url"]
                },
                "hash": record_hash
            }

        }), 201


    except Exception as e:

        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": "Enrollment failed",
            "error":   str(e)
        }), 500
