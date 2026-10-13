import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from backend.database import Base

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=False)
    stream_url = Column(String(500), nullable=False)
    is_simulation = Column(Boolean, default=False)
    loop_simulation = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)
    ai_enabled = Column(Boolean, default=True)
    sampling_rate = Column(Integer, default=2)  # FPS for inference
    sensitivity = Column(Float, default=0.25)   # AI threshold
    pre_buffer_seconds = Column(Integer, default=4)
    post_buffer_seconds = Column(Integer, default=4)
    status = Column(String(20), default="OFFLINE")  # ONLINE, OFFLINE, DEGRADED, DISABLED
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    incidents = relationship("Incident", back_populates="camera", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "stream_url": self.stream_url,
            "is_simulation": self.is_simulation,
            "loop_simulation": self.loop_simulation,
            "enabled": self.enabled,
            "ai_enabled": self.ai_enabled,
            "sampling_rate": self.sampling_rate,
            "sensitivity": self.sensitivity,
            "pre_buffer_seconds": self.pre_buffer_seconds,
            "post_buffer_seconds": self.post_buffer_seconds,
            "status": self.status,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(50), unique=True, index=True, nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    category = Column(String(50), nullable=False, default="Suspected Violence")
    raw_ai_label = Column(String(100), nullable=True)
    severity = Column(String(20), default="High")  # Critical, High, Medium, Low
    peak_confidence = Column(Float, default=0.0)
    average_confidence = Column(Float, default=0.0)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # Status: ALERT_TRIGGERED, CLIP_PROCESSING, AWAITING_REVIEW, RESOLVED
    status = Column(String(30), default="AWAITING_REVIEW")
    
    # Clip status: PENDING, PROCESSING, READY, FAILED
    clip_status = Column(String(20), default="PENDING")
    clip_path = Column(String(300), nullable=True)
    thumbnail_path = Column(String(300), nullable=True)
    
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    camera = relationship("Camera", back_populates="incidents")
    reviews = relationship("IncidentReview", back_populates="incident", cascade="all, delete-orphan")
    events = relationship("IncidentEvent", back_populates="incident", cascade="all, delete-orphan")

    def to_dict(self):
        latest_review = self.reviews[-1].to_dict() if self.reviews else None
        return {
            "id": self.id,
            "public_id": self.public_id,
            "camera_id": self.camera_id,
            "camera_name": self.camera.name if self.camera else None,
            "camera_location": self.camera.location if self.camera else None,
            "category": self.category,
            "raw_ai_label": self.raw_ai_label,
            "severity": self.severity,
            "peak_confidence": round(self.peak_confidence, 3),
            "average_confidence": round(self.average_confidence, 3),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": self.status,
            "clip_status": self.clip_status,
            "clip_url": f"/api/incidents/{self.id}/clip" if self.clip_status == "READY" else None,
            "thumbnail_url": f"/api/incidents/{self.id}/thumbnail" if self.thumbnail_path else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "latest_review": latest_review,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class IncidentReview(Base):
    __tablename__ = "incident_reviews"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    reviewer = Column(String(100), default="Operator")
    classification = Column(String(50), nullable=False)  # Confirmed Violence, False Positive / Not Violence, Needs Review
    reason = Column(String(150), nullable=True)  # E.g. "Sports / playful activity", "Crowd movement", etc.
    notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, default=datetime.datetime.utcnow)

    incident = relationship("Incident", back_populates="reviews")

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "reviewer": self.reviewer,
            "classification": self.classification,
            "reason": self.reason,
            "notes": self.notes,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # TRIGGERED, CLIP_GENERATED, ACKNOWLEDGED, REVIEWED
    event_at = Column(DateTime, default=datetime.datetime.utcnow)
    metadata_json = Column(Text, nullable=True)
    actor = Column(String(100), default="System")

    incident = relationship("Incident", back_populates="events")

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "event_type": self.event_type,
            "event_at": self.event_at.isoformat() if self.event_at else None,
            "metadata_json": self.metadata_json,
            "actor": self.actor,
        }


class AiPrediction(Base):
    __tablename__ = "ai_predictions"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    captured_at = Column(DateTime, default=datetime.datetime.utcnow)
    label = Column(String(100), nullable=False)
    normalized_category = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    processing_latency_ms = Column(Float, default=0.0)

    def to_dict(self):
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "label": self.label,
            "normalized_category": self.normalized_category,
            "confidence": round(self.confidence, 3),
            "processing_latency_ms": round(self.processing_latency_ms, 1),
        }
