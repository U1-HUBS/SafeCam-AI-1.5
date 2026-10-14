import React from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { useAuth } from "../context/AuthContext";
import {
  ShieldAlert,
  Video,
  History,
  BarChart3,
  Plus,
  Bell,
  Volume2,
  VolumeX,
  Upload,
  Tag,
  Users,
  LogOut,
  User as UserIcon,
} from "lucide-react";

interface HeaderProps {
  cameraCount: number;
  activeAlertCount: number;
  onAddCamera?: () => void;
  onUploadSimulation?: () => void;
  soundEnabled?: boolean;
  onToggleSound?: () => void;
  yoloLabelsEnabled?: boolean;
  onToggleYoloLabels?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  cameraCount,
  activeAlertCount,
  onAddCamera,
  onUploadSimulation,
  soundEnabled = true,
  onToggleSound,
  yoloLabelsEnabled = true,
  onToggleYoloLabels,
}) => {
  const router = useRouter();
  const { user, logout, hasRole } = useAuth();

  const navItems = [
    { label: "Live Wall", href: "/", icon: Video, show: true },
    { label: "Incident History", href: "/history", icon: History, show: true },
    {
      label: "Reports & KPIs",
      href: "/reports",
      icon: BarChart3,
      show: hasRole(["admin", "supervisor"]),
    },
    {
      label: "Users & Access",
      href: "/users",
      icon: Users,
      show: hasRole(["admin"]),
    },
  ];

  const getRoleBadge = () => {
    switch (user?.role) {
      case "admin":
        return {
          label: "ADMIN",
          style: "bg-red-500/20 text-red-300 border-red-500/40",
        };
      case "supervisor":
        return {
          label: "SUPERVISOR",
          style: "bg-amber-500/20 text-amber-300 border-amber-500/40",
        };
      case "security":
      default:
        return {
          label: "SECURITY",
          style: "bg-blue-500/20 text-blue-300 border-blue-500/40",
        };
    }
  };

  const roleBadge = getRoleBadge();

  return (
    <header className="bg-sentinel-card border-b border-sentinel-border px-6 py-3 sticky top-0 z-40">
      <div className="flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-6">
          <Link href="/" className="flex items-center space-x-3 group">
            <div className="bg-red-500/10 p-2 rounded-lg border border-red-500/30 group-hover:border-red-500/60 transition">
              <ShieldAlert className="w-6 h-6 text-red-500" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-wide">SAFECAM AI</h1>
              <p className="text-xs text-gray-400">AI Central Monitoring & Violence Detection</p>
            </div>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-1 pl-4 border-l border-sentinel-border">
            {navItems
              .filter((item) => item.show)
              .map((item) => {
                const Icon = item.icon;
                const isActive = router.pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition ${
                      isActive
                        ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                        : "text-gray-400 hover:text-gray-200 hover:bg-white/5"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
          </nav>
        </div>

        {/* Status badges & Actions */}
        <div className="flex items-center space-x-3">
          {/* Sound Toggle */}
          {onToggleSound && (
            <button
              onClick={onToggleSound}
              title={soundEnabled ? "Mute alert audio" : "Enable alert audio"}
              className={`p-2 rounded-lg border text-xs flex items-center space-x-1.5 transition ${
                soundEnabled
                  ? "bg-blue-500/10 border-blue-500/30 text-blue-400 hover:bg-blue-500/20"
                  : "bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
              <span className="hidden sm:inline">{soundEnabled ? "Audio On" : "Muted"}</span>
            </button>
          )}

          {/* YOLO Labels Toggle */}
          {onToggleYoloLabels && (
            <button
              onClick={onToggleYoloLabels}
              title={
                yoloLabelsEnabled
                  ? "Hide YOLO person labels on live cameras"
                  : "Show YOLO person labels on live cameras"
              }
              className={`px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center space-x-1.5 transition ${
                yoloLabelsEnabled
                  ? "bg-cyan-500/20 border-cyan-500/50 text-cyan-300 shadow-sm shadow-cyan-500/20 hover:bg-cyan-500/30"
                  : "bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700 hover:text-gray-200"
              }`}
            >
              <Tag className="w-3.5 h-3.5" />
              <span>
                Labels:{" "}
                <strong className={yoloLabelsEnabled ? "text-cyan-200 font-bold" : "text-gray-400"}>
                  {yoloLabelsEnabled ? "ON" : "OFF"}
                </strong>
              </span>
            </button>
          )}

          {/* Active Cameras Badge */}
          <div className="hidden sm:flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-gray-300">
              Cameras: <strong className="text-white font-semibold">{cameraCount}</strong>
            </span>
          </div>

          {/* Active Alerts Badge */}
          <div
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-medium ${
              activeAlertCount > 0
                ? "bg-red-500/20 border-red-500/50 text-red-400 animate-bounce"
                : "bg-slate-800/80 border-slate-700 text-gray-400"
            }`}
          >
            <Bell className="w-3.5 h-3.5" />
            <span>
              Alerts:{" "}
              <strong className={activeAlertCount > 0 ? "text-red-300" : "text-white"}>
                {activeAlertCount}
              </strong>
            </span>
          </div>

          {/* Admin-only: Simulate Video Button */}
          {hasRole(["admin"]) && onUploadSimulation && (
            <button
              onClick={onUploadSimulation}
              className="bg-indigo-600/80 hover:bg-indigo-500 text-white text-xs font-semibold px-3 py-2 rounded-lg flex items-center space-x-1.5 shadow transition border border-indigo-500/30"
              title="Upload video to simulate a CCTV camera"
            >
              <Upload className="w-4 h-4" />
              <span>Simulate Video</span>
            </button>
          )}

          {/* Admin-only: Add Camera Button */}
          {hasRole(["admin"]) && onAddCamera && (
            <button
              onClick={onAddCamera}
              className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3 py-2 rounded-lg flex items-center space-x-1.5 shadow transition"
            >
              <Plus className="w-4 h-4" />
              <span>Add Camera</span>
            </button>
          )}

          {/* User Profile & Role Pill */}
          {user && (
            <div className="flex items-center space-x-2.5 pl-3 border-l border-sentinel-border">
              <div className="flex flex-col text-right">
                <span className="text-xs font-semibold text-gray-200 leading-tight">
                  {user.name}
                </span>
                <span
                  className={`text-[9px] uppercase font-mono px-1.5 py-0.5 rounded border mt-0.5 self-end ${roleBadge.style}`}
                >
                  {roleBadge.label}
                </span>
              </div>

              <button
                onClick={logout}
                title="Log out of Safecam AI"
                className="p-1.5 rounded-lg bg-gray-800/80 hover:bg-red-500/20 hover:text-red-400 border border-gray-700 text-gray-400 transition"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
