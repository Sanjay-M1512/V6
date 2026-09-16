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