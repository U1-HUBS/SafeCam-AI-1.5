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

# Ensure storage directories exist
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{STORAGE_DIR / 'cctv_sentinel.db'}")

# Default AI & Aggregation Configuration
DEFAULT_AI_THRESHOLD = float(os.getenv("DEFAULT_AI_THRESHOLD", "0.25"))
DEFAULT_SAMPLING_RATE = int(os.getenv("DEFAULT_SAMPLING_RATE", "2"))  # FPS sampled for AI
DEFAULT_PRE_BUFFER_SECONDS = int(os.getenv("DEFAULT_PRE_BUFFER_SECONDS", "8"))
DEFAULT_POST_BUFFER_SECONDS = int(os.getenv("DEFAULT_POST_BUFFER_SECONDS", "8"))
DEFAULT_ROLLING_WINDOW_SECONDS = int(os.getenv("DEFAULT_ROLLING_WINDOW_SECONDS", "6"))
DEFAULT_POSITIVE_RATIO = float(os.getenv("DEFAULT_POSITIVE_RATIO", "0.50"))
DEFAULT_MIN_POSITIVE_FRAMES = int(os.getenv("DEFAULT_MIN_POSITIVE_FRAMES", "3"))
DEFAULT_COOLDOWN_SECONDS = int(os.getenv("DEFAULT_COOLDOWN_SECONDS", "20"))
