"use client";

import { useRef, useState } from "react";

const SESSION_LIMIT_MS = 55000;

export function useSpeechRecognition({ playingRef, setOrbState, onInterim, onFlush }) {
  const [micActive, setMicActive] = useState(false);
  const micOnRef = useRef(false);

  const srRef = useRef(null);
  const accumulatedRef = useRef([]);
  const lastInterimRef = useRef("");
  const sessionTimerRef = useRef(null);
  const shouldRestartRef = useRef(false);
  const flushScheduledRef = useRef(false);
  const startSessionRef = useRef(null);
  const flushTranscriptRef = useRef(null);

  const dedup = (existingText, newSegment) => {
    if (!existingText || !newSegment) return newSegment;
    const existWords = existingText.trim().split(/\s+/);
    const newWords = newSegment.trim().split(/\s+/);
    for (let overlap = Math.min(8, existWords.length, newWords.length); overlap >= 2; overlap--) {
      const tail = existWords.slice(-overlap).join(" ").toLowerCase();
      const head = newWords.slice(0, overlap).join(" ").toLowerCase();
      if (tail === head) return newWords.slice(overlap).join(" ");
    }
    return newSegment;
  };

  const getFullTranscript = () => {
    const parts = [...accumulatedRef.current];
    if (lastInterimRef.current.trim()) parts.push(lastInterimRef.current.trim());
    return parts.join(" ").trim();
  };

  const flushTranscript = () => {
    flushScheduledRef.current = false;
    const full = getFullTranscript();
    micOnRef.current = false;
    setMicActive(false);
    accumulatedRef.current = [];
    lastInterimRef.current = "";
    setOrbState("idle");
    onFlush?.(full.trim());
  };
  flushTranscriptRef.current = flushTranscript;

  const startSession = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    const sr = new SpeechRecognition();
    sr.continuous = true; sr.interimResults = true; sr.lang = "en-IN"; sr.maxAlternatives = 1;
    srRef.current = sr;

    sr.onresult = (e) => {
      if (playingRef.current) return;
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const result = e.results[i];
        if (result.isFinal) {
          const text = result[0].transcript.trim();
          if (text) {
            const clean = dedup(accumulatedRef.current.join(" "), text);
            if (clean) accumulatedRef.current.push(clean);
            lastInterimRef.current = "";
          }
        } else {
          interim += result[0].transcript;
        }
      }
      lastInterimRef.current = interim;
      onInterim?.(getFullTranscript());
    };

    sr.onend = () => {
      if (sessionTimerRef.current) { clearTimeout(sessionTimerRef.current); sessionTimerRef.current = null; }
      if (shouldRestartRef.current) { startSessionRef.current?.(); }
      else if (!flushScheduledRef.current) { flushScheduledRef.current = true; flushTranscriptRef.current?.(); }
    };

    sr.onerror = (e) => {
      if (sessionTimerRef.current) { clearTimeout(sessionTimerRef.current); sessionTimerRef.current = null; }
      if (e.error === "no-speech" && shouldRestartRef.current) { startSessionRef.current?.(); return; }
      if (shouldRestartRef.current) setTimeout(() => startSessionRef.current?.(), 300);
    };

    try { sr.start(); } catch (err) { console.error("sr.start() failed:", err); }

    sessionTimerRef.current = setTimeout(() => {
      if (!shouldRestartRef.current) return;
      if (lastInterimRef.current.trim()) {
        const clean = dedup(accumulatedRef.current.join(" "), lastInterimRef.current.trim());
        if (clean) accumulatedRef.current.push(clean);
        lastInterimRef.current = "";
      }
      srRef.current?.stop();
    }, SESSION_LIMIT_MS);
  };
  startSessionRef.current = startSession;

  const startSpeechRecognition = () => {
    if (micOnRef.current) return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert("Use Chrome or Edge for speech recognition."); return; }
    accumulatedRef.current = [];
    lastInterimRef.current = "";
    flushScheduledRef.current = false;
    shouldRestartRef.current = true;
    micOnRef.current = true;
    setMicActive(true);
    setOrbState("listening");
    onInterim?.("");
    startSession();
  };

  const stopSpeechRecognition = () => {
    shouldRestartRef.current = false;
    if (sessionTimerRef.current) { clearTimeout(sessionTimerRef.current); sessionTimerRef.current = null; }
    if (srRef.current) { srRef.current.stop(); srRef.current = null; }
    else if (!flushScheduledRef.current) { flushScheduledRef.current = true; flushTranscript(); }
  };

  const cancelSpeechRecognition = () => {
    shouldRestartRef.current = false;
    flushScheduledRef.current = true;
    if (sessionTimerRef.current) { clearTimeout(sessionTimerRef.current); sessionTimerRef.current = null; }
    if (srRef.current) {
      srRef.current.onend = null; srRef.current.onerror = null; srRef.current.onresult = null;
      try { srRef.current.stop(); } catch { }
      srRef.current = null;
    }
    accumulatedRef.current = [];
    lastInterimRef.current = "";
    micOnRef.current = false;
    setMicActive(false);
    setOrbState("idle");
    onInterim?.("");
  };

  const cleanupSpeechRecognition = () => {
    shouldRestartRef.current = false;
    flushScheduledRef.current = true;
    if (sessionTimerRef.current) { clearTimeout(sessionTimerRef.current); sessionTimerRef.current = null; }
    if (srRef.current) {
      srRef.current.onend = null; srRef.current.onerror = null;
      try { srRef.current.stop(); } catch { }
      srRef.current = null;
    }
    accumulatedRef.current = [];
    lastInterimRef.current = "";
    micOnRef.current = false;
    setMicActive(false);
  };

  return {
    micActive,
    micOnRef,
    startSpeechRecognition,
    stopSpeechRecognition,
    cancelSpeechRecognition,
    cleanupSpeechRecognition,
  };
}
