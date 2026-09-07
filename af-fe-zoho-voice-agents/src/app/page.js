"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { SquarePen } from "lucide-react";
import { EnhancedBackground } from "@/components/EnhancedBackground";
import { EnhancedAIOrb } from "@/components/EnhancedAIOrb";
import { Header } from "@/components/Header";
import { InputBar } from "@/components/InputBar";
import { ChatMessages } from "@/components/ChatMessages";
import { FETCH_TIMEOUT_MS, FETCH_RETRY_DELAY_MS } from "@/lib/config";
import { useZohoAuth } from "@/hooks/useZohoAuth";
import { useAudioPlayer } from "@/hooks/useAudioPlayer";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { useWebSocket } from "@/hooks/useWebSocket";

export default function Home() {
  // ── Shared UI state ──────────────────────────────────────────────────────
  const [orbState, setOrbState] = useState("idle");
  const [isCorrecting, setIsCorrecting] = useState(false);
  const [theme, setTheme] = useState("light");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [tempTranscript, setTempTranscript] = useState("");
  const [selectedVoice, setSelectedVoice] = useState("female");

  const voiceRef = useRef("female");
  const pendingUserMsgId = useRef(null);
  const transcriptRef = useRef("");
  const sessionId = useRef(
    typeof window !== "undefined" && window.crypto?.randomUUID
      ? window.crypto.randomUUID()
      : Math.random().toString(36).substring(2, 11)
  );

  // ── Message helpers ──────────────────────────────────────────────────────
  const lastBotRef = useRef({ content: "", time: 0 });

  const addBot = (content) => {
    const now = Date.now();
    if (content === lastBotRef.current.content && now - lastBotRef.current.time < 3000) return;
    lastBotRef.current = { content, time: now };
    const uid = typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `${now}-${Math.random().toString(36).slice(2)}`;
    setMessages(p => [...p, { id: uid, role: "assistant", content, timestamp: new Date() }]);
  };

  const addConnectCard = () => {
    const uid = typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `c-${Date.now()}`;
    setMessages(p => [...p, { id: uid, role: "assistant", content: "__CONNECT_CARD__", timestamp: new Date() }]);
  };

  // ── Auth ─────────────────────────────────────────────────────────────────
  const {
    zohoStatus, zohoStatusRef, teamsUserId, teamsTenantId,
    connectCardShownRef, connectZoho, disconnectZoho,
  } = useZohoAuth({
    onWelcome: addBot,
    onShowConnectCard: addConnectCard,
    onConnected: () => setMessages(p => p.filter(m => m.content !== "__CONNECT_CARD__")),
    onDisconnected: () => {
      setMessages(p => [...p, {
        id: Date.now().toString(), role: "assistant",
        content: "__DISCONNECT_BANNER__", timestamp: new Date(),
      }]);
      connectCardShownRef.current = true;
      setTimeout(() => addConnectCard(), 500);
    },
  });

  // ── Audio ────────────────────────────────────────────────────────────────
  const { playingRef, botAudRef, playAudio: _playAudio, stopBotAud, speakFallback, resetPlaying } = useAudioPlayer({
    setOrbState,
    getMicActive: () => micOnRef.current,
  });

  // Clear STT buffer before playing so mic echo doesn't leak into input
  const playAudio = (b64, mime) => {
    setTempTranscript("");
    setInput("");
    _playAudio(b64, mime);
  };

  // ── Speech recognition ───────────────────────────────────────────────────
  const { micActive, micOnRef, startSpeechRecognition, stopSpeechRecognition, cancelSpeechRecognition, cleanupSpeechRecognition } = useSpeechRecognition({
    playingRef,
    setOrbState,
    onInterim: (text) => { setTempTranscript(text); setInput(text); },
    onFlush: (text) => {
      setTempTranscript(text);
      setInput(text);
      if (text && wsRef.current?.readyState === WebSocket.OPEN) {
        setIsCorrecting(true);
        wsRef.current.send(JSON.stringify({ type: "correct", text }));
      }
    },
  });

  // ── WebSocket ────────────────────────────────────────────────────────────
  const { wsRef, connectWebSocket, sendMessage, disconnect: disconnectWs } = useWebSocket({
    voiceRef,
    sessionId,
    teamsUserId,
    teamsTenantId,
    startSpeechRecognition,
    onReply: (m) => {
      playingRef.current = true;
      const userText = transcriptRef.current.trim();
      if (userText && !pendingUserMsgId.current) {
        const uid = typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : `${Date.now() - 1}-${Math.random().toString(36).slice(2)}`;
        setMessages(p => [...p, { id: uid, role: "user", content: userText, timestamp: new Date() }]);
      }
      transcriptRef.current = "";
      pendingUserMsgId.current = null;
      setTempTranscript("");
      setInput("");
      addBot(m.text);
      const audioData = m.audio_base64 || m.audio_b64;
      if (audioData) {
        playAudio(audioData, m.audio_mime || "audio/wav");
      } else {
        speakFallback(m.text, () => setTimeout(() => setOrbState(micOnRef.current ? "listening" : "idle"), 1500));
      }
    },
    onStatus: (value) => {
      if (value === "listening") {
        if (!playingRef.current) setOrbState(micOnRef.current ? "listening" : "idle");
        if (!botAudRef.current) resetPlaying(600);
      }
      if (value === "processing") setOrbState("processing");
      if (value === "speaking") { setOrbState("speaking"); playingRef.current = true; }
      if (value === "interrupted" || value === "error") setOrbState("idle");
    },
    onConnectRequired: (m) => {
      if (!connectCardShownRef.current) {
        connectCardShownRef.current = true;
        addBot(m.text || "Please connect your Zoho account.");
        setTimeout(() => addConnectCard(), 400);
      }
      setOrbState("idle");
    },
    onTranscriptCorrected: (m) => {
      setIsCorrecting(false);
      const id = pendingUserMsgId.current;
      if (id) {
        setMessages(p => p.map(msg => msg.id === id ? { ...msg, content: m.text } : msg));
      } else {
        setTempTranscript(m.text);
        setInput(m.text);
      }
    },
    onClose: () => { cleanupSpeechRecognition(); setOrbState("idle"); },
  });

  // Connect WS once user ID is known
  useEffect(() => {
    if (!teamsUserId) return;
    setTimeout(() => connectWebSocket(false), 1000);
  }, [teamsUserId]);

  // ── Text chat ─────────────────────────────────────────────────────────────
  const handleSendMessage = async (content) => {
    if (micOnRef.current) cancelSpeechRecognition();
    transcriptRef.current = "";
    const userMsgId = Date.now().toString();
    pendingUserMsgId.current = userMsgId;
    setMessages(p => [...p, { id: userMsgId, role: "user", content, timestamp: new Date() }]);
    setOrbState("processing");
    setInput("");
    setTempTranscript("");

    if (!teamsUserId) {
      addBot("System initializing. Please wait a second...");
      setOrbState("idle");
      return;
    }

    if (sendMessage({ type: "chat", text: content, user_id: teamsUserId })) return;

    const doFetch = async () => {
      const fd = new FormData();
      fd.append("message", content);
      fd.append("user_id", teamsUserId);
      fd.append("include_audio", "true");
      fd.append("voice", voiceRef.current);
      const r = await fetch("/api/chat", {
        method: "POST",
        body: fd,
        signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
      });
      return r.json();
    };

    let d;
    try {
      d = await doFetch();
    } catch {
      try {
        await new Promise(res => setTimeout(res, FETCH_RETRY_DELAY_MS));
        d = await doFetch();
      } catch {
        addBot("Connection error. Please try again.");
        setOrbState("idle");
        return;
      }
    }

    try {
      if (d.action === "connect_required") {
        addBot(d.reply || "Please connect your Zoho account.");
        setTimeout(() => addConnectCard(), 400);
        return;
      }
      addBot(d.reply || "Something went wrong.");
      const audioData = d.audio_base64 || d.audio_b64;
      if (audioData) {
        playAudio(audioData, d.audio_mime || "audio/wav");
      } else if (d.reply) {
        speakFallback(d.reply);
      }
    } catch {
      addBot("Connection error. Please try again.");
      setOrbState("idle");
    }
  };

  // ── Interrupt ─────────────────────────────────────────────────────────────
  const interruptBot = () => {
    stopBotAud();
    setInput("");
    setTempTranscript("");
    sendMessage({ type: "interrupt" });
    setOrbState("idle");
  };

  // ── Mic click ─────────────────────────────────────────────────────────────
  const handleMicClick = () => {
    if (orbState === "processing") return;
    if (orbState === "speaking") { interruptBot(); return; }
    if (micOnRef.current) stopSpeechRecognition();
    else startSpeechRecognition();
  };

  // ── New Chat ──────────────────────────────────────────────────────────────
  const handleNewChat = () => {
    cleanupSpeechRecognition();
    stopBotAud();

    const isConnected = zohoStatusRef.current?.connected;
    if (isConnected && teamsUserId) {
      fetch(`/auth/zoho/new-chat?chat_id=${encodeURIComponent(sessionId.current)}&tenant_id=${encodeURIComponent(teamsTenantId || "default")}`, { method: "POST" })
        .catch(err => console.error("Failed to clear backend history:", err));
    }

    disconnectWs();
    sessionId.current = window.crypto?.randomUUID ? window.crypto.randomUUID() : Math.random().toString(36).substring(2, 11);
    connectCardShownRef.current = false;

    const name = zohoStatusRef.current?.email?.split("@")[0];
    const welcomeMsg = {
      id: Date.now().toString(),
      role: "assistant",
      timestamp: new Date(),
      content: isConnected
        ? (
          `Hey${name ? " " + name : ""}! 👋 Fresh start — I'm ready to help.\n\n` +
          `Here's what I can do:\n` +
          `• Create or update tasks and projects\n` +
          `• Log time on a task\n` +
          `• Report or list bugs\n` +
          `• Check milestones and team members\n` +
          `• Show your projects or tasks\n\n` +
          `Just say it or type it!\n\n` +
          `💡 Tip: Press Esc anytime to cancel what you're typing or stop listening.`
        )
        : "👋 Welcome to Zoho Voice Logger!\n\nConnect your Zoho account to get started.",
    };

    setMessages([welcomeMsg]);
    if (!isConnected) {
      connectCardShownRef.current = true;
      setTimeout(() => addConnectCard(), 400);
    }
    setInput("");
    setTempTranscript("");
    setOrbState("idle");
    setTimeout(() => connectWebSocket(false), 500);
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className={`relative w-full h-screen overflow-hidden font-sans ${theme === "dark" ? "dark" : ""}`}>
      <div className={`relative w-full h-full ${theme === "dark" ? "bg-[#0a0e1a]" : "bg-white"} transition-colors duration-500`}>

        <EnhancedBackground theme={theme} />

        <Header
          theme={theme}
          onThemeToggle={() => setTheme(theme === "light" ? "dark" : "light")}
          zohoStatus={zohoStatus}
          onConnectZoho={connectZoho}
          onDisconnectZoho={disconnectZoho}
          selectedVoice={selectedVoice}
          onVoiceChange={(v) => {
            setSelectedVoice(v);
            voiceRef.current = v;
            sendMessage({ type: "config", voice: v });
          }}
        />

        <div className="relative w-full h-full pt-20 pb-32">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center gap-6">
              <EnhancedAIOrb state={orbState} theme={theme} />
              <div className="flex flex-col items-center gap-1">
                <p className={`text-base font-['Plus_Jakarta_Sans'] ${theme === "dark" ? "text-gray-400" : "text-gray-500"}`}>
                  How can I help with your Zoho Projects?
                </p>
                <p className={`text-xs font-['Plus_Jakarta_Sans'] animate-pulse ${theme === "dark" ? "text-gray-600" : "text-gray-400"}`}>
                  Connecting…
                </p>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col">
              <div className="relative flex justify-end px-4 py-2 flex-shrink-0 z-10">
                <motion.button
                  onClick={handleNewChat}
                  title="New Chat"
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-['Plus_Jakarta_Sans'] font-medium transition-colors ${theme === "dark"
                    ? "bg-[#2f2f2f] border border-[#4a4a4a] text-gray-300 hover:bg-[#3a3a3a]"
                    : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
                    }`}
                  style={{ boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }}
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                >
                  <SquarePen className="w-3.5 h-3.5" />
                  New Chat
                </motion.button>
              </div>
              <div className="flex-1 overflow-hidden">
                <ChatMessages
                  messages={messages}
                  theme={theme}
                  orbState={orbState}
                  onConnectZoho={connectZoho}
                  tempTranscript={tempTranscript}
                />
              </div>
            </div>
          )}
        </div>

        {/* Voice status pill */}
        <AnimatePresence>
          {(orbState === "processing" || orbState === "speaking" || (orbState === "listening" && micActive)) && (
            <div className="fixed bottom-28 left-1/2 -translate-x-1/2 z-50">
              <motion.div
                key={orbState}
                initial={{ opacity: 0, y: 8, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.9 }}
                transition={{ duration: 0.2 }}
                className="flex items-center gap-2 px-4 py-2 rounded-full text-white text-xs font-['Plus_Jakarta_Sans'] font-semibold shadow-lg"
                style={{
                  background:
                    orbState === "listening" ? "rgba(239,68,68,0.92)" :
                    orbState === "processing" ? "rgba(34,197,94,0.92)" :
                    orbState === "speaking"   ? "rgba(99,102,241,0.92)" :
                    "rgba(100,100,100,0.9)",
                  boxShadow:
                    orbState === "listening" ? "0 0 16px rgba(239,68,68,0.5)" :
                    orbState === "processing" ? "0 0 16px rgba(34,197,94,0.5)" :
                    orbState === "speaking"   ? "0 0 16px rgba(99,102,241,0.5)" :
                    "none",
                }}
              >
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                    style={{ background: orbState === "listening" ? "#fca5a5" : orbState === "processing" ? "#86efac" : "#a5b4fc" }} />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-white" />
                </span>
                {orbState === "listening"  && "Listening..."}
                {orbState === "processing" && "Processing..."}
                {orbState === "speaking"   && "Speaking..."}
              </motion.div>
            </div>
          )}
        </AnimatePresence>

        <InputBar
          onSend={handleSendMessage}
          theme={theme}
          onMicClick={handleMicClick}
          input={input}
          setInput={setInput}
          orbState={orbState}
          isCorrecting={isCorrecting}
          onCancel={() => {
            if (orbState === "speaking" || orbState === "processing") interruptBot();
            else cancelSpeechRecognition();
          }}
        />

      </div>
    </div>
  );
}
