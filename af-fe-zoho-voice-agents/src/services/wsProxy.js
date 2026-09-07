import { BACKEND_URL } from "@/lib/config";

// Base backend URL (without trailing slash)
const _BACKEND = (BACKEND_URL || "").replace(/\/$/, "");

/**
 * Returns the full WebSocket URL for a given path.
 *
 * Priority order:
 * 1. If NEXT_PUBLIC_BACKEND_WS_URL env var is set, use it directly.
 * 2. If BACKEND_URL is defined, convert it to ws(s) scheme.
 * 3. Fallback to the browser's location (useful for static hosting).
 */
export const getWsUrl = (path) => {

  // 2. Convert regular backend URL to ws(s)
  if (_BACKEND) {
    const wsBase = _BACKEND.replace(/^https/, "wss").replace(/^http/, "ws");
    return `${wsBase}${path}`;
  }

  // 3. Fallback to location (client‑side only)
  if (typeof location !== "undefined") {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${location.host}${path}`;
  }

  // If nothing works, return empty string so callers can handle the error.
  return "";
};
