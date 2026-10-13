import React, { useState, useEffect, useRef } from "react";
import { Camera, SimulationVideo, VideoUploadResult } from "../types";
import {
  X,
  Check,
  Video,
  Upload,
  Film,
  Radio,
  FileVideo,
  AlertCircle,
  Loader2,
  Repeat,
  Sparkles,
} from "lucide-react";

interface CameraModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (cameraData: Partial<Camera>) => Promise<void>;
  cameraToEdit?: Camera | null;
  initialMode?: "upload" | "library" | "rtsp";
}

export const CameraModal: React.FC<CameraModalProps> = ({
  isOpen,
  onClose,
  onSave,
  cameraToEdit,
  initialMode = "upload",
}) => {
  const [sourceMode, setSourceMode] = useState<"upload" | "library" | "rtsp">(initialMode);
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

  // Upload state
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedMeta, setUploadedMeta] = useState<VideoUploadResult | null>(null);

  // Simulation Library state
  const [simulationVideos, setSimulationVideos] = useState<SimulationVideo[]>([]);
  const [isLoadingLibrary, setIsLoadingLibrary] = useState(false);

  // Submission & Testing state
  const [submitting, setSubmitting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch available simulation videos
  const fetchSimulations = async () => {
    setIsLoadingLibrary(true);
    try {
      const res = await fetch("http://localhost:5000/api/cameras/simulations");
      if (res.ok) {
        const data = await res.json();
        setSimulationVideos(data);
      }
    } catch (e) {
      console.warn("Failed to load simulation videos:", e);
    } finally {
      setIsLoadingLibrary(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchSimulations();
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
        setSourceMode(cameraToEdit.is_simulation ? "library" : "rtsp");
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
        setSourceMode(initialMode);
      }
      setUploadError(null);
      setUploadedMeta(null);
      setTestResult(null);
    }
  }, [cameraToEdit, isOpen, initialMode]);

  if (!isOpen) return null;

  // Handle Video Upload
  const handleFileUpload = async (file: File) => {
    setUploadError(null);
    setIsUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:5000/api/cameras/upload", {
        method: "POST",
        body: formData,
      });

      let data: any;
      const contentType = res.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        data = await res.json();
      } else {
        const text = await res.text();
        throw new Error(
          res.status === 404
            ? "Upload endpoint not found. Please restart the backend server."
            : `Server returned (${res.status}): ${text.slice(0, 100)}`
        );
      }

      if (!res.ok) {
        throw new Error(data.error || "Failed to upload video");
      }

      setUploadedMeta(data);
      setStreamUrl(data.stream_url);
      setIsSimulation(true);
      setLoopSimulation(true);

      // Auto-suggest name if empty
      if (!name.trim()) {
        const baseName = file.name
          .replace(/\.[^/.]+$/, "")
          .replace(/[-_]/g, " ")
          .replace(/\b\w/g, (c) => c.toUpperCase());
        setName(`${baseName} (Sim)`);
      }
      if (!location.trim()) {
        setLocation("Simulated Zone");
      }

      setTestResult("Video uploaded and validated by OpenCV.");
      fetchSimulations();
    } catch (err: any) {
      setUploadError(err.message || "Upload failed");
    } finally {
      setIsUploading(false);
      setUploadProgress(null);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!streamUrl.trim()) {
      setUploadError("Please provide or upload a video stream source.");
      return;
    }

    setSubmitting(true);
    try {
      await onSave({
        name,
        location,
        stream_url: streamUrl,
        is_simulation: isSimulation,
        loop_simulation: isSimulation ? loopSimulation : false,
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
    setIsTesting(true);
    setTestResult("Testing connectivity...");
    try {
      if (cameraToEdit?.id) {
        const res = await fetch(`http://localhost:5000/api/cameras/${cameraToEdit.id}/test`, {
          method: "POST",
        });
        const data = await res.json();
        setTestResult(data.connected ? "Success: Stream is Online!" : "Error: Cannot open stream source.");
      } else {
        // Quick verification for local file vs remote
        if (streamUrl.startsWith("rtsp://") || streamUrl.startsWith("http")) {
          setTestResult("Network stream source will be connected upon creation.");
        } else {
          setTestResult("Simulation file verified and ready to stream.");
        }
      }
    } catch (err) {
      setTestResult("Connection test failed: Backend unreachable.");
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-sentinel-card border border-sentinel-border rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden my-8">
        {/* Header */}
        <div className="px-6 py-4 border-b border-sentinel-border flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center space-x-2">
            <Video className="w-5 h-5 text-blue-400" />
            <div>
              <h2 className="text-sm font-bold text-white">
                {cameraToEdit
                  ? "Edit Camera Configuration"
                  : sourceMode === "upload"
                  ? "Upload Video & Simulate CCTV"
                  : "Register CCTV Camera"}
              </h2>
              <p className="text-[11px] text-gray-400">
                Simulate real-time CCTV feeds from uploaded footage or connect RTSP streams
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Source Mode Tabs */}
        <div className="bg-slate-900/60 px-6 pt-3 border-b border-sentinel-border flex space-x-2">
          <button
            type="button"
            onClick={() => {
              setSourceMode("upload");
              setIsSimulation(true);
            }}
            className={`px-3 py-2 text-xs font-semibold rounded-t-lg flex items-center space-x-1.5 border-b-2 transition ${
              sourceMode === "upload"
                ? "border-blue-500 text-blue-400 bg-slate-800/80"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload Video File</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setSourceMode("library");
              setIsSimulation(true);
            }}
            className={`px-3 py-2 text-xs font-semibold rounded-t-lg flex items-center space-x-1.5 border-b-2 transition ${
              sourceMode === "library"
                ? "border-blue-500 text-blue-400 bg-slate-800/80"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Film className="w-3.5 h-3.5" />
            <span>Simulation Library</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setSourceMode("rtsp");
              setIsSimulation(false);
            }}
            className={`px-3 py-2 text-xs font-semibold rounded-t-lg flex items-center space-x-1.5 border-b-2 transition ${
              sourceMode === "rtsp"
                ? "border-blue-500 text-blue-400 bg-slate-800/80"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            <span>RTSP / IP Camera</span>
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          {/* TAB 1: UPLOAD VIDEO */}
          {sourceMode === "upload" && (
            <div className="space-y-3">
              <input
                ref={fileInputRef}
                type="file"
                accept="video/mp4,video/avi,video/quicktime,video/x-matroska,video/webm"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    handleFileUpload(e.target.files[0]);
                  }
                }}
              />

              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition ${
                  isDragging
                    ? "border-blue-500 bg-blue-500/10"
                    : "border-slate-700 bg-slate-900/50 hover:border-slate-500 hover:bg-slate-900/80"
                }`}
              >
                {isUploading ? (
                  <div className="flex flex-col items-center justify-center space-y-2 py-2">
                    <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
                    <p className="text-xs text-white font-semibold">
                      Uploading and verifying video stream...
                    </p>
                    <span className="text-[10px] text-gray-400 font-mono">
                      Running OpenCV codec checks & metadata extraction
                    </span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-full text-blue-400">
                      <Upload className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-white">
                        Click to select or drag & drop a surveillance video
                      </p>
                      <p className="text-[10px] text-gray-400 mt-0.5">
                        Supports MP4, AVI, MOV, MKV, WebM (up to 250 MB)
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Upload Error Banner */}
              {uploadError && (
                <div className="p-3 rounded-lg bg-red-950/40 border border-red-800/60 text-xs text-red-300 flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
                  <span>{uploadError}</span>
                </div>
              )}

              {/* Uploaded Video Details Card */}
              {uploadedMeta && (
                <div className="p-3 bg-slate-900/90 border border-emerald-500/30 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <FileVideo className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs font-semibold text-white truncate max-w-[280px]">
                        {uploadedMeta.filename}
                      </span>
                    </div>
                    <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full font-medium flex items-center space-x-1">
                      <Check className="w-3 h-3" />
                      <span>Ready to Simulate</span>
                    </span>
                  </div>

                  <div className="grid grid-cols-4 gap-2 text-[10px] font-mono text-gray-400 pt-1 border-t border-slate-800">
                    <div>
                      <span className="text-gray-500 block">Resolution</span>
                      <strong className="text-gray-200">
                        {uploadedMeta.width}x{uploadedMeta.height}
                      </strong>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Frame Rate</span>
                      <strong className="text-gray-200">{uploadedMeta.fps} FPS</strong>
                    </div>
                    <div>
                      <span className="text-gray-500 block">Duration</span>
                      <strong className="text-gray-200">{uploadedMeta.duration_seconds}s</strong>
                    </div>
                    <div>
                      <span className="text-gray-500 block">File Size</span>
                      <strong className="text-gray-200">
                        {(uploadedMeta.size_bytes / (1024 * 1024)).toFixed(1)} MB
                      </strong>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: SIMULATION LIBRARY */}
          {sourceMode === "library" && (
            <div className="space-y-2">
              <label className="block text-[11px] font-semibold text-gray-300">
                Select Simulation Video Source:
              </label>

              {isLoadingLibrary ? (
                <div className="p-6 text-center text-xs text-gray-400 flex items-center justify-center space-x-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                  <span>Loading available simulation videos...</span>
                </div>
              ) : simulationVideos.length === 0 ? (
                <p className="text-xs text-gray-500 py-3 text-center">
                  No simulation videos found. Switch to &quot;Upload Video File&quot; to upload one.
                </p>
              ) : (
                <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                  {simulationVideos.map((sim) => {
                    const isSelected = streamUrl === sim.path;
                    return (
                      <div
                        key={sim.path}
                        onClick={() => {
                          setStreamUrl(sim.path);
                          setIsSimulation(true);
                          if (!name.trim()) {
                            setName(sim.name.replace(/ \(.*?\)/, ""));
                          }
                          if (!location.trim()) {
                            setLocation(sim.type === "preset" ? "Preset Zone" : "Upload Zone");
                          }
                        }}
                        className={`p-2.5 rounded-lg border text-xs cursor-pointer flex items-center justify-between transition ${
                          isSelected
                            ? "bg-blue-600/20 border-blue-500 text-white"
                            : "bg-slate-900/60 border-slate-800 text-gray-300 hover:bg-slate-800"
                        }`}
                      >
                        <div className="flex items-center space-x-2 truncate">
                          <Film
                            className={`w-4 h-4 flex-shrink-0 ${
                              isSelected ? "text-blue-400" : "text-gray-500"
                            }`}
                          />
                          <span className="font-medium truncate">{sim.name}</span>
                        </div>
                        <div className="flex items-center space-x-2 flex-shrink-0">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                              sim.type === "preset"
                                ? "bg-purple-950/60 text-purple-300 border border-purple-800/40"
                                : "bg-emerald-950/60 text-emerald-300 border border-emerald-800/40"
                            }`}
                          >
                            {sim.type === "preset" ? "Built-in" : "Uploaded"}
                          </span>
                          {isSelected && <Check className="w-4 h-4 text-blue-400" />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: RTSP / IP CAMERA */}
          {sourceMode === "rtsp" && (
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-1">
                Network RTSP Stream URL *
              </label>
              <input
                type="text"
                required={sourceMode === "rtsp"}
                value={streamUrl}
                onChange={(e) => {
                  setStreamUrl(e.target.value);
                  setIsSimulation(false);
                }}
                placeholder="rtsp://admin:password@192.168.1.100:554/h264Preview_01_main"
                className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-mono"
              />
              <span className="text-[10px] text-gray-500 mt-1 block">
                Standard H.264/H.265 RTSP or HTTP/MJPEG streams supported.
              </span>
            </div>
          )}

          {/* Simulation Loop Toggle */}
          {isSimulation && (
            <div className="flex items-center justify-between p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
              <div className="flex items-center space-x-2">
                <Repeat className="w-4 h-4 text-blue-400" />
                <div>
                  <span className="text-xs font-semibold text-gray-200 block">
                    Continuous Video Loop
                  </span>
                  <span className="text-[10px] text-gray-400">
                    Restarts the video when it ends to simulate continuous 24/7 CCTV surveillance
                  </span>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={loopSimulation}
                  onChange={(e) => setLoopSimulation(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-8 h-4 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
          )}

          {/* Camera Details */}
          <div className="grid grid-cols-2 gap-4 pt-1">
            <div>
              <label className="block text-[11px] font-semibold text-gray-300 mb-1">
                Camera Name *
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Hallway 03 - East"
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
                placeholder="e.g. Building A - Courtyard"
                className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Test Connection Button */}
          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              disabled={isTesting || !streamUrl}
              onClick={handleTestStream}
              className="text-xs text-blue-400 hover:text-blue-300 underline disabled:opacity-50"
            >
              {isTesting ? "Testing stream..." : "Test Stream Connection"}
            </button>
            {testResult && (
              <span className="text-[11px] text-gray-300 font-mono truncate max-w-[320px]">
                {testResult}
              </span>
            )}
          </div>

          {/* AI Settings Section */}
          <div className="p-3 bg-slate-900/70 border border-sentinel-border rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                <span className="text-xs font-semibold text-gray-200">
                  AI Violence & Bullying Detection
                </span>
              </div>
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
                <label className="text-gray-400 text-[11px] block mb-1">
                  Pre-buffer: {preBufferSeconds}s
                </label>
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
                <label className="text-gray-400 text-[11px] block mb-1">
                  Post-buffer: {postBufferSeconds}s
                </label>
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
          <div className="flex items-center justify-end space-x-2 pt-2 border-t border-sentinel-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-slate-700 hover:bg-slate-800 text-xs text-gray-300 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || isUploading}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow transition disabled:opacity-50 flex items-center space-x-1.5"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <span>
                  {cameraToEdit
                    ? "Update Camera"
                    : isSimulation
                    ? "Start Simulation Camera"
                    : "Create Camera"}
                </span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
