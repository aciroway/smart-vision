import time
from typing import Dict

import eventlet
eventlet.monkey_patch()

import cv2
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from ultralytics import YOLO


# =========================
# Config
# =========================
WEBCAM_URL = "http://10.0.0.100:8080/video"

MODEL_PATH = "yolov8n.pt"
CONF_LEVEL = 0.5
IMG_SIZE = 320

INFER_EVERY_SECONDS = 1.0
DANGER_BBOX_WIDTH_PX = 350


# =========================
# Morse (RU + EN + digits + basic punctuation)
# =========================
MORSE: Dict[str, str] = {
    # English
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    # Digits
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    # Russian (common ITU / RU standard)
    "А": ".-",
    "Б": "-...",
    "В": ".--",
    "Г": "--.",
    "Д": "-..",
    "Е": ".",
    "Ж": "...-",
    "З": "--..",
    "И": "..",
    "Й": ".---",
    "К": "-.-",
    "Л": ".-..",
    "М": "--",
    "Н": "-.",
    "О": "---",
    "П": ".--.",
    "Р": ".-.",
    "С": "...",
    "Т": "-",
    "У": "..-",
    "Ф": "..-.",
    "Х": "....",
    "Ц": "-.-.",
    "Ч": "---.",
    "Ш": "----",
    "Щ": "--.-",
    "Ъ": "--.--",
    "Ы": "-.--",
    "Ь": "-..-",
    "Э": "..-..",
    "Ю": "..--",
    "Я": ".-.-",
    # Punctuation (basic)
    ".": ".-.-.-",
    ",": "--..--",
    "?": "..--..",
    "!": "-.-.--",
    ":": "---...",
    ";": "-.-.-.",
    "(": "-.--.",
    ")": "-.--.-",
    "-": "-....-",
    "/": "-..-.",
    "\"": ".-..-.",
    "'": ".----.",
    "@": ".--.-.",
    "=": "-...-",
}


def normalize_text_for_morse(text: str) -> str:
    t = (text or "").upper()
    t = t.replace("Ё", "Е")
    # Normalize whitespace
    t = " ".join(t.split())
    return t


def text_to_morse(text: str) -> str:
    """
    Output format:
      - Letters separated by single spaces
      - Words separated by ' / '
    Unsupported characters are skipped.
    """
    t = normalize_text_for_morse(text)
    if not t:
        return ""

    words = []
    for word in t.split(" "):
        letters = []
        for ch in word:
            code = MORSE.get(ch)
            if code:
                letters.append(code)
        if letters:
            words.append(" ".join(letters))
    return " / ".join(words)


# =========================
# Detection labels (EN->RU)
# =========================
NAMES_RU: Dict[str, str] = {
    "person": "Человек",
    "car": "Машина",
    "bus": "Автобус",
    "bicycle": "Велосипед",
    "dog": "Собака",
    "door": "Дверь",
    "chair": "Стул",
    "cup": "Кружка",
    "cell phone": "Телефон",
    "traffic light": "Светофор",
    "stop sign": "Знак стоп",
}


def bbox_width_xyxy(xyxy) -> float:
    return float(xyxy[2] - xyxy[0])


def bbox_x_center_xyxy(xyxy) -> float:
    return float((xyxy[0] + xyxy[2]) / 2.0)


def direction_from_x(x_center: float, frame_w: int) -> str:
    if frame_w <= 0:
        return "прямо"
    if x_center < frame_w / 3.0:
        return "слева"
    if x_center > 2.0 * frame_w / 3.0:
        return "справа"
    return "прямо"


# =========================
# Flask + Socket.IO
# =========================
app = Flask(__name__, static_folder=".")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


@app.get("/")
def index():
    return send_from_directory(".", "index.html")


@socketio.on("manual_text")
def on_manual_text(payload):
    text = ""
    if isinstance(payload, dict):
        text = str(payload.get("text") or "")
    text = text.strip()
    if not text:
        return
    socketio.emit("vibrate", {"morse": text_to_morse(text), "text": text})


def detection_loop():
    model = YOLO(MODEL_PATH)

    cap = None
    last_infer_at = 0.0
    last_emitted_text = None

    while True:
        try:
            if cap is None or not cap.isOpened():
                cap = cv2.VideoCapture(WEBCAM_URL)
                if not cap.isOpened():
                    socketio.sleep(1.0)
                    continue

            # Keep stream fresh: grab a few frames, use the last one.
            for _ in range(5):
                cap.grab()
            ok, frame = cap.retrieve()
            if not ok or frame is None:
                try:
                    cap.release()
                except Exception:
                    pass
                cap = None
                socketio.sleep(0.5)
                continue

            now = time.time()
            if now - last_infer_at < INFER_EVERY_SECONDS:
                socketio.sleep(0.02)
                continue
            last_infer_at = now

            h, w = frame.shape[:2]
            results = model.predict(frame, imgsz=IMG_SIZE, conf=CONF_LEVEL, verbose=False)
            if not results:
                socketio.sleep(0)
                continue

            r = results[0]

            # Pick top1 by bbox width, tie by conf.
            best = None  # (bbox_width, conf, name_en, x_center, label_ru)
            boxes = getattr(r, "boxes", None)
            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    conf = float(box.conf[0])
                    if conf < CONF_LEVEL:
                        continue
                    cls = int(box.cls[0])
                    name_en = model.names.get(cls, str(cls))
                    label_ru = NAMES_RU.get(name_en)
                    if not label_ru:
                        continue
                    xyxy = box.xyxy[0].tolist()
                    bbox_w = bbox_width_xyxy(xyxy)
                    x_center = bbox_x_center_xyxy(xyxy)
                    cand = (bbox_w, conf, name_en, x_center, label_ru)
                    if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1] > best[1]):
                        best = cand

            if best is None:
                socketio.sleep(0)
                continue

            bbox_w, conf, name_en, x_center, label_ru = best
            direction = direction_from_x(x_center=x_center, frame_w=w)
            danger = "ОПАСНО " if bbox_w > DANGER_BBOX_WIDTH_PX else ""
            text = f"{danger}{label_ru} {direction}".strip()
            morse = text_to_morse(text)

            # Avoid spamming the same phrase every second.
            if text != last_emitted_text:
                socketio.emit("vibrate", {"morse": morse, "text": text})
                last_emitted_text = text

            socketio.sleep(0)
        except Exception:
            # Keep the loop alive on transient errors.
            socketio.sleep(0.5)


if __name__ == "__main__":
    socketio.start_background_task(detection_loop)
    socketio.run(app, host="0.0.0.0", port=5000)
