import { useEffect, useState } from "react";

export const useWsBaseUrl = () => {
  const [wsUrl, setWsUrl] = useState("");

  useEffect(() => {
    console.log('[useWsBaseUrl] Fetching WS base URL from /api/deployment/ws-url...');
    fetch("/api/deployment/ws-url")
      .then((res) => {
        console.log('[useWsBaseUrl] API response status:', res.status);
        return res.json();
      })
      .then((data) => {
        console.log('[useWsBaseUrl] API response data:', data);
        if (data && data.wsUrl) {
          const cleaned = data.wsUrl.replace(/\/+$/, "");
          console.log('[useWsBaseUrl] Setting WS base URL to:', cleaned);
          setWsUrl(cleaned);
        } else {
          console.error('[useWsBaseUrl] No wsUrl in response:', data);
        }
      })
      .catch((err) => {
        console.error("[useWsBaseUrl] Failed to fetch WS base URL:", err);
      });
  }, []);

  return wsUrl;
};
