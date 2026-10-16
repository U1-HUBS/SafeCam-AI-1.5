export const API_HOST =
  process.env.NEXT_PUBLIC_API_HOST || "http://127.0.0.1:5000";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || `${API_HOST}/api`;
