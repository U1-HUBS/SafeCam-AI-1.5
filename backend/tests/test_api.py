import pytest
from backend.app import create_app
from backend.database import SessionLocal, Base, engine
from backend.models import Camera, Incident

@pytest.fixture
def client():
    app, sm = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
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
