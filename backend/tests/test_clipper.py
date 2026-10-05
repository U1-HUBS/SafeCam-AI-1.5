import os
import time
import cv2
import numpy as np
import pytest
from backend.services.clip_service import save_incident_clip
from backend.database import SessionLocal
from backend.models import Camera, Incident

def test_clip_generation():
    db = SessionLocal()
    cam = db.query(Camera).first()
    if not cam:
        cam = Camera(name="Clip Test Cam", location="Zone A", stream_url="dummy.mp4")
        db.add(cam)
        db.commit()

    import uuid
    incident = Incident(
        public_id=f"INC-CLIP-{uuid.uuid4().hex[:6].upper()}",
        camera_id=cam.id,
        category="Suspected Fight",
        severity="High",
        clip_status="PENDING"
    )
    db.add(incident)
    db.commit()
    inc_id = incident.id
    db.close()

    # Generate 30 dummy frames
    frames = []
    for i in range(30):
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        img[:] = (i * 5, 100, 150)
        frames.append((time.time() + i * 0.1, img))

    success = save_incident_clip(inc_id, frames, fps=10.0)
    assert success is True

    db = SessionLocal()
    refreshed = db.query(Incident).filter(Incident.id == inc_id).first()
    assert refreshed.clip_status == "READY"
    assert refreshed.clip_path is not None
    assert os.path.exists(refreshed.clip_path)
    assert refreshed.thumbnail_path is not None
    assert os.path.exists(refreshed.thumbnail_path)
    db.close()
