import subprocess
import sys
from pathlib import Path
import pytest

from backend.database import SessionLocal
from backend.models import User, Camera, Incident, IncidentReview
from scripts.reset_db import reset_database, ROOT_DIR


def test_reset_database_users_only():
    """Verify reset_database in users_only mode resets schema and seeds 3 users."""
    res = reset_database(users_only=True, clean_media=False, with_samples=False)
    assert res["users"] == 3
    assert res["cameras"] == 0
    assert res["samples"] == 0

    db = SessionLocal()
    try:
        users = db.query(User).all()
        assert len(users) == 3
        user_map = {u.username: u for u in users}

        assert "admin" in user_map
        assert user_map["admin"].role == "admin"
        assert user_map["admin"].check_password("admin123") is True
        assert user_map["admin"].check_password("wrong") is False

        assert "supervisor" in user_map
        assert user_map["supervisor"].role == "supervisor"
        assert user_map["supervisor"].check_password("super123") is True

        assert "security" in user_map
        assert user_map["security"].role == "security"
        assert user_map["security"].check_password("sec123") is True

        # Ensure no cameras were created
        cameras = db.query(Camera).all()
        assert len(cameras) == 0
    finally:
        db.close()


def test_reset_database_with_default_cameras():
    """Verify reset_database seeds both users and default cameras."""
    res = reset_database(users_only=False, clean_media=False, with_samples=False)
    assert res["users"] == 3
    assert res["cameras"] == 4
    assert res["samples"] == 0

    db = SessionLocal()
    try:
        assert db.query(User).count() == 3
        cameras = db.query(Camera).all()
        assert len(cameras) == 4
        cam_names = [c.name for c in cameras]
        assert "Camera 01 - Main Entrance" in cam_names
        assert "Camera 02 - North Hallway" in cam_names
        assert "Camera 03 - Cafeteria Courtyard" in cam_names
        assert "Camera 04 - East Playground" in cam_names
    finally:
        db.close()


def test_reset_database_with_samples():
    """Verify reset_database with_samples flag seeds reviewed test incidents."""
    res = reset_database(users_only=False, clean_media=False, with_samples=True)
    assert res["users"] == 3
    assert res["cameras"] == 4
    assert res["samples"] == 2

    db = SessionLocal()
    try:
        incidents = db.query(Incident).all()
        assert len(incidents) == 2

        reviews = db.query(IncidentReview).all()
        assert len(reviews) == 2
        classes = [r.classification for r in reviews]
        assert "Confirmed Violence" in classes
        assert "False Positive" in classes
    finally:
        db.close()


def test_cli_execution():
    """Verify scripts/reset_db.py can be invoked via CLI with flags."""
    script_path = ROOT_DIR / "scripts" / "reset_db.py"
    proc = subprocess.run(
        [sys.executable, str(script_path), "--users-only", "--yes"],
        capture_output=True,
        text=True,
        cwd=str(ROOT_DIR)
    )
    assert proc.returncode == 0
    assert "Database reset & seeding completed successfully!" in proc.stdout
    assert "Users:   3" in proc.stdout
    assert "Cameras: 0" in proc.stdout
