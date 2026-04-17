import React, { useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";
import { morseToPattern, textToMorse, TIMINGS } from "../morse.js";

function fmtTime(ts) {
  try {
    return new Date(ts).toLocaleTimeString();
  } catch {
    return "";
  }
}

function dirArrow(direction) {
  if (direction === "left") return "←";
  if (direction === "right") return "→";
  return "↑";
}

function useAudio() {
  const ctxRef = useRef(null);

  const ensureCtx = () => {
    if (!ctxRef.current) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return null;
      ctxRef.current = new Ctx();
    }
    return ctxRef.current;
  };

  const beep = async (ms = 80, freq = 880) => {
    const ctx = ensureCtx();
    if (!ctx) return false;
    if (ctx.state === "suspended") await ctx.resume();

    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = "sine";
    o.frequency.value = freq;
    g.gain.value = 0.05;
    o.connect(g);
    g.connect(ctx.destination);
    o.start();
    o.stop(ctx.currentTime + ms / 1000);
    return true;
  };

  return { ensureCtx, beep };
}

function computeFlashScheduleFromMorse(morse) {
  // return array of {t, on} events in ms
  const s = String(morse || "").trim();
  if (!s) return [];
  const { dot, dash, gap, letterGap, wordGap } = TIMINGS;

  const events = [];
  const tokens = s.split("");
  let t = 0;
  for (let i = 0; i < tokens.length; i++) {
    const ch = tokens[i];
    if (ch === "." || ch === "-") {
      const dur = ch === "." ? dot : dash;
      events.push({ t, on: true });
      events.push({ t: t + dur, on: false });
      t += dur;
      const next = tokens[i + 1];
      if (next === "." || next === "-") t += gap;
    } else if (ch === "/") {
      t += wordGap;
    } else if (ch === " ") {
      const prev = tokens[i - 1];
      const next = tokens[i + 1];
      if ((prev === "." || prev === "-") && next && next !== "/" && next !== " ") t += letterGap;
    }
  }
  return events;
}

export default function App() {
  const [connected, setConnected] = useState(false);
  const [serverDemoMode, setServerDemoMode] = useState(false);
  const [unlocked, setUnlocked] = useState(false);
  const [strongVisual, setStrongVisual] = useState(true);

  const [last, setLast] = useState({
    text: "Waiting…",
    morse: "",
    direction: "center",
    danger: false,
    ts: ""
  });

  const [logLines, setLogLines] = useState([]);
  const addLog = (line) =>
    setLogLines((xs) => [String(line), ...xs].slice(0, 25));

  const { ensureCtx, beep } = useAudio();

  const socket = useMemo(() => {
    // IMPORTANT: use current origin by default; phone must open correct IP/host.
    return io({
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionDelay: 300,
      reconnectionDelayMax: 2000
    });
  }, []);

  const flashRef = useRef({ timers: [] });
  const [flashOn, setFlashOn] = useState(false);

  const clearFlashTimers = () => {
    flashRef.current.timers.forEach((id) => clearTimeout(id));
    flashRef.current.timers = [];
    setFlashOn(false);
  };

  const playFallback = async (morse) => {
    // sound + flash pulses
    const events = computeFlashScheduleFromMorse(morse);
    clearFlashTimers();

    // flash schedule
    for (const ev of events) {
      const id = setTimeout(() => setFlashOn(ev.on), ev.t);
      flashRef.current.timers.push(id);
    }
    const endId = setTimeout(() => setFlashOn(false), (events.at(-1)?.t || 0) + 50);
    flashRef.current.timers.push(endId);

    // simple beep (not symbol-accurate, but immediate and noticeable)
    // we beep at the start of each symbol
    for (const ev of events) {
      if (ev.on) setTimeout(() => beep(strongVisual ? 80 : 60, 880), ev.t);
    }
  };

  const playMorse = async (text) => {
    const morse = textToMorse(text);
    const pattern = morseToPattern(morse);
    const canVibrate = "vibrate" in navigator && typeof navigator.vibrate === "function";

    if (unlocked && canVibrate && pattern.length) {
      navigator.vibrate(pattern);
      // keep flash too for demo clarity (optional)
      await playFallback(morse);
      return { morse, used: "vibration" };
    }

    // fallback: audio + flash
    await playFallback(morse);
    return { morse, used: "fallback" };
  };

  useEffect(() => {
    const onConnect = () => {
      setConnected(true);
      addLog("[FRONTEND] connected");
    };
    const onDisconnect = (reason) => {
      setConnected(false);
      addLog(`[FRONTEND] disconnected: ${reason}`);
    };
    const onStatus = (data) => {
      if (data && typeof data.demoMode === "boolean") setServerDemoMode(data.demoMode);
    };

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    socket.on("status", onStatus);
    socket.on("message", async (data) => {
      console.log("[FRONTEND] RECEIVED:", data);
      addLog(`[FRONTEND] RECEIVED: ${JSON.stringify(data)}`);

      const text = String((data && data.text) || "");
      const direction = (data && data.direction) || "center";
      const danger = Boolean(data && data.danger);

      const { morse } = await playMorse(text);
      setLast({
        text,
        direction,
        danger,
        morse,
        ts: (data && data.ts) || new Date().toISOString()
      });
    });

    socket.io.on("reconnect_attempt", () => addLog("[FRONTEND] reconnecting…"));
    socket.io.on("reconnect", () => addLog("[FRONTEND] reconnected"));

    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      socket.off("status", onStatus);
      socket.off("message");
      clearFlashTimers();
      socket.close();
    };
  }, [socket, unlocked, strongVisual]);

  const startSystem = async () => {
    setUnlocked(true);
    // Unlock audio
    ensureCtx();
    // Give immediate haptic/audio cue
    if ("vibrate" in navigator) navigator.vibrate([30, 40, 30]);
    await beep(60, 880);
    addLog("[FRONTEND] system unlocked (vibration/audio)");
  };

  const testSOS = async () => {
    socket.emit("test_sos");
  };

  const toggleDemoMode = (enabled) => {
    socket.emit("set_demo_mode", { enabled });
    setServerDemoMode(enabled);
  };

  const bg = last.danger ? "rgba(239,68,68,0.22)" : "rgba(255,255,255,0.04)";
  const dangerPulse = last.danger ? "dangerPulse 900ms ease-in-out infinite" : "none";
  const flashOverlayOpacity = flashOn ? (strongVisual ? 0.85 : 0.45) : 0;

  return (
    <div style={styles.page}>
      <style>{`
        @keyframes dangerPulse {
          0% { background-color: rgba(239,68,68,0.18); }
          50% { background-color: rgba(239,68,68,0.36); }
          100% { background-color: rgba(239,68,68,0.18); }
        }
      `}</style>

      <div
        style={{
          ...styles.flashOverlay,
          opacity: flashOverlayOpacity,
          background: last.danger ? "#ff0000" : "#ffffff"
        }}
      />

      <div style={styles.header}>
        <div style={styles.title}>Smart Vision • Real-time demo</div>
        <div style={{ ...styles.status, background: connected ? "rgba(34,197,94,0.20)" : "rgba(239,68,68,0.18)" }}>
          {connected ? "connected" : "disconnected"}
        </div>
      </div>

      <div style={styles.mainGrid}>
        <div style={styles.card}>
          <div style={{ ...styles.bigBox, background: bg, animation: dangerPulse }}>
            <div style={styles.arrow}>{dirArrow(last.direction)}</div>
            <div style={styles.bigText}>{last.text || "—"}</div>
            <div style={styles.morse}>{last.morse || "—"}</div>
          </div>

          <div style={styles.row}>
            <button onClick={startSystem} style={styles.btnPrimary}>
              Start system
            </button>
            <button onClick={testSOS} style={styles.btn}>
              Test vibration (SOS)
            </button>
            <label style={styles.switch}>
              <input
                type="checkbox"
                checked={serverDemoMode}
                onChange={(e) => toggleDemoMode(e.target.checked)}
              />
              <span>Demo mode</span>
            </label>
          </div>

          <div style={styles.row}>
            <label style={styles.switch}>
              <input
                type="checkbox"
                checked={strongVisual}
                onChange={(e) => setStrongVisual(e.target.checked)}
              />
              <span>Stronger visual pulses</span>
            </label>
            <div style={styles.hint}>
              Unlock required once for vibration/audio on mobile.
            </div>
          </div>
        </div>

        <div style={styles.card}>
          <div style={styles.panelTitle}>Debug panel</div>
          <div style={styles.kv}>
            <div style={styles.k}>Connection</div>
            <div style={styles.v}>{connected ? "connected" : "disconnected"}</div>
            <div style={styles.k}>Demo mode</div>
            <div style={styles.v}>{serverDemoMode ? "ON" : "OFF"}</div>
            <div style={styles.k}>Last text</div>
            <div style={styles.v}>{last.text || "—"}</div>
            <div style={styles.k}>Last morse</div>
            <div style={styles.v}>{last.morse || "—"}</div>
            <div style={styles.k}>Last update</div>
            <div style={styles.v}>{last.ts ? fmtTime(last.ts) : "—"}</div>
            <div style={styles.k}>Unlocked</div>
            <div style={styles.v}>{unlocked ? "yes" : "no"}</div>
            <div style={styles.k}>Vibrate API</div>
            <div style={styles.v}>{"vibrate" in navigator ? "supported" : "not supported"}</div>
          </div>

          <div style={styles.logs}>
            {logLines.map((l, i) => (
              <div key={i} style={styles.logLine}>
                {l}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "radial-gradient(900px 600px at 20% 0%, #131c31, #0b0f17)",
    color: "#eef2ff",
    padding: 16,
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
    position: "relative",
    overflow: "hidden"
  },
  flashOverlay: {
    position: "fixed",
    inset: 0,
    pointerEvents: "none",
    transition: "opacity 60ms linear",
    zIndex: 1
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
    marginBottom: 12,
    position: "relative",
    zIndex: 2
  },
  title: { fontSize: 14, color: "#a8b3cf", letterSpacing: 0.3 },
  status: {
    fontSize: 13,
    padding: "6px 10px",
    borderRadius: 999,
    border: "1px solid rgba(255,255,255,0.10)",
    color: "#e5e7eb"
  },
  mainGrid: {
    display: "grid",
    gridTemplateColumns: "1fr",
    gap: 12,
    maxWidth: 1100,
    margin: "0 auto",
    position: "relative",
    zIndex: 2
  },
  card: {
    background: "rgba(18, 26, 42, 0.78)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 16,
    padding: 14,
    backdropFilter: "blur(10px)"
  },
  bigBox: {
    borderRadius: 16,
    border: "1px solid rgba(255,255,255,0.10)",
    padding: 14,
    display: "grid",
    gap: 10
  },
  arrow: {
    fontSize: 86,
    lineHeight: 1,
    fontWeight: 900,
    textAlign: "center"
  },
  bigText: {
    fontSize: "clamp(26px, 5.4vw, 52px)",
    fontWeight: 900,
    lineHeight: 1.05,
    textAlign: "center"
  },
  morse: {
    fontFamily:
      'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    fontSize: 16,
    color: "#a8b3cf",
    textAlign: "center",
    wordBreak: "break-word"
  },
  row: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 12
  },
  btnPrimary: {
    border: 0,
    borderRadius: 14,
    padding: "12px 14px",
    background: "linear-gradient(135deg, rgba(124,58,237,0.95), rgba(99,102,241,0.95))",
    color: "white",
    fontWeight: 900,
    fontSize: 15
  },
  btn: {
    borderRadius: 14,
    padding: "12px 14px",
    background: "rgba(255,255,255,0.06)",
    color: "#eef2ff",
    border: "1px solid rgba(255,255,255,0.12)",
    fontWeight: 800,
    fontSize: 14
  },
  switch: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    color: "#e5e7eb",
    fontSize: 14
  },
  hint: { color: "#a8b3cf", fontSize: 13 },
  panelTitle: { fontWeight: 900, fontSize: 16, marginBottom: 10 },
  kv: {
    display: "grid",
    gridTemplateColumns: "160px 1fr",
    gap: "6px 10px",
    alignItems: "start"
  },
  k: { color: "#a8b3cf", fontSize: 13 },
  v: { color: "#eef2ff", fontSize: 13, wordBreak: "break-word" },
  logs: {
    marginTop: 12,
    paddingTop: 10,
    borderTop: "1px solid rgba(255,255,255,0.08)",
    maxHeight: 260,
    overflow: "auto"
  },
  logLine: {
    fontFamily:
      'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    fontSize: 12,
    color: "#cbd5e1",
    padding: "2px 0"
  }
};

