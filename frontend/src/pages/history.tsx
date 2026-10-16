import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Header } from "../components/Header";
import { IncidentReviewModal } from "../components/IncidentReviewModal";
import { Incident, Camera } from "../types";
import { Search, Filter, PlayCircle, ShieldCheck, AlertOctagon, HelpCircle, Film } from "lucide-react";
import { useAuth } from "../context/AuthContext";

import { API_BASE } from "../config/api";

export default function HistoryPage() {
  const { authFetch, user } = useAuth();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [cameraFilter, setCameraFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [classificationFilter, setClassificationFilter] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const [incRes, camRes] = await Promise.all([
        authFetch(`${API_BASE}/incidents`),
        authFetch(`${API_BASE}/cameras`),
      ]);
      if (incRes.ok) setIncidents(await incRes.json());
      if (camRes.ok) setCameras(await camRes.json());
    } catch (e) {
      console.error("Failed to fetch history:", e);
    }
  }, [authFetch]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Dynamically build filter list of active and historic removed cameras
  const cameraOptions = useMemo(() => {
    const map = new Map<string, string>();
    cameras.forEach((c) => map.set(String(c.id), c.name));
    incidents.forEach((i) => {
      if (i.camera_id && !map.has(String(i.camera_id))) {
        map.set(String(i.camera_id), i.camera_name ? `${i.camera_name} (Removed)` : `Camera #${i.camera_id} (Removed)`);
      }
    });
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [cameras, incidents]);

  const filteredIncidents = incidents.filter((inc) => {
    if (search && !inc.public_id.toLowerCase().includes(search.toLowerCase()) &&
        !inc.category.toLowerCase().includes(search.toLowerCase()) &&
        !(inc.camera_name || "").toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (cameraFilter && String(inc.camera_id) !== cameraFilter) return false;
    if (severityFilter && inc.severity !== severityFilter) return false;
    if (classificationFilter) {
      const cls = inc.latest_review?.classification || "Awaiting Review";
      if (!cls.includes(classificationFilter)) return false;
    }
    return true;
  });

  const handleSubmitReview = async (reviewData: {
    incidentId: number;
    classification: string;
    reason?: string;
    notes?: string;
    reviewer?: string;
  }) => {
    await authFetch(`${API_BASE}/incidents/${reviewData.incidentId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...reviewData,
        reviewer: reviewData.reviewer || user?.name || "Reviewer",
      }),
    });
    fetchData();
  };


  return (
    <>
      <Header cameraCount={cameras.length} activeAlertCount={0} />

      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Title & Filter Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide">Incident History & Audit Log</h1>
            <p className="text-xs text-gray-400 mt-0.5">
              Search, filter, and inspect past AI violence detections and operator reviews.
            </p>
          </div>

          {/* Search Input */}
          <div className="flex items-center space-x-2">
            <div className="relative">
              <Search className="w-4 h-4 text-gray-500 absolute left-3 top-2.5" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search incident ID, category..."
                className="bg-slate-900 border border-sentinel-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500 w-64"
              />
            </div>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-3.5 flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center space-x-1.5 text-gray-400">
            <Filter className="w-3.5 h-3.5" />
            <span className="font-semibold text-gray-300">Filters:</span>
          </div>

          <select
            value={cameraFilter}
            onChange={(e) => setCameraFilter(e.target.value)}
            className="bg-slate-900 border border-sentinel-border rounded-lg px-2.5 py-1.5 text-white text-xs focus:outline-none"
          >
            <option value="">All Cameras</option>
            {cameraOptions.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-900 border border-sentinel-border rounded-lg px-2.5 py-1.5 text-white text-xs focus:outline-none"
          >
            <option value="">All Severities</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>

          <select
            value={classificationFilter}
            onChange={(e) => setClassificationFilter(e.target.value)}
            className="bg-slate-900 border border-sentinel-border rounded-lg px-2.5 py-1.5 text-white text-xs focus:outline-none"
          >
            <option value="">All Classifications</option>
            <option value="Confirmed">Confirmed Violence</option>
            <option value="False Positive">False Positive</option>
            <option value="Needs Review">Needs Review</option>
            <option value="Awaiting Review">Awaiting Review</option>
          </select>

          <div className="ml-auto text-gray-400 text-xs">
            Showing <strong className="text-white">{filteredIncidents.length}</strong> of {incidents.length} incidents
          </div>
        </div>

        {/* Table */}
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl overflow-hidden shadow">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-900/80 border-b border-sentinel-border text-gray-400 uppercase tracking-wider text-[10px]">
                <th className="py-3 px-4">Incident ID</th>
                <th className="py-3 px-4">Camera & Location</th>
                <th className="py-3 px-4">Detected Time</th>
                <th className="py-3 px-4">AI Category</th>
                <th className="py-3 px-4">Peak Conf</th>
                <th className="py-3 px-4">Classification</th>
                <th className="py-3 px-4">Reviewer</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sentinel-border">
              {filteredIncidents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-gray-500">
                    No incident records match the selected criteria.
                  </td>
                </tr>
              ) : (
                filteredIncidents.map((inc) => {
                  const rev = inc.latest_review;
                  return (
                    <tr key={inc.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 font-mono font-bold text-blue-400">
                        {inc.public_id}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-white">{inc.camera_name || (inc.camera_id ? `Cam #${inc.camera_id}` : "Removed Camera")}</div>
                        <div className="text-[11px] text-gray-400">{inc.camera_location || "N/A"}</div>
                      </td>
                      <td className="py-3 px-4 text-gray-300">
                        {new Date(inc.detected_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-medium text-white">{inc.category}</span>
                      </td>
                      <td className="py-3 px-4 font-mono text-gray-300">
                        {(inc.peak_confidence * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-4">
                        {rev ? (
                          rev.classification.includes("Confirmed") ? (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">
                              <AlertOctagon className="w-3 h-3" />
                              <span>Confirmed Violence</span>
                            </span>
                          ) : rev.classification.includes("False Positive") ? (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                              <ShieldCheck className="w-3 h-3" />
                              <span>False Positive</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                              <HelpCircle className="w-3 h-3" />
                              <span>Needs Review</span>
                            </span>
                          )
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-800 text-gray-400 border border-gray-700">
                            Awaiting Review
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-gray-400">
                        {rev ? rev.reviewer : "—"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => setSelectedIncident(inc)}
                          className="px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-blue-400 text-xs font-medium inline-flex items-center space-x-1 transition"
                        >
                          <Film className="w-3.5 h-3.5" />
                          <span>Inspect Clip</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </main>

      <IncidentReviewModal
        incident={selectedIncident}
        onClose={() => setSelectedIncident(null)}
        onSubmitReview={handleSubmitReview}
      />
    </>
  );
}
