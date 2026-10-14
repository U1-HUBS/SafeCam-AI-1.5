#!/usr/bin/env python3
"""
Safecam AI Database Reset and Seeding Utility

Drops all database tables, recreates schema cleanly, and seeds default user
accounts (Admin, Supervisor, Security) with role-based access control.
Optionally seeds default cameras or sample reviewed incidents.
"""

import sys
import os
import shutil
import argparse
import datetime
from pathlib import Path

# Add project root to sys.path so 'backend.*' imports resolve cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database import engine, Base, SessionLocal
from backend.models import (
    User,
    Camera,
    Incident,
    IncidentReview,
    IncidentEvent,
    AiPrediction
)
from backend.config import (
    SAMPLE_VIDEOS_DIR,
    CLIPS_DIR,
    THUMBNAILS_DIR,
    STORAGE_DIR
)


def seed_users(db) -> list[User]:
    """Seeds standard role-based user accounts."""
    users = [
        User(
            username="admin",
            email="admin@sentinel.local",
            name="System Administrator",
            role="admin",
            active=True,
        ),
        User(
            username="supervisor",
            email="supervisor@sentinel.local",
            name="Shift Supervisor",
            role="supervisor",
            active=True,
        ),
        User(
            username="security",
            email="security@sentinel.local",
            name="Security Officer",
            role="security",
            active=True,
        ),
    ]

    users[0].set_password("admin123")
    users[1].set_password("super123")
    users[2].set_password("sec123")

    db.add_all(users)
    db.commit()
    for u in users:
        db.refresh(u)
    return users


def seed_cameras(db) -> list[Camera]:
    """Seeds default simulation cameras."""
    sample_video_path = str(SAMPLE_VIDEOS_DIR / "sample_hallway.mp4")

    # If sample video is missing, generate it if possible
    if not os.path.exists(sample_video_path):
        gen_script = ROOT_DIR / "sample_videos" / "generate_sample.py"
        if gen_script.exists():
            try:
                import subprocess
                subprocess.run([sys.executable, str(gen_script)], check=True)
            except Exception as e:
                print(f"[Warning] Could not auto-generate sample video: {e}")

    cams = [
        Camera(
            name="Camera 01 - Main Entrance",
            location="Building A - Gate",
            stream_url=sample_video_path,
            is_simulation=True,
            loop_simulation=True,
            enabled=True,
            ai_enabled=True,
            sampling_rate=2,
            sensitivity=0.25,
            status="OFFLINE"
        ),
        Camera(
            name="Camera 02 - North Hallway",
            location="Building B - Floor 2",
            stream_url=sample_video_path,
            is_simulation=True,
            loop_simulation=True,
            enabled=True,
            ai_enabled=True,
            sampling_rate=2,
            sensitivity=0.25,
            status="OFFLINE"
        ),
        Camera(
            name="Camera 03 - Cafeteria Courtyard",
            location="Campus Center",
            stream_url=sample_video_path,
            is_simulation=True,
            loop_simulation=True,
            enabled=True,
            ai_enabled=True,
            sampling_rate=2,
            sensitivity=0.25,
            status="OFFLINE"
        ),
        Camera(
            name="Camera 04 - East Playground",
            location="Athletic Zone",
            stream_url=sample_video_path,
            is_simulation=True,
            loop_simulation=True,
            enabled=True,
            ai_enabled=True,
            sampling_rate=2,
            sensitivity=0.25,
            status="OFFLINE"
        ),
    ]

    db.add_all(cams)
    db.commit()
    for c in cams:
        db.refresh(c)
    return cams


def seed_sample_incidents(db, cameras: list[Camera]) -> list[Incident]:
    """Seeds sample incidents and reviews for testing analytics and training UI."""
    if not cameras:
        return []

    utc_now = datetime.datetime.now(datetime.timezone.utc)
    cam1 = cameras[0]
    cam2 = cameras[1] if len(cameras) > 1 else cameras[0]

    inc1 = Incident(
        public_id=f"inc-seed-01",
        camera_id=cam1.id,
        category="Suspected Fight",
        raw_ai_label="violent fight with kicking and punching contact",
        severity="Critical",
        peak_confidence=0.88,
        average_confidence=0.74,
        status="RESOLVED",
        started_at=utc_now - datetime.timedelta(hours=2),
        detected_at=utc_now - datetime.timedelta(hours=2) + datetime.timedelta(seconds=2),
        ended_at=utc_now - datetime.timedelta(hours=2) + datetime.timedelta(seconds=12),
        acknowledged_by="admin",
        acknowledged_at=utc_now - datetime.timedelta(hours=2) + datetime.timedelta(seconds=15),
    )

    inc2 = Incident(
        public_id=f"inc-seed-02",
        camera_id=cam2.id,
        category="Suspected Fight",
        raw_ai_label="physical punch or strike with hand contact",
        severity="Low",
        peak_confidence=0.36,
        average_confidence=0.29,
        status="RESOLVED",
        started_at=utc_now - datetime.timedelta(hours=1),
        detected_at=utc_now - datetime.timedelta(hours=1) + datetime.timedelta(seconds=1),
        ended_at=utc_now - datetime.timedelta(hours=1) + datetime.timedelta(seconds=10),
        acknowledged_by="security",
        acknowledged_at=utc_now - datetime.timedelta(hours=1) + datetime.timedelta(seconds=12),
    )

    db.add_all([inc1, inc2])
    db.commit()
    db.refresh(inc1)
    db.refresh(inc2)

    # Add reviews (1 confirmed violence, 1 false positive)
    rev1 = IncidentReview(
        incident_id=inc1.id,
        reviewer="admin",
        classification="Confirmed Violence",
        reason="Physical altercation between students",
        notes="Verified hallway fight. Security was dispatched.",
        reviewed_at=utc_now - datetime.timedelta(hours=2) + datetime.timedelta(minutes=5),
    )
    rev2 = IncidentReview(
        incident_id=inc2.id,
        reviewer="security",
        classification="False Positive",
        reason="Playful interaction / celebration",
        notes="Students high-fived after exam. Non-violent.",
        reviewed_at=utc_now - datetime.timedelta(hours=1) + datetime.timedelta(minutes=3),
    )

    db.add_all([rev1, rev2])
    db.commit()
    return [inc1, inc2]


def clean_storage_media():
    """Removes recorded video clips and thumbnails from disk."""
    for folder, name in [(CLIPS_DIR, "clips"), (THUMBNAILS_DIR, "thumbnails")]:
        if folder.exists():
            count = 0
            for item in folder.iterdir():
                if item.is_file():
                    try:
                        item.unlink()
                        count += 1
                    except Exception:
                        pass
            print(f"[*] Cleaned {count} files from storage/{name}/")


def reset_database(
    users_only: bool = False,
    clean_media: bool = False,
    with_samples: bool = False
) -> dict:
    """
    Core database reset and seeding workflow.
    Returns dictionary with counts of seeded entities.
    """
    print("[*] Dropping all existing database tables...")
    # Explicitly close all lingering connections in pool
    engine.dispose()
    Base.metadata.drop_all(bind=engine)

    print("[*] Recreating clean database schema...")
    Base.metadata.create_all(bind=engine)

    if clean_media:
        clean_storage_media()

    db = SessionLocal()
    try:
        print("[*] Seeding default user accounts...")
        users = seed_users(db)
        print(f"    -> Seeded {len(users)} users (admin, supervisor, security).")

        cameras = []
        if not users_only:
            print("[*] Seeding default cameras...")
            cameras = seed_cameras(db)
            print(f"    -> Seeded {len(cameras)} cameras.")

        samples = []
        if with_samples and cameras:
            print("[*] Seeding sample incidents and reviews...")
            samples = seed_sample_incidents(db, cameras)
            print(f"    -> Seeded {len(samples)} sample reviewed incidents.")

        return {
            "users": len(users),
            "cameras": len(cameras),
            "samples": len(samples)
        }
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Reset and seed Safecam AI surveillance database."
    )
    parser.add_argument(
        "--users-only",
        action="store_true",
        help="Only seed user accounts (do not seed cameras or incidents)."
    )
    parser.add_argument(
        "--clean-media",
        action="store_true",
        help="Remove generated video clips and thumbnails from disk."
    )
    parser.add_argument(
        "--with-samples",
        action="store_true",
        help="Seed sample reviewed incidents for testing reports and model training."
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip interactive confirmation prompt."
    )

    args = parser.parse_args()

    print("==================================================")
    print("     Safecam AI Database Reset & Seeding Utility  ")
    print("==================================================")

    if not args.yes:
        confirm = input("WARNING: This will erase all existing database records. Proceed? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Operation cancelled by user.")
            sys.exit(0)

    try:
        results = reset_database(
            users_only=args.users_only,
            clean_media=args.clean_media,
            with_samples=args.with_samples
        )
        print("==================================================")
        print("Database reset & seeding completed successfully!")
        print(f"  * Users:   {results['users']} (admin, supervisor, security)")
        print(f"  * Cameras: {results['cameras']}")
        print(f"  * Samples: {results['samples']}")
        print("==================================================")
        print("Default credentials:")
        print("  - Admin:      admin / admin123")
        print("  - Supervisor: supervisor / super123")
        print("  - Security:   security / sec123")
        print("==================================================")
    except Exception as e:
        print(f"[ERROR] Database reset failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
