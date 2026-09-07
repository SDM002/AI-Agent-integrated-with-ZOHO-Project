"use client";

import { motion, AnimatePresence } from "motion/react";

export function VoiceMode({
  onToggleListening,
  isListening,
  theme,
  voiceState = "idle",
  transcript,
  selectedVoice = "female",
  onVoiceChange,
}) {

  const colors = {
    idle:       "#0078D7",
    listening:  "#ef4444", // Red for active mic
    processing: "#f97316", // Orange for thinking
    speaking:   "#22c55e", // Green for talking
  };

  const labels = {
    idle:       "Tap to talk",
    listening:  "I'm listening...",
    processing: "Thinking...",
    speaking:   "Speaking...",
  };

  const color = colors[voiceState] || colors.idle;

  return (
    <motion.div className="flex flex-col items-center gap-6 w-full max-w-sm"
      initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}>

      {/* Live Transcript Area */}
      <div className="h-20 flex items-center justify-center w-full px-4 text-center">
        <AnimatePresence mode="wait">
          {transcript ? (
            <motion.p 
              key="transcript"
              className={`text-lg font-medium leading-tight ${theme === "dark" ? "text-white" : "text-gray-800"}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
            >
              &quot;{transcript}&quot;
            </motion.p>
          ) : (
            <motion.p 
              key="prompt"
              className={`text-sm ${theme === "dark" ? "text-white/40" : "text-gray-400"}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              {voiceState === "idle" ? "How can I help with your Zoho Projects?" : ""}
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* Main Mic Button & Rings */}
      <div className="relative flex items-center justify-center w-40 h-40">
        
        {/* Breathing background glow */}
        <motion.div 
          className="absolute inset-0 rounded-full blur-2xl opacity-20"
          style={{ backgroundColor: color }}
          animate={{ scale: [1, 1.2, 1], opacity: [0.1, 0.3, 0.1] }}
          transition={{ duration: 2, repeat: Infinity }}
        />

        {/* Pulse rings — listening */}
        {voiceState === "listening" && [1, 2, 3].map(i => (
          <motion.div key={i} className="absolute rounded-full"
            style={{ width: 80, height: 80, border: `2px solid ${color}` }}
            animate={{ scale: [1, 2.5], opacity: [0.5, 0] }}
            transition={{ duration: 2, repeat: Infinity, delay: i * 0.6, ease: "easeOut" }}
          />
        ))}

        {/* Spinning border — processing */}
        {voiceState === "processing" && (
          <motion.div className="absolute rounded-full"
            style={{ width: 100, height: 100, border: `4px solid transparent`, borderTopColor: color, borderRightColor: color }}
            animate={{ rotate: 360 }}
            transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
          />
        )}

        {/* The Button */}
        <motion.button 
          onClick={voiceState !== "processing" ? onToggleListening : undefined}
          className="relative w-24 h-24 rounded-full flex items-center justify-center z-10 shadow-2xl"
          style={{
            background: `radial-gradient(circle at 35% 35%, ${color}ee, ${color})`,
            boxShadow: `0 0 40px ${color}40`,
            cursor: voiceState === "processing" ? "default" : "pointer",
          }}
          whileHover={voiceState !== "processing" ? { scale: 1.05 } : {}}
          whileTap={voiceState !== "processing" ? { scale: 0.95 } : {}}
        >
          {voiceState === "listening" ? (
            <div className="flex gap-1 items-center h-8">
              {[0, 1, 2, 3, 4].map(i => (
                <motion.div key={i} className="w-1.5 rounded-full bg-white shadow-sm"
                  animate={{ height: [8, 32, 8] }}
                  transition={{ duration: 0.4, repeat: Infinity, delay: i * 0.1, ease: "easeInOut" }}
                />
              ))}
            </div>
          ) : voiceState === "processing" ? (
            <div className="flex gap-2">
              {[0, 1, 2].map(i => (
                <motion.div key={i} className="w-3 h-3 rounded-full bg-white shadow-sm"
                  animate={{ scale: [0.8, 1.4, 0.8], opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.2 }}
                />
              ))}
            </div>
          ) : voiceState === "speaking" ? (
            <div className="flex gap-0.5 items-center h-8">
              {[0, 1, 2, 3, 4, 5, 6].map(i => (
                <motion.div key={i} className="w-1 rounded-full bg-white shadow-sm"
                  animate={{ height: [4, 24, 4] }}
                  transition={{ duration: 0.3, repeat: Infinity, delay: i * 0.05, ease: "easeInOut" }}
                />
              ))}
            </div>
          ) : (
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" x2="12" y1="19" y2="22"/>
            </svg>
          )}
        </motion.button>
      </div>

      {/* Label area removed per user request - visual effect is enough */}
      <div className="flex flex-col items-center gap-1 min-h-[1.5rem]">
        {voiceState === "listening" && (
          <p className={`text-xs ${theme === "dark" ? "text-white/30" : "text-gray-400"}`}>
            Tap to finish manually
          </p>
        )}
      </div>

    </motion.div>
  );
}
