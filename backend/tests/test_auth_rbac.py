import pytest
import uuid
from backend.app import create_app
from backend.database import SessionLocal
from backend.models import Camera, Incident, User


@pytest.fixture
def app_and_client():
    app, sm = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def get_token_for(client, username, password):
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.get_data(as_text=True)}"
    data = resp.get_json()
    return data["token"]


def test_seed_users_and_login_success(app_and_client):
    client = app_and_client

    # Admin login
    admin_token = get_token_for(client, "admin", "admin123")
    assert admin_token is not None

    # Supervisor login
    super_token = get_token_for(client, "supervisor", "super123")
    assert super_token is not None

    # Security login
    sec_token = get_token_for(client, "security", "sec123")
    assert sec_token is not None

    # /api/auth/me check
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {sec_token}"})
    assert resp.status_code == 200
    user_info = resp.get_json()
    assert user_info["username"] == "security"
    assert user_info["role"] == "security"


def test_login_invalid_password(app_and_client):
    client = app_and_client
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert resp.status_code == 401
    assert "Invalid" in resp.get_json()["error"]


def test_unauthenticated_request_rejected(app_and_client):
    client = app_and_client
    resp = client.get("/api/cameras")
    assert resp.status_code == 401
    assert "missing" in resp.get_json()["error"].lower()


def test_admin_camera_crud(app_and_client):
    client = app_and_client
    admin_token = get_token_for(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create camera
    new_cam = {
        "name": "RBAC Test Camera",
        "location": "North Wing",
        "stream_url": "sample_videos/sample_hallway.mp4",
        "is_simulation": True,
    }
    resp = client.post("/api/cameras", json=new_cam, headers=headers)
    assert resp.status_code == 201
    cam_id = resp.get_json()["id"]

    # Read camera
    resp = client.get(f"/api/cameras/{cam_id}", headers=headers)
    assert resp.status_code == 200

    # Update camera
    resp = client.put(f"/api/cameras/{cam_id}", json={"name": "Updated RBAC Cam"}, headers=headers)
    assert resp.status_code == 200

    # Delete camera
    resp = client.delete(f"/api/cameras/{cam_id}", headers=headers)
    assert resp.status_code == 200


def test_supervisor_cannot_create_or_delete_camera(app_and_client):
    client = app_and_client
    super_token = get_token_for(client, "supervisor", "super123")
    headers = {"Authorization": f"Bearer {super_token}"}

    # Supervisor can read cameras
    resp = client.get("/api/cameras", headers=headers)
    assert resp.status_code == 200

    # Supervisor CANNOT create camera (403 Forbidden)
    resp = client.post("/api/cameras", json={"name": "Forbidden Cam", "stream_url": "url"}, headers=headers)
    assert resp.status_code == 403

    # Supervisor CANNOT delete camera (403 Forbidden)
    resp = client.delete("/api/cameras/1", headers=headers)
    assert resp.status_code == 403


def test_security_cannot_create_or_delete_camera(app_and_client):
    client = app_and_client
    sec_token = get_token_for(client, "security", "sec123")
    headers = {"Authorization": f"Bearer {sec_token}"}

    # Security can read cameras
    resp = client.get("/api/cameras", headers=headers)
    assert resp.status_code == 200

    # Security CANNOT create camera (403 Forbidden)
    resp = client.post("/api/cameras", json={"name": "Forbidden Cam", "stream_url": "url"}, headers=headers)
    assert resp.status_code == 403

    # Security CANNOT delete camera (403 Forbidden)
    resp = client.delete("/api/cameras/1", headers=headers)
    assert resp.status_code == 403


def test_security_can_acknowledge_and_review_incident(app_and_client):
    client = app_and_client
    sec_token = get_token_for(client, "security", "sec123")
    headers = {"Authorization": f"Bearer {sec_token}"}

    # Seed an incident
    db = SessionLocal()
    cam = db.query(Camera).first()
    if not cam:
        cam = Camera(name="Test Cam", location="Loc", stream_url="sample_videos/sample_hallway.mp4")
        db.add(cam)
        db.commit()

    inc = Incident(
        public_id=f"INC-{uuid.uuid4().hex[:6].upper()}",
        camera_id=cam.id,
        category="Suspected Violence",
        status="AWAITING_REVIEW",
    )
    db.add(inc)
    db.commit()
    inc_id = inc.id
    db.close()

    # Security acknowledges incident
    ack_resp = client.post(f"/api/incidents/{inc_id}/acknowledge", json={}, headers=headers)
    assert ack_resp.status_code == 200
    assert ack_resp.get_json()["acknowledged_by"] == "Security Officer"

    # Security reviews incident
    rev_resp = client.post(f"/api/incidents/{inc_id}/review", json={
        "classification": "Confirmed Violence",
        "reason": "Physical altercation detected",
        "notes": "Verified by Security Officer on duty."
    }, headers=headers)
    assert rev_resp.status_code == 200
    assert rev_resp.get_json()["status"] == "RESOLVED"


def test_reports_rbac(app_and_client):
    client = app_and_client
    admin_token = get_token_for(client, "admin", "admin123")
    super_token = get_token_for(client, "supervisor", "super123")
    sec_token = get_token_for(client, "security", "sec123")

    # Admin can access reports
    resp = client.get("/api/reports/summary", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200

    # Supervisor can access reports
    resp = client.get("/api/reports/summary", headers={"Authorization": f"Bearer {super_token}"})
    assert resp.status_code == 200

    # Security CANNOT access reports (403 Forbidden)
    resp = client.get("/api/reports/summary", headers={"Authorization": f"Bearer {sec_token}"})
    assert resp.status_code == 403


def test_user_management_rbac(app_and_client):
    client = app_and_client
    admin_token = get_token_for(client, "admin", "admin123")
    super_token = get_token_for(client, "supervisor", "super123")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    super_headers = {"Authorization": f"Bearer {super_token}"}

    # Supervisor cannot list users (403 Forbidden)
    resp = client.get("/api/auth/users", headers=super_headers)
    assert resp.status_code == 403

    # Admin can list users
    resp = client.get("/api/auth/users", headers=admin_headers)
    assert resp.status_code == 200
    users = resp.get_json()
    assert len(users) >= 3

    # Admin can create user
    new_user = {
        "username": f"testuser_{uuid.uuid4().hex[:4]}",
        "email": f"test_{uuid.uuid4().hex[:4]}@sentinel.local",
        "password": "password123",
        "name": "Test Officer",
        "role": "security"
    }
    resp = client.post("/api/auth/users", json=new_user, headers=admin_headers)
    assert resp.status_code == 201
    created_id = resp.get_json()["id"]

    # Admin can update user role
    resp = client.put(f"/api/auth/users/{created_id}", json={"role": "supervisor"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.get_json()["role"] == "supervisor"

    # Admin can delete user
    resp = client.delete(f"/api/auth/users/{created_id}", headers=admin_headers)
    assert resp.status_code == 200
