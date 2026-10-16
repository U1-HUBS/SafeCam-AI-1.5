import os
import uuid
import datetime
from pathlib import Path
import numpy as np
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import cv2

from backend.config import (
    BASE_DIR,
    SAMPLE_VIDEOS_DIR,
    UPLOADS_DIR,
    ALLOWED_VIDEO_EXTENSIONS,
    MAX_UPLOAD_SIZE_BYTES,
    resolve_stream_source
)
from backend.database import SessionLocal
from backend.models import Camera
from backend.auth import login_required, roles_required

cameras_bp = Blueprint("cameras", __name__)

# References to global stream_manager set in app.py
stream_manager = None

def set_stream_manager(sm):
    global stream_manager
    stream_manager = sm


@cameras_bp.route("", methods=["GET"])
@login_required
def list_cameras():
    db = SessionLocal()
    try:
        include_deleted = request.args.get("include_deleted", "").lower() in ("1", "true", "yes")
        query = db.query(Camera)
        if not include_deleted:
            query = query.filter(Camera.is_deleted == False)
        cameras = query.all()
        result = []
        for cam in cameras:
            cam_data = cam.to_dict()
            if stream_manager and not cam.is_deleted:
                status_info = stream_manager.get_camera_status(cam.id)
                cam_data["runtime_status"] = status_info.get("status", cam.status)
                cam_data["latest_prediction"] = status_info.get("latest_prediction")
            result.append(cam_data)
        return jsonify(result)
    finally:
        db.close()


@cameras_bp.route("", methods=["POST"])
@roles_required("admin")
def create_camera():
    data = request.json or {}
    if not data.get("name") or not data.get("stream_url"):
        return jsonify({"error": "name and stream_url are required"}), 400

    db = SessionLocal()
    try:
        camera = Camera(
            name=data["name"],
            location=data.get("location", "Main Hallway"),
            stream_url=data["stream_url"],
            is_simulation=data.get("is_simulation", False),
            loop_simulation=data.get("loop_simulation", True),
            enabled=data.get("enabled", True),
            ai_enabled=data.get("ai_enabled", True),
            sampling_rate=data.get("sampling_rate", 2),
            sensitivity=data.get("sensitivity", 0.25),
            pre_buffer_seconds=data.get("pre_buffer_seconds", 8),
            post_buffer_seconds=data.get("post_buffer_seconds", 8),
        )
        db.add(camera)
        db.commit()
        db.refresh(camera)

        if stream_manager and camera.enabled:
            stream_manager.start_camera(camera)

        return jsonify(camera.to_dict()), 201
    finally:
        db.close()


@cameras_bp.route("/<int:camera_id>", methods=["GET"])
@login_required
def get_camera(camera_id):
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id, Camera.is_deleted == False).first()
        if not camera:
            return jsonify({"error": "Camera not found"}), 404
        cam_data = camera.to_dict()
        if stream_manager:
            status_info = stream_manager.get_camera_status(camera.id)
            cam_data["runtime_status"] = status_info.get("status", camera.status)
            cam_data["latest_prediction"] = status_info.get("latest_prediction")
        return jsonify(cam_data)
    finally:
        db.close()


@cameras_bp.route("/<int:camera_id>", methods=["PUT"])
@roles_required("admin")
def update_camera(camera_id):
    data = request.json or {}
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id, Camera.is_deleted == False).first()
        if not camera:
            return jsonify({"error": "Camera not found"}), 404

        for key in ["name", "location", "stream_url", "is_simulation", "loop_simulation",
                    "enabled", "ai_enabled", "sampling_rate", "sensitivity",
                    "pre_buffer_seconds", "post_buffer_seconds"]:
            if key in data:
                setattr(camera, key, data[key])

        db.commit()
        db.refresh(camera)

        if stream_manager:
            if camera.enabled:
                stream_manager.start_camera(camera)
            else:
                stream_manager.stop_camera(camera.id)

        return jsonify(camera.to_dict())
    finally:
        db.close()


@cameras_bp.route("/<int:camera_id>", methods=["DELETE"])
@roles_required("admin")
def delete_camera(camera_id):
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id, Camera.is_deleted == False).first()
        if not camera:
            return jsonify({"error": "Camera not found"}), 404

        # 1. Stop live stream ingestion and background AI worker
        if stream_manager:
            stream_manager.stop_camera(camera.id)

        # 2. Snapshot camera name & location onto any associated incidents missing them
        for inc in camera.incidents:
            if not inc.camera_name:
                inc.camera_name = camera.name
            if not inc.camera_location:
                inc.camera_location = camera.location

        # 3. Soft delete: Mark camera as deleted and offline, preserving all historic alerts and incidents
        camera.is_deleted = True
        camera.enabled = False
        camera.status = "OFFLINE"
        camera.deleted_at = datetime.datetime.utcnow()
        db.commit()

        return jsonify({
            "message": "Camera removed from live monitoring; incident history preserved",
            "camera_id": camera.id
        })
    finally:
        db.close()


@cameras_bp.route("/upload", methods=["POST"])
@roles_required("admin")
def upload_simulation_video():
    """
    Accepts a video file upload for CCTV camera simulation, validates it using OpenCV,
    extracts metadata (fps, resolution, duration), and saves to storage/uploads/.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    original_name = file.filename
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        return jsonify({"error": f"Unsupported video format '{ext}'. Allowed formats: {allowed}"}), 400

    clean_name = secure_filename(original_name)
    if not clean_name:
        clean_name = f"video_{uuid.uuid4().hex[:6]}{ext}"
    timestamp_str = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp_str}_{uuid.uuid4().hex[:6]}_{clean_name}"
    saved_path = UPLOADS_DIR / unique_filename

    file.save(str(saved_path))
    file_size = saved_path.stat().st_size

    if file_size > MAX_UPLOAD_SIZE_BYTES:
        saved_path.unlink(missing_ok=True)
        max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        return jsonify({"error": f"File exceeds maximum allowed size of {max_mb} MB"}), 400

    # Validate video using OpenCV
    cap = cv2.VideoCapture(str(saved_path))
    if not cap.isOpened():
        saved_path.unlink(missing_ok=True)
        return jsonify({"error": "Failed to decode video file. Format may be corrupted or unsupported."}), 400

    ret, frame = cap.read()
    if not ret or frame is None:
        cap.release()
        saved_path.unlink(missing_ok=True)
        return jsonify({"error": "Video file contains no readable frames."}), 400

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or np.isnan(fps):
        fps = 20.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    duration = round(frame_count / fps, 2) if fps > 0 and frame_count > 0 else 0.0
    rel_path = str(saved_path.relative_to(BASE_DIR)).replace("\\", "/")

    return jsonify({
        "success": True,
        "stream_url": rel_path,
        "absolute_path": str(saved_path),
        "filename": original_name,
        "stored_filename": unique_filename,
        "size_bytes": file_size,
        "fps": round(fps, 2),
        "width": width,
        "height": height,
        "duration_seconds": duration,
        "frame_count": frame_count
    }), 201


@cameras_bp.route("/simulations", methods=["GET"])
@login_required
def list_simulations():
    """
    Returns available simulation videos from presets and user uploads.
    """
    simulations = []

    # Built-in sample presets
    if SAMPLE_VIDEOS_DIR.exists():
        for p in sorted(SAMPLE_VIDEOS_DIR.glob("*")):
            if p.suffix.lower() in ALLOWED_VIDEO_EXTENSIONS:
                rel = str(p.relative_to(BASE_DIR)).replace("\\", "/")
                display_name = p.stem.replace("_", " ").title()
                if "fight" in p.name.lower():
                    display_name += " (Altercation Preset)"
                elif "hallway" in p.name.lower():
                    display_name += " (Normal Corridor Preset)"
                else:
                    display_name += " (Preset)"
                simulations.append({
                    "name": display_name,
                    "path": rel,
                    "type": "preset",
                    "filename": p.name,
                    "size_bytes": p.stat().st_size
                })

    # User-uploaded videos
    if UPLOADS_DIR.exists():
        for p in sorted(UPLOADS_DIR.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True):
            if p.suffix.lower() in ALLOWED_VIDEO_EXTENSIONS:
                rel = str(p.relative_to(BASE_DIR)).replace("\\", "/")
                clean_display = p.name
                parts = p.name.split("_", 2)
                if len(parts) >= 3:
                    clean_display = parts[2]
                simulations.append({
                    "name": f"{clean_display} (Uploaded)",
                    "path": rel,
                    "type": "uploaded",
                    "filename": p.name,
                    "size_bytes": p.stat().st_size,
                    "uploaded_at": datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat()
                })

    return jsonify(simulations)


@cameras_bp.route("/<int:camera_id>/test", methods=["POST"])
@roles_required("admin", "supervisor")
def test_camera(camera_id):
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id, Camera.is_deleted == False).first()
        if not camera:
            return jsonify({"error": "Camera not found"}), 404

        source = resolve_stream_source(camera.stream_url)
        cap = cv2.VideoCapture(source)
        opened = cap.isOpened()
        can_read = False
        if opened:
            ret, _ = cap.read()
            can_read = ret
        cap.release()

        return jsonify({
            "camera_id": camera_id,
            "stream_url": camera.stream_url,
            "resolved_source": str(source),
            "connected": opened and can_read,
            "status": "ONLINE" if (opened and can_read) else "OFFLINE"
        })
    finally:
        db.close()
