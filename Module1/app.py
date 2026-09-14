from flask import Flask, render_template, request, jsonify
import os
import uuid

from services.preprocessing import preprocess_image
from services.ocr_service import perform_ocr
from services.document_parser import parse_document

from services.validation import (
    validate_passport,
    validate_aadhaar,
    validate_document_structure,
    calculate_document_score,
    cross_document_validation
)


# ============================================================
# FLASK CONFIGURATION
# ============================================================

app = Flask(__name__)

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
# PROCESS ONE DOCUMENT
# ============================================================

def process_document(file):
    """
    Complete Module 1 processing pipeline.

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
    """

    if file is None:
        raise ValueError(
            "No file provided"
        )

    if file.filename == "":
        raise ValueError(
            "Empty filename"
        )


    # --------------------------------------------------------
    # Generate temporary filename
    # --------------------------------------------------------

    extension = os.path.splitext(
        file.filename
    )[1].lower()

    if not extension:
        extension = ".jpg"

    unique_filename = (
        str(uuid.uuid4())
        + extension
    )

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        unique_filename
    )


    # --------------------------------------------------------
    # Save image
    # --------------------------------------------------------

    file.save(
        file_path
    )


    try:

        # ====================================================
        # STEP 1 — PREPROCESSING
        # ====================================================

        preprocessed_images = (
            preprocess_image(
                file_path
            )
        )


        # ====================================================
        # STEP 2 — OCR
        # ====================================================

        ocr_result = perform_ocr(
            preprocessed_images
        )


        # ----------------------------------------------------
        # IMPORTANT:
        #
        # We now keep the COMPLETE OCR result.
        #
        # It contains:
        #   general OCR
        #   MRZ OCR
        #   Aadhaar OCR
        # ----------------------------------------------------

        ocr_text = ocr_result.get(
            "text",
            ""
        )

        ocr_confidence = ocr_result.get(
            "confidence",
            0.0
        )


        # ====================================================
        # STEP 3 — DOCUMENT PARSING
        # ====================================================

        # Pass the complete OCR result.
        #
        # The updated parser can use:
        #   ocr_result["text"]
        #   ocr_result["mrz"]
        #   ocr_result["aadhaar"]

        parsed_result = parse_document(
            ocr_result
        )


        document_type = parsed_result.get(
            "document_type",
            "unknown"
        )

        fields = parsed_result.get(
            "fields",
            {}
        )


        # ====================================================
        # STEP 4 — FIELD VALIDATION
        # ====================================================

        if document_type == "passport":

            field_validation = (
                validate_passport(
                    fields
                )
            )

        elif document_type == "aadhaar":

            field_validation = (
                validate_aadhaar(
                    fields
                )
            )

        else:

            field_validation = {}


        # ====================================================
        # STEP 5 — STRUCTURE VALIDATION
        # ====================================================

        structure_validation = (
            validate_document_structure(
                document_type,
                fields
            )
        )


        # ====================================================
        # STEP 6 — DOCUMENT SCORE
        # ====================================================

        document_score = (
            calculate_document_score(
                field_validation,
                structure_validation
            )
        )


        # ====================================================
        # RETURN DOCUMENT RESULT
        # ====================================================

        return {

            "document_type":
                document_type,

            "ocr": {

                "text":
                    ocr_text,

                "confidence":
                    ocr_confidence,

                # Useful for debugging and
                # improving extraction later.
                "general":
                    ocr_result.get(
                        "general",
                        {}
                    ),

                "mrz":
                    ocr_result.get(
                        "mrz",
                        {}
                    ),

                "aadhaar":
                    ocr_result.get(
                        "aadhaar",
                        {}
                    )
            },

            "fields":
                fields,

            "field_validation":
                field_validation,

            "structure_validation":
                structure_validation,

            "document_score":
                document_score
        }


    finally:

        # ----------------------------------------------------
        # Remove temporary uploaded file
        # ----------------------------------------------------

        if os.path.exists(
            file_path
        ):

            os.remove(
                file_path
            )


# ============================================================
# VERIFY PASSPORT + AADHAAR
# ============================================================

@app.route(
    "/api/verify",
    methods=["POST"]
)
def verify_documents():

    try:

        # ----------------------------------------------------
        # Get uploaded files
        # ----------------------------------------------------

        passport_file = (
            request.files.get(
                "passport"
            )
        )

        aadhaar_file = (
            request.files.get(
                "aadhaar"
            )
        )


        # ----------------------------------------------------
        # Check Passport
        # ----------------------------------------------------

        if passport_file is None:

            return jsonify({

                "success": False,

                "message":
                    "Passport image is required"

            }), 400


        # ----------------------------------------------------
        # Check Aadhaar
        # ----------------------------------------------------

        if aadhaar_file is None:

            return jsonify({

                "success": False,

                "message":
                    "Aadhaar image is required"

            }), 400


        # ====================================================
        # PROCESS PASSPORT
        # ====================================================

        passport_result = (
            process_document(
                passport_file
            )
        )


        # ====================================================
        # PROCESS AADHAAR
        # ====================================================

        aadhaar_result = (
            process_document(
                aadhaar_file
            )
        )


        # ====================================================
        # CROSS-DOCUMENT VALIDATION
        # ====================================================

        cross_validation = (
            cross_document_validation(

                passport_result[
                    "fields"
                ],

                aadhaar_result[
                    "fields"
                ]

            )
        )


        # ====================================================
        # FINAL RESPONSE
        # ====================================================

        return jsonify({

            "success":
                True,

            "passport":
                passport_result,

            "aadhaar":
                aadhaar_result,

            "cross_document_validation":
                cross_validation
        })


    except Exception as error:

        print(
            "\nVerification Error:",
            str(error)
        )


        return jsonify({

            "success":
                False,

            "message":
                "Document processing failed",

            "error":
                str(error)

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