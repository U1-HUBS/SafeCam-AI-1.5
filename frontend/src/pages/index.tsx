import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Header } from "../components/Header";
import { CameraWall } from "../components/CameraWall";
import { AlertQueue } from "../components/AlertQueue";
import { IncidentReviewModal } from "../components/IncidentReviewModal";
import { CameraModal } from "../components/CameraModal";
import { Camera, Incident } from "../types";
import { playAlertChime } from "../utils/audio";
import { useAuth } from "../context/AuthContext";

const API_BASE = "http://localhost:5000/api";

export default function SurveillancePage() {
  const { authFetch, user } = useAuth();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [cameraModalOpen, setCameraModalOpen] = useState(false);
  const [editingCamera, setEditingCamera] = useState<Camera | null>(null);
  const [modalInitialMode, setModalInitialMode] = useState<"upload" | "library" | "rtsp">("upload");
  const [yoloLabelsEnabled, setYoloLabelsEnabled] = useState(true);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("cctv_yolo_labels");
      if (saved !== null) {
        setYoloLabelsEnabled(saved === "1");
      }
    } catch (e) {
      // Ignore localStorage errors
    }
  }, []);

  const handleToggleYoloLabels = () => {
    setYoloLabelsEnabled((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("cctv_yolo_labels", next ? "1" : "0");
      } catch (e) {}
      return next;
    });
  };

  // Fetch cameras
  const fetchCameras = useCallback(async () => {
    try {
      const res = await authFetch(`${API_BASE}/cameras`);
      if (res.ok) {
        const data = await res.json();
        setCameras(data);
      }
    } catch (e) {
      // Backend might still be starting
    }
  }, [authFetch]);

  // Fetch active incidents (awaiting review)
  const fetchIncidents = useCallback(async () => {
    try {
      const res = await authFetch(`${API_BASE}/incidents?status=AWAITING_REVIEW`);
      if (res.ok) {
        const data = await res.json();
        setIncidents(data);
      }
    } catch (e) {
      // Backend offline
    }
  }, [authFetch]);


  // Initial load and periodic polling for camera stats
  useEffect(() => {
    fetchCameras();
    fetchIncidents();
    const interval = setInterval(() => {
      fetchCameras();
    }, 2500);
    return () => clearInterval(interval);
  }, [fetchCameras, fetchIncidents]);

  // Connect to SSE for instant real-time alerts
  useEffect(() => {
    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource(`${API_BASE}/events`);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "incident.created") {
            if (soundEnabled) {
              playAlertChime();
            }
            fetchIncidents();
            fetchCameras();
          } else if (data.type === "incident.clip_ready") {
            setSelectedIncident((prev) => {
              if (prev && prev.id === data.incident_id) {
                return {
                  ...prev,
                  clip_status: "READY",
                  clip_url: data.clip_url || `/api/incidents/${data.incident_id}/clip`,
                  thumbnail_url: data.thumbnail_url || prev.thumbnail_url,
                };
              }
              return prev;
            });
            fetchIncidents();
          } else if (data.type === "incident.acknowledged" || data.type === "incident.reviewed") {
            fetchIncidents();
          }
        } catch (err) {
          // ignore heartbeat
        }
      };

      eventSource.onerror = () => {
        // SSE reconnects automatically
      };
    } catch (err) {
      console.warn("SSE connection error:", err);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [soundEnabled, fetchIncidents, fetchCameras]);

  // Set of camera IDs that currently have active alerts
  const activeAlertCameraIds = useMemo(() => {
    return new Set(incidents.map((i) => i.camera_id).filter((id): id is number => typeof id === "number"));
  }, [incidents]);

  // Acknowledge incident
  const handleAcknowledge = async (incidentId: number) => {
    try {
      await authFetch(`${API_BASE}/incidents/${incidentId}/acknowledge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operator: user?.name || "Security Operator" }),
      });
      fetchIncidents();
    } catch (e) {
      console.error("Failed to acknowledge incident:", e);
    }
  };

  // Submit human review
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
        classification: reviewData.classification,
        reason: reviewData.reason,
        notes: reviewData.notes,
        reviewer: reviewData.reviewer || user?.name || "Operator",
      }),
    });
    fetchIncidents();
    fetchCameras();
  };

  // Save (Create or Update) camera
  const handleSaveCamera = async (camData: Partial<Camera>) => {
    try {
      if (editingCamera?.id) {
        await authFetch(`${API_BASE}/cameras/${editingCamera.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(camData),
        });
      } else {
        await authFetch(`${API_BASE}/cameras`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(camData),
        });
      }
      fetchCameras();
    } catch (e) {
      console.error("Failed to save camera:", e);
    }
  };

  // Remove camera from live monitoring
  const handleDeleteCamera = async (id: number) => {
    if (confirm("Are you sure you want to remove this camera from live monitoring? Past alerts and incident records will be preserved in incident history.")) {
      try {
        await authFetch(`${API_BASE}/cameras/${id}`, { method: "DELETE" });
        await fetchCameras();
        await fetchIncidents();
      } catch (e) {
        console.error("Failed to remove camera:", e);
      }
    }
  };

  return (
    <>
      <Header
        cameraCount={cameras.length}
        activeAlertCount={incidents.length}
        soundEnabled={soundEnabled}
        onToggleSound={() => setSoundEnabled(!soundEnabled)}
        yoloLabelsEnabled={yoloLabelsEnabled}
        onToggleYoloLabels={handleToggleYoloLabels}
        onUploadSimulation={() => {
          setEditingCamera(null);
          setModalInitialMode("upload");
          setCameraModalOpen(true);
        }}
        onAddCamera={() => {
          setEditingCamera(null);
          setModalInitialMode("upload");
          setCameraModalOpen(true);
        }}
      />

      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* CCTV Camera Wall */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400">
              Live CCTV Grid View
            </h2>
            <span className="text-[11px] text-gray-500 font-mono">
              Auto-sampling @ 2 FPS
            </span>
          </div>
          <CameraWall
            cameras={cameras}
            activeAlertCameraIds={activeAlertCameraIds}
            yoloLabelsEnabled={yoloLabelsEnabled}
            onEditCamera={(cam) => {
              setEditingCamera(cam);
              setModalInitialMode(cam.is_simulation ? "library" : "rtsp");
              setCameraModalOpen(true);
            }}
            onDeleteCamera={handleDeleteCamera}
          />
        </section>

        {/* Active Alerts Queue */}
        <section className="pt-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400">
              Real-Time Alert Dispatch
            </h2>
          </div>
          <AlertQueue
            alerts={incidents}
            onAcknowledge={handleAcknowledge}
            onOpenReview={(inc) => setSelectedIncident(inc)}
          />
        </section>
      </main>

      {/* Review Modal */}
      <IncidentReviewModal
        incident={selectedIncident}
        onClose={() => setSelectedIncident(null)}
        onSubmitReview={handleSubmitReview}
      />

      {/* Camera Add/Edit Modal */}
      <CameraModal
        isOpen={cameraModalOpen}
        onClose={() => {
          setCameraModalOpen(false);
          setEditingCamera(null);
        }}
        cameraToEdit={editingCamera}
        initialMode={modalInitialMode}
        onSave={handleSaveCamera}
      />
    </>
  );
}
