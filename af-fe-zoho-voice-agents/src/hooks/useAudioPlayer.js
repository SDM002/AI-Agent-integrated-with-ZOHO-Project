"use client";

import { useRef } from "react";

export function useAudioPlayer({ setOrbState, getMicActive }) {
  const botAudRef = useRef(null);
  const playingRef = useRef(false);
  const playTimeoutRef = useRef(null);

  const clearPlayTimeout = () => {
    if (playTimeoutRef.current) {
      clearTimeout(playTimeoutRef.current);
      playTimeoutRef.current = null;
    }
  };

  const resetPlaying = (delay = 0) => {
    clearPlayTimeout();
    if (delay > 0) {
      playTimeoutRef.current = setTimeout(() => {
        playingRef.current = false;
        playTimeoutRef.current = null;
      }, delay);
    } else {
      playingRef.current = false;
    }
  };

  const stopBotAud = () => {
    clearPlayTimeout();
    if (typeof window !== "undefined" && window.speechSynthesis) window.speechSynthesis.cancel();
    if (botAudRef.current) {
      const audio = botAudRef.current;
      botAudRef.current = null;
      const pp = audio._playPromise;
      if (pp) {
        pp.then(() => { audio.pause(); audio.currentTime = 0; if (audio.src) URL.revokeObjectURL(audio.src); })
          .catch(() => { audio.pause(); if (audio.src) URL.revokeObjectURL(audio.src); });
      } else {
        audio.pause();
        if (audio.src) URL.revokeObjectURL(audio.src);
      }
    }
    playingRef.current = false;
    setOrbState(getMicActive() ? "listening" : "idle");
  };

  const speakFallback = (text, onEnd) => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      resetPlaying();
      if (onEnd) onEnd(); else setOrbState("idle");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text.replace(/[*_]/g, ""));
    playingRef.current = true;
    setOrbState("speaking");

    const wordCount = text.split(/\s+/).length;
    const maxMs = Math.max(4000, wordCount * 500) + 2000;
    clearPlayTimeout();
    playTimeoutRef.current = setTimeout(() => {
      playingRef.current = false;
      playTimeoutRef.current = null;
      if (onEnd) onEnd(); else setOrbState("idle");
    }, maxMs);

    utterance.onend = () => { clearPlayTimeout(); playingRef.current = false; if (onEnd) onEnd(); else setOrbState("idle"); };
    utterance.onerror = () => { clearPlayTimeout(); playingRef.current = false; if (onEnd) onEnd(); else setOrbState("idle"); };
    window.speechSynthesis.speak(utterance);
  };

  const playAudio = async (b64, mime) => {
    stopBotAud();
    clearPlayTimeout();
    const bytes = atob(b64);
    const buf = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) buf[i] = bytes.charCodeAt(i);
    const url = URL.createObjectURL(new Blob([buf], { type: mime }));
    const audio = new Audio(url);
    botAudRef.current = audio;
    playingRef.current = true;
    audio._startTime = Date.now();
    setOrbState("speaking");

    playTimeoutRef.current = setTimeout(() => {
      playingRef.current = false;
      playTimeoutRef.current = null;
      setOrbState(getMicActive() ? "listening" : "idle");
    }, 30000);

    audio.onended = () => {
      clearPlayTimeout();
      URL.revokeObjectURL(url);
      if (botAudRef.current === audio) botAudRef.current = null;
      playingRef.current = false;
      setTimeout(() => setOrbState(getMicActive() ? "listening" : "idle"), 500);
    };
    audio.onerror = () => { clearPlayTimeout(); playingRef.current = false; setOrbState("idle"); };

    const p = audio.play();
    audio._playPromise = p;
    p.then(() => { }).catch((err) => {
      clearPlayTimeout();
      if (err.name !== "AbortError" && err.name === "NotAllowedError") alert("Click anywhere to enable audio.");
      playingRef.current = false;
      setOrbState("idle");
    });
  };

  return { playingRef, botAudRef, playAudio, stopBotAud, speakFallback, resetPlaying };
}
