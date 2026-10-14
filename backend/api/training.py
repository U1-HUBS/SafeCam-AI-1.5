import os
from pathlib import Path
from flask import Blueprint, jsonify, request, send_file

from backend.config import DATASETS_DIR
from backend.services.training_service import trainer_service, dataset_manager

training_bp = Blueprint("training", __name__)


@training_bp.route("/stats", methods=["GET"])
def get_stats():
    """Returns dataset review counts, estimated frames, and active model status."""
    stats = dataset_manager.get_audit_dataset_stats()
    return jsonify(stats), 200


@training_bp.route("/start", methods=["POST"])
def start_training():
    """Trigger background retraining of the SafeCamViolenceHead."""
    status_info = trainer_service.get_status()
    if status_info.get("is_training"):
        return jsonify({
            "success": False,
            "message": "A training session is already in progress.",
            "status": status_info
        }), 409

    success = trainer_service.start_training()
    if not success:
        return jsonify({
            "success": False,
            "message": "Failed to initiate training session."
        }), 400

    return jsonify({
        "success": True,
        "message": "Safecam AI model training started.",
        "status": trainer_service.get_status()
    }), 200


@training_bp.route("/status", methods=["GET"])
def get_status():
    """Returns real-time progress, stage, logs, and metrics of training."""
    return jsonify(trainer_service.get_status()), 200


@training_bp.route("/export", methods=["POST"])
def export_dataset():
    """Exports reviewed incidents and frames into a downloadable ZIP archive."""
    try:
        export_id, zip_path = dataset_manager.export_dataset_zip()
        return jsonify({
            "success": True,
            "export_id": export_id,
            "filename": zip_path.name,
            "download_url": f"/api/training/download/{export_id}"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@training_bp.route("/download/<export_id>", methods=["GET"])
def download_dataset(export_id: str):
    """Downloads the exported dataset ZIP archive."""
    # Sanitize export_id
    safe_name = os.path.basename(export_id)
    if not safe_name.endswith(".zip"):
        safe_name = f"{safe_name}.zip"

    zip_file = DATASETS_DIR / safe_name
    if not zip_file.exists():
        return jsonify({"error": "Dataset archive not found"}), 404

    return send_file(
        str(zip_file),
        mimetype="application/zip",
        as_attachment=True,
        download_name=safe_name
    )
