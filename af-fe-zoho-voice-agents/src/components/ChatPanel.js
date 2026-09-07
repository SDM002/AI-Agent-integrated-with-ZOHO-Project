"use client";

import { motion, AnimatePresence } from "motion/react";

export function ChatPanel({ messages, theme }) {
  return (
    <motion.div
      className={`w-full max-w-md h-full rounded-3xl backdrop-blur-2xl overflow-hidden flex flex-col ${
        theme === "dark"
          ? "bg-white/5 border border-white/10"
          : "bg-white/90 border border-gray-200"
      }`}
      style={{
        boxShadow: theme === "dark"
          ? "0 20px 80px rgba(0,0,0,0.4), 0 0 40px rgba(0,120,215,0.1), inset 0 1px 0 rgba(255,255,255,0.05)"
          : "0 20px 80px rgba(0,0,0,0.15), 0 0 40px rgba(0,120,215,0.05), inset 0 1px 0 rgba(255,255,255,0.8)",
      }}
      initial={{ x: 50, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      {/* Chat header */}
      <div className={`p-6 ${theme === "dark" ? "border-b border-white/10" : "border-b border-gray-200"}`}>
        <h2 className={`font-['Sora'] font-semibold ${theme === "dark" ? "text-white" : "text-gray-900"}`}>
          Conversation
        </h2>
        <p className={`text-sm font-['Plus_Jakarta_Sans'] mt-1 ${theme === "dark" ? "text-white/50" : "text-gray-500"}`}>
          {messages.length} messages
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <AnimatePresence initial={false}>
          {messages.length === 0 ? (
            <motion.div
              className="flex flex-col items-center justify-center h-full text-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-4 ${
                theme === "dark" ? "bg-white/5" : "bg-gray-100"
              }`}>
                <svg
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  className={theme === "dark" ? "text-white/30" : "text-gray-400"}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              </div>
              <p className={`font-['Plus_Jakarta_Sans'] ${theme === "dark" ? "text-white/40" : "text-gray-400"}`}>
                Start a conversation
              </p>
            </motion.div>
          ) : (
            messages.map((message, index) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ delay: index * 0.05 }}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <motion.div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 font-['Plus_Jakarta_Sans'] ${
                    message.role === "user"
                      ? "bg-gradient-to-br from-[#0078D7] to-[#0098D7] text-white"
                      : theme === "dark"
                        ? "bg-white/5 border border-white/10 text-white/90"
                        : "bg-gray-100 text-gray-900"
                  }`}
                  style={{
                    boxShadow:
                      message.role === "user"
                        ? "0 4px 20px rgba(0,120,215,0.3), 0 0 30px rgba(0,217,255,0.1)"
                        : theme === "dark"
                          ? "0 4px 16px rgba(0,0,0,0.1)"
                          : "0 2px 8px rgba(0,0,0,0.05)",
                  }}
                  initial={{ scale: 0.95, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 25 }}
                >
                  <p className="text-sm leading-relaxed">{message.content}</p>
                  <span
                    className={`text-xs mt-2 block ${
                      message.role === "user"
                        ? "text-white/70"
                        : theme === "dark"
                          ? "text-white/40"
                          : "text-gray-500"
                    }`}
                  >
                    {message.timestamp.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </motion.div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
