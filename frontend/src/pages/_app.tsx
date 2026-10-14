import "@/styles/globals.css";
import type { AppProps } from "next/app";
import Head from "next/head";
import { useRouter } from "next/router";
import React, { useEffect } from "react";
import { AuthProvider, useAuth } from "../context/AuthContext";
import { Loader2, ShieldAlert } from "lucide-react";

function RouteGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();

  const isLoginPage = router.pathname === "/login";

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated && !isLoginPage) {
        router.replace("/login");
      }
    }
  }, [isAuthenticated, isLoading, isLoginPage, router]);

  if (isLoginPage) {
    return <>{children}</>;
  }

  if (isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen bg-sentinel-bg flex flex-col items-center justify-center space-y-3">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        <span className="text-xs text-gray-400">Verifying operator credentials...</span>
      </div>
    );
  }

  // Check RBAC for page routes
  if (router.pathname === "/users" && user?.role !== "admin") {
    return (
      <div className="min-h-screen bg-sentinel-bg flex flex-col items-center justify-center p-6 text-center space-y-4">
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-2xl">
          <ShieldAlert className="w-10 h-10 text-red-500" />
        </div>
        <h2 className="text-xl font-bold text-white">403 — Access Forbidden</h2>
        <p className="text-xs text-gray-400 max-w-sm">
          User Management requires System Administrator privileges. Your current role is{" "}
          <span className="font-semibold text-white uppercase">{user?.role}</span>.
        </p>
        <button
          onClick={() => router.push("/")}
          className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-lg"
        >
          Return to Live Wall
        </button>
      </div>
    );
  }

  if (router.pathname === "/reports" && user?.role === "security") {
    return (
      <div className="min-h-screen bg-sentinel-bg flex flex-col items-center justify-center p-6 text-center space-y-4">
        <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-2xl">
          <ShieldAlert className="w-10 h-10 text-amber-500" />
        </div>
        <h2 className="text-xl font-bold text-white">403 — Access Restricted</h2>
        <p className="text-xs text-gray-400 max-w-sm">
          Analytics & Reports require Supervisor or Administrator privileges.
        </p>
        <button
          onClick={() => router.push("/")}
          className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-lg"
        >
          Return to Live Wall
        </button>
      </div>
    );
  }

  return <>{children}</>;
}

export default function App({ Component, pageProps }: AppProps) {
  return (
    <AuthProvider>
      <Head>
        <title>CCTV Sentinel — AI Violence Monitoring</title>
        <meta name="description" content="AI CCTV Central Monitoring & Violence Incident Management System" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <div className="min-h-screen bg-sentinel-bg text-gray-100 flex flex-col">
        <RouteGuard>
          <Component {...pageProps} />
        </RouteGuard>
      </div>
    </AuthProvider>
  );
}
