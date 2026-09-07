"use client";

import { useRef, useEffect } from "react";
import { useWsBaseUrl } from "@/hooks/useWsBaseUrl";

export function useWebSocket({
  voiceRef,
  sessionId,
  teamsUserId,
  teamsTenantId,
  onReply,
  onStatus,
  onConnectRequired,
  onTranscriptCorrected,
  onClose,
  startSpeechRecognition,
}) {
  const wsRef = useRef(null);
  const wsBaseUrl = useWsBaseUrl(); // fetched from /api/deployment/ws-url

  // Auto‑connect as soon as the base URL is available
  useEffect(() => {
    console.log('[useWebSocket] wsBaseUrl changed:', wsBaseUrl);
    if (wsBaseUrl && !wsRef.current) {
      console.log('[useWebSocket] wsBaseUrl ready – auto-connecting...');
      connectWebSocket();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsBaseUrl]);

  const connectWebSocket = (autoStartMic = true) => {
    // If already open, reuse the socket
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      if (autoStartMic) startSpeechRecognition?.();
      return;
    }

    console.log('[useWebSocket] connectWebSocket called, wsBaseUrl:', wsBaseUrl);
    if (!wsBaseUrl) {
      console.warn('[useWebSocket] WS base URL not loaded yet – aborting');
      return;
    }

    const ws = new WebSocket(`${wsBaseUrl}/ws/voice`);
    wsRef.current = ws;
    console.log(`Connecting WebSocket to ${wsBaseUrl}/ws/voice`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      ws.send(JSON.stringify({
        type: 'config',
        voice: voiceRef.current,
        chat_id: sessionId.current,
        tenant_id: teamsTenantId,
        user_id: teamsUserId,
      }));
      if (autoStartMic) setTimeout(() => startSpeechRecognition?.(), 300);
    };

    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      console.log('WS Message:', m.type, m);
      if (m.type === 'status') onStatus?.(m.value);
      if (m.type === 'connect_required' || m.action === 'connect_required') onConnectRequired?.(m);
      if (m.type === 'transcript_corrected') onTranscriptCorrected?.(m);
      if (m.type === 'reply') onReply?.(m);
      if (m.type === 'interrupted') onStatus?.('interrupted');
    };

    ws.onclose = () => { console.log('WS closed'); onClose?.(); };
    ws.onerror = () => onStatus?.('error');
  };

  const sendMessage = (payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
      return true;
    }
    return false;
  };

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  return { wsRef, connectWebSocket, sendMessage, disconnect };
}
