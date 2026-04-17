# Smart Vision Demo (YOLO → Server → Web → Morse)

## What this is
- **Python worker** (`yolo_worker.py`) reads `WEBCAM_URL`, runs **YOLOv8n** every ~1s (imgsz=640, conf=0.3), selects **one most important object** (priority: person > car > others) and prints JSON lines.
- **Node server** (`server.js`) reads JSON lines from the worker, throttles to **one emit every 2 seconds**, and broadcasts to all Socket.IO clients as a structured payload:

```json
{
  "text": "Человек справа",
  "direction": "right",
  "danger": true,
  "morse": "... --- ...",
  "ts": "2026-04-17T09:00:00.000Z"
}
```

- **React frontend** (`web/`) connects via Socket.IO, shows a big debug/demo UI, converts incoming text→Morse and plays immediately:
  - vibration if supported/unlocked
  - otherwise audio beep + full-screen flash fallback

## Run (local demo)

### 1) Install Node deps
```bash
npm install
npm run web:install
```

### 2) Build the web UI (so the Node server can serve it)
```bash
npm run web:build
```

### 3) Run the server
```bash
# optional: override camera url
export WEBCAM_URL="http://100.0.0.100:4747/video"

# optional: start in demo mode even if camera fails
export DEMO_MODE=1

npm run server
```

Open on laptop: `http://127.0.0.1:5000/`

Open on phone (Android/iPhone): `http://<YOUR_PC_IP>:5000/`

Then press **Start system** once (required to unlock vibration/audio in mobile browsers).

## Demo-proof mode
- Toggle **Demo mode** ON in the UI to force the server to send fake messages every 2 seconds:
  - `Человек слева`
  - `ОПАСНО Машина прямо`
  - `Человек справа`

This makes the pitch work even if YOLO/camera/network fails.

