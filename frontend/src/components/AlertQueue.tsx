import React from "react";
import { Incident } from "../types";
import { AlertCircle, CheckCircle2, PlayCircle, Clock } from "lucide-react";

interface AlertQueueProps {
  alerts: Incident[];
  onAcknowledge: (incidentId: number) => void;
  onOpenReview: (incident: Incident) => void;
}

export const AlertQueue: React.FC<AlertQueueProps> = ({
  alerts,
  onAcknowledge,
  onOpenReview,
}) => {
  if (alerts.length === 0) {
    return (
      <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-4 flex items-center justify-between text-xs text-gray-400">
        <div className="flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          <span>No active incidents requiring immediate attention. All streams normal.</span>
        </div>
        <span className="text-[11px] text-gray-500 font-mono">Status: MONITORING</span>
      </div>
    );
  }

  return (
    <div className="bg-sentinel-card border border-red-500/40 rounded-xl overflow-hidden shadow-lg">
      <div className="px-4 py-2.5 bg-red-950/40 border-b border-red-500/30 flex items-center justify-between">
        <div className="flex items-center space-x-2 text-red-400 font-bold text-xs uppercase tracking-wider">
          <AlertCircle className="w-4 h-4 text-red-400 animate-pulse" />
          <span>Active Incident Alerts ({alerts.length})</span>
        </div>
        <span className="text-[11px] text-red-300 font-medium">Requires Operator Review</span>
      </div>

      <div className="divide-y divide-sentinel-border max-h-64 overflow-y-auto">
        {alerts.map((alert) => {
          const isAcked = !!alert.acknowledged_at;
          const sevColor =
            alert.severity === "Critical"
              ? "bg-red-600 text-white"
              : alert.severity === "High"
              ? "bg-orange-600 text-white"
              : "bg-yellow-600 text-white";

          return (
            <div
              key={alert.id}
              className={`p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 transition ${
                isAcked ? "bg-slate-900/40" : "bg-red-500/5 hover:bg-red-500/10"
              }`}
            >
              {/* Alert details */}
              <div className="flex items-start space-x-3">
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${sevColor}`}>
                  {alert.severity}
                </span>

                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-white tracking-wide">
                      {alert.category}
                    </span>
                    <span className="text-gray-400 text-xs font-mono">• {alert.public_id}</span>
                  </div>
                  <div className="flex items-center space-x-3 text-[11px] text-gray-400 mt-0.5">
                    <span>
                      Camera: <strong className="text-gray-200">{alert.camera_name || (alert.camera_id ? `Cam #${alert.camera_id}` : "Removed Camera")}</strong>
                    </span>
                    <span>
                      Confidence: <strong className="text-white">{(alert.peak_confidence * 100).toFixed(1)}%</strong>
                    </span>
                    <span className="flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-gray-500" />
                      <span>{alert.detected_at ? new Date(alert.detected_at).toLocaleTimeString() : "Just now"}</span>
                    </span>
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center space-x-2 self-end md:self-center">
                {!isAcked ? (
                  <button
                    onClick={() => onAcknowledge(alert.id)}
                    className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-xs text-gray-200 font-medium transition"
                  >
                    Acknowledge
                  </button>
                ) : (
                  <span className="text-[11px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-md">
                    Acked: {alert.acknowledged_by}
                  </span>
                )}

                <button
                  onClick={() => onOpenReview(alert)}
                  className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-semibold flex items-center space-x-1.5 shadow transition"
                >
                  <PlayCircle className="w-3.5 h-3.5" />
                  <span>Review Incident</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
