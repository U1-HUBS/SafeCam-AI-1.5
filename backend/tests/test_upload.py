import io
import os
import tempfile
from pathlib import Path
import cv2
import numpy as np
import pytest

from backend.app import create_app
from backend.config import BASE_DIR, UPLOADS_DIR

@pytest.fixture
def client():
    app, sm = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Authenticate as admin by default for upload tests
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        token = resp.get_json()["token"]
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        yield client


def generate_temp_mp4(frames_count: int = 15, fps: int = 20, width: int = 320, height: int = 240) -> bytes:
    """Helper to generate an in-memory valid MP4 video."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))
        for i in range(frames_count):
            frame = np.full((height, width, 3), (i * 15) % 255, dtype=np.uint8)
            cv2.putText(frame, f"F{i}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            out.write(frame)
        out.release()

        with open(tmp_path, "rb") as f:
            data = f.read()
        return data
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_upload_valid_video(client):
    video_bytes = generate_temp_mp4(frames_count=20, fps=20, width=320, height=240)
    data = {
        "file": (io.BytesIO(video_bytes), "cafeteria_cctv.mp4")
    }

    resp = client.post(
        "/api/cameras/upload",
        data=data,
        content_type="multipart/form-data"
    )
    assert resp.status_code == 201
    res = resp.get_json()
    assert res["success"] is True
    assert res["filename"] == "cafeteria_cctv.mp4"
    assert res["width"] == 320
    assert res["height"] == 240
    assert res["fps"] == 20.0
    assert res["frame_count"] == 20
    assert res["duration_seconds"] == 1.0
    assert res["stream_url"].startswith("storage/uploads/")

    # Verify file exists on disk
    file_path = BASE_DIR / res["stream_url"]
    assert file_path.exists()
    assert file_path.stat().st_size > 0

def test_upload_unsupported_extension(client):
    data = {
        "file": (io.BytesIO(b"fake text data"), "video.txt")
    }
    resp = client.post(
        "/api/cameras/upload",
        data=data,
        content_type="multipart/form-data"
    )
    assert resp.status_code == 400
    res = resp.get_json()
    assert "Unsupported video format" in res["error"]

def test_upload_corrupted_video(client):
    data = {
        "file": (io.BytesIO(b"THIS IS NOT A VALID MP4 FILE DATA"), "bad_file.mp4")
    }
    resp = client.post(
        "/api/cameras/upload",
        data=data,
        content_type="multipart/form-data"
    )
    assert resp.status_code == 400
    res = resp.get_json()
    assert "Failed to decode" in res["error"] or "readable frames" in res["error"]

def test_list_simulations(client):
    resp = client.get("/api/cameras/simulations")
    assert resp.status_code == 200
    sims = resp.get_json()
    assert isinstance(sims, list)
    # Check that at least the sample hallway preset is discovered
    preset_names = [s["name"] for s in sims if s["type"] == "preset"]
    assert any("Hallway" in name for name in preset_names)

def test_create_and_test_simulated_camera(client):
    video_bytes = generate_temp_mp4(frames_count=15, fps=15, width=320, height=240)
    upload_resp = client.post(
        "/api/cameras/upload",
        data={"file": (io.BytesIO(video_bytes), "sim_test.mp4")},
        content_type="multipart/form-data"
    )
    assert upload_resp.status_code == 201
    upload_data = upload_resp.get_json()

    # Create camera with this stream URL
    cam_payload = {
        "name": "Simulated Entrance Cam",
        "location": "Entrance Hall",
        "stream_url": upload_data["stream_url"],
        "is_simulation": True,
        "loop_simulation": True,
        "enabled": True,
        "ai_enabled": True
    }
    create_resp = client.post("/api/cameras", json=cam_payload)
    assert create_resp.status_code == 201
    cam_id = create_resp.get_json()["id"]

    # Test camera connectivity
    test_resp = client.post(f"/api/cameras/{cam_id}/test")
    assert test_resp.status_code == 200
    test_data = test_resp.get_json()
    assert test_data["connected"] is True
    assert test_data["status"] == "ONLINE"
