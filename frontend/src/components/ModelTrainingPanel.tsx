import React, { useState, useEffect, useRef } from "react";
import {
  Brain,
  Zap,
  Download,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Layers,
  Activity,
  Terminal,
  ShieldCheck,
  ShieldAlert,
  Check
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

import { API_BASE } from "../config/api";

interface TrainingStats {
  total_reviewed: number;
  confirmed_violence: number;
  false_positives: number;
  needs_review: number;
  estimated_frames: number;
  ready_to_train: boolean;
  recommended_min_samples: number;
  active_model: {
    model_name: string;
    version: string;
    is_trained: boolean;
    trained_at: string | null;
    accuracy: number | null;
    path: string | null;
  };
}

interface TrainingStatus {
  is_training: boolean;
  status: string;
  progress_percent: number;
  current_stage_label: string;
  metrics: {
    accuracy: number;
    samples_used: number;
    total_frames: number;
    fp_suppression_rate?: number;
  } | null;
  logs: string[];
  error_message: string | null;
  last_completed_at: string | null;
  active_version: string;
}

export const ModelTrainingPanel: React.FC = () => {
  const { authFetch } = useAuth();
  const [stats, setStats] = useState<TrainingStats | null>(null);
  const [status, setStatus] = useState<TrainingStatus | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);

  const fetchStats = async () => {
    try {
      const res = await authFetch(`${API_BASE}/training/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error("Failed to load training stats:", e);
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await authFetch(`${API_BASE}/training/status`);
      if (res.ok) {
        const data: TrainingStatus = await res.json();
        setStatus(data);
        if (data.is_training) {
          // Continue polling if still training
          if (!pollingRef.current) {
            pollingRef.current = setInterval(fetchStatus, 1200);
          }
        } else if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
          fetchStats(); // Refresh stats on completion
        }
      }
    } catch (e) {
      console.error("Failed to fetch training status:", e);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchStatus();

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [status?.logs]);

  const handleStartTraining = async () => {
    setFeedbackMsg(null);
    try {
      const res = await authFetch(`${API_BASE}/training/start`, {
        method: "POST",
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setFeedbackMsg({
          type: "success",
          text: "Safecam AI active learning background worker started!",
        });
        fetchStatus();
        if (!pollingRef.current) {
          pollingRef.current = setInterval(fetchStatus, 1200);
        }
      } else {
        setFeedbackMsg({
          type: "error",
          text: data.message || "Failed to trigger training session.",
        });
      }
    } catch (e) {
      setFeedbackMsg({
        type: "error",
        text: "Network error triggering training session.",
      });
    }
  };

  const handleExportDataset = async () => {
    setIsExporting(true);
    setFeedbackMsg(null);
    try {
      const res = await authFetch(`${API_BASE}/training/export`, {
        method: "POST",
      });
      const data = await res.json();
      if (res.ok && data.success && data.download_url) {
        window.open(`${API_BASE.replace('/api', '')}${data.download_url}`, "_blank");
        setFeedbackMsg({
          type: "success",
          text: `Dataset archive created (${data.filename})! Download starting...`,
        });
      } else {
        setFeedbackMsg({
          type: "error",
          text: data.error || "Failed to export dataset.",
        });
      }
    } catch (e) {
      setFeedbackMsg({
        type: "error",
        text: "Error exporting dataset archive.",
      });
    } finally {
      setIsExporting(false);
    }
  };

  const isTrainingActive = status?.is_training ?? false;
  const currentProgress = status?.progress_percent ?? 0;

  return (
    <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 space-y-5">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-sentinel-border/50 pb-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-blue-500/10 border border-blue-500/30 rounded-lg text-blue-400">
            <Brain className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-white tracking-wide">
                Safecam AI Fine-Tuning & Model Management
              </h2>
              <span className="px-2 py-0.5 text-[10px] font-mono font-semibold rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/40">
                {status?.active_version || stats?.active_model?.version || "v1.0-baseline"}
              </span>
              {stats?.active_model?.is_trained && (
                <span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1">
                  <Check className="w-3 h-3" /> Calibrated Head Hot-Reloaded
                </span>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              Refine Safecam AI using operator-reviewed incidents to eliminate false alarms and maximize detection accuracy.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleExportDataset}
            disabled={isExporting || isTrainingActive}
            className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-gray-200 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 border border-slate-700 rounded-lg transition-colors"
            title="Download reviewed clips and frames formatted for PyTorch / YOLO"
          >
            {isExporting ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-400" />
            ) : (
              <Download className="w-3.5 h-3.5 text-gray-400" />
            )}
            Export Dataset ZIP
          </button>

          <button
            onClick={handleStartTraining}
            disabled={isTrainingActive}
            className="flex items-center gap-2 px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 active:bg-blue-700 disabled:opacity-50 rounded-lg shadow-lg shadow-blue-500/20 transition-all border border-blue-400/30"
          >
            {isTrainingActive ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-white" />
                <span>Training Safecam AI... ({currentProgress}%)</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4 text-amber-300 fill-amber-300" />
                <span>Train More on Audits</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* User Alerts / Feedback */}
      {feedbackMsg && (
        <div
          className={`p-3 rounded-lg text-xs flex items-center justify-between border ${
            feedbackMsg.type === "success"
              ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300"
              : "bg-red-950/40 border-red-500/40 text-red-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {feedbackMsg.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-400" />
            ) : (
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
            )}
            <span>{feedbackMsg.text}</span>
          </div>
          <button
            onClick={() => setFeedbackMsg(null)}
            className="text-gray-400 hover:text-white text-xs ml-4"
          >
            ✕
          </button>
        </div>
      )}

      {/* Dataset & Model Stats Grid */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-slate-900/80 border border-sentinel-border rounded-lg p-3">
            <div className="flex items-center justify-between text-gray-400 text-[11px] font-semibold">
              <span>CONFIRMED VIOLENCE</span>
              <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
            </div>
            <div className="text-xl font-bold font-mono text-red-400 mt-1">
              {stats.confirmed_violence}
            </div>
            <div className="text-[10px] text-gray-500 mt-0.5">Ground-truth class 1</div>
          </div>

          <div className="bg-slate-900/80 border border-sentinel-border rounded-lg p-3">
            <div className="flex items-center justify-between text-gray-400 text-[11px] font-semibold">
              <span>FALSE POSITIVES</span>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
              {stats.false_positives}
            </div>
            <div className="text-[10px] text-gray-500 mt-0.5">Ground-truth class 0</div>
          </div>

          <div className="bg-slate-900/80 border border-sentinel-border rounded-lg p-3">
            <div className="flex items-center justify-between text-gray-400 text-[11px] font-semibold">
              <span>FRAME SAMPLES</span>
              <Layers className="w-3.5 h-3.5 text-blue-400" />
            </div>
            <div className="text-xl font-bold font-mono text-white mt-1">
              ~{stats.estimated_frames}
            </div>
            <div className="text-[10px] text-gray-500 mt-0.5">Sampled @ 2 FPS</div>
          </div>

          <div className="bg-slate-900/80 border border-sentinel-border rounded-lg p-3">
            <div className="flex items-center justify-between text-gray-400 text-[11px] font-semibold">
              <span>CALIBRATED ACCURACY</span>
              <Activity className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="text-xl font-bold font-mono text-amber-400 mt-1">
              {status?.metrics?.accuracy
                ? `${status.metrics.accuracy}%`
                : stats.active_model.accuracy
                ? `${stats.active_model.accuracy}%`
                : "Baseline"}
            </div>
            <div className="text-[10px] text-gray-500 mt-0.5">Validation score</div>
          </div>
        </div>
      )}

      {/* Progress & Live Logs Section (visible during or after training) */}
      {(isTrainingActive || status?.logs?.length) && (
        <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-gray-300 font-medium">
              <RefreshCw
                className={`w-3.5 h-3.5 ${
                  isTrainingActive ? "animate-spin text-blue-400" : "text-emerald-400"
                }`}
              />
              <span>{status?.current_stage_label || "Idle"}</span>
            </div>
            <span className="font-mono text-blue-400 font-semibold">{currentProgress}%</span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-blue-600 via-indigo-500 to-emerald-400 transition-all duration-300"
              style={{ width: `${currentProgress}%` }}
            />
          </div>

          {/* Terminal Logs */}
          <div className="bg-black/80 rounded border border-slate-900 p-2.5 font-mono text-[11px] text-gray-300 max-h-36 overflow-y-auto space-y-1">
            <div className="flex items-center gap-1.5 text-gray-500 mb-1 border-b border-gray-800 pb-1 text-[10px] uppercase font-semibold">
              <Terminal className="w-3 h-3" />
              <span>Safecam AI Active Learning Console</span>
            </div>
            {status?.logs?.map((log, idx) => (
              <div
                key={idx}
                className={
                  log.includes("ERROR")
                    ? "text-red-400"
                    : log.includes("Hot-Reloaded") || log.includes("complete")
                    ? "text-emerald-400"
                    : "text-gray-300"
                }
              >
                {log}
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}
    </div>
  );
};
