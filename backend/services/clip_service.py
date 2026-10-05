import os
import time
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple
from backend.config import CLIPS_DIR, THUMBNAILS_DIR
from backend.database import SessionLocal
from backend.models import Incident, IncidentEvent

def save_incident_clip(
    incident_id: int,
    frames: List[Tuple[float, np.ndarray]],  # list of (timestamp, frame_bgr)
    fps: float = 15.0
) -> bool:
    """
    Saves an assembled list of frames (pre-buffer + event + post-buffer) as an MP4 clip
    and extracts a thumbnail. Updates database record status to READY or FAILED.
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

        # Get frame dimensions
        sample_frame = frames[0][1]
        height, width = sample_frame.shape[:2]

        # Use mp4v or avc1 fourcc
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(clip_path, fourcc, fps, (width, height))

        thumbnail_saved = False
        mid_index = len(frames) // 2

        for i, (ts, frame) in enumerate(frames):
            # Optional overlay timestamp on clip
            cv2.putText(
                frame,
                f"INCIDENT: {incident.public_id} | CAM #{incident.camera_id}",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )
            writer.write(frame)

            if i == mid_index and not thumbnail_saved:
                cv2.imwrite(thumb_path, frame)
                thumbnail_saved = True

        writer.release()

        # If thumbnail wasn't written
        if not thumbnail_saved and len(frames) > 0:
            cv2.imwrite(thumb_path, frames[0][1])

        # Update database record
        incident.clip_status = "READY"
        incident.clip_path = clip_path
        incident.thumbnail_path = thumb_path
        
        # Add timeline event
        event = IncidentEvent(
            incident_id=incident.id,
            event_type="CLIP_GENERATED",
            actor="ClipService",
            metadata_json=f'{{"frames_count": {len(frames)}, "fps": {fps}}}'
        )
        db.add(event)
        db.commit()
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
