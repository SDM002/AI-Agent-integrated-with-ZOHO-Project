"use client";

import { motion, AnimatePresence } from "motion/react";
import { useState, useRef, useEffect } from "react";
import { Mic, ArrowUp } from "lucide-react";

export function InputBar({ onSend, theme, onMicClick, onCancel, input = "", setInput, orbState = "idle", isCorrecting = false }) {
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef(null);

  const dark = theme === "dark";

  // Auto-resize textarea — expands up to 200px for long voice transcripts
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }, [input]);

  const handleSubmit = () => {
    if (input.trim()) {
      onSend(input);
      setInput("");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
    if (e.key === "Escape") {
      e.preventDefault();
      setInput("");
      if (onCancel) onCancel();
    }
  };

  return (
    <div className="fixed bottom-8 left-1/2 -translate-x-1/2 w-full max-w-3xl px-8 z-40">
      <motion.div
        className={`relative flex flex-col gap-1 px-4 py-3 rounded-[28px] backdrop-blur-xl transition-all duration-300 ${
          dark ? "bg-[#2f2f2f] border border-[#4a4a4a]" : "bg-white border border-gray-300"
        }`}
        style={{
          boxShadow: isFocused
            ? dark ? "0 0 0 2px rgba(0,120,215,0.35)" : "0 0 0 2px rgba(0,120,215,0.2)"
            : "0 2px 8px rgba(0,0,0,0.1)",
        }}
        animate={{ scale: isFocused ? 1.005 : 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
      >
        {/* Voice transcript label — shown when text came from voice input */}
        <AnimatePresence>
          {isCorrecting && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-center gap-1.5 px-1"
            >
              <svg className="w-3 h-3 animate-spin text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              <span className={`text-[11px] font-['Plus_Jakarta_Sans'] ${dark ? "text-white/40" : "text-gray-400"}`}>
                Correcting transcript…
              </span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Textarea + send/mic row */}
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onKeyDown={handleKeyDown}
            placeholder={
              isCorrecting
                ? "Correcting transcript…"
                : "Message Skysecure AI Agent"
            }
            rows={1}
            className={`flex-1 bg-transparent outline-none font-['Plus_Jakarta_Sans'] text-[15px] resize-none leading-relaxed ${
              dark ? "text-white placeholder:text-gray-400" : "text-gray-900 placeholder:text-gray-500"
            }`}
            style={{ maxHeight: "200px", overflowY: "auto", scrollbarWidth: "none", msOverflowStyle: "none" }}
          />

          <div className="flex-shrink-0 mb-0.5">
            {input.trim() ? (
              <motion.button
                type="button"
                onClick={handleSubmit}
                disabled={orbState === "processing"}
                className="w-8 h-8 rounded-full flex items-center justify-center"
                style={{
                  opacity:       orbState === "processing" ? 0.35 : 1,
                  cursor:        orbState === "processing" ? "not-allowed" : "pointer",
                  pointerEvents: orbState === "processing" ? "none" : "auto",
                  background:    orbState === "processing" ? "#22c55e" : dark ? "#ffffff" : "#000000",
                  color:         orbState === "processing" ? "#ffffff" : dark ? "#000000" : "#ffffff",
                  boxShadow:     orbState === "processing" ? "0 0 12px rgba(34,197,94,0.5)" : "none",
                }}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                transition={{ type: "spring", stiffness: 400, damping: 17 }}
              >
                <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
              </motion.button>
            ) : (
              <motion.button
                type="button"
                onClick={onMicClick}
                disabled={orbState === "processing"}
                className="relative w-8 h-8 rounded-full flex items-center justify-center"
                style={{
                  opacity:       orbState === "processing" ? 0.35 : 1,
                  cursor:        orbState === "processing" ? "not-allowed" : "pointer",
                  pointerEvents: orbState === "processing" ? "none" : "auto",
                  background:
                    orbState === "listening"  ? "rgba(239,68,68,0.15)" :
                    orbState === "processing" ? "rgba(34,197,94,0.15)" :
                    orbState === "speaking"   ? "rgba(99,102,241,0.15)" :
                    "transparent",
                  color:
                    orbState === "listening"  ? "#ef4444" :
                    orbState === "processing" ? "#22c55e" :
                    orbState === "speaking"   ? "#6366f1" :
                    dark ? "#9ca3af" : "#4b5563",
                }}
                animate={{ scale: orbState === "listening" ? [1, 1.15, 1] : 1 }}
                transition={
                  orbState === "listening"
                    ? { repeat: Infinity, duration: 1.2, ease: "easeInOut" }
                    : { type: "spring", stiffness: 400, damping: 17 }
                }
                whileTap={{ scale: 0.9 }}
              >
                {orbState === "listening" && (
                  <span className="absolute inset-0 rounded-full animate-ping bg-red-400 opacity-30" />
                )}
                <Mic className="w-4 h-4 relative z-10" />
              </motion.button>
            )}
          </div>
        </div>

      </motion.div>
    </div>
  );
}
