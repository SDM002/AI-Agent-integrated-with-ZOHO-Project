"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "motion/react";
import { EnhancedBackground } from "@/components/EnhancedBackground";

function SelectPortalContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [portals, setPortals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const userId = searchParams.get("user_id") || "";

  useEffect(() => {
    if (!userId) {
      setError("Missing user context. Please try logging in again.");
      setLoading(false);
      return;
    }
    fetchPortals();
  }, [userId]);

  const fetchPortals = async () => {
    try {
      const normalizedId = userId.toLowerCase();
      const r = await fetch(`/auth/zoho/portals?teams_user_id=${encodeURIComponent(normalizedId)}`);
      if (r.status === 401 || r.status === 404) {
        setError("Session expired or user not found. Please log in again.");
        return;
      }
      const d = await r.json();
      if (d.portals && d.portals.length > 0) {
        setPortals(d.portals);
      } else {
        setError("No portals found for this account.");
      }
    } catch (err) {
      setError("Failed to load portals.");
    } finally {
      setLoading(false);
    }
  };

  const [success, setSuccess] = useState(false);
  const [countdown, setCountdown] = useState(3);

  useEffect(() => {
    if (!success) return;
    let count = 3;
    setCountdown(count);
    const timer = setInterval(() => {
      count -= 1;
      setCountdown(count);
      if (count <= 0) {
        clearInterval(timer);
        window.close();
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [success]);

  const handleSelect = async (portal) => {
    setLoading(true);
    try {
      const normalizedId = userId.toLowerCase();
      const r = await fetch("/auth/zoho/select-portal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          teams_user_id: normalizedId,
          portal_id: portal.id,
          portal_name: portal.name
        })
      });
      if (r.ok) {
        setSuccess(true);
      } else {
        setError("Failed to save portal selection.");
      }
    } catch (err) {
      setError("Connection error.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="relative w-full h-screen overflow-hidden bg-[#0a0e1a] text-white flex items-center justify-center font-['Plus_Jakarta_Sans']">
        <EnhancedBackground theme="dark" />
        <motion.div
          className="relative z-10 w-full max-w-md p-10 rounded-3xl bg-white/5 border border-white/10 backdrop-blur-2xl shadow-2xl text-center"
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
        >
          <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold mb-4 text-white">Connection Success!</h1>
          <p className="text-white/60 mb-8 leading-relaxed">
            Your Zoho account has been successfully linked. <br />
            <strong>You can now close this window</strong> and return to Microsoft Teams to start chatting.
          </p>
          <button
            onClick={() => window.close()}
            className="w-full py-4 rounded-2xl bg-white/10 hover:bg-white/20 transition-all font-semibold"
          >
            {countdown > 0 ? `Closing in ${countdown}...` : "Close Window"}
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#0a0e1a] text-white flex items-center justify-center font-['Plus_Jakarta_Sans']">
      <EnhancedBackground theme="dark" />

      <motion.div
        className="relative z-10 w-full max-w-md p-8 rounded-3xl bg-white/5 border border-white/10 backdrop-blur-2xl shadow-2xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold mb-2">Select Your Portal</h1>
          <p className="text-white/60 text-sm">Choose the Zoho Projects organization you wish to use.</p>
        </div>

        {loading ? (
          <div className="flex flex-col items-center py-12 gap-4">
            <div className="w-8 h-8 border-2 border-[#0078D7] border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-white/40">Loading your portals...</p>
          </div>
        ) : error ? (
          <div className="text-center py-8">
            <p className="text-red-400 mb-6">{error}</p>
            <button
              onClick={() => router.push("/")}
              className="px-6 py-2 rounded-full bg-white/10 hover:bg-white/20 transition-all text-sm"
            >
              Back to Chat
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {portals.map((p) => (
              <motion.button
                key={p.id}
                onClick={() => handleSelect(p)}
                className="w-full text-left px-5 py-4 rounded-2xl bg-white/5 border border-white/5 hover:bg-white/10 hover:border-white/20 transition-all group"
                whileHover={{ x: 5 }}
                whileTap={{ scale: 0.98 }}
              >
                <div className="font-semibold text-white/90 group-hover:text-white">{p.name}</div>
                <div className="text-[10px] text-white/30 uppercase mt-1">ID: {p.id}</div>
              </motion.button>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}

export default function SelectPortal() {
  return (
    <Suspense fallback={<div className="bg-[#0a0e1a] w-full h-screen flex items-center justify-center text-white/40">Loading...</div>}>
      <SelectPortalContent />
    </Suspense>
  );
}