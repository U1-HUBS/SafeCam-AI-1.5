import os
import json
import time
import queue
from flask import Flask, Response, jsonify
from flask_cors import CORS

from backend.config import SAMPLE_VIDEOS_DIR
from backend.database import engine, Base, SessionLocal
from backend.models import Camera, Incident, IncidentEvent, IncidentReview
from backend.services.stream_manager import StreamManager
from backend.api.cameras import cameras_bp, set_stream_manager as set_cam_sm
from backend.api.incidents import incidents_bp, set_event_callback as set_inc_cb
from backend.api.reports import reports_bp
from backend.api.stream import stream_bp, set_stream_manager as set_str_sm

# Global event subscribers for SSE
event_subscribers = []

def broadcast_event(data: dict):
    payload = json.dumps(data)
    for q in list(event_subscribers):
        try:
            q.put_nowait(payload)
        except Exception:
            event_subscribers.remove(q)

def create_app():
    # Initialize DB
    Base.metadata.create_all(bind=engine)

    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Stream Manager with event callback
    stream_manager = StreamManager(event_callback=broadcast_event)
    set_cam_sm(stream_manager)
    set_str_sm(stream_manager)
    set_inc_cb(broadcast_event)

    # Register Blueprints
    app.register_blueprint(cameras_bp, url_prefix="/api/cameras")
    app.register_blueprint(incidents_bp, url_prefix="/api/incidents")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(stream_bp, url_prefix="/api/stream")

    # Real-Time SSE Endpoint
    @app.route("/api/events")
    def sse_events():
        q = queue.Queue(maxsize=50)
        event_subscribers.append(q)

        def event_stream():
            try:
                # Send initial ping
                yield f"data: {json.dumps({'type': 'connected'})}\n\n"
                while True:
                    try:
                        msg = q.get(timeout=20.0)
                        yield f"data: {msg}\n\n"
                    except queue.Empty:
                        # Keep-alive heartbeat
                        yield f": keep-alive\n\n"
            finally:
                if q in event_subscribers:
                    event_subscribers.remove(q)

        return Response(event_stream(), mimetype="text/event-stream")

    @app.route("/api/health")
    def health_check():
        return jsonify({
            "status": "healthy",
            "cameras_active": len(stream_manager.workers),
            "subscribers": len(event_subscribers)
        })

    # Auto-seed initial cameras if empty
    with app.app_context():
        _seed_initial_cameras(stream_manager)

    return app, stream_manager

def _seed_initial_cameras(stream_manager: StreamManager):
    db = SessionLocal()
    try:
        count = db.query(Camera).count()
        if count == 0:
            sample_video_path = str(SAMPLE_VIDEOS_DIR / "sample_hallway.mp4")
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
                    sensitivity=0.25
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
                    sensitivity=0.25
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
                    sensitivity=0.25
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
                    sensitivity=0.25
                ),
            ]
            db.add_all(cams)
            db.commit()

        # Start stream workers
        stream_manager.reload_all_active_cameras()
    finally:
        db.close()


if __name__ == "__main__":
    app, sm = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
