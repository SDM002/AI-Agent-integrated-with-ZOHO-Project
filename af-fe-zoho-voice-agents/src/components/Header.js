"use client";

/**
 * src/components/Header.js
 * Zoho connection status + connect/disconnect
 * Uses lucide icons: Sun, Moon, Power, ChevronDown, Link
 */
import { motion, AnimatePresence } from "motion/react";
import { Sun, Moon, Power, ChevronDown, Link } from "lucide-react";
import { useState, useEffect, useRef } from "react";

const voiceOptions = [
  { value: "warm", label: "Warm", icon: "🌟", accent: "#10b981" },
  { value: "professional", label: "Professional", icon: "💼", accent: "#6366f1" },
  { value: "fast", label: "Fast", icon: "⚡", accent: "#f59e0b" },
  { value: "female", label: "Female", icon: "🎙", accent: "#ec4899" },
  { value: "male", label: "Male", icon: "🎙", accent: "#3b82f6" },
];

export function Header({ theme, onThemeToggle, zohoStatus, onConnectZoho, onDisconnectZoho, selectedVoice = "warm", onVoiceChange }) {
  const [isVoiceOpen, setIsVoiceOpen] = useState(false);
  const [showZohoMenu, setShowZohoMenu] = useState(false);
  const voiceDropdownRef = useRef(null);
  const zohoMenuRef = useRef(null);

  const currentVoice = voiceOptions.find(v => v.value === selectedVoice) || voiceOptions[0];

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (voiceDropdownRef.current && !voiceDropdownRef.current.contains(e.target)) setIsVoiceOpen(false);
      if (zohoMenuRef.current && !zohoMenuRef.current.contains(e.target)) setShowZohoMenu(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <motion.header
      className="fixed top-0 left-0 right-0 z-50 px-8 py-4"
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
    >
      <div className="max-w-[1600px] mx-auto flex items-center justify-between gap-8">

        {/* LEFT: Logo */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <motion.div
            className="w-9 h-9 rounded-lg bg-gradient-to-br from-[#0078D7] to-[#00d9ff] flex items-center justify-center"
            whileHover={{ scale: 1.08, rotate: 5 }}
            whileTap={{ scale: 0.95 }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
            </svg>
          </motion.div>
          <div>
            <h1 className={`text-sm font-['Sora'] font-bold leading-none ${theme === "dark" ? "text-white" : "text-gray-900"}`}>
              Zoho Voice Logger
            </h1>
            <p className={`text-[10px] font-['Plus_Jakarta_Sans'] mt-0.5 ${theme === "dark" ? "text-white/40" : "text-gray-400"}`}>
              Skysecure Technologies
            </p>
          </div>
        </div>

        {/* RIGHT: Controls */}
        <div className="flex items-center gap-3">

          {/* Zoho Connection Status */}
          <div className="relative" ref={zohoMenuRef}>
            <motion.button
              onClick={() => setShowZohoMenu(!showZohoMenu)}
              className={`flex items-center gap-2 px-3 py-2 rounded-full backdrop-blur-xl text-xs font-['Plus_Jakarta_Sans'] font-medium transition-all ${zohoStatus?.connected
                  ? theme === "dark"
                    ? "bg-emerald-500/20 border border-emerald-500/30 text-emerald-400"
                    : "bg-emerald-50 border border-emerald-200 text-emerald-700"
                  : theme === "dark"
                    ? "bg-orange-500/20 border border-orange-500/30 text-orange-400"
                    : "bg-orange-50 border border-orange-200 text-orange-700"
                }`}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <span className={`w-2 h-2 rounded-full ${zohoStatus?.connected ? "bg-emerald-500" : "bg-orange-500"}`} />
              {zohoStatus?.connected
                ? (zohoStatus.email?.includes("@") ? zohoStatus.email.split("@")[0] : "Connected")
                : "Connect Zoho"}
              <ChevronDown className="w-3 h-3 opacity-60" />
            </motion.button>

            <AnimatePresence>
              {showZohoMenu && (
                <motion.div
                  className={`absolute right-0 top-full mt-2 w-56 rounded-2xl p-2 z-50 ${theme === "dark" ? "bg-[#1a1f2e] border border-white/10" : "bg-white border border-gray-100"
                    }`}
                  style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.15)" }}
                  initial={{ opacity: 0, y: -8, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                >
                  {zohoStatus?.connected ? (
                    <>
                      <div className={`px-3 pt-3 pb-1`}>
                        <p className={`text-[10px] font-['Plus_Jakarta_Sans'] uppercase tracking-wide mb-0.5 ${theme === "dark" ? "text-white/30" : "text-gray-400"}`}>
                          Signed in as
                        </p>
                        <p className={`text-xs font-['Plus_Jakarta_Sans'] font-semibold break-all ${theme === "dark" ? "text-white/90" : "text-gray-800"}`}>
                          {zohoStatus.email || "Zoho Account"}
                        </p>
                      </div>
                      <div className={`mx-3 my-2 border-t ${theme === "dark" ? "border-white/10" : "border-gray-100"}`} />
                      <motion.button
                        onClick={() => { onDisconnectZoho?.(); setShowZohoMenu(false); }}
                        className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-red-500 ${theme === "dark" ? "hover:bg-red-500/10" : "hover:bg-red-50"
                          }`}
                        whileHover={{ x: 2 }}
                      >
                        <Power className="w-3.5 h-3.5" />
                        Disconnect Zoho
                      </motion.button>
                    </>
                  ) : (
                    <motion.button
                      onClick={() => { setShowZohoMenu(false); onConnectZoho?.(); }}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-[#0078D7] ${theme === "dark" ? "hover:bg-[#0078D7]/10" : "hover:bg-blue-50"
                        }`}
                      whileHover={{ x: 2 }}
                    >
                      <Link className="w-3.5 h-3.5" />
                      Login to Zoho
                    </motion.button>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Voice selector */}
          <div className="relative" ref={voiceDropdownRef}>
            <motion.button
              onClick={() => setIsVoiceOpen(!isVoiceOpen)}
              className={`flex items-center gap-2 px-3 py-2 rounded-full backdrop-blur-xl text-xs font-['Plus_Jakarta_Sans'] font-medium transition-all ${theme === "dark"
                  ? "bg-white/5 border border-white/10 text-white/80 hover:bg-white/10"
                  : "bg-white/90 border border-gray-200 text-gray-700 hover:bg-white"
                }`}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <span>{currentVoice.icon}</span>
              <span>{currentVoice.label}</span>
              <ChevronDown className="w-3 h-3 opacity-60" />
            </motion.button>

            <AnimatePresence>
              {isVoiceOpen && (
                <motion.div
                  className={`absolute right-0 top-full mt-2 w-44 rounded-2xl p-1.5 z-50 ${theme === "dark" ? "bg-[#1a1f2e] border border-white/10" : "bg-white/95 border border-gray-200"
                    }`}
                  style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.15)" }}
                  initial={{ opacity: 0, y: -10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                >
                  {voiceOptions.map(option => (
                    <motion.button
                      key={option.value}
                      onClick={() => { onVoiceChange?.(option.value); setIsVoiceOpen(false); }}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl transition-all ${selectedVoice === option.value
                          ? theme === "dark" ? "text-white" : "text-gray-900"
                          : theme === "dark" ? "hover:bg-white/5 text-white/70" : "hover:bg-gray-100 text-gray-600"
                        }`}
                      style={
                        selectedVoice === option.value
                          ? { backgroundColor: `${option.accent}25`, borderLeft: `3px solid ${option.accent}` }
                          : { borderLeft: `3px solid transparent` }
                      }
                      whileHover={{ x: 2 }}
                    >
                      <span>{option.icon}</span>
                      <span className="text-xs font-['Plus_Jakarta_Sans'] font-medium"
                        style={{ color: selectedVoice === option.value ? option.accent : undefined }}>
                        {option.label}
                      </span>
                    </motion.button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Theme toggle */}
          <motion.button
            onClick={onThemeToggle}
            className={`p-2 rounded-full backdrop-blur-xl transition-all ${theme === "dark" ? "bg-white/5 border border-white/10 hover:bg-white/10" : "bg-white/90 border border-gray-200 hover:bg-white"
              }`}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            {theme === "dark"
              ? <Sun className="w-3.5 h-3.5 text-yellow-400" />
              : <Moon className="w-3.5 h-3.5 text-gray-600" />}
          </motion.button>
        </div>
      </div>
    </motion.header>
  );
}
