import React, { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import { useAuth } from "../context/AuthContext";
import {
  ShieldAlert,
  Lock,
  User as UserIcon,
  ArrowRight,
  ShieldCheck,
  Shield,
  Loader2,
  AlertCircle,
  Eye,
  EyeOff,
} from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace("/");
    }
  }, [isAuthenticated, authLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError("Please provide both username/email and password.");
      return;
    }

    setError(null);
    setIsSubmitting(true);
    const result = await login(username.trim(), password);
    setIsSubmitting(false);

    if (result.success) {
      router.push("/");
    } else {
      setError(result.error || "Login failed. Check your credentials.");
    }
  };

  const handleQuickLogin = async (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setError(null);
    setIsSubmitting(true);
    const result = await login(u, p);
    setIsSubmitting(false);

    if (result.success) {
      router.push("/");
    } else {
      setError(result.error || "Login failed.");
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-sentinel-bg flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>Login — CCTV Sentinel AI Monitoring</title>
      </Head>

      <div className="min-h-screen bg-sentinel-bg flex flex-col justify-center items-center px-4 py-12 relative overflow-hidden">
        {/* Ambient background glows */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-red-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-md w-full space-y-8 z-10">
          {/* Header Brand */}
          <div className="text-center space-y-2">
            <div className="inline-flex items-center justify-center p-3.5 bg-red-500/10 border border-red-500/30 rounded-2xl shadow-lg shadow-red-500/10">
              <ShieldAlert className="w-9 h-9 text-red-500" />
            </div>
            <h1 className="text-2xl font-bold tracking-wider text-white">CCTV SENTINEL</h1>
            <p className="text-xs text-gray-400">
              AI Central Monitoring & Violence Incident Management System
            </p>
          </div>

          {/* Login Card */}
          <div className="bg-sentinel-card border border-sentinel-border rounded-2xl p-6 shadow-2xl backdrop-blur-sm space-y-6">
            <div className="border-b border-sentinel-border pb-3">
              <h2 className="text-base font-semibold text-gray-200">Sign in to your account</h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Role-based access requires operator authentication.
              </p>
            </div>

            {error && (
              <div className="flex items-center space-x-2.5 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs animate-shake">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  Username or Email
                </label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. admin or security"
                    className="w-full bg-slate-900 border border-sentinel-border rounded-lg pl-9 pr-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 transition placeholder:text-gray-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full bg-slate-900 border border-sentinel-border rounded-lg pl-9 pr-10 py-2 text-sm text-white focus:outline-none focus:border-blue-500 transition placeholder:text-gray-600"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-gray-500 hover:text-gray-300"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full mt-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold py-2.5 px-4 rounded-lg flex items-center justify-center space-x-2 text-sm shadow-md transition"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Quick Demo Logins Section */}
            <div className="pt-4 border-t border-sentinel-border space-y-3">
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span className="font-semibold uppercase tracking-wider text-[10px] text-gray-400">
                  Quick Demo Accounts
                </span>
                <span className="text-[11px] text-gray-400">Click to log in</span>
              </div>

              <div className="grid grid-cols-1 gap-2">
                {/* Admin Role Card */}
                <button
                  type="button"
                  onClick={() => handleQuickLogin("admin", "admin123")}
                  disabled={isSubmitting}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-red-500/20 bg-red-500/5 hover:bg-red-500/10 hover:border-red-500/40 transition text-left group"
                >
                  <div className="flex items-center space-x-2.5">
                    <div className="p-1.5 rounded-md bg-red-500/20 text-red-400 group-hover:scale-105 transition">
                      <Shield className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-xs font-semibold text-white">Administrator</span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-red-500/20 text-red-300 font-mono">
                          ADMIN
                        </span>
                      </div>
                      <p className="text-[11px] text-gray-400">Full system & camera configuration, users</p>
                    </div>
                  </div>
                  <span className="text-xs text-gray-400 group-hover:text-red-400 font-medium">Use &rarr;</span>
                </button>

                {/* Supervisor Role Card */}
                <button
                  type="button"
                  onClick={() => handleQuickLogin("supervisor", "super123")}
                  disabled={isSubmitting}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-amber-500/20 bg-amber-500/5 hover:bg-amber-500/10 hover:border-amber-500/40 transition text-left group"
                >
                  <div className="flex items-center space-x-2.5">
                    <div className="p-1.5 rounded-md bg-amber-500/20 text-amber-400 group-hover:scale-105 transition">
                      <ShieldCheck className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-xs font-semibold text-white">Shift Supervisor</span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 font-mono">
                          SUPERVISOR
                        </span>
                      </div>
                      <p className="text-[11px] text-gray-400">Incident review & auditing, analytics KPIs</p>
                    </div>
                  </div>
                  <span className="text-xs text-gray-400 group-hover:text-amber-400 font-medium">Use &rarr;</span>
                </button>

                {/* Security Operator Role Card */}
                <button
                  type="button"
                  onClick={() => handleQuickLogin("security", "sec123")}
                  disabled={isSubmitting}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-blue-500/20 bg-blue-500/5 hover:bg-blue-500/10 hover:border-blue-500/40 transition text-left group"
                >
                  <div className="flex items-center space-x-2.5">
                    <div className="p-1.5 rounded-md bg-blue-500/20 text-blue-400 group-hover:scale-105 transition">
                      <ShieldAlert className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-xs font-semibold text-white">Security Officer</span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-500/20 text-blue-300 font-mono">
                          SECURITY
                        </span>
                      </div>
                      <p className="text-[11px] text-gray-400">Live wall, alert acknowledgment & incident review</p>
                    </div>
                  </div>
                  <span className="text-xs text-gray-400 group-hover:text-blue-400 font-medium">Use &rarr;</span>
                </button>
              </div>
            </div>
          </div>

          {/* Footer Info */}
          <div className="text-center text-[11px] text-gray-400">
            CCTV Sentinel v2.0 &bull; Edge AI Violence Detection &bull; Multi-Tier RBAC
          </div>
        </div>
      </div>
    </>
  );
}
