from flask import Blueprint, request, jsonify
from Module2.services.user_service import register_user, login_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api")


@auth_bp.route("/register", methods=["POST"])
@auth_bp.route("/auth/register", methods=["POST"])
def register_endpoint():
    """
    User registration endpoint.
    Accepts JSON or multipart/form-data with:
        - email: user's email
        - role: 'SSB', 'Investigator', or 'Admin'
        - password: minimum 6 characters
    """
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email") or request.form.get("email")
        role = data.get("role") or request.form.get("role")
        password = data.get("password") or request.form.get("password")

        result, status_code = register_user(email, role, password)
        return jsonify(result), status_code

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "Registration failed due to server error",
            "error": str(e)
        }), 500


@auth_bp.route("/login", methods=["POST"])
@auth_bp.route("/auth/login", methods=["POST"])
def login_endpoint():
    """
    User login endpoint.
    Accepts JSON or multipart/form-data with:
        - email: user's email
        - password: user's password
    """
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email") or request.form.get("email")
        password = data.get("password") or request.form.get("password")

        result, status_code = login_user(email, password)
        return jsonify(result), status_code

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "Login failed due to server error",
            "error": str(e)
        }), 500

