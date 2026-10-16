# Safecam AI — AI CCTV Central Monitoring & Violence Incident Management System

**Safecam AI** is a centralized monitoring system for multiple CCTV cameras that uses an AI violence-detection engine to identify suspected violence (fighting or physical altercations).

---

## Key Features

1. **Multi-Camera Central Live Wall**: Monitor RTSP feeds and local video simulation streams in real time with continuous playback and HUD metadata.
2. **AI Violence Detection**: Frame sampling with OpenCLIP ViT-B/32 baseline and temporal event aggregation (rolling window, hysteresis, and cooldown) to prevent single-frame false alarms.
3. **Automated Incident Clipping**: Preserves footage from **before, during, and after** the detected event (pre-event and post-event buffer).
4. **Real-Time Alert Dispatch**: Instant alerts pushed via Server-Sent Events (SSE) with on-screen visual banners and Web Audio chime.
5. **Human Review Workflow**: Operators can inspect the incident clip and classify the event as **Confirmed Violence**, **False Positive / Not Violence**, or **Needs Review**, with audit logging and feedback reason tagging.
6. **Searchable History & Reports**: Filter past incidents by date, camera, severity, and review classification, and track false-positive rates.

---

## Quick Start (No Docker Required)

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 2. Backend Setup
From the repository root:
```powershell
# Install backend Python dependencies
python -m pip install flask flask-cors sqlalchemy pytest opencv-python numpy open_clip_torch torch torchvision ultralytics

# Generate synthetic sample videos (for simulation)
python sample_videos/generate_sample.py

# Run backend tests
python -m pytest backend/tests -v

# Start Flask Backend API (port 5000)
python backend/app.py
```

### 3. Frontend Setup
In a second terminal:
```powershell
cd frontend
npm install
npm run dev
```

Visit the monitoring dashboard at: **`http://localhost:3000`**

Or launch both at once with:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-all.ps1
```

---

## Architecture

- **Backend**: Python, Flask, SQLAlchemy (SQLite default), OpenCV VideoCapture / VideoWriter
- **AI / Ingestion**: Frame sampler, temporal rolling window aggregator, OpenCLIP ViT-B/32
- **Frontend**: Next.js (React), TypeScript, Tailwind CSS, Web Audio API chime, Server-Sent Events (SSE)
- **Storage**: Local filesystem for MP4 clips and thumbnails (`storage/clips/`, `storage/thumbnails/`)
