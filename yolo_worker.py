import json
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

import cv2
from ultralytics import YOLO


WEBCAM_URL = os.environ.get("WEBCAM_URL", "http://10.0.0.100:8080/video")

MODEL_PATH = os.environ.get("MODEL_PATH", "yolov8n.pt")
CONF_LEVEL = float(os.environ.get("CONF_LEVEL", "0.3"))
IMG_SIZE = int(os.environ.get("IMG_SIZE", "640"))

INFER_EVERY_SECONDS = float(os.environ.get("INFER_EVERY_SECONDS", "1.0"))
DANGER_BBOX_WIDTH_PX = int(os.environ.get("DANGER_BBOX_WIDTH_PX", "350"))


# COCO-focused RU labels (no non-COCO like "door")
NAMES_RU: Dict[str, str] = {
    "person": "Человек",
    "car": "Машина",
    "bus": "Автобус",
    "bicycle": "Велосипед",
    "dog": "Собака",
    "chair": "Стул",
    "cup": "Кружка",
    "cell phone": "Телефон",
    "traffic light": "Светофор",
    "stop sign": "Знак стоп",
}


PRIORITY: Dict[str, int] = {
    "person": 100,
    "car": 80,
}


def bbox_width_xyxy(xyxy) -> float:
    return float(xyxy[2] - xyxy[0])


def bbox_x_center_xyxy(xyxy) -> float:
    return float((xyxy[0] + xyxy[2]) / 2.0)


def direction_from_x(x_center: float, frame_w: int) -> str:
    if frame_w <= 0:
        return "center"
    if x_center < frame_w / 3.0:
        return "left"
    if x_center > 2.0 * frame_w / 3.0:
        return "right"
    return "center"


def direction_ru(direction: str) -> str:
    return {"left": "слева", "center": "прямо", "right": "справа"}.get(direction, "прямо")


def choose_best(
    model: YOLO, result, frame_w: int
) -> Optional[Tuple[str, float, float, str, bool, str]]:
    """
    Returns: (name_en, conf, bbox_w, direction, danger, text_ru)
    Filtering:
      - conf >= CONF_LEVEL
      - only classes present in NAMES_RU (COCO subset we care about)
    Prioritization:
      - person > car > others (via PRIORITY)
      - within same priority: larger bbox width, then higher conf
    """
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return None

    best = None  # (prio, bbox_w, conf, name_en, direction, danger, text_ru)
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
        direction = direction_from_x(x_center=x_center, frame_w=frame_w)
        danger = bbox_w > DANGER_BBOX_WIDTH_PX

        prio = PRIORITY.get(name_en, 10)
        danger_prefix = "ОПАСНО " if danger else ""
        text = f"{danger_prefix}{label_ru} {direction_ru(direction)}".strip()

        cand = (prio, bbox_w, conf, name_en, direction, danger, text)
        if best is None:
            best = cand
            continue

        # higher prio first, then bbox width, then conf
        if cand[0] > best[0] or (cand[0] == best[0] and cand[1] > best[1]) or (
            cand[0] == best[0] and cand[1] == best[1] and cand[2] > best[2]
        ):
            best = cand

    if not best:
        return None

    prio, bbox_w, conf, name_en, direction, danger, text = best
    return name_en, conf, bbox_w, direction, danger, text


def log_detected(name_en: str, conf: float, width: float):
    print(f"[YOLO] detected: {name_en} | conf: {conf:.2f} | width: {int(width)}px", file=sys.stderr)


def main():
    print(f"[WORKER] WEBCAM_URL={WEBCAM_URL}", file=sys.stderr)
    print(f"[WORKER] MODEL_PATH={MODEL_PATH} imgsz={IMG_SIZE} conf={CONF_LEVEL}", file=sys.stderr)

    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(WEBCAM_URL)
    if not cap.isOpened():
        print("[WORKER] WARNING: camera not opened, will retry", file=sys.stderr)

    last_infer = 0.0
    last_sent = ""

    while True:
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(WEBCAM_URL)
            time.sleep(0.5)
            continue

        # reduce latency: grab a few frames then retrieve last
        for _ in range(5):
            cap.grab()
        ok, frame = cap.retrieve()
        if not ok or frame is None:
            print("[WORKER] WARNING: frame read failed, reconnecting", file=sys.stderr)
            try:
                cap.release()
            except Exception:
                pass
            cap = None
            time.sleep(0.5)
            continue

        now = time.time()
        if now - last_infer < INFER_EVERY_SECONDS:
            time.sleep(0.01)
            continue
        last_infer = now

        h, w = frame.shape[:2]
        results = model.predict(frame, imgsz=IMG_SIZE, conf=CONF_LEVEL, verbose=False)
        if not results:
            print("[YOLO] WARNING: no results object", file=sys.stderr)
            continue

        r = results[0]
        best = choose_best(model, r, frame_w=w)
        if not best:
            print("[YOLO] WARNING: no relevant detections", file=sys.stderr)
            continue

        name_en, conf, bbox_w, direction, danger, text = best
        log_detected(name_en, conf, bbox_w)

        # avoid repeating identical text too frequently
        if text == last_sent:
            continue
        last_sent = text

        payload = {
            "text": text,
            "direction": direction,
            "danger": bool(danger),
            "label": name_en,
            "conf": conf,
            "bbox_width": int(bbox_w),
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

