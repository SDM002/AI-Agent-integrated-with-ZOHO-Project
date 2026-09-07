"use client";

import { useState, useRef, useEffect } from "react";

export function useZohoAuth({ onWelcome, onShowConnectCard, onConnected, onDisconnected }) {
  const [zohoStatus, setZohoStatus] = useState({ connected: false });
  const [teamsUserId, setTeamsUserId] = useState(() => {
    if (typeof window === "undefined") return "";
    let gid = localStorage.getItem("zoho_agent_guest_id");
    if (!gid) {
      gid = `guest_${Math.random().toString(36).substring(2, 10)}`;
      localStorage.setItem("zoho_agent_guest_id", gid);
    }
    return gid;
  });
  const [teamsTenantId, setTeamsTenantId] = useState("default");

  const zohoStatusRef = useRef({ connected: false });
  const teamsInitializedRef = useRef(false);
  const connectCardShownRef = useRef(false);

  // ── Teams SDK initialisation ─────────────────────────────────────────────
  useEffect(() => {
    const fallbackToGuest = () => {
      let guestId = localStorage.getItem("zoho_agent_guest_id");
      if (!guestId) {
        guestId = `guest_${Math.random().toString(36).substring(2, 10)}`;
        localStorage.setItem("zoho_agent_guest_id", guestId);
      }
      teamsInitializedRef.current = true;
      setTeamsUserId(guestId);
    };

    const s = document.createElement("script");
    s.src = "https://res.cdn.office.net/teams-js/2.0.0/js/MicrosoftTeams.min.js";
    s.onerror = () => {
      console.log("Teams SDK failed to load — using guest ID");
      fallbackToGuest();
    };
    s.onload = async () => {
      try {
        if (!window.microsoftTeams) { fallbackToGuest(); return; }
        await window.microsoftTeams.app.initialize();
        const ctx = await window.microsoftTeams.app.getContext();
        const uid = (
          ctx.user?.loginHint ||
          ctx.user?.userPrincipalName ||
          ctx.user?.id ||
          ""
        ).toLowerCase();
        const tid = ctx.user?.tenant?.id || "default";
        if (uid && uid !== "local_user") {
          teamsInitializedRef.current = true;
          setTeamsUserId(uid);
          setTeamsTenantId(tid);
          console.log("Teams SDK initialized:", uid);
        } else {
          console.log("Teams SDK: no valid user — using guest ID");
          fallbackToGuest();
        }
      } catch {
        console.log("Not running inside Teams — using guest ID");
        fallbackToGuest();
      }
    };
    document.head.appendChild(s);
  }, []);

  // ── Zoho status polling ──────────────────────────────────────────────────
  const buildWelcome = (email, greeting = "Zoho is connected. How can I help you today?") => {
    const firstName = email?.includes("@") ? email.split("@")[0] : "";
    return (
      `Hey${firstName ? " " + firstName : ""}! 👋 ${greeting}\n\n` +
      `Here's what I can do:\n` +
      `• Create or update tasks and projects\n` +
      `• Log time on a task\n` +
      `• Report or list bugs\n` +
      `• Check milestones and team members\n` +
      `• Show your projects or tasks\n\n` +
      `Just say it or type it!\n\n` +
      `💡 Tip: Press Esc anytime to cancel what you're typing or stop listening.`
    );
  };

  const checkZoho = async (uid, justConnected = false, silent = false) => {
    try {
      const r = await fetch(`/auth/zoho/status?teams_user_id=${encodeURIComponent(uid)}`);
      const text = await r.text();
      if (!text || !text.trim()) return;
      let d;
      try { d = JSON.parse(text); } catch { return; }
      const wasConnected = zohoStatusRef.current?.connected;
      setZohoStatus(d);
      zohoStatusRef.current = d;

      if (silent) {
        if (!wasConnected && d.connected) {
          connectCardShownRef.current = false;
          onConnected?.();
          onWelcome?.(buildWelcome(d.email));
        }
        return;
      }

      if (d.connected) {
        connectCardShownRef.current = false;
        onConnected?.();
        if (justConnected || !wasConnected) {
          setTimeout(() => onWelcome?.(buildWelcome(d.email)), 3000);
        }
      } else {
        if (!teamsInitializedRef.current) return;
        if (connectCardShownRef.current) return;
        connectCardShownRef.current = true;
        setTimeout(() => {
          if (zohoStatusRef.current?.connected) return;
          onWelcome?.("👋 Welcome to Zoho Voice Logger!\n\nConnect your Zoho account to get started.");
          setTimeout(() => {
            if (!zohoStatusRef.current?.connected) onShowConnectCard?.();
          }, 400);
        }, 3000);
      }
    } catch (err) {
      console.error("Status check failed:", err);
      if (!silent) {
        setZohoStatus({ connected: false });
        zohoStatusRef.current = { connected: false };
      }
    }
  };

  useEffect(() => {
    if (!teamsUserId) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("connected") === "true") {
      window.history.replaceState({}, "", "/");
      checkZoho(teamsUserId, true);
    } else {
      checkZoho(teamsUserId, false);
    }
    const pollId = setInterval(() => {
      if (!zohoStatusRef.current?.connected) checkZoho(teamsUserId, false, true);
    }, 3000);
    return () => clearInterval(pollId);
  }, [teamsUserId]);

  // ── Auth actions ─────────────────────────────────────────────────────────
  const connectZoho = () => {
    window.open(
      `/auth/zoho/login?teams_user_id=${encodeURIComponent(teamsUserId)}&teams_tenant_id=${encodeURIComponent(teamsTenantId)}`,
      "_blank"
    );
    setTimeout(() => checkZoho(teamsUserId), 5000);
  };

  const disconnectZoho = async () => {
    setZohoStatus({ connected: false });
    zohoStatusRef.current = { connected: false };
    connectCardShownRef.current = false;
    try {
      const uid = teamsUserId || "local_user";
      const r = await fetch(
        `/auth/zoho/disconnect?teams_user_id=${encodeURIComponent(uid.toLowerCase())}`,
        { method: "DELETE" }
      );
      if (r.ok) onDisconnected?.();
      else console.error("Backend disconnect failed");
    } catch (err) {
      console.error("Disconnect fetch error:", err);
    }
  };

  return {
    zohoStatus,
    zohoStatusRef,
    teamsUserId,
    teamsTenantId,
    connectCardShownRef,
    connectZoho,
    disconnectZoho,
  };
}
