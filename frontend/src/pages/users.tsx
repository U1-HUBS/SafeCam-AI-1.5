import React, { useState, useEffect, useCallback } from "react";
import Head from "next/head";
import { Header } from "../components/Header";
import { useAuth } from "../context/AuthContext";
import { User, Role } from "../types";
import {
  Users,
  UserPlus,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Edit2,
  Trash2,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  X,
  Lock,
} from "lucide-react";

const API_BASE = "http://localhost:5000/api";

export default function UsersManagementPage() {
  const { authFetch, user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  // Form states
  const [formData, setFormData] = useState({
    username: "",
    name: "",
    email: "",
    password: "",
    role: "security" as Role,
    active: true,
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);

  const fetchUsers = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await authFetch(`${API_BASE}/auth/users`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      } else {
        const err = await res.json();
        setError(err.error || "Failed to load users");
      }
    } catch (e) {
      setError("Network error fetching users list");
    } finally {
      setIsLoading(false);
    }
  }, [authFetch]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleOpenAdd = () => {
    setFormData({
      username: "",
      name: "",
      email: "",
      password: "",
      role: "security",
      active: true,
    });
    setFormError(null);
    setIsAddModalOpen(true);
  };

  const handleOpenEdit = (user: User) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      name: user.name,
      email: user.email,
      password: "", // empty means keep existing
      role: user.role,
      active: user.active,
    });
    setFormError(null);
  };

  const handleSaveAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSubmitting(true);
    try {
      const res = await authFetch(`${API_BASE}/auth/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      if (!res.ok) {
        setFormError(data.error || "Failed to create user");
      } else {
        setIsAddModalOpen(false);
        fetchUsers();
      }
    } catch (e) {
      setFormError("Network error occurred");
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    setFormError(null);
    setFormSubmitting(true);
    try {
      const payload: any = {
        name: formData.name,
        email: formData.email,
        role: formData.role,
        active: formData.active,
      };
      if (formData.password.trim()) {
        payload.password = formData.password.trim();
      }

      const res = await authFetch(`${API_BASE}/auth/users/${editingUser.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        setFormError(data.error || "Failed to update user");
      } else {
        setEditingUser(null);
        fetchUsers();
      }
    } catch (e) {
      setFormError("Network error occurred");
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDeleteUser = async (user: User) => {
    if (!confirm(`Are you sure you want to delete user "${user.username}"?`)) return;
    try {
      const res = await authFetch(`${API_BASE}/auth/users/${user.id}`, {
        method: "DELETE",
      });
      if (res.ok) {
        fetchUsers();
      } else {
        const data = await res.json();
        alert(data.error || "Failed to delete user");
      }
    } catch (e) {
      alert("Network error deleting user");
    }
  };

  const getRoleIconAndBadge = (role: Role) => {
    switch (role) {
      case "admin":
        return {
          icon: Shield,
          label: "Admin",
          badge: "bg-red-500/20 text-red-300 border-red-500/30",
        };
      case "supervisor":
        return {
          icon: ShieldCheck,
          label: "Supervisor",
          badge: "bg-amber-500/20 text-amber-300 border-amber-500/30",
        };
      case "security":
      default:
        return {
          icon: ShieldAlert,
          label: "Security",
          badge: "bg-blue-500/20 text-blue-300 border-blue-500/30",
        };
    }
  };

  return (
    <>
      <Head>
        <title>User Management & RBAC — CCTV Sentinel</title>
      </Head>

      <Header cameraCount={0} activeAlertCount={0} />

      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Title & Action */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide flex items-center space-x-2">
              <Users className="w-5 h-5 text-blue-400" />
              <span>User & Role-Based Access Control</span>
            </h1>
            <p className="text-xs text-gray-400 mt-0.5">
              Manage operators, supervisors, and administrative credentials for CCTV Sentinel.
            </p>
          </div>

          <button
            onClick={handleOpenAdd}
            className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3.5 py-2 rounded-lg flex items-center space-x-1.5 shadow transition self-start md:self-auto"
          >
            <UserPlus className="w-4 h-4" />
            <span>Add New User</span>
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Users Table */}
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl overflow-hidden shadow-lg">
          {isLoading ? (
            <div className="p-12 flex justify-center items-center">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-gray-400 uppercase text-[10px] tracking-wider border-b border-sentinel-border">
                  <tr>
                    <th className="px-5 py-3.5">User</th>
                    <th className="px-5 py-3.5">Email</th>
                    <th className="px-5 py-3.5">Role</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5">Created</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-sentinel-border">
                  {users.map((u) => {
                    const { icon: RoleIcon, label, badge } = getRoleIconAndBadge(u.role);
                    const isSelf = u.id === currentUser?.id;

                    return (
                      <tr key={u.id} className="hover:bg-slate-800/40 transition">
                        <td className="px-5 py-3.5">
                          <div className="flex items-center space-x-3">
                            <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-gray-300">
                              {u.name.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <div className="font-semibold text-white flex items-center space-x-1.5">
                                <span>{u.name}</span>
                                {isSelf && (
                                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                    You
                                  </span>
                                )}
                              </div>
                              <span className="text-gray-400 text-[11px]">@{u.username}</span>
                            </div>
                          </div>
                        </td>

                        <td className="px-5 py-3.5 text-gray-300 font-mono text-[11px]">{u.email}</td>

                        <td className="px-5 py-3.5">
                          <span
                            className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold border ${badge}`}
                          >
                            <RoleIcon className="w-3.5 h-3.5" />
                            <span>{label}</span>
                          </span>
                        </td>

                        <td className="px-5 py-3.5">
                          {u.active ? (
                            <span className="inline-flex items-center space-x-1 text-emerald-400 font-medium">
                              <CheckCircle className="w-3.5 h-3.5" />
                              <span>Active</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center space-x-1 text-gray-500 font-medium">
                              <XCircle className="w-3.5 h-3.5" />
                              <span>Inactive</span>
                            </span>
                          )}
                        </td>

                        <td className="px-5 py-3.5 text-gray-400 text-[11px]">
                          {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                        </td>

                        <td className="px-5 py-3.5 text-right">
                          <div className="flex items-center justify-end space-x-2">
                            <button
                              onClick={() => handleOpenEdit(u)}
                              title="Edit User"
                              className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 transition"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>

                            {!isSelf && (
                              <button
                                onClick={() => handleDeleteUser(u)}
                                title="Delete User"
                                className="p-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Add User Modal */}
        {isAddModalOpen && (
          <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-sentinel-card border border-sentinel-border rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-fade-in">
              <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
                <h3 className="text-base font-bold text-white flex items-center space-x-2">
                  <UserPlus className="w-5 h-5 text-blue-400" />
                  <span>Add New System User</span>
                </h3>
                <button
                  onClick={() => setIsAddModalOpen(false)}
                  className="text-gray-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {formError && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-xs flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              <form onSubmit={handleSaveAdd} className="space-y-3.5 text-xs">
                <div>
                  <label className="block text-gray-300 font-medium mb-1">Full Name</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Officer John Davis"
                    className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-gray-300 font-medium mb-1">Username</label>
                    <input
                      type="text"
                      required
                      value={formData.username}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                      placeholder="e.g. jdavis"
                      className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-gray-300 font-medium mb-1">Password</label>
                    <input
                      type="password"
                      required
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      placeholder="Password"
                      className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-gray-300 font-medium mb-1">Email Address</label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="e.g. jdavis@sentinel.local"
                    className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 font-medium mb-1">Role & Permissions</label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value as Role })}
                    className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="security">Security Operator (Live wall, alerts & review)</option>
                    <option value="supervisor">Supervisor (Incident audits, reviews, reports)</option>
                    <option value="admin">Administrator (Full system & user access)</option>
                  </select>
                </div>

                <div className="flex items-center space-x-2 pt-2">
                  <input
                    type="checkbox"
                    id="add_active"
                    checked={formData.active}
                    onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                    className="rounded border-sentinel-border bg-slate-900 text-blue-600 focus:ring-0"
                  />
                  <label htmlFor="add_active" className="text-gray-300 font-medium cursor-pointer">
                    Account is Active
                  </label>
                </div>

                <div className="flex justify-end space-x-2 pt-3 border-t border-sentinel-border">
                  <button
                    type="button"
                    onClick={() => setIsAddModalOpen(false)}
                    className="px-4 py-2 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={formSubmitting}
                    className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold transition flex items-center space-x-1.5"
                  >
                    {formSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    <span>Create User</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit User Modal */}
        {editingUser && (
          <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-sentinel-card border border-sentinel-border rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-fade-in">
              <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
                <h3 className="text-base font-bold text-white flex items-center space-x-2">
                  <Edit2 className="w-5 h-5 text-blue-400" />
                  <span>Edit User: @{editingUser.username}</span>
                </h3>
                <button
                  onClick={() => setEditingUser(null)}
                  className="text-gray-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {formError && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-xs flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              <form onSubmit={handleSaveEdit} className="space-y-3.5 text-xs">
                <div>
                  <label className="block text-gray-300 font-medium mb-1">Full Name</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 font-medium mb-1">Email Address</label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 font-medium mb-1">Role & Permissions</label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value as Role })}
                    disabled={editingUser.id === currentUser?.id}
                    className="w-full bg-slate-900 border border-sentinel-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 disabled:opacity-50"
                  >
                    <option value="security">Security Operator (Live wall, alerts & review)</option>
                    <option value="supervisor">Supervisor (Incident audits, reviews, reports)</option>
                    <option value="admin">Administrator (Full system & user access)</option>
                  </select>
                  {editingUser.id === currentUser?.id && (
                    <p className="text-[10px] text-gray-400 mt-1">
                      You cannot change your own administrator role.
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-gray-300 font-medium mb-1">
                    Reset Password (leave blank to keep current)
                  </label>
                  <div className="relative">
                    <Lock className="w-3.5 h-3.5 text-gray-500 absolute left-3 top-3" />
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      placeholder="New password (optional)"
                      className="w-full bg-slate-900 border border-sentinel-border rounded-lg pl-9 pr-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2 pt-2">
                  <input
                    type="checkbox"
                    id="edit_active"
                    checked={formData.active}
                    disabled={editingUser.id === currentUser?.id}
                    onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                    className="rounded border-sentinel-border bg-slate-900 text-blue-600 focus:ring-0 disabled:opacity-50"
                  />
                  <label htmlFor="edit_active" className="text-gray-300 font-medium cursor-pointer">
                    Account is Active
                  </label>
                </div>

                <div className="flex justify-end space-x-2 pt-3 border-t border-sentinel-border">
                  <button
                    type="button"
                    onClick={() => setEditingUser(null)}
                    className="px-4 py-2 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={formSubmitting}
                    className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold transition flex items-center space-x-1.5"
                  >
                    {formSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    <span>Save Changes</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
