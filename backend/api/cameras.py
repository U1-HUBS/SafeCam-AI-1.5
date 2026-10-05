from flask import Blueprint, request, jsonify
from backend.database import SessionLocal
from backend.models import Camera
import cv2

cameras_bp = Blueprint("cameras", __name__)

# References to global stream_manager set in app.py
stream_manager = None

def set_stream_manager(sm):
    global stream_manager
    stream_manager = sm


@cameras_bp.route("", methods=["GET"])
def list_cameras():
    db = SessionLocal()
    try:
        cameras = db.query(Camera).all()
        result = []
        for cam in cameras:
            cam_data = cam.to_dict()
            if stream_manager:
                status_info = stream_manager.get_camera_status(cam.id)
                cam_data["runtime_status"] = status_info.get("status", cam.status)
                cam_data["latest_prediction"] = status_info.get("latest_prediction")
            result.append(cam_data)
        return jsonify(result)
    finally:
        db.close()


@cameras_bp.route("", methods=["POST"])
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
def get_camera(camera_id):
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
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
def update_camera(camera_id):
    data = request.json or {}
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
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
def delete_camera(camera_id):
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            return jsonify({"error": "Camera not found"}), 404

        if stream_manager:
            stream_manager.stop_camera(camera.id)

        db.delete(camera)
        db.commit()
        return jsonify({"message": "Camera deleted"})
    finally:
        db.close()


@cameras_bp.route("/<int:camera_id>/test", methods=["POST"])
def test_camera(camera_id):
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            return jsonify({"error": "Camera not found"}), 404

        cap = cv2.VideoCapture(camera.stream_url)
        opened = cap.isOpened()
        can_read = False
        if opened:
            ret, _ = cap.read()
            can_read = ret
        cap.release()

        return jsonify({
            "camera_id": camera_id,
            "stream_url": camera.stream_url,
            "connected": opened and can_read,
            "status": "ONLINE" if (opened and can_read) else "OFFLINE"
        })
    finally:
        db.close()
