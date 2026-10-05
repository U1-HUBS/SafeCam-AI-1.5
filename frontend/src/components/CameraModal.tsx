import React, { useState, useEffect } from "react";
import { Camera } from "../types";
import { X, Check, Activity, Video } from "lucide-react";

interface CameraModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (cameraData: Partial<Camera>) => Promise<void>;
  cameraToEdit?: Camera | null;
}

export const CameraModal: React.FC<CameraModalProps> = ({
  isOpen,
  onClose,
  onSave,
  cameraToEdit,
}) => {
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [streamUrl, setStreamUrl] = useState("");
  const [isSimulation, setIsSimulation] = useState(true);
  const [loopSimulation, setLoopSimulation] = useState(true);
  const [aiEnabled, setAiEnabled] = useState(true);
  const [samplingRate, setSamplingRate] = useState(2);
  const [sensitivity, setSensitivity] = useState(0.25);
  const [preBufferSeconds, setPreBufferSeconds] = useState(8);
  const [postBufferSeconds, setPostBufferSeconds] = useState(8);
  const [submitting, setSubmitting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  useEffect(() => {
    if (cameraToEdit) {
      setName(cameraToEdit.name);
      setLocation(cameraToEdit.location);
      setStreamUrl(cameraToEdit.stream_url);
      setIsSimulation(cameraToEdit.is_simulation);
      setLoopSimulation(cameraToEdit.loop_simulation);
      setAiEnabled(cameraToEdit.ai_enabled);
      setSamplingRate(cameraToEdit.sampling_rate);
      setSensitivity(cameraToEdit.sensitivity);
      setPreBufferSeconds(cameraToEdit.pre_buffer_seconds);
      setPostBufferSeconds(cameraToEdit.post_buffer_seconds);
    } else {
      setName("");
      setLocation("");
      setStreamUrl("sample_videos/sample_hallway.mp4");
      setIsSimulation(true);
      setLoopSimulation(true);
      setAiEnabled(true);
      setSamplingRate(2);
      setSensitivity(0.25);
      setPreBufferSeconds(8);
      setPostBufferSeconds(8);
    }
    setTestResult(null);
  }, [cameraToEdit, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSave({
        name,
        location,
        stream_url: streamUrl,
        is_simulation: isSimulation,
        loop_simulation: loopSimulation,
        ai_enabled: aiEnabled,
        sampling_rate: Number(samplingRate),
        sensitivity: Number(sensitivity),
        pre_buffer_seconds: Number(preBufferSeconds),
        post_buffer_seconds: Number(postBufferSeconds),
      });
      onClose();
    } catch (err) {
      console.error("Error saving camera:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleTestStream = async () => {
    setTestResult("Testing connectivity...");
    try {
      // If editing existing
      if (cameraToEdit?.id) {
        const res = await fetch(`http://localhost:5000/api/cameras/${cameraToEdit.id}/test`, {
          method: "POST",
        });
        const data = await res.json();
        setTestResult(data.connected ? "Success: Stream is Online!" : "Error: Cannot open stream source.");
      } else {
        setTestResult("Stream path set. Connection will be established upon creation.");
      }
    } catch (err) {
      setTestResult("Connection failed: Backend unreachable.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-sentinel-card border border-sentinel-border rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-sentinel-border flex items-center justify-between bg-slate-900/80">
          <div className="flex items-center space-x-2">
            <Video className="w-5 h-5 text-blue-400" />
            <h2 className="text-sm font-bold text-white">
              {cameraToEdit ? "Edit Camera Configuration" : "Register New CCTV Camera"}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-1">
                Camera Name *
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Hallway 02"
                className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-1">
                Location Area *
              </label>
              <input
                type="text"
                required
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Building B - 2nd Floor"
                className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Stream Type and Source */}
          <div>
            <label className="block text-[11px] font-semibold text-gray-300 mb-1">
              Stream Source (RTSP URL or Simulation Video) *
            </label>
            <input
              type="text"
              required
              value={streamUrl}
              onChange={(e) => setStreamUrl(e.target.value)}
              placeholder="rtsp://user:pass@192.168.1.100:554/live or sample_videos/..."
              className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-mono"
            />

            {/* Quick preset buttons for simulation */}
            <div className="flex items-center space-x-2 mt-2">
              <span className="text-[10px] text-gray-500">Presets:</span>
              <button
                type="button"
                onClick={() => {
                  setStreamUrl("sample_videos/sample_hallway.mp4");
                  setIsSimulation(true);
                }}
                className="px-2 py-0.5 rounded text-[10px] bg-slate-800 hover:bg-slate-700 text-gray-300 border border-slate-700"
              >
                Normal Hallway Video
              </button>
              <button
                type="button"
                onClick={() => {
                  setStreamUrl("sample_videos/sample_fight.mp4");
                  setIsSimulation(true);
                }}
                className="px-2 py-0.5 rounded text-[10px] bg-red-950/50 hover:bg-red-900/50 text-red-300 border border-red-800/40"
              >
                Altercation Simulation Video
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              onClick={handleTestStream}
              className="text-xs text-blue-400 hover:text-blue-300 underline"
            >
              Test Stream Connection
            </button>
            {testResult && (
              <span className="text-[11px] text-gray-300 font-mono">{testResult}</span>
            )}
          </div>

          {/* AI Settings */}
          <div className="p-3 bg-slate-900/70 border border-sentinel-border rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-200">AI Violence Detection</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={aiEnabled}
                  onChange={(e) => setAiEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-8 h-4 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-gray-400 text-[11px] block mb-1">
                  Sampling Rate: {samplingRate} FPS
                </label>
                <input
                  type="range"
                  min="1"
                  max="6"
                  value={samplingRate}
                  onChange={(e) => setSamplingRate(Number(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <label className="text-gray-400 text-[11px] block mb-1">
                  Detection Sensitivity: {sensitivity.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0.10"
                  max="0.60"
                  step="0.05"
                  value={sensitivity}
                  onChange={(e) => setSensitivity(Number(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs pt-1">
              <div>
                <label className="text-gray-400 text-[11px] block mb-1">Pre-buffer: {preBufferSeconds}s</label>
                <input
                  type="number"
                  min="4"
                  max="30"
                  value={preBufferSeconds}
                  onChange={(e) => setPreBufferSeconds(Number(e.target.value))}
                  className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                />
              </div>
              <div>
                <label className="text-gray-400 text-[11px] block mb-1">Post-buffer: {postBufferSeconds}s</label>
                <input
                  type="number"
                  min="4"
                  max="30"
                  value={postBufferSeconds}
                  onChange={(e) => setPostBufferSeconds(Number(e.target.value))}
                  className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                />
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-slate-700 hover:bg-slate-800 text-xs text-gray-300 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow transition disabled:opacity-50"
            >
              {submitting ? "Saving..." : cameraToEdit ? "Update Camera" : "Create Camera"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
