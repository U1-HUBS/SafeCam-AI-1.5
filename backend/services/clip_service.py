import os
import time
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Callable
from backend.config import CLIPS_DIR, THUMBNAILS_DIR, CLIP_MAX_HEIGHT, CLIP_TARGET_FPS
from backend.database import SessionLocal
from backend.models import Incident, IncidentEvent


def create_browser_compatible_writer(output_path: str, fps: float, width: int, height: int) -> cv2.VideoWriter:
    """
    Creates a VideoWriter that produces native H.264 video streams supported by
    all modern web browsers (Chrome, Edge, Firefox, Safari) in HTML5 <video> tags.
    Prioritizes Windows Media Foundation (MSMF H264) hardware/system encoder.
    """
    # 1. On Windows, MSMF produces native H.264 MP4 supported natively by all browsers
    try:
        writer = cv2.VideoWriter(output_path, cv2.CAP_MSMF, cv2.VideoWriter_fourcc(*'H264'), fps, (width, height))
        if writer.isOpened():
            return writer
    except Exception:
        pass

    try:
        writer = cv2.VideoWriter(output_path, cv2.CAP_MSMF, cv2.VideoWriter_fourcc(*'avc1'), fps, (width, height))
        if writer.isOpened():
            return writer
    except Exception:
        pass

    # 2. General cross-platform attempts
    for fourcc_code in ['avc1', 'H264', 'mp4v']:
        try:
            fourcc = cv2.VideoWriter_fourcc(*fourcc_code)
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            if writer.isOpened():
                return writer
        except Exception:
            continue

    # Fallback default
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    return cv2.VideoWriter(output_path, fourcc, fps, (width, height))


def ensure_clip_browser_playable(clip_path: str) -> bool:
    """
    Verifies if an existing MP4 clip is encoded in browser-playable H.264.
    If encoded in legacy/raw MPEG-4 (FMP4/mp4v) which browsers cannot play,
    transcodes it into native H.264 in-place.
    """
    if not clip_path or not os.path.exists(clip_path):
        return False

    try:
        cap = cv2.VideoCapture(clip_path)
        if not cap.isOpened():
            return False

        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec = ''.join([chr((fourcc_int >> (8 * i)) & 0xFF) for i in range(4)]).lower()
        if codec in ['h264', 'avc1']:
            cap.release()
            return True

        # Needs transcoding to H.264 for HTML5 web playback
        fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if w <= 0 or h <= 0:
            cap.release()
            return False

        temp_path = clip_path + ".h264_tmp.mp4"
        writer = create_browser_compatible_writer(temp_path, fps, w, h)
        if not writer.isOpened():
            cap.release()
            return False

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            writer.write(frame)

        cap.release()
        writer.release()

        # Atomic replace
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            os.replace(temp_path, clip_path)
            return True
        elif os.path.exists(temp_path):
            os.remove(temp_path)
            return False

    except Exception as e:
        print(f"[ClipService] Warning: Failed to transcode {clip_path} to H264: {e}")
        return False

    return True


def save_incident_clip(
    incident_id: int,
    frames: List[Tuple[float, np.ndarray]],  # list of (timestamp, frame_bgr)
    fps: float = 15.0,
    event_callback: Optional[Callable[[dict], None]] = None
) -> bool:
    """
    Saves an assembled list of frames (pre-buffer + event + post-buffer) as an MP4 clip
    and extracts a thumbnail. Updates database record status to READY or FAILED.
    Optimized for high-speed encoding with resolution clamping and FPS normalization.
    """
    if not frames:
        _update_incident_failed(incident_id)
        return False

    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return False

        incident.clip_status = "PROCESSING"
        db.commit()

        # Output paths
        clip_filename = f"incident_{incident.public_id}.mp4"
        thumb_filename = f"thumb_{incident.public_id}.jpg"
        clip_path = str(CLIPS_DIR / clip_filename)
        thumb_path = str(THUMBNAILS_DIR / thumb_filename)

        # Immediate thumbnail generation if not already written
        if not incident.thumbnail_path or not os.path.exists(incident.thumbnail_path):
            mid_index = len(frames) // 2
            try:
                cv2.imwrite(thumb_path, frames[mid_index][1])
                incident.thumbnail_path = thumb_path
                db.commit()
            except Exception as te:
                print(f"[ClipService] Warning: Failed to save thumbnail: {te}")

        # Subsample frames if over-dense to keep encoding fast and smooth
        target_fps = CLIP_TARGET_FPS if CLIP_TARGET_FPS > 0 else 15.0
        if len(frames) > 2:
            duration = frames[-1][0] - frames[0][0]
            if duration > 0.5:
                input_fps = len(frames) / duration
                if input_fps > target_fps * 1.25:
                    step = max(1, int(round(input_fps / target_fps)))
                    frames = frames[::step]
                    fps = target_fps
                else:
                    fps = min(fps, target_fps)
            else:
                fps = target_fps
        else:
            fps = target_fps

        # Check resolution and clamp if larger than CLIP_MAX_HEIGHT (e.g. 720p)
        sample_frame = frames[0][1]
        orig_h, orig_w = sample_frame.shape[:2]
        if orig_h > CLIP_MAX_HEIGHT:
            out_h = CLIP_MAX_HEIGHT
            out_w = int(orig_w * (CLIP_MAX_HEIGHT / orig_h))
            if out_w % 2 != 0:
                out_w -= 1
            need_resize = True
        else:
            out_h, out_w = orig_h, orig_w
            need_resize = False

        writer = create_browser_compatible_writer(clip_path, fps, out_w, out_h)

        overlay_text = f"INCIDENT: {incident.public_id} | CAM #{incident.camera_id}"
        for _, frame in frames:
            proc_frame = cv2.resize(frame, (out_w, out_h)) if need_resize else frame.copy()
            cv2.putText(
                proc_frame,
                overlay_text,
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )
            writer.write(proc_frame)

        writer.release()

        # Update database record
        incident.clip_status = "READY"
        incident.clip_path = clip_path
        if not incident.thumbnail_path or not os.path.exists(incident.thumbnail_path):
            incident.thumbnail_path = thumb_path
        
        # Add timeline event
        event = IncidentEvent(
            incident_id=incident.id,
            event_type="CLIP_GENERATED",
            actor="ClipService",
            metadata_json=f'{{"frames_count": {len(frames)}, "fps": {fps}, "resolution": "{out_w}x{out_h}"}}'
        )
        db.add(event)
        db.commit()

        # Emit real-time notification
        if event_callback:
            try:
                event_callback({
                    "type": "incident.clip_ready",
                    "incident_id": incident.id,
                    "clip_url": f"/api/incidents/{incident.id}/clip",
                    "thumbnail_url": f"/api/incidents/{incident.id}/thumbnail"
                })
            except Exception as cb_err:
                print(f"[ClipService] Warning: Callback error on clip_ready: {cb_err}")

        return True

    except Exception as e:
        print(f"[ClipService] Error saving clip for incident #{incident_id}: {e}")
        _update_incident_failed(incident_id)
        return False
    finally:
        db.close()


def _update_incident_failed(incident_id: int):
    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident:
            incident.clip_status = "FAILED"
            db.commit()
    except Exception:
        pass
    finally:
        db.close()
