import cv2
from ultralytics import YOLO
import config


class SmartDetector:
    def __init__(self):
        self.model = YOLO(config.MODEL_PATH)
        # Добавь в словарь навигации больше "препятствий"
        self.nav_logic = {
            'person': 'пешеход',
            'chair': 'препятствие',
            'table': 'препятствие',
            'door': 'дверь',
            'wall': 'препятствие',  # YOLOv8 иногда может путать, но добавим
            'tvmonitor': 'препятствие'  # Телевизоры на стенах часто мешают

        }

    def analyze(self, frame):
        # Уменьшаем verbose, чтобы не спамить в консоль
        results = self.model.track(frame, imgsz=config.IMG_SIZE, conf=config.CONF_LEVEL, verbose=False)

        for r in results:
            # Сортируем объекты по уверенности, берем самый надежный
            boxes = sorted(r.boxes, key=lambda x: x.conf[0], reverse=True)

            for box in boxes:
                conf = box.conf[0]
                cls = int(box.cls[0])
                name_en = self.model.names[cls]

                # Фильтр: если это пешеход, но уверенность ниже 0.7 — игнорим
                if name_en == 'person' and conf < 0.7:
                    continue

                # Определяем сторону
                x_center = (box.xyxy[0][0] + box.xyxy[0][2]) / 2

                # Настройка зон (можешь подкрутить цифры под свой экран)
                if x_center < 150:
                    side = "слева"
                elif x_center > 490:
                    side = "справа"
                else:
                    side = "прямо"

                if name_en in self.nav_logic:
                    return f"{self.nav_logic[name_en]} {side}"
        return None