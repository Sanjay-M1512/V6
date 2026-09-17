import re
from datetime import datetime, timezone
from werkzeug.security import check_password_hash  # kept for legacy hashed-password fallback only
from google.cloud.firestore_v1.base_query import FieldFilter
from Module2.services.firebase_service import get_db

USERS_COLLECTION = "users"
ALLOWED_ROLES = ["SSB", "Investigator", "Admin"]


def normalize_role(role_input):
    """
    Validates and normalizes role input against ALLOWED_ROLES.
    Matches case-insensitively.
    Returns normalized string (e.g. 'SSB', 'Investigator', 'Admin') or None.
    """
    if not role_input or not isinstance(role_input, str):
        return None
    
    clean = role_input.strip().lower()
    for role in ALLOWED_ROLES:
        if clean == role.lower():
            return role
    return None


def register_user(email, role, password):
    """
    Registers a new user in the 'users' collection.
    
    Parameters:
        email (str): User email address.
        role (str): Role ('SSB', 'Investigator', or 'Admin').
        password (str): Plaintext password (will be hashed).
        
    Returns:
        tuple: (result_dict, status_code)
    """
    # 1. Validate Email
    if not email or not isinstance(email, str) or not email.strip():
        return {"success": False, "message": "Email is required"}, 400
    
    email_clean = email.strip().lower()
    email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(email_regex, email_clean):
        return {"success": False, "message": "Invalid email format"}, 400

    # 2. Validate Role
    norm_role = normalize_role(role)
    if not norm_role:
        return {
            "success": False,
            "message": f"Invalid role '{role}'. Allowed roles are: {', '.join(ALLOWED_ROLES)}"
        }, 400

    # 3. Validate Password
    if not password or not isinstance(password, str) or len(password.strip()) < 6:
        return {
            "success": False,
            "message": "Password is required and must be at least 6 characters long"
        }, 400

    db = get_db()

    # 4. Check if user already exists
    existing = list(
        db.collection(USERS_COLLECTION)
        .where(filter=FieldFilter("email", "==", email_clean))
        .limit(1)
        .stream()
    )
    if existing:
        return {
            "success": False,
            "message": f"User with email '{email_clean}' is already registered"
        }, 409

    # 5. Store Password as it is & Create User Record
    user_data = {
        "email": email_clean,
        "role": norm_role,
        "password": str(password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    doc_ref = db.collection(USERS_COLLECTION).document()
    doc_ref.set(user_data)

    return {
        "success": True,
        "message": "User registered successfully",
        "user": {
            "id": doc_ref.id,
            "email": email_clean,
            "role": norm_role,
            "created_at": user_data["created_at"]
        }
    }, 201


def login_user(email, password):
    """
    Authenticates user credentials against the 'users' collection.
    
    Parameters:
        email (str): User email address.
        password (str): Plaintext password.
        
    Returns:
        tuple: (result_dict, status_code)
    """
    if not email or not password:
        return {"success": False, "message": "Email and password are required"}, 400

    email_clean = str(email).strip().lower()
    input_pass = str(password)
    db = get_db()

    # Find user by email
    matches = list(
        db.collection(USERS_COLLECTION)
        .where(filter=FieldFilter("email", "==", email_clean))
        .limit(1)
        .stream()
    )

    if not matches:
        return {"success": False, "message": "Invalid email or password"}, 401

    user_doc = matches[0]
    user_data = user_doc.to_dict()
    stored_password = str(user_data.get("password", ""))

    # Compare directly as it is; fallback to check_password_hash if an existing hash is found
    is_valid = (stored_password == input_pass)
    if not is_valid and stored_password.startswith(("scrypt:", "pbkdf2:")):
        is_valid = check_password_hash(stored_password, input_pass)

    if not is_valid:
        return {"success": False, "message": "Invalid email or password"}, 401

    return {
        "success": True,
        "message": "Login successful",
        "user": {
            "id": user_doc.id,
            "email": user_data.get("email"),
            "role": user_data.get("role")
        }
    }, 200
