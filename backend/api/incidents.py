import os
import datetime
from flask import Blueprint, request, jsonify, send_file, Response
from backend.database import SessionLocal
from backend.models import Incident, IncidentReview, IncidentEvent

incidents_bp = Blueprint("incidents", __name__)

# Real-time event callback hook
event_callback = None

def set_event_callback(cb):
    global event_callback
    event_callback = cb


@incidents_bp.route("", methods=["GET"])
def list_incidents():
    db = SessionLocal()
    try:
        query = db.query(Incident)

        # Filters
        camera_id = request.args.get("camera_id")
        if camera_id:
            query = query.filter(Incident.camera_id == int(camera_id))

        status = request.args.get("status")
        if status:
            query = query.filter(Incident.status == status)

        severity = request.args.get("severity")
        if severity:
            query = query.filter(Incident.severity == severity)

        # Order newest first
        incidents = query.order_by(Incident.detected_at.desc()).limit(100).all()
        return jsonify([inc.to_dict() for inc in incidents])
    finally:
        db.close()


@incidents_bp.route("/<int:incident_id>", methods=["GET"])
def get_incident(incident_id):
    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return jsonify({"error": "Incident not found"}), 404

        data = incident.to_dict()
        data["events"] = [e.to_dict() for e in incident.events]
        data["reviews"] = [r.to_dict() for r in incident.reviews]
        return jsonify(data)
    finally:
        db.close()


@incidents_bp.route("/<int:incident_id>/acknowledge", methods=["POST"])
def acknowledge_incident(incident_id):
    data = request.json or {}
    operator_name = data.get("operator", "Security Operator")

    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return jsonify({"error": "Incident not found"}), 404

        incident.acknowledged_at = datetime.datetime.utcnow()
        incident.acknowledged_by = operator_name
        
        event = IncidentEvent(
            incident_id=incident.id,
            event_type="ACKNOWLEDGED",
            actor=operator_name
        )
        db.add(event)
        db.commit()

        if event_callback:
            event_callback({
                "type": "incident.acknowledged",
                "incident_id": incident.id,
                "acknowledged_by": operator_name
            })

        return jsonify(incident.to_dict())
    finally:
        db.close()


@incidents_bp.route("/<int:incident_id>/review", methods=["POST"])
def review_incident(incident_id):
    data = request.json or {}
    classification = data.get("classification")
    if not classification:
        return jsonify({"error": "classification is required"}), 400

    reviewer = data.get("reviewer", "Supervisor")
    reason = data.get("reason", "")
    notes = data.get("notes", "")

    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return jsonify({"error": "Incident not found"}), 404

        review = IncidentReview(
            incident_id=incident.id,
            reviewer=reviewer,
            classification=classification,
            reason=reason,
            notes=notes
        )
        db.add(review)

        incident.status = "RESOLVED"
        event = IncidentEvent(
            incident_id=incident.id,
            event_type="REVIEWED",
            actor=reviewer,
            metadata_json=f'{{"classification": "{classification}", "reason": "{reason}"}}'
        )
        db.add(event)
        db.commit()

        if event_callback:
            event_callback({
                "type": "incident.reviewed",
                "incident_id": incident.id,
                "classification": classification
            })

        return jsonify(incident.to_dict())
    finally:
        db.close()


@incidents_bp.route("/<int:incident_id>/clip", methods=["GET"])
def get_incident_clip(incident_id):
    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident or not incident.clip_path or not os.path.exists(incident.clip_path):
            return jsonify({"error": "Clip not ready or not found"}), 404

        # Guarantee clip is in browser-decodable H.264 format
        from backend.services.clip_service import ensure_clip_browser_playable
        ensure_clip_browser_playable(incident.clip_path)

        # conditional=True enables HTTP 206 Partial Content byte-range streaming for HTML5 video players
        response = send_file(incident.clip_path, mimetype="video/mp4", conditional=True)
        response.headers["Accept-Ranges"] = "bytes"
        return response
    finally:
        db.close()


@incidents_bp.route("/<int:incident_id>/thumbnail", methods=["GET"])
def get_incident_thumbnail(incident_id):
    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident or not incident.thumbnail_path or not os.path.exists(incident.thumbnail_path):
            return jsonify({"error": "Thumbnail not found"}), 404

        return send_file(incident.thumbnail_path, mimetype="image/jpeg")
    finally:
        db.close()
