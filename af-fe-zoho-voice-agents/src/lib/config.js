export const BACKEND_URL = (typeof window !== "undefined" && window.__RUNTIME_ENV__?.BACKEND_URL)
  || process.env.BACKEND_URL;

export const FETCH_TIMEOUT_MS = Number(
  (typeof window !== "undefined" && window.__RUNTIME_ENV__?.FETCH_TIMEOUT_MS)
  || process.env.FETCH_TIMEOUT_MS
);

export const FETCH_RETRY_DELAY_MS = Number(
  (typeof window !== "undefined" && window.__RUNTIME_ENV__?.FETCH_RETRY_DELAY_MS)
  || process.env.FETCH_RETRY_DELAY_MS
);