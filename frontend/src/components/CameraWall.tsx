import React, { useState } from "react";
import { Camera } from "../types";
import { Video, AlertTriangle, ShieldCheck, Settings, Trash2, Activity, Users, Tag } from "lucide-react";
import { useAuth } from "../context/AuthContext";

interface CameraWallProps {
  cameras: Camera[];
  activeAlertCameraIds: Set<number>;
  onEditCamera: (camera: Camera) => void;
  onDeleteCamera: (id: number) => void;
  yoloLabelsEnabled?: boolean;
}

export const CameraWall: React.FC<CameraWallProps> = ({
  cameras,
  activeAlertCameraIds,
  onEditCamera,
  onDeleteCamera,
  yoloLabelsEnabled = true,
}) => {
  const { hasRole } = useAuth();
  const isAdmin = hasRole(["admin"]);
  const [cameraOverrides, setCameraOverrides] = useState<Record<number, boolean>>({});


  const toggleCameraLabels = (id: number) => {
    setCameraOverrides((prev) => {
      const current = prev[id] !== undefined ? prev[id] : yoloLabelsEnabled;
      return { ...prev, [id]: !current };
    });
  };
  if (cameras.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-16 text-center border border-dashed border-sentinel-border rounded-xl bg-sentinel-card/50">
        <Video className="w-12 h-12 text-gray-500 mb-3" />
        <h3 className="text-base font-semibold text-gray-200">No Cameras Registered</h3>
        <p className="text-xs text-gray-400 mt-1 max-w-sm">
          Add an RTSP stream or choose a simulated video source to begin monitoring.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-2 gap-4">
      {cameras.map((camera) => {
        const isAlerting = activeAlertCameraIds.has(camera.id);
        const isOnline = camera.runtime_status === "ONLINE" || camera.status === "ONLINE";
        const prediction = camera.latest_prediction;
        const isCameraLabelsOn = cameraOverrides[camera.id] !== undefined ? cameraOverrides[camera.id] : yoloLabelsEnabled;

        return (
          <div
            key={camera.id}
            className={`relative rounded-xl overflow-hidden border bg-sentinel-card transition-all duration-300 ${
              isAlerting
                ? "border-red-500 ring-4 ring-red-500/20 shadow-lg shadow-red-500/10 alert-pulse"
                : "border-sentinel-border hover:border-slate-600"
            }`}
          >
            {/* Tile Header */}
            <div className="flex items-center justify-between px-3.5 py-2.5 bg-slate-900/90 border-b border-sentinel-border">
              <div className="flex items-center space-x-2 truncate">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${
                    isAlerting
                      ? "bg-red-500 animate-ping"
                      : isOnline
                      ? "bg-emerald-500"
                      : "bg-red-500"
                  }`}
                />
                <span className="font-semibold text-xs text-white truncate">{camera.name}</span>
                <span className="text-[11px] text-gray-400 truncate">({camera.location})</span>
              </div>

              <div className="flex items-center space-x-1.5">
                {/* AI Status Badge */}
                {camera.ai_enabled && (
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase flex items-center space-x-1 ${
                      isAlerting || prediction?.is_violent
                        ? "bg-red-500/20 text-red-400 border border-red-500/40"
                        : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                    }`}
                  >
                    {isAlerting || prediction?.is_violent ? (
                      <>
                        <AlertTriangle className="w-3 h-3 text-red-400" />
                        <span>{prediction?.category || "VIOLENCE DETECTED"}</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="w-3 h-3 text-emerald-400" />
                        <span>AI NORMAL</span>
                      </>
                    )}
                  </span>
                )}

                {/* Person Count Badge */}
                {camera.ai_enabled && prediction?.person_count !== undefined && (
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider flex items-center space-x-1 ${
                      prediction.person_count === 1
                        ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                        : prediction.person_count > 1
                        ? "bg-blue-500/10 text-blue-400 border border-blue-500/30"
                        : "bg-slate-700/30 text-gray-400 border border-slate-700/40"
                    }`}
                  >
                    <Users className="w-3 h-3" />
                    <span>
                      {prediction.person_count}{" "}
                      {prediction.person_count === 1 ? "Person" : "Persons"}
                    </span>
                  </span>
                )}

                {/* Toggle YOLO Labels button */}
                <button
                  onClick={() => toggleCameraLabels(camera.id)}
                  className={`p-1 rounded transition ${
                    isCameraLabelsOn
                      ? "text-cyan-300 hover:text-cyan-200 bg-cyan-500/20 border border-cyan-500/40"
                      : "text-gray-500 hover:text-gray-300 hover:bg-slate-800"
                  }`}
                  title={isCameraLabelsOn ? "Turn off YOLO labels for this camera" : "Turn on YOLO labels for this camera"}
                >
                  <Tag className="w-3.5 h-3.5" />
                </button>

                {/* Edit & Delete actions (Admin only) */}
                {isAdmin && (
                  <>
                    <button
                      onClick={() => onEditCamera(camera)}
                      className="p-1 text-gray-400 hover:text-blue-400 hover:bg-slate-800 rounded transition"
                      title="Configure camera"
                    >
                      <Settings className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => onDeleteCamera(camera.id)}
                      className="p-1 text-gray-400 hover:text-red-400 hover:bg-slate-800 rounded transition"
                      title="Remove camera"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Video Viewport */}
            <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
              {isOnline ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`http://localhost:5000/api/stream/${camera.id}/live?labels=${isCameraLabelsOn ? 1 : 0}`}
                  alt={camera.name}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // Fallback to placeholder if stream interrupted
                    (e.target as HTMLElement).style.display = "none";
                  }}
                />
              ) : (
                <div className="flex flex-col items-center justify-center text-gray-500 text-xs">
                  <Video className="w-8 h-8 mb-2 opacity-50" />
                  <span>STREAM OFFLINE</span>
                  <span className="text-[10px] text-gray-600 mt-1 max-w-[200px] truncate">
                    {camera.stream_url}
                  </span>
                </div>
              )}

              {/* Live Overlay HUD */}
              <div className="absolute top-2 left-2 flex items-center space-x-2 bg-black/60 backdrop-blur-sm px-2 py-1 rounded text-[10px] text-gray-300 font-mono">
                <span className={`w-1.5 h-1.5 rounded-full ${camera.is_simulation ? "bg-purple-400" : "bg-red-500"} animate-pulse`}></span>
                <span>{camera.is_simulation ? "SIMULATION FEED" : "LIVE REC"}</span>
                <span>• {camera.sampling_rate} FPS</span>
              </div>

              {/* Confidence & Person HUD (bottom-left) */}
              {prediction && (
                <div className="absolute bottom-2 left-2 bg-black/75 backdrop-blur-sm px-2.5 py-1 rounded text-[10px] text-gray-300 border border-white/10 flex items-center space-x-2 font-mono">
                  <Activity className="w-3 h-3 text-blue-400" />
                  <span>Conf: <strong className="text-white">{(prediction.confidence * 100).toFixed(1)}%</strong></span>
                  <span className="text-gray-500">|</span>
                  <span>{prediction.latency_ms.toFixed(0)}ms</span>
                  {prediction.person_count !== undefined && (
                    <>
                      <span className="text-gray-500">|</span>
                      <span className={prediction.person_count === 1 ? "text-amber-400 font-bold" : "text-blue-400"}>
                        {prediction.person_count === 1 ? "1 Solo Person" : `${prediction.person_count} Persons`}
                      </span>
                    </>
                  )}
                </div>
              )}

              {/* Big Alert Banner when active */}
              {isAlerting && (
                <div className="absolute inset-0 bg-red-600/10 pointer-events-none flex items-center justify-center">
                  <div className="bg-red-600/90 text-white font-extrabold px-4 py-2 rounded-lg shadow-xl tracking-wider text-sm flex items-center space-x-2 animate-bounce">
                    <AlertTriangle className="w-5 h-5 text-yellow-300" />
                    <span>SUSPECTED VIOLENCE DETECTED</span>
                  </div>
                </div>
              )}
            </div>

            {/* Tile Footer */}
            <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900/60 text-[11px] text-gray-400 border-t border-sentinel-border">
              <span className="truncate">
                Buffer: {camera.pre_buffer_seconds}s pre / {camera.post_buffer_seconds}s post
              </span>
              <span className="text-gray-500 font-mono">
                Sensitivity: {camera.sensitivity.toFixed(2)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
