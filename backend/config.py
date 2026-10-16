import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
BACKEND_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
CLIPS_DIR = STORAGE_DIR / "clips"
THUMBNAILS_DIR = STORAGE_DIR / "thumbnails"
SAMPLE_VIDEOS_DIR = BASE_DIR / "sample_videos"
UPLOADS_DIR = STORAGE_DIR / "uploads"

MODELS_DIR = STORAGE_DIR / "models"
DATASETS_DIR = STORAGE_DIR / "datasets"

# Ensure storage directories exist
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
DATASETS_DIR.mkdir(parents=True, exist_ok=True)

# Upload constraints
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}
MAX_UPLOAD_SIZE_BYTES = 250 * 1024 * 1024  # 250 MB


def resolve_stream_source(stream_url: str):
    """
    Resolves a camera stream URL or video path to an absolute path if it is a local file.
    Network streams (RTSP, HTTP, HTTPS) and device IDs are preserved.
    """
    if not stream_url:
        return stream_url
    stream_str = str(stream_url).strip()
    if stream_str.isdigit():
        return int(stream_str)
    lower = stream_str.lower()
    if lower.startswith(("rtsp://", "rtsps://", "http://", "https://")):
        return stream_str
    p = Path(stream_str)
    if not p.is_absolute():
        p = BASE_DIR / p
    return str(p)

def _normalize_database_url(url: str | None) -> str:
    if not url:
        db_file = STORAGE_DIR / "cctv_sentinel.db"
        db_file.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_file.as_posix()}"

    if url.startswith("sqlite:///"):
        path_part = url[len("sqlite:///"):].strip()
        if path_part == ":memory:":
            return url
        p = Path(path_part)
        if not p.is_absolute() and not (len(path_part) > 1 and path_part[1] == ":"):
            p = (BASE_DIR / p).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{p.as_posix()}"

    return url

DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL"))

# Default AI & Aggregation Configuration
DEFAULT_AI_THRESHOLD = float(os.getenv("DEFAULT_AI_THRESHOLD", "0.25"))
DEFAULT_SAMPLING_RATE = int(os.getenv("DEFAULT_SAMPLING_RATE", "2"))  # FPS sampled for AI
DEFAULT_PRE_BUFFER_SECONDS = int(os.getenv("DEFAULT_PRE_BUFFER_SECONDS", "4"))
DEFAULT_POST_BUFFER_SECONDS = int(os.getenv("DEFAULT_POST_BUFFER_SECONDS", "4"))
CLIP_MAX_HEIGHT = int(os.getenv("CLIP_MAX_HEIGHT", "720"))
CLIP_TARGET_FPS = float(os.getenv("CLIP_TARGET_FPS", "15.0"))
DEFAULT_ROLLING_WINDOW_SECONDS = int(os.getenv("DEFAULT_ROLLING_WINDOW_SECONDS", "6"))
DEFAULT_POSITIVE_RATIO = float(os.getenv("DEFAULT_POSITIVE_RATIO", "0.50"))
DEFAULT_MIN_POSITIVE_FRAMES = int(os.getenv("DEFAULT_MIN_POSITIVE_FRAMES", "3"))
DEFAULT_COOLDOWN_SECONDS = int(os.getenv("DEFAULT_COOLDOWN_SECONDS", "20"))

# Violence Detection Accuracy & Spatiotemporal Fusion Tuning
DEFAULT_KINETIC_WEIGHT = float(os.getenv("DEFAULT_KINETIC_WEIGHT", "0.35"))
DEFAULT_VISUAL_WEIGHT = float(os.getenv("DEFAULT_VISUAL_WEIGHT", "0.65"))
DEFAULT_EMA_ALPHA = float(os.getenv("DEFAULT_EMA_ALPHA", "0.40"))
DEFAULT_MIN_SUSTAINED_SECONDS = float(os.getenv("DEFAULT_MIN_SUSTAINED_SECONDS", "1.5"))
DEFAULT_MOTION_GATE_THRESHOLD = float(os.getenv("DEFAULT_MOTION_GATE_THRESHOLD", "0.04"))

# Multi-Person & Physical Contact Gating
REQUIRE_MULTI_PERSON_FOR_VIOLENCE = bool(os.getenv("REQUIRE_MULTI_PERSON_FOR_VIOLENCE", "False") == "True")
REQUIRE_PHYSICAL_CONTACT_FOR_VIOLENCE = bool(os.getenv("REQUIRE_PHYSICAL_CONTACT_FOR_VIOLENCE", "False") == "True")
CONTACT_MARGIN_PIXELS = int(os.getenv("CONTACT_MARGIN_PIXELS", "20"))

# Authentication & RBAC Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "sentinel-jwt-secret-key-2026-cctv")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

