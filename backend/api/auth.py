import datetime
from flask import Blueprint, request, jsonify, g
from sqlalchemy import or_

from backend.database import SessionLocal
from backend.models import User
from backend.auth import generate_token, login_required, roles_required

auth_bp = Blueprint("auth", __name__)

VALID_ROLES = {"admin", "supervisor", "security"}


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    identifier = data.get("username") or data.get("email")
    password = data.get("password")

    if not identifier or not password:
        return jsonify({"error": "Username/email and password are required"}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()

        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid username or password"}), 401

        if not user.active:
            return jsonify({"error": "Account has been deactivated. Contact an administrator."}), 403

        token = generate_token(user)
        return jsonify({
            "token": token,
            "user": user.to_dict()
        }), 200
    finally:
        db.close()


@auth_bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    return jsonify(g.current_user.to_dict()), 200


@auth_bp.route("/users", methods=["GET"])
@roles_required("admin")
def list_users():
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id.asc()).all()
        return jsonify([u.to_dict() for u in users]), 200
    finally:
        db.close()


@auth_bp.route("/users", methods=["POST"])
@roles_required("admin")
def create_user():
    data = request.json or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password")
    name = (data.get("name") or "").strip()
    role = (data.get("role") or "security").strip().lower()

    if not username or not email or not password or not name:
        return jsonify({"error": "Username, email, password, and name are required"}), 400

    if role not in VALID_ROLES:
        return jsonify({"error": f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}"}), 400

    db = SessionLocal()
    try:
        existing = db.query(User).filter(
            or_(User.username == username, User.email == email)
        ).first()
        if existing:
            return jsonify({"error": "Username or email is already registered"}), 409

        new_user = User(
            username=username,
            email=email,
            name=name,
            role=role,
            active=data.get("active", True),
        )
        new_user.set_password(password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return jsonify(new_user.to_dict()), 201
    finally:
        db.close()


@auth_bp.route("/users/<int:user_id>", methods=["PUT"])
@roles_required("admin")
def update_user(user_id):
    data = request.json or {}
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        if "name" in data and data["name"].strip():
            user.name = data["name"].strip()

        if "email" in data and data["email"].strip():
            email = data["email"].strip()
            # check conflict
            conflict = db.query(User).filter(User.email == email, User.id != user_id).first()
            if conflict:
                return jsonify({"error": "Email is already taken"}), 409
            user.email = email

        if "role" in data:
            role = data["role"].strip().lower()
            if role not in VALID_ROLES:
                return jsonify({"error": f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}"}), 400
            user.role = role

        if "active" in data:
            # Prevent disabling self
            if user_id == g.current_user.id and not data["active"]:
                return jsonify({"error": "Cannot deactivate your own administrator account"}), 400
            user.active = bool(data["active"])

        if "password" in data and data["password"]:
            user.set_password(data["password"])

        db.commit()
        db.refresh(user)
        return jsonify(user.to_dict()), 200
    finally:
        db.close()


@auth_bp.route("/users/<int:user_id>", methods=["DELETE"])
@roles_required("admin")
def delete_user(user_id):
    if user_id == g.current_user.id:
        return jsonify({"error": "Cannot delete your own administrator account"}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        db.delete(user)
        db.commit()
        return jsonify({"message": f"User '{user.username}' deleted successfully"}), 200
    finally:
        db.close()
