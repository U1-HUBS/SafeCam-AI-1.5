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

def test_clip_generation_with_downscaling_and_callback():
    db = SessionLocal()
    cam = db.query(Camera).first()
    if not cam:
        cam = Camera(name="Clip Test Cam 2", location="Zone B", stream_url="dummy2.mp4")
        db.add(cam)
        db.commit()

    import uuid
    incident = Incident(
        public_id=f"INC-HD-{uuid.uuid4().hex[:6].upper()}",
        camera_id=cam.id,
        category="Suspected Assault",
        severity="Critical",
        clip_status="PENDING"
    )
    db.add(incident)
    db.commit()
    inc_id = incident.id
    db.close()

    # Generate 1080p frames (1080, 1920, 3) to test resolution clamping
    frames = []
    base_t = time.time()
    for i in range(20):
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img[:] = (20, 40, i * 10)
        frames.append((base_t + i * (1.0 / 30.0), img))

    callback_events = []
    def on_event(evt):
        callback_events.append(evt)

    t0 = time.time()
    success = save_incident_clip(inc_id, frames, fps=30.0, event_callback=on_event)
    duration = time.time() - t0

    assert success is True
    # Clamped encoding should finish rapidly
    assert duration < 5.0

    # Verify event callback fired
    assert len(callback_events) == 1
    assert callback_events[0]["type"] == "incident.clip_ready"
    assert callback_events[0]["incident_id"] == inc_id

    # Verify clip resolution in metadata event or inspect video
    db = SessionLocal()
    refreshed = db.query(Incident).filter(Incident.id == inc_id).first()
    assert refreshed.clip_status == "READY"
    cap = cv2.VideoCapture(refreshed.clip_path)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec = ''.join([chr((fourcc_int >> (8 * i)) & 0xFF) for i in range(4)]).lower()
    cap.release()
    assert h <= 720
    assert codec in ['h264', 'avc1']
    db.close()

def test_ensure_clip_browser_playable():
    from backend.services.clip_service import ensure_clip_browser_playable
    # Create a non-h264 dummy video using mp4v/FMP4
    test_legacy = "storage/clips/test_legacy_fmp4.mp4"
    vw = cv2.VideoWriter(test_legacy, cv2.VideoWriter_fourcc(*'mp4v'), 15.0, (320, 240))
    for _ in range(10):
        vw.write(np.zeros((240, 320, 3), dtype=np.uint8))
    vw.release()

    # Transcode it to H.264
    success = ensure_clip_browser_playable(test_legacy)
    assert success is True

    # Verify it is now H264
    cap = cv2.VideoCapture(test_legacy)
    fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec = ''.join([chr((fourcc_int >> (8 * i)) & 0xFF) for i in range(4)]).lower()
    cap.release()
    assert codec in ['h264', 'avc1']

    if os.path.exists(test_legacy):
        os.remove(test_legacy)


