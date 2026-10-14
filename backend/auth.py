import datetime
from functools import wraps
import jwt
from flask import request, jsonify, g

from backend.config import JWT_SECRET_KEY, JWT_EXPIRY_HOURS
from backend.database import SessionLocal
from backend.models import User


def generate_token(user: User) -> str:
    """
    Generates a signed JWT token containing user identity and role.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "iat": now,
        "exp": now + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """
    Decodes and validates a JWT token. Raises exceptions on failure.
    """
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])


def extract_token_from_request() -> str | None:
    """
    Extracts JWT from Authorization header (Bearer token) or ?token= query parameter.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    
    # Also support query parameter for HTML5 media / stream tags
    token_param = request.args.get("token")
    if token_param:
        return token_param.strip()

    return None


def authenticate_request():
    """
    Validates token and attaches active user to flask.g.current_user.
    Returns (user, None) on success or (None, (error_dict, status_code)) on failure.
    """
    token = extract_token_from_request()
    if not token:
        return None, ({"error": "Authentication token missing"}, 401)

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        return None, ({"error": "Token has expired, please log in again"}, 401)
    except jwt.InvalidTokenError:
        return None, ({"error": "Invalid authentication token"}, 401)

    raw_sub = payload.get("sub")
    if not raw_sub:
        return None, ({"error": "Invalid token subject"}, 401)
    user_id = int(raw_sub)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.active:
            return None, ({"error": "User account inactive or not found"}, 401)
        # Detach user representation for request context
        g.current_user = user
        return user, None
    finally:
        db.close()


def login_required(f):
    """
    Decorator requiring valid user authentication.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user, err = authenticate_request()
        if err:
            return jsonify(err[0]), err[1]
        return f(*args, **kwargs)
    return decorated


def roles_required(*allowed_roles):
    """
    Decorator requiring valid user authentication AND membership in allowed_roles.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user, err = authenticate_request()
            if err:
                return jsonify(err[0]), err[1]

            if user.role not in allowed_roles:
                return jsonify({
                    "error": f"Access forbidden. Required role: {', '.join(allowed_roles)}. Your role: {user.role}"
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator
