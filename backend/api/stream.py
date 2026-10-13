import time
import cv2
import numpy as np
from flask import Blueprint, Response, jsonify, request

stream_bp = Blueprint("stream", __name__)

stream_manager = None

def set_stream_manager(sm):
    global stream_manager
    stream_manager = sm

def generate_placeholder_frame(text: str = "NO SIGNAL"):
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(
        img,
        text,
        (180, 240),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (100, 100, 100),
        2
    )
    _, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()

def mjpeg_generator(camera_id: int, show_labels: bool = True):
    while True:
        frame_bytes = None
        if stream_manager:
            frame = stream_manager.get_latest_frame(camera_id, annotated=show_labels)
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
                if ret:
                    frame_bytes = buffer.tobytes()

        if frame_bytes is None:
            frame_bytes = generate_placeholder_frame("CAMERA OFFLINE")
            time.sleep(1.0)
        else:
            time.sleep(0.06)  # ~15 fps playback rate for browser

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@stream_bp.route("/<int:camera_id>/live")
def live_mjpeg_stream(camera_id: int):
    show_labels = request.args.get("labels", "1").lower() not in ["0", "false", "no", "off"]
    return Response(
        mjpeg_generator(camera_id, show_labels=show_labels),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@stream_bp.route("/<int:camera_id>/labels", methods=["POST"])
def toggle_camera_labels(camera_id: int):
    data = request.json or {}
    enabled = bool(data.get("enabled", True))
    if stream_manager:
        stream_manager.set_camera_labels(camera_id, enabled)
    return jsonify({"camera_id": camera_id, "labels_enabled": enabled})

@stream_bp.route("/<int:camera_id>/snapshot")
def camera_snapshot(camera_id: int):
    if stream_manager:
        frame = stream_manager.get_latest_frame(camera_id)
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                return Response(buffer.tobytes(), mimetype='image/jpeg')

    placeholder = generate_placeholder_frame("NO SIGNAL")
    return Response(placeholder, mimetype='image/jpeg')
