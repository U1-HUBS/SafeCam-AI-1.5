import React, { useState, useEffect, useCallback } from "react";
import { Header } from "../components/Header";
import { SummaryReport, Camera } from "../types";
import { AlertCircle, CheckCircle, ShieldAlert, TrendingDown, Camera as CameraIcon } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const API_BASE = "http://localhost:5000/api";

export default function ReportsPage() {
  const { authFetch } = useAuth();
  const [report, setReport] = useState<SummaryReport | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchReports = useCallback(async () => {
    try {
      const [repRes, camRes] = await Promise.all([
        authFetch(`${API_BASE}/reports/summary`),
        authFetch(`${API_BASE}/cameras`),
      ]);
      if (repRes.ok) setReport(await repRes.json());
      if (camRes.ok) setCameras(await camRes.json());
    } catch (e) {
      console.error("Failed to load reports:", e);
    } finally {
      setLoading(false);
    }
  }, [authFetch]);


  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  return (
    <>
      <Header cameraCount={cameras.length} activeAlertCount={0} />

      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        <div>
          <h1 className="text-xl font-bold text-white tracking-wide">Surveillance Analytics & Model KPIs</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Evaluate violence detection accuracy, review throughput, and camera false-positive rates.
          </p>
        </div>

        {/* KPI Cards */}
        {report && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-4">
              <div className="text-gray-400 text-xs font-semibold uppercase">Total AI Alerts</div>
              <div className="text-2xl font-bold text-white mt-1 font-mono">{report.total_alerts}</div>
              <div className="text-[11px] text-gray-500 mt-1">Aggregated events</div>
            </div>

            <div className="bg-sentinel-card border border-red-500/30 rounded-xl p-4">
              <div className="text-red-400 text-xs font-semibold uppercase">Confirmed Violence</div>
              <div className="text-2xl font-bold text-red-400 mt-1 font-mono">{report.confirmed_violence}</div>
              <div className="text-[11px] text-gray-500 mt-1">Verified by operator</div>
            </div>

            <div className="bg-sentinel-card border border-emerald-500/30 rounded-xl p-4">
              <div className="text-emerald-400 text-xs font-semibold uppercase">False Positives</div>
              <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">{report.false_positives}</div>
              <div className="text-[11px] text-gray-500 mt-1">Feedback dataset</div>
            </div>

            <div className="bg-sentinel-card border border-amber-500/30 rounded-xl p-4">
              <div className="text-amber-400 text-xs font-semibold uppercase">Needs Review</div>
              <div className="text-2xl font-bold text-amber-400 mt-1 font-mono">{report.needs_review}</div>
              <div className="text-[11px] text-gray-500 mt-1">Escalated cases</div>
            </div>

            <div className="bg-sentinel-card border border-blue-500/30 rounded-xl p-4">
              <div className="text-blue-400 text-xs font-semibold uppercase">FP Rate</div>
              <div className="text-2xl font-bold text-blue-400 mt-1 font-mono">{report.false_positive_rate}%</div>
              <div className="text-[11px] text-gray-500 mt-1">Of reviewed incidents</div>
            </div>
          </div>
        )}

        {/* Charts and Visual Breakdown */}
        {report && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* By Severity */}
            <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300">
                Incidents by Severity
              </h3>
              <div className="space-y-3">
                {Object.entries(report.by_severity).map(([sev, count]) => {
                  const maxCount = Math.max(...Object.values(report.by_severity), 1);
                  const pct = (count / maxCount) * 100;
                  const barColor =
                    sev === "Critical"
                      ? "bg-red-600"
                      : sev === "High"
                      ? "bg-orange-500"
                      : sev === "Medium"
                      ? "bg-yellow-500"
                      : "bg-blue-500";

                  return (
                    <div key={sev} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-300 font-medium">{sev}</span>
                        <span className="font-mono text-gray-400">{count}</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${barColor}`}
                          style={{ width: `${pct}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* By Category */}
            <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300">
                Incidents by Detection Category
              </h3>
              <div className="space-y-3">
                {Object.entries(report.by_category).length === 0 ? (
                  <p className="text-xs text-gray-500">No detection category records yet.</p>
                ) : (
                  Object.entries(report.by_category).map(([cat, count]) => {
                    const maxCount = Math.max(...Object.values(report.by_category), 1);
                    const pct = (count / maxCount) * 100;
                    return (
                      <div key={cat} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-300 font-medium">{cat}</span>
                          <span className="font-mono text-gray-400">{count}</span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-blue-600"
                            style={{ width: `${pct}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* By Camera Distribution */}
            <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 space-y-4 md:col-span-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300">
                Alert Volume by Camera
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(report.by_camera).length === 0 ? (
                  <p className="text-xs text-gray-500 col-span-4">No camera alert records yet.</p>
                ) : (
                  Object.entries(report.by_camera).map(([camName, count]) => (
                    <div
                      key={camName}
                      className="bg-slate-900 border border-sentinel-border rounded-lg p-3 text-xs"
                    >
                      <div className="flex items-center space-x-2 text-gray-400">
                        <CameraIcon className="w-3.5 h-3.5 text-blue-400" />
                        <span className="font-medium text-white truncate">{camName}</span>
                      </div>
                      <div className="text-xl font-bold text-white font-mono mt-2">{count}</div>
                      <div className="text-[10px] text-gray-500 mt-0.5">Total Triggered Alerts</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
