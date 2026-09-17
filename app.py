from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import uuid
import cv2

from Module1.services.preprocessing import preprocess_image
from Module1.services.ocr_service import perform_ocr
from Module1.services.document_parser import parse_document

from Module1.services.validation import (
    validate_passport,
    validate_aadhaar,
    validate_driving_license,
    validate_document_structure,
    calculate_document_score,
    cross_document_validation
)
from Module2.routes.enrollment import enrollment_bp
from Module2.routes.auth_routes import auth_bp
from Module2.routes.log_routes import logs_bp
from Module2.services.verification_service import verify_identity_workflow
from Module2.services.log_service import save_forensic_log
from Module3.app import biometrics_bp, OUTPUT_FOLDER as MOD3_OUTPUT_FOLDER
from Module3.services.face_input import process_face_file


# ============================================================
# FLASK CONFIGURATION
# ============================================================

app = Flask(
    __name__,
    template_folder="templates"
)
CORS(app)  # Enable CORS for all origins

# Register Module 2 (Enrollment, Auth, Logs) & Module 3 (Biometrics) blueprints
app.register_blueprint(enrollment_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(biometrics_bp)

UPLOAD_FOLDER = "uploads"

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
# PROCESS ONE DOCUMENT (MODULE 1 + OPTIONAL FACE EXTRACTION)
# ============================================================

def process_document(file, doc_type_hint=None):
    """
    Complete Module 1 processing pipeline with face extraction.

    Upload
       ↓
    Preprocessing
       ↓
    OCR
       ↓
    Document Parsing
       ↓
    Field Validation
       ↓
    Structure Validation
       ↓
    Document Score
       ↓
    Face Extraction (Module 3 bridge)
    """

    if file is None:
        raise ValueError("No file provided")

    if file.filename == "":
        raise ValueError("Empty filename")

    extension = os.path.splitext(file.filename)[1].lower()

    if not extension:
        extension = ".jpg"

    unique_filename = str(uuid.uuid4()) + extension

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        unique_filename
    )

    file.save(file_path)

    try:

        # ====================================================
        # STEP 1 — PREPROCESSING
        # ====================================================

        preprocessed_images = preprocess_image(file_path)


        # ====================================================
        # STEP 2 — OCR
        # ====================================================

        ocr_result = perform_ocr(preprocessed_images)

        ocr_text = ocr_result.get("text", "")
        ocr_confidence = ocr_result.get("confidence", 0.0)


        # ====================================================
        # STEP 3 — DOCUMENT PARSING
        # ====================================================

        parsed_result = parse_document(ocr_result)

        document_type = parsed_result.get("document_type", "unknown")
        fields = parsed_result.get("fields", {})


        # ====================================================
        # STEP 4 — FIELD VALIDATION
        # ====================================================

        if document_type == "passport":
            field_validation = validate_passport(fields)
        elif document_type == "aadhaar":
            field_validation = validate_aadhaar(fields)
        elif document_type == "driving_license":
            field_validation = validate_driving_license(fields)
        else:
            field_validation = {}


        # ====================================================
        # STEP 5 — STRUCTURE VALIDATION
        # ====================================================

        structure_validation = validate_document_structure(
            document_type,
            fields
        )


        # ====================================================
        # STEP 6 — DOCUMENT SCORE
        # ====================================================

        document_score = calculate_document_score(
            field_validation,
            structure_validation
        )


        # ====================================================
        # STEP 7 — FACE EXTRACTION (MODULE 3 INTEGRATION)
        # ====================================================

        face_data = None
        try:
            face_res = process_face_file(file_path)
            if face_res.get("success") and face_res.get("face_image") is not None:
                target_type = doc_type_hint or document_type
                if target_type in ("passport", "aadhaar", "driving_license"):
                    face_fname = f"{target_type}_face.jpg"
                    face_out_path = os.path.join(MOD3_OUTPUT_FOLDER, face_fname)
                    cv2.imwrite(face_out_path, face_res["face_image"])
                    face_data = {
                        "face_found": True,
                        "face_filename": face_fname,
                        "face_quality_score": face_res.get("face_quality_score"),
                        "quality_status": face_res.get("quality_status"),
                        "blur_score": face_res.get("blur_score"),
                        "image_type": face_res.get("image_type"),
                        "message": "Face extracted successfully"
                    }
        except Exception as face_err:
            print(f"Face extraction warning for {file.filename}: {face_err}")


        result_dict = {
            "document_type": document_type,
            "ocr": {
                "text": ocr_text,
                "confidence": ocr_confidence
            },
            "fields": fields,
            "field_validation": field_validation,
            "structure_validation": structure_validation,
            "document_score": document_score
        }

        if face_data:
            result_dict["face"] = face_data

        return result_dict

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# ============================================================
# VERIFY PASSPORT + AADHAAR / DRIVING LICENSE
# ============================================================

@app.route("/api/verify", methods=["POST"])
def verify_documents():

    try:

        passport_file = request.files.get("passport")
        aadhaar_file = request.files.get("aadhaar")
        dl_file = request.files.get("driving_license")

        id_file = aadhaar_file or dl_file
        id_key = "aadhaar" if aadhaar_file else "driving_license"

        if passport_file is None:
            return jsonify({
                "success": False,
                "message": "Passport image is required"
            }), 400

        if id_file is None:
            return jsonify({
                "success": False,
                "message": "Aadhaar or Driving License image is required"
            }), 400

        passport_result = process_document(passport_file, doc_type_hint="passport")
        id_result = process_document(id_file, doc_type_hint=id_key)

        cross_validation = cross_document_validation(
            passport_result["fields"],
            id_result["fields"],
            id_key
        )

        response_data = {
            "success": True,
            "passport": passport_result,
            "cross_document_validation": cross_validation
        }

        response_data[id_key] = id_result

        # ----------------------------------------------------
        # MODULE 2 — OFFICER BIOMETRIC & INTEGRITY VERIFICATION
        # If officer uploads a .firpiv fingerprint, run verification
        # ----------------------------------------------------
        officer_fp_file = (
            request.files.get("fingerprint_file")
            or request.files.get("fingerprint")
        )

        if officer_fp_file and officer_fp_file.filename:
            fp_bytes = officer_fp_file.read()

            passport_no = passport_result.get("fields", {}).get("passport_number")
            second_doc_no = (
                id_result.get("fields", {}).get("aadhaar_number")
                if id_key == "aadhaar"
                else id_result.get("fields", {}).get("dl_number")
            )

            verif_res, verif_code = verify_identity_workflow(
                passport_number=passport_no,
                second_doc_number=second_doc_no,
                second_doc_type=id_key,
                officer_firpiv_bytes=fp_bytes
            )

            response_data["verification"] = verif_res.get("verification")
            if "reason" in verif_res:
                response_data["reason"] = verif_res["reason"]
            if "identity" in verif_res:
                response_data["identity"] = verif_res["identity"]
            if "fingerprint" in verif_res:
                response_data["fingerprint"] = verif_res["fingerprint"]
            if "integrity" in verif_res:
                response_data["integrity"] = verif_res["integrity"]

        # ----------------------------------------------------
        # FORENSIC AUDIT LOGGING
        # Automatically record complete process details & scores
        # ----------------------------------------------------
        try:
            officer_email = (
                request.form.get("officer_email")
                or request.headers.get("X-Officer-Email")
                or "system"
            )
            officer_role = (
                request.form.get("role")
                or request.headers.get("X-Officer-Role")
                or "SSB"
            )

            scores_payload = {
                "passport_score": passport_result.get("document_score"),
                "id_score": id_result.get("document_score"),
                "cross_validation_score": cross_validation.get("score") if isinstance(cross_validation, dict) else None,
            }
            if "fingerprint" in response_data and isinstance(response_data["fingerprint"], dict):
                scores_payload["fingerprint_match_score"] = response_data["fingerprint"].get("match_score")

            final_verdict = "DOCUMENT_VALIDATED"
            if "verification" in response_data and isinstance(response_data["verification"], dict):
                final_verdict = response_data["verification"].get("final_status", "UNKNOWN")

            save_forensic_log({
                "action": "VERIFICATION",
                "officer_email": officer_email,
                "role": officer_role,
                "passport_no": passport_result.get("fields", {}).get("passport_number"),
                "national_id": response_data.get("identity", {}).get("national_id"),
                "second_doc_type": id_key,
                "second_doc_no": (
                    id_result.get("fields", {}).get("aadhaar_number")
                    if id_key == "aadhaar"
                    else id_result.get("fields", {}).get("dl_number")
                ),
                "scores": scores_payload,
                "verification_status": final_verdict,
                "details": {
                    "passport_fields": passport_result.get("fields"),
                    "id_fields": id_result.get("fields"),
                    "cross_validation": cross_validation,
                    "verification": response_data.get("verification"),
                    "reason": response_data.get("reason"),
                    "integrity": response_data.get("integrity")
                }
            })
        except Exception as log_err:
            print(f"[Warning] Forensic logging failed: {log_err}")

        if officer_fp_file and officer_fp_file.filename:
            return jsonify(response_data), verif_code

        return jsonify(response_data)

    except Exception as error:

        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": "Document processing failed",
            "error": str(error)
        }), 500


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
