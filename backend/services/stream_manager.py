import time
import uuid
import datetime
import threading
from collections import deque
from typing import Dict, Optional, Callable
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
        pre_buffer_seconds: int = 8,
        post_buffer_seconds: int = 8,
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

        self.latest_prediction = {
            "label": label,
            "category": category,
            "confidence": confidence,
            "is_violent": is_violent,
            "timestamp": timestamp,
            "latency_ms": latency_ms,
        }

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

    def _handle_incident_trigger(self, trigger_data: Dict):
        """
        Creates an incident in the database, kicks off pre+post clip capture,
        and triggers the real-time event notification.
        """
        db = SessionLocal()
        try:
            public_id = f"INC-{datetime.datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            incident = Incident(
                public_id=public_id,
                camera_id=self.camera_id,
                category=trigger_data["category"],
                raw_ai_label=trigger_data["raw_ai_label"],
                severity=trigger_data["severity"],
                peak_confidence=trigger_data["peak_confidence"],
                average_confidence=trigger_data["average_confidence"],
                started_at=trigger_data["started_at"],
                detected_at=trigger_data["detected_at"],
                status="AWAITING_REVIEW",
                clip_status="PROCESSING"
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
        # Run saving asynchronously
        threading.Thread(
            target=save_incident_clip,
            args=(incident_id, frames),
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
            cameras = db.query(Camera).filter(Camera.enabled == True).all()
            for cam in cameras:
                self.start_camera(cam)
        finally:
            db.close()

    def get_latest_frame(self, camera_id: int) -> Optional[np.ndarray]:
        worker = self.workers.get(camera_id)
        if worker:
            return worker.latest_frame
        return None

    def get_camera_status(self, camera_id: int) -> Dict:
        worker = self.workers.get(camera_id)
        if not worker:
            return {"status": "OFFLINE", "ai_status": None}
        return {
            "status": worker.status,
            "latest_prediction": worker.latest_prediction
        }
