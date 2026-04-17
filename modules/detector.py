import cv2
from ultralytics import YOLO


class SmartDetector:
    def __init__(self, model_path='yolov8n.pt'):
        self.model = YOLO(model_path)
        # Навигационные фразы
        self.nav_logic = {
            'person': 'Впереди человек',
            'chair': 'Препятствие',
            'door': 'Дверь',
            'bottle': 'Бутылка на пути'
        }

    def analyze(self, frame):
        results = self.model.track(frame, stream=True, imgsz=320, verbose=False)
        for r in results:
            for box in r.boxes:
                if box.conf[0] > 0.5:
                    cls = int(box.cls[0])
                    name_en = self.model.names[cls]

                    # Определяем сторону
                    x_center = (box.xyxy[0][0] + box.xyxy[0][2]) / 2
                    side = "слева" if x_center < 210 else "справа" if x_center > 430 else "прямо"

                    # Если есть в словаре навигации — возвращаем фразу
                    if name_en in self.nav_logic:
                        return f"{self.nav_logic[name_en]} {side}"
        return None