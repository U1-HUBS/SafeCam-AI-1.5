import React, { useState } from "react";
import { Incident } from "../types";
import { X, CheckCircle, AlertOctagon, HelpCircle, Film, Shield, Send } from "lucide-react";

interface IncidentReviewModalProps {
  incident: Incident | null;
  onClose: () => void;
  onSubmitReview: (data: {
    incidentId: number;
    classification: string;
    reason?: string;
    notes?: string;
    reviewer?: string;
  }) => Promise<void>;
}

const FALSE_POSITIVE_REASONS = [
  "Sports / playful physical activity",
  "Hugging / horseplay",
  "Crowd movement",
  "Camera blur / lens reflection",
  "Lighting / shadow anomaly",
  "Occlusion / obstruction",
  "Sudden camera movement",
  "Non-violent scene misclassified",
  "Other"
];

export const IncidentReviewModal: React.FC<IncidentReviewModalProps> = ({
  incident,
  onClose,
  onSubmitReview,
}) => {
  const [classification, setClassification] = useState<
    "Confirmed Violence" | "False Positive / Not Violence" | "Needs Review"
  >("Confirmed Violence");
  const [reason, setReason] = useState<string>(FALSE_POSITIVE_REASONS[0]);
  const [notes, setNotes] = useState<string>("");
  const [reviewer, setReviewer] = useState<string>("Security Officer");
  const [submitting, setSubmitting] = useState<boolean>(false);

  if (!incident) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmitReview({
        incidentId: incident.id,
        classification,
        reason: classification.includes("False Positive") ? reason : undefined,
        notes,
        reviewer,
      });
      onClose();
    } catch (err) {
      console.error("Error submitting review:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-sentinel-card border border-sentinel-border rounded-2xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-sentinel-border flex items-center justify-between bg-slate-900/80">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-sm text-blue-400 font-bold">{incident.public_id}</span>
              <span className="text-gray-500">•</span>
              <span className="text-xs text-gray-400">{incident.camera_name} ({incident.camera_location})</span>
            </div>
            <h2 className="text-base font-bold text-white mt-0.5">Incident Review & Classification</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Video Player & Clip details (7 cols) */}
          <div className="lg:col-span-7 flex flex-col space-y-4">
            <div className="aspect-video bg-black rounded-xl overflow-hidden border border-sentinel-border relative flex items-center justify-center">
              {incident.clip_status === "READY" ? (
                <video
                  src={`http://localhost:5000/api/incidents/${incident.id}/clip`}
                  controls
                  autoPlay
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="flex flex-col items-center justify-center text-gray-400 text-xs p-6 text-center">
                  <Film className="w-10 h-10 mb-2 opacity-50 text-blue-400 animate-spin" />
                  <span className="font-semibold text-gray-300">Assembling Pre & Post Event Video Clip...</span>
                  <span className="text-[11px] text-gray-500 mt-1">
                    Clip Status: {incident.clip_status}
                  </span>
                </div>
              )}
            </div>

            {/* AI Incident Metadata Box */}
            <div className="bg-slate-900/60 border border-sentinel-border rounded-xl p-4 text-xs space-y-2">
              <div className="flex justify-between items-center pb-2 border-b border-sentinel-border/50">
                <span className="text-gray-400 font-medium">Detection Category:</span>
                <span className="font-bold text-red-400">{incident.category}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Peak Confidence:</span>
                <span className="font-mono text-white font-semibold">{(incident.peak_confidence * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Average Confidence:</span>
                <span className="font-mono text-white">{(incident.average_confidence * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Detected Timestamp:</span>
                <span className="font-mono text-gray-300">{new Date(incident.detected_at).toLocaleString()}</span>
              </div>
              {incident.raw_ai_label && (
                <div className="flex justify-between items-center pt-1 border-t border-sentinel-border/50 text-[11px]">
                  <span className="text-gray-500">Raw AI Label:</span>
                  <span className="text-gray-400 font-mono truncate max-w-[220px]">{incident.raw_ai_label}</span>
                </div>
              )}
            </div>
          </div>

          {/* Right: Review Form (5 cols) */}
          <div className="lg:col-span-5 flex flex-col justify-between">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-2 uppercase tracking-wide">
                  Classification Decision
                </label>
                <div className="grid grid-cols-1 gap-2">
                  <button
                    type="button"
                    onClick={() => setClassification("Confirmed Violence")}
                    className={`p-3 rounded-xl border text-left flex items-center space-x-3 transition ${
                      classification === "Confirmed Violence"
                        ? "bg-red-500/20 border-red-500 text-white font-bold"
                        : "bg-slate-900 border-sentinel-border text-gray-300 hover:border-slate-600"
                    }`}
                  >
                    <AlertOctagon className="w-5 h-5 text-red-500 shrink-0" />
                    <div>
                      <div className="text-xs font-bold">Confirmed Violence</div>
                      <div className="text-[10px] text-gray-400">Verified altercation / violent act</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setClassification("False Positive / Not Violence")}
                    className={`p-3 rounded-xl border text-left flex items-center space-x-3 transition ${
                      classification === "False Positive / Not Violence"
                        ? "bg-emerald-500/20 border-emerald-500 text-white font-bold"
                        : "bg-slate-900 border-sentinel-border text-gray-300 hover:border-slate-600"
                    }`}
                  >
                    <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
                    <div>
                      <div className="text-xs font-bold">False Positive / Not Violence</div>
                      <div className="text-[10px] text-gray-400">Normal activity or misclassification</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setClassification("Needs Review")}
                    className={`p-3 rounded-xl border text-left flex items-center space-x-3 transition ${
                      classification === "Needs Review"
                        ? "bg-amber-500/20 border-amber-500 text-white font-bold"
                        : "bg-slate-900 border-sentinel-border text-gray-300 hover:border-slate-600"
                    }`}
                  >
                    <HelpCircle className="w-5 h-5 text-amber-400 shrink-0" />
                    <div>
                      <div className="text-xs font-bold">Needs Review</div>
                      <div className="text-[10px] text-gray-400">Escalate for further supervisor investigation</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* False Positive Reason dropdown (if selected) */}
              {classification === "False Positive / Not Violence" && (
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">
                    False Positive Reason:
                  </label>
                  <select
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                  >
                    {FALSE_POSITIVE_REASONS.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Reviewer Name */}
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  Reviewer Name:
                </label>
                <input
                  type="text"
                  value={reviewer}
                  onChange={(e) => setReviewer(e.target.value)}
                  className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                  placeholder="e.g. Officer Smith"
                />
              </div>

              {/* Review Notes */}
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  Review Notes:
                </label>
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 resize-none"
                  placeholder="Provide context or explanation for auditing..."
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2.5 rounded-xl text-xs flex items-center justify-center space-x-2 shadow-lg shadow-blue-600/20 transition disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{submitting ? "Saving Review..." : "Submit Classification & Audit"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
