from flask import Blueprint, jsonify
from backend.database import SessionLocal
from backend.models import Incident, IncidentReview, Camera
from backend.auth import roles_required

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("/summary", methods=["GET"])
@roles_required("admin", "supervisor")
def get_summary_report():
    db = SessionLocal()
    try:
        all_incidents = db.query(Incident).all()
        total_alerts = len(all_incidents)

        confirmed_count = 0
        false_positive_count = 0
        needs_review_count = 0
        awaiting_review_count = 0

        by_camera = {}
        by_severity = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        by_category = {}

        for inc in all_incidents:
            cam_name = inc.camera.name if inc.camera else f"Camera #{inc.camera_id}"
            by_camera[cam_name] = by_camera.get(cam_name, 0) + 1

            sev = inc.severity or "Medium"
            by_severity[sev] = by_severity.get(sev, 0) + 1

            cat = inc.category or "Other"
            by_category[cat] = by_category.get(cat, 0) + 1

            if inc.reviews:
                last_cls = inc.reviews[-1].classification
                if "Confirmed" in last_cls:
                    confirmed_count += 1
                elif "False Positive" in last_cls:
                    false_positive_count += 1
                elif "Needs Review" in last_cls:
                    needs_review_count += 1
            else:
                awaiting_review_count += 1

        reviewed_total = confirmed_count + false_positive_count
        fp_rate = (false_positive_count / reviewed_total * 100) if reviewed_total > 0 else 0.0

        return jsonify({
            "total_alerts": total_alerts,
            "confirmed_violence": confirmed_count,
            "false_positives": false_positive_count,
            "needs_review": needs_review_count,
            "awaiting_review": awaiting_review_count,
            "false_positive_rate": round(fp_rate, 1),
            "by_camera": by_camera,
            "by_severity": by_severity,
            "by_category": by_category,
        })
    finally:
        db.close()
