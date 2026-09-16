import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
load_dotenv()

# --------------------------------------------------
# Firebase Initialization
# --------------------------------------------------

_db = None


def initialize_firebase():

    global _db

    if _db is not None:
        return _db

    if firebase_admin._apps:
        _db = firestore.client()
        return _db

    service_account_path = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT",
        "firebase/firebase-service-account.json"
    )

    if not os.path.exists(service_account_path):
        raise FileNotFoundError(
            f"Firebase service account file not found: {service_account_path}"
        )

    cred = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)
    _db = firestore.client()
    return _db


def get_db():
    return initialize_firebase()


# --------------------------------------------------
# Verification DB
# --------------------------------------------------

COLLECTION_NAME = "verification_db"


def create_enrollment(data):

    document_ref = get_db().collection(COLLECTION_NAME).document()

    document_ref.set(data)

    return document_ref.id


def get_enrollment_by_id(enrollment_id):

    document_ref = (
        get_db().collection(COLLECTION_NAME)
        .document(enrollment_id)
        .get()
    )

    if not document_ref.exists:
        return None

    return document_ref.to_dict()


def find_identity_by_documents(passport_number, second_doc_number=None, second_doc_type=None):
    """
    Search verification_db for an enrolled identity record.

    Matches passport_number AND (aadhaar_number OR driving_license_number).
    Returns (record, error_reason).
    """
    db = get_db()

    if not passport_number:
        return None, "Passport number is required for search"

    p_clean = str(passport_number).strip().upper()

    # Query by passport_no
    matches = list(
        db.collection(COLLECTION_NAME)
        .where("passport_no", "==", p_clean)
        .stream()
    )

    # Fallback search if casing differs
    if not matches and p_clean != p_clean.lower():
        matches = list(
            db.collection(COLLECTION_NAME)
            .where("passport_no", "==", p_clean.lower())
            .stream()
        )

    if not matches:
        return None, "Identity record not found"

    # Normalize second document if provided
    s_clean = None
    if second_doc_number:
        s_clean = (
            str(second_doc_number)
            .strip()
            .replace(" ", "")
            .replace("-", "")
            .upper()
        )

    matched_records = []

    for doc_snap in matches:
        data = doc_snap.to_dict()
        data["firebase_id"] = doc_snap.id
        doc_list = data.get("documents", [])

        if s_clean:
            has_match = False
            for doc_item in doc_list:
                if not isinstance(doc_item, dict):
                    continue
                d_num = (
                    str(doc_item.get("number", ""))
                    .strip()
                    .replace(" ", "")
                    .replace("-", "")
                    .upper()
                )
                if d_num == s_clean:
                    has_match = True
                    break
            if has_match:
                matched_records.append(data)
        else:
            # If no second document was supplied to filter, accept passport match
            matched_records.append(data)

    if not matched_records:
        label = second_doc_type or "Aadhaar / Driving License"
        return None, f"Passport found, but no matching record with provided {label} number"

    if len(matched_records) > 1:
        return None, "Multiple identity records found matching the provided document numbers"

    return matched_records[0], None
