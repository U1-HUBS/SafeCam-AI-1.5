import time
import uuid
import datetime
import threading
from collections import deque
from typing import Dict, List, Optional, Callable
import cv2
import numpy as np

from backend.config import resolve_stream_source
from backend.database import SessionLocal
from backend.models import Camera, Incident, IncidentEvent, AiPrediction
from backend.services.ai_service import ViolenceClassifier, TemporalAggregator, KineticMotionEstimator
from backend.services.clip_service import save_incident_clip

class CameraStreamWorker:
    """
    Ingests frames for a single camera (RTSP or local video simulation),
    maintains a rolling buffer for pre-event preservation, samples frames for AI,
    and runs the temporal aggregation logic.
    """
    def __init__(
        self,
        camera_id: int,
        stream_url: str,
        is_simulation: bool = False,
        loop_simulation: bool = True,
        ai_enabled: bool = True,
        sampling_rate: int = 2,
        sensitivity: float = 0.25,
        pre_buffer_seconds: int = 4,
        post_buffer_seconds: int = 4,
        classifier: Optional[ViolenceClassifier] = None,
        event_callback: Optional[Callable[[Dict], None]] = None
    ):
        self.camera_id = camera_id
        self.stream_url = stream_url
        self.is_simulation = is_simulation
        self.loop_simulation = loop_simulation
        self.ai_enabled = ai_enabled
        self.sampling_rate = max(1, sampling_rate)
        self.sensitivity = sensitivity
        self.pre_buffer_seconds = pre_buffer_seconds
        self.post_buffer_seconds = post_buffer_seconds
        self.classifier = classifier or ViolenceClassifier()
        self.event_callback = event_callback

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.latest_persons: List[Dict] = []
        self.latest_violent_state: bool = False
        self.latest_ai_label: str = ""
        self.show_yolo_labels: bool = True
        self.latest_prediction: Optional[Dict] = None
        self.status = "OFFLINE"

        # Dedicated isolated kinetic motion estimator for this specific camera
        self.motion_estimator = KineticMotionEstimator()

        # Rolling buffer: deque of (timestamp, frame_bgr)
        self.rolling_buffer: deque = deque()
        self.lock = threading.Lock()

        # Aggregator
        self.aggregator = TemporalAggregator(
            camera_id=self.camera_id,
            threshold=self.sensitivity
        )

        # Active incident recording queue: list of active incident clip collectors
        self.active_incident_collectors = []

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        # Finalize any in-flight incident collectors so ongoing recordings are saved cleanly
        with self.lock:
            for collector in list(self.active_incident_collectors):
                try:
                    self._finalize_incident_clip(collector)
                except Exception as ce:
                    print(f"[CameraStreamWorker] Warning: Error finalizing clip on worker stop: {ce}")
            self.active_incident_collectors.clear()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def _run(self):
        while self.running:
            source = resolve_stream_source(self.stream_url)
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                self.status = "OFFLINE"
                self._update_camera_status("OFFLINE")
                time.sleep(2.0)
                continue

            self.status = "ONLINE"
            self._update_camera_status("ONLINE")

            # Determine FPS
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0 or np.isnan(fps):
                fps = 20.0
            frame_delay = 1.0 / fps

            sample_interval = 1.0 / self.sampling_rate
            last_sample_time = 0.0

            while self.running:
                start_read = time.time()
                ret, frame = cap.read()

                if not ret:
                    if self.is_simulation and self.loop_simulation:
                        # Reset video to beginning for continuous simulation
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        break

                now = time.time()

                with self.lock:
                    self.latest_frame = frame.copy()
                    
                    # Store in rolling buffer
                    self.rolling_buffer.append((now, frame.copy()))
                    
                    # Clean up rolling buffer beyond pre_buffer_seconds
                    cutoff = now - self.pre_buffer_seconds
                    while self.rolling_buffer and self.rolling_buffer[0][0] < cutoff:
                        self.rolling_buffer.popleft()

                    # Feed active incident collectors
                    for collector in list(self.active_incident_collectors):
                        collector["frames"].append((now, frame.copy()))
                        if now >= collector["target_end_time"]:
                            self._finalize_incident_clip(collector)
                            self.active_incident_collectors.remove(collector)

                # Sample for AI
                if self.ai_enabled and (now - last_sample_time >= sample_interval):
                    last_sample_time = now
                    self._process_ai_frame(frame, now)

                # Pace simulation playback to match real time
                if self.is_simulation:
                    elapsed = time.time() - start_read
                    sleep_time = frame_delay - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                else:
                    time.sleep(0.005)

            cap.release()
            time.sleep(1.0)

        self.status = "OFFLINE"
        self._update_camera_status("OFFLINE")

    def _process_ai_frame(self, frame: np.ndarray, timestamp: float):
        t0 = time.time()
        label, category, confidence, is_violent = self.classifier.predict_frame(
            frame,
            timestamp,
            camera_id=self.camera_id,
            motion_estimator=self.motion_estimator
        )
        latency_ms = (time.time() - t0) * 1000.0

        persons = self.classifier.get_detected_persons(self.camera_id)
        self.latest_persons = persons

        self.latest_prediction = {
            "label": label,
            "category": category,
            "confidence": confidence,
            "is_violent": is_violent,
            "timestamp": timestamp,
            "latency_ms": latency_ms,
            "person_count": len(persons),
            "persons": persons
        }

        # Generate annotated frame with YOLO bounding boxes and labels for live monitoring
        self._render_annotated_frame(frame, persons, is_violent, label)

        # Check aggregator
        trigger = self.aggregator.add_prediction(
            timestamp=timestamp,
            label=label,
            category=category,
            confidence=confidence,
            is_violent=is_violent
        )

        if trigger:
            self._handle_incident_trigger(trigger)

    def render_annotations(self, frame: np.ndarray) -> np.ndarray:
        if frame is None or frame.size == 0:
            return frame

        annotated = frame.copy()
        h, w = annotated.shape[:2]

        with self.lock:
            persons = list(self.latest_persons)
            is_violent = self.latest_violent_state
            label = self.latest_ai_label

        person_count = len(persons)
        is_solo = (person_count <= 1)

        # Draw YOLO bounding boxes for each detected person
        for i, p in enumerate(persons):
            bx, by, bw, bh = p["box"]
            conf = p.get("conf", 0.90)
            pid = p.get("id", i + 1)

            # Determine box styling
            if is_violent:
                box_color = (40, 40, 230)      # Bright Red (BGR)
                tag_bg = (30, 30, 200)
                tag_text = f"Person #{pid} [VIOLENCE] {int(conf * 100)}%"
            elif is_solo:
                box_color = (40, 215, 255)     # Amber / Yellow (BGR)
                tag_bg = (30, 180, 220)
                tag_text = f"Person #{pid} [SOLO] {int(conf * 100)}%"
            else:
                box_color = (80, 220, 80)      # Emerald Green (BGR)
                tag_bg = (60, 180, 60)
                tag_text = f"Person #{pid} {int(conf * 100)}%"

            # Crisp high-contrast bounding box
            cv2.rectangle(annotated, (bx - 1, by - 1), (bx + bw + 1, by + bh + 1), (0, 0, 0), 1)
            cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), box_color, 2)

            # Header pill tag
            (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            pill_y1 = max(0, by - th - 8)
            pill_y2 = by
            cv2.rectangle(annotated, (bx, pill_y1), (bx + tw + 10, pill_y2), (0, 0, 0), -1)
            cv2.rectangle(annotated, (bx, pill_y1), (bx + tw + 10, pill_y2), tag_bg, 1)
            cv2.putText(
                annotated,
                tag_text,
                (bx + 5, by - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        # Top-Right HUD Badge: Always visible YOLO Status Indicator
        if person_count == 0:
            hud_label = "YOLO: SCANNING"
            hud_sub = "0 PERSONS DETECTED"
            hud_bg = (100, 100, 100)
        elif is_solo:
            hud_label = "YOLO: 1 PERSON"
            hud_sub = "SOLO (VIOLENCE SUPPRESSED)"
            hud_bg = (20, 140, 180)
        elif is_violent:
            hud_label = f"YOLO: {person_count} PERSONS"
            hud_sub = "ALTERCATION DETECTED"
            hud_bg = (30, 30, 200)
        else:
            hud_label = f"YOLO: {person_count} PERSONS"
            hud_sub = "MONITORING ACTIVE"
            hud_bg = (40, 140, 40)

        badge_w = 210
        badge_h = 36
        cv2.rectangle(annotated, (w - badge_w - 10, 8), (w - 10, 8 + badge_h), (20, 20, 20), -1)
        cv2.rectangle(annotated, (w - badge_w - 10, 8), (w - 10, 8 + badge_h), hud_bg, 1)
        cv2.putText(annotated, hud_label, (w - badge_w - 2, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(annotated, hud_sub, (w - badge_w - 2, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (180, 220, 255), 1, cv2.LINE_AA)

        return annotated

    def _render_annotated_frame(self, frame: np.ndarray, persons: List[Dict], is_violent: bool, label: str):
        with self.lock:
            self.latest_persons = persons
            self.latest_violent_state = is_violent
            self.latest_ai_label = label
        annotated = self.render_annotations(frame)
        with self.lock:
            self.latest_annotated_frame = annotated
        return annotated

    def _handle_incident_trigger(self, trigger_data: Dict):
        """
        Creates an incident in the database, kicks off pre+post clip capture,
        and triggers the real-time event notification.
        """
        db = SessionLocal()
        try:
            public_id = f"INC-{datetime.datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            # Instant snapshot capture (<20ms) so operators have immediate preview
            thumb_path = None
            if self.latest_frame is not None and self.latest_frame.size > 0:
                from backend.config import THUMBNAILS_DIR
                thumb_filename = f"thumb_{public_id}.jpg"
                candidate_path = str(THUMBNAILS_DIR / thumb_filename)
                try:
                    cv2.imwrite(candidate_path, self.latest_frame)
                    thumb_path = candidate_path
                except Exception as te:
                    print(f"[CameraStreamWorker] Warning: Instant thumbnail write failed: {te}")

            cam = db.query(Camera).filter(Camera.id == self.camera_id).first()
            cam_name = cam.name if cam else None
            cam_location = cam.location if cam else None

            incident = Incident(
                public_id=public_id,
                camera_id=self.camera_id,
                camera_name=cam_name,
                camera_location=cam_location,
                category=trigger_data["category"],
                raw_ai_label=trigger_data["raw_ai_label"],
                severity=trigger_data["severity"],
                peak_confidence=trigger_data["peak_confidence"],
                average_confidence=trigger_data["average_confidence"],
                started_at=trigger_data["started_at"],
                detected_at=trigger_data["detected_at"],
                status="AWAITING_REVIEW",
                clip_status="PROCESSING",
                thumbnail_path=thumb_path
            )
            db.add(incident)
            db.commit()
            db.refresh(incident)

            # Record event
            event = IncidentEvent(
                incident_id=incident.id,
                event_type="TRIGGERED",
                actor="AiAggregator",
                metadata_json=f'{{"peak_confidence": {trigger_data["peak_confidence"]}}}'
            )
            db.add(event)
            db.commit()

            incident_id = incident.id
            incident_dict = incident.to_dict()

            # Snapshot pre-buffer frames
            with self.lock:
                pre_frames = list(self.rolling_buffer)
                target_end = time.time() + self.post_buffer_seconds
                self.active_incident_collectors.append({
                    "incident_id": incident_id,
                    "target_end_time": target_end,
                    "frames": pre_frames
                })

            # Real-time event callback
            if self.event_callback:
                self.event_callback({
                    "type": "incident.created",
                    "incident": incident_dict
                })

        except Exception as e:
            print(f"[CameraStreamWorker] Error creating incident: {e}")
        finally:
            db.close()

    def _finalize_incident_clip(self, collector: Dict):
        incident_id = collector["incident_id"]
        frames = collector["frames"]
        # Run saving asynchronously with real-time event notification
        threading.Thread(
            target=save_incident_clip,
            args=(incident_id, frames),
            kwargs={"event_callback": self.event_callback},
            daemon=True
        ).start()

    def _update_camera_status(self, status: str):
        db = SessionLocal()
        try:
            cam = db.query(Camera).filter(Camera.id == self.camera_id).first()
            if cam:
                cam.status = status
                cam.last_seen_at = datetime.datetime.utcnow()
                db.commit()
        except Exception:
            pass
        finally:
            db.close()


class StreamManager:
    """
    Central manager for all active camera streams.
    """
    def __init__(self, event_callback: Optional[Callable[[Dict], None]] = None):
        self.workers: Dict[int, CameraStreamWorker] = {}
        self.classifier = ViolenceClassifier()
        self.event_callback = event_callback
        self.lock = threading.Lock()

    def start_camera(self, camera: Camera):
        with self.lock:
            if camera.id in self.workers:
                self.workers[camera.id].stop()

            worker = CameraStreamWorker(
                camera_id=camera.id,
                stream_url=camera.stream_url,
                is_simulation=camera.is_simulation,
                loop_simulation=camera.loop_simulation,
                ai_enabled=camera.ai_enabled,
                sampling_rate=camera.sampling_rate,
                sensitivity=camera.sensitivity,
                pre_buffer_seconds=camera.pre_buffer_seconds,
                post_buffer_seconds=camera.post_buffer_seconds,
                classifier=self.classifier,
                event_callback=self.event_callback
            )
            self.workers[camera.id] = worker
            worker.start()

    def stop_camera(self, camera_id: int):
        with self.lock:
            if camera_id in self.workers:
                self.workers[camera_id].stop()
                del self.workers[camera_id]

    def reload_all_active_cameras(self):
        db = SessionLocal()
        try:
            cameras = db.query(Camera).filter(Camera.is_deleted == False, Camera.enabled == True).all()
            for cam in cameras:
                self.start_camera(cam)
        finally:
            db.close()

    def get_latest_frame(self, camera_id: int, annotated: bool = True) -> Optional[np.ndarray]:
        worker = self.workers.get(camera_id)
        if worker:
            frame = worker.latest_frame
            if frame is not None:
                if annotated and worker.show_yolo_labels:
                    return worker.render_annotations(frame)
                return frame
        return None

    def set_camera_labels(self, camera_id: int, enabled: bool):
        worker = self.workers.get(camera_id)
        if worker:
            worker.show_yolo_labels = enabled

    def get_camera_status(self, camera_id: int) -> Dict:
        worker = self.workers.get(camera_id)
        if not worker:
            return {"status": "OFFLINE", "ai_status": None}
        return {
            "status": worker.status,
            "latest_prediction": worker.latest_prediction
        }
