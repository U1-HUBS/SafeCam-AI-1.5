import time
import os
import torch
import pytest
from pathlib import Path

from backend.app import create_app
from backend.database import SessionLocal, Base, engine
from backend.models import Camera, Incident, IncidentReview
from backend.services.training_service import (
    SafeCamViolenceHead,
    TrainingDatasetManager,
    InAppModelTrainer,
    trainer_service,
    dataset_manager,
)


@pytest.fixture
def client():
    app, sm = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        token = resp.get_json()["token"]
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        yield client


def test_safecam_violence_head_forward():
    """Verify SafeCamViolenceHead architecture and forward pass on 1D and 2D tensors."""
    head = SafeCamViolenceHead(in_features=512)
    head.eval()

    # Test 1D vector (single frame feature)
    vec_1d = torch.randn(512)
    out_1d = head(vec_1d)
    assert out_1d.shape == torch.Size([1])
    assert 0.0 <= out_1d.item() <= 1.0

    # Test 2D batch
    batch_2d = torch.randn(8, 512)
    out_2d = head(batch_2d)
    assert out_2d.shape == torch.Size([8, 1])
    assert torch.all(out_2d >= 0.0) and torch.all(out_2d <= 1.0)


def test_dataset_manager_stats_and_gather():
    """Verify dataset manager statistics and sample gathering."""
    db = SessionLocal()
    try:
        # Create a test camera
        cam = db.query(Camera).first()
        if not cam:
            cam = Camera(name="Training Test Cam", location="Test Wing", stream_url="sample.mp4")
            db.add(cam)
            db.commit()

        import uuid
        # Seed 1 confirmed violence and 1 false positive incident
        inc1 = Incident(
            public_id=f"inc-{uuid.uuid4().hex[:8]}",
            camera_id=cam.id,
            category="Suspected Fight",
            severity="High",
            status="confirmed",
            peak_confidence=0.88,
        )
        inc2 = Incident(
            public_id=f"inc-{uuid.uuid4().hex[:8]}",
            camera_id=cam.id,
            category="Suspected Fight",
            severity="Low",
            status="false_positive",
            peak_confidence=0.35,
        )
        db.add_all([inc1, inc2])
        db.commit()

        rev1 = IncidentReview(
            incident_id=inc1.id,
            reviewer="Admin",
            classification="Confirmed Violence",
            reason="Aggressive physical push",
        )
        rev2 = IncidentReview(
            incident_id=inc2.id,
            reviewer="Admin",
            classification="False Positive",
            reason="Two students high fiving",
        )
        db.add_all([rev1, rev2])
        db.commit()

        mgr = TrainingDatasetManager()
        stats = mgr.get_audit_dataset_stats()
        assert stats["total_reviewed"] >= 2
        assert stats["confirmed_violence"] >= 1
        assert stats["false_positives"] >= 1
        assert "active_model" in stats

        samples = mgr.gather_audited_samples()
        assert len(samples) >= 2
        labels = [s["label"] for s in samples]
        assert 1 in labels
        assert 0 in labels
    finally:
        db.close()


def test_in_app_trainer_execution(monkeypatch):
    """Verify InAppModelTrainer runs to completion, saves weights, and triggers callbacks."""
    monkeypatch.setenv("FAST_TRAINING", "1")
    trainer = InAppModelTrainer()
    reloaded_paths = []

    def dummy_callback(path: str):
        reloaded_paths.append(path)

    trainer.register_on_complete(dummy_callback)

    started = trainer.start_training()
    assert started is True

    # Check status during training
    status_active = trainer.get_status()
    assert status_active["status"] in ["EXTRACTING", "ENCODING", "TRAINING", "EVALUATING", "COMPLETED"]

    # Wait for completion (fast on synthetic/CPU calibration samples)
    for _ in range(120):
        time.sleep(0.2)
        st = trainer.get_status()
        if not st["is_training"]:
            break

    final_status = trainer.get_status()
    assert final_status["status"] == "COMPLETED"
    assert final_status["progress_percent"] == 100
    assert final_status["metrics"] is not None
    assert final_status["metrics"]["accuracy"] > 0
    assert len(reloaded_paths) == 1
    assert os.path.exists(reloaded_paths[0])


def test_training_api_endpoints(client):
    """Verify all REST API endpoints under /api/training."""
    # 1. GET /api/training/stats
    resp = client.get("/api/training/stats")
    assert resp.status_code == 200
    stats = resp.get_json()
    assert "total_reviewed" in stats
    assert "active_model" in stats

    # 2. GET /api/training/status
    resp = client.get("/api/training/status")
    assert resp.status_code == 200
    status_info = resp.get_json()
    assert "is_training" in status_info
    assert "progress_percent" in status_info

    # 3. POST /api/training/export
    resp = client.post("/api/training/export")
    assert resp.status_code == 200
    export_data = resp.get_json()
    assert export_data["success"] is True
    assert "export_id" in export_data
    export_id = export_data["export_id"]

    # 4. GET /api/training/download/<id>
    resp = client.get(f"/api/training/download/{export_id}")
    assert resp.status_code == 200
    assert resp.headers.get("Content-Type") == "application/zip"
