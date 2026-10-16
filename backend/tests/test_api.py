import pytest
from backend.app import create_app
from backend.database import SessionLocal, Base, engine
from backend.models import Camera, Incident

@pytest.fixture
def client():
    app, sm = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Authenticate as admin by default for regression test suite
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        token = resp.get_json()["token"]
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        yield client


def test_camera_crud(client):
    # 1. Create camera
    new_cam = {
        "name": "Test Science Hall",
        "location": "Science Wing",
        "stream_url": "test_stream.mp4",
        "is_simulation": True,
        "sampling_rate": 2,
        "sensitivity": 0.3
    }
    resp = client.post("/api/cameras", json=new_cam)
    assert resp.status_code == 201
    data = resp.get_json()
    cam_id = data["id"]
    assert data["name"] == "Test Science Hall"

    # 2. Get camera
    resp = client.get(f"/api/cameras/{cam_id}")
    assert resp.status_code == 200
    assert resp.get_json()["location"] == "Science Wing"

    # 3. Update camera
    resp = client.put(f"/api/cameras/{cam_id}", json={"name": "Updated Science Hall"})
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Updated Science Hall"

    # 4. Delete camera
    resp = client.delete(f"/api/cameras/{cam_id}")
    assert resp.status_code == 200

    # 5. Confirm deletion
    resp = client.get(f"/api/cameras/{cam_id}")
    assert resp.status_code == 404

def test_incident_acknowledge_and_review(client):
    # Seed an incident directly in DB
    db = SessionLocal()
    cam = db.query(Camera).first()
    if not cam:
        cam = Camera(name="Test Cam", location="Test Loc", stream_url="fake.mp4")
        db.add(cam)
        db.commit()

    import uuid
    inc = Incident(
        public_id=f"INC-TEST-{uuid.uuid4().hex[:6].upper()}",
        camera_id=cam.id,
        category="Suspected Fight",
        raw_ai_label="a physical fight between people",
        severity="High",
        peak_confidence=0.78,
        average_confidence=0.72,
        status="AWAITING_REVIEW"
    )
    db.add(inc)
    db.commit()
    inc_id = inc.id
    db.close()

    # 1. List incidents
    resp = client.get("/api/incidents")
    assert resp.status_code == 200
    items = resp.get_json()
    assert any(i["id"] == inc_id for i in items)

    # 2. Acknowledge incident
    resp = client.post(f"/api/incidents/{inc_id}/acknowledge", json={"operator": "Officer Dave"})
    assert resp.status_code == 200
    assert resp.get_json()["acknowledged_by"] == "Officer Dave"

    # 3. Submit Review (Confirmed Violence)
    resp = client.post(f"/api/incidents/{inc_id}/review", json={
        "classification": "Confirmed Violence",
        "reviewer": "Principal Martinez",
        "reason": "Physical altercation confirmed",
        "notes": "Followed up with school resource officer."
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "RESOLVED"

    # 4. Check summary report
    resp = client.get("/api/reports/summary")
    assert resp.status_code == 200
    rep = resp.get_json()
    assert rep["total_alerts"] >= 1
    assert rep["confirmed_violence"] >= 1


def test_incident_preserved_when_camera_deleted(client):
    # 1. Create a dedicated test camera
    new_cam = {
        "name": "Gym Annex Cam",
        "location": "Gymnasium West",
        "stream_url": "test_gym.mp4",
        "is_simulation": True,
    }
    resp = client.post("/api/cameras", json=new_cam)
    assert resp.status_code == 201
    cam_id = resp.get_json()["id"]

    # 2. Add an incident associated with this camera
    import uuid
    public_id = f"INC-GYM-{uuid.uuid4().hex[:6].upper()}"
    db = SessionLocal()
    inc = Incident(
        public_id=public_id,
        camera_id=cam_id,
        camera_name="Gym Annex Cam",
        camera_location="Gymnasium West",
        category="Physical Aggression",
        severity="High",
        peak_confidence=0.85,
        status="AWAITING_REVIEW"
    )
    db.add(inc)
    db.commit()
    inc_id = inc.id
    db.close()

    # Verify incident exists and has camera name
    resp = client.get(f"/api/incidents/{inc_id}")
    assert resp.status_code == 200
    assert resp.get_json()["camera_name"] == "Gym Annex Cam"
    assert resp.get_json()["camera_location"] == "Gymnasium West"

    # 3. Delete/remove camera from live monitoring
    del_resp = client.delete(f"/api/cameras/{cam_id}")
    assert del_resp.status_code == 200
    assert "preserved" in del_resp.get_json()["message"]

    # 4. Confirm camera is no longer returned in active camera list
    cams_resp = client.get("/api/cameras")
    assert cams_resp.status_code == 200
    active_cam_ids = [c["id"] for c in cams_resp.get_json()]
    assert cam_id not in active_cam_ids

    # 5. Confirm the incident was NOT deleted and is still returned!
    inc_resp = client.get(f"/api/incidents/{inc_id}")
    assert inc_resp.status_code == 200
    inc_data = inc_resp.get_json()
    assert inc_data["id"] == inc_id
    assert inc_data["public_id"] == public_id
    assert inc_data["camera_name"] == "Gym Annex Cam"
    assert inc_data["camera_location"] == "Gymnasium West"

    # 6. Verify incident is still in active queue (/api/incidents?status=AWAITING_REVIEW)
    queue_resp = client.get("/api/incidents?status=AWAITING_REVIEW")
    assert queue_resp.status_code == 200
    queue_ids = [i["id"] for i in queue_resp.get_json()]
    assert inc_id in queue_ids

    # 7. Verify incident can still be reviewed
    rev_resp = client.post(f"/api/incidents/{inc_id}/review", json={
        "classification": "Confirmed Violence",
        "reviewer": "Officer Dave",
        "reason": "Gym altercation confirmed"
    })
    assert rev_resp.status_code == 200
    assert rev_resp.get_json()["status"] == "RESOLVED"

