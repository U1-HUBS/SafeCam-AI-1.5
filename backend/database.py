import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_schema_migrations(target_engine=None):
    """
    Non-destructively verifies and adds newly introduced schema columns to existing databases
    so that historic data, alerts, and incidents are preserved without requiring a database wipe.
    """
    from sqlalchemy import inspect, text
    eng = target_engine or engine
    inspector = inspect(eng)
    table_names = inspector.get_table_names()

    with eng.begin() as conn:
        if "cameras" in table_names:
            camera_cols = [c["name"] for c in inspector.get_columns("cameras")]
            if "is_deleted" not in camera_cols:
                conn.execute(text("ALTER TABLE cameras ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))
            if "deleted_at" not in camera_cols:
                conn.execute(text("ALTER TABLE cameras ADD COLUMN deleted_at DATETIME"))

        if "incidents" in table_names:
            incident_cols = [c["name"] for c in inspector.get_columns("incidents")]
            if "camera_name" not in incident_cols:
                conn.execute(text("ALTER TABLE incidents ADD COLUMN camera_name VARCHAR(100)"))
            if "camera_location" not in incident_cols:
                conn.execute(text("ALTER TABLE incidents ADD COLUMN camera_location VARCHAR(150)"))

            # Backfill existing incidents with camera name and location if not yet populated
            try:
                conn.execute(text("""
                    UPDATE incidents
                    SET camera_name = (SELECT name FROM cameras WHERE cameras.id = incidents.camera_id),
                        camera_location = (SELECT location FROM cameras WHERE cameras.id = incidents.camera_id)
                    WHERE (camera_name IS NULL OR camera_location IS NULL)
                      AND camera_id IS NOT NULL
                      AND EXISTS (SELECT 1 FROM cameras WHERE cameras.id = incidents.camera_id)
                """))
            except Exception:
                pass

