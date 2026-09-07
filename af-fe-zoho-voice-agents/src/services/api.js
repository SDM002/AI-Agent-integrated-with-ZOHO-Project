import { BACKEND_URL } from "@/lib/config";

const _BACKEND = (BACKEND_URL || "").replace(/\/$/, "");

export const apiUrl = (path) => `${_BACKEND}${path}`;

export { getWsUrl as wsUrl } from "@/services/wsProxy";
