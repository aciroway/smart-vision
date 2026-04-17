import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import cors from "cors";
import express from "express";
import { Server } from "socket.io";

import { textToMorse } from "./morse.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// =========================
// Config
// =========================
const PORT = Number(process.env.PORT || 5000);
const YOLO_WORKER = process.env.YOLO_WORKER || "yolo_worker.py";
const DEMO_MODE_DEFAULT = process.env.DEMO_MODE === "1";
const PYTHON_DEFAULT = process.env.PYTHON || path.join(__dirname, "venv", "bin", "python");

// 2s throttled emit requirement
const EMIT_EVERY_MS = 2000;

// =========================
// Express + Socket.IO
// =========================
const app = express();
app.use(cors({ origin: true, credentials: true }));
app.use(express.json({ limit: "256kb" }));

// Serve built React app if present
app.use(express.static(path.join(__dirname, "web", "dist")));
app.get("/", (req, res) => res.sendFile(path.join(__dirname, "web", "dist", "index.html")));

const httpServer = app.listen(PORT, "0.0.0.0", () => {
  console.log(`[SERVER] Listening on 0.0.0.0:${PORT}`);
});

const io = new Server(httpServer, {
  cors: { origin: "*", methods: ["GET", "POST"] }
});

let demoMode = DEMO_MODE_DEFAULT;
let lastEmitAt = 0;
let lastSentKey = "";

function nowMs() {
  return Date.now();
}

function buildMessage({ text, direction, danger }) {
  const morse = textToMorse(text);
  return {
    text,
    direction, // left | center | right
    danger: Boolean(danger),
    morse,
    ts: new Date().toISOString()
  };
}

function emitToAll(message) {
  console.log("[SERVER] Emitting:", message);
  io.emit("message", message);
}

function shouldEmit(message) {
  const t = nowMs();
  if (t - lastEmitAt < EMIT_EVERY_MS) return false;
  const key = `${message.text}|${message.direction}|${message.danger}`;
  if (key === lastSentKey) return false;
  lastEmitAt = t;
  lastSentKey = key;
  return true;
}

io.on("connection", (socket) => {
  console.log("[SOCKET] Client connected:", socket.id);
  socket.emit("status", { connected: true, demoMode });

  socket.on("disconnect", (reason) => {
    console.log("[SOCKET] Client disconnected:", socket.id, reason);
  });

  socket.on("set_demo_mode", (payload) => {
    const enabled = Boolean(payload && payload.enabled);
    demoMode = enabled;
    console.log("[SERVER] Demo mode:", demoMode ? "ON" : "OFF");
    io.emit("status", { demoMode });
  });

  socket.on("manual_text", (payload) => {
    const text = String((payload && payload.text) || "").trim();
    if (!text) return;
    const msg = buildMessage({
      text,
      direction: "center",
      danger: text.toUpperCase().includes("ОПАСНО")
    });
    // manual should play immediately even if throttled (demo UX)
    lastEmitAt = 0;
    lastSentKey = "";
    emitToAll(msg);
  });

  socket.on("test_sos", () => {
    const msg = buildMessage({ text: "SOS", direction: "center", danger: false });
    lastEmitAt = 0;
    lastSentKey = "";
    emitToAll(msg);
  });
});

// =========================
// Demo mode generator
// =========================
const DEMO_MESSAGES = [
  { text: "Человек слева", direction: "left", danger: false },
  { text: "ОПАСНО Машина прямо", direction: "center", danger: true },
  { text: "Человек справа", direction: "right", danger: false }
];
let demoIdx = 0;
setInterval(() => {
  if (!demoMode) return;
  const m = DEMO_MESSAGES[demoIdx++ % DEMO_MESSAGES.length];
  const msg = buildMessage(m);
  if (shouldEmit(msg)) emitToAll(msg);
}, 250);

// =========================
// YOLO worker (Python) -> JSON lines
// =========================
let worker = null;

function startWorker() {
  const cmd = PYTHON_DEFAULT;
  const workerPath = path.isAbsolute(YOLO_WORKER) ? YOLO_WORKER : path.join(__dirname, YOLO_WORKER);

  console.log(`[WORKER] Starting: ${cmd} ${workerPath}`);
  worker = spawn(cmd, [workerPath], {
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env }
  });

  worker.stdout.setEncoding("utf8");
  worker.stderr.setEncoding("utf8");

  let buf = "";
  worker.stdout.on("data", (chunk) => {
    buf += chunk;
    while (true) {
      const idx = buf.indexOf("\n");
      if (idx === -1) break;
      const line = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 1);
      if (!line) continue;

      let payload;
      try {
        payload = JSON.parse(line);
      } catch (e) {
        console.warn("[WORKER] Non-JSON:", line);
        continue;
      }

      if (demoMode) continue; // demo overrides YOLO
      if (!payload || !payload.text) {
        console.warn("[WORKER] Empty payload:", payload);
        continue;
      }

      const msg = buildMessage({
        text: payload.text,
        direction: payload.direction || "center",
        danger: Boolean(payload.danger)
      });
      if (shouldEmit(msg)) emitToAll(msg);
    }
  });

  worker.stderr.on("data", (chunk) => {
    // keep it loud for demo debugging
    for (const line of String(chunk).split("\n")) {
      const s = line.trim();
      if (s) console.log("[WORKER]", s);
    }
  });

  worker.on("exit", (code, signal) => {
    console.warn("[WORKER] Exited:", { code, signal });
    worker = null;
    // auto-restart unless in demo mode (still can restart; harmless)
    setTimeout(() => startWorker(), 1500);
  });
}

startWorker();

