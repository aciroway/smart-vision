import cv2
from ultralytics import YOLO
import pyttsx3
import threading
import time

# --- НАСТРОЙКИ ---
MODEL_PATH = 'yolov8n.pt'
CONF_LEVEL = 0.5
IMG_SIZE = 320

NAMES_RU = {
    'person': 'Человек', 'car': 'Машина', 'bus': 'Автобус',
    'bicycle': 'Велосипед', 'dog': 'Собака', 'door': 'Дверь',
    'chair': 'Стул', 'cup': 'Кружка', 'cell phone': 'Телефон',
    'traffic light': 'Светофор', 'stop sign': 'Знак стоп'
}

# --- ИНИЦИАЛИЗАЦИЯ ---
model = YOLO(MODEL_PATH)
engine = pyttsx3.init()
engine.setProperty('rate', 190)  # Чуть быстрее речь для динамики


def speak(text):
    def target():
        engine.say(text)
        engine.runAndWait()

    threading.Thread(target=target, daemon=True).start()


# --- ПОДКЛЮЧЕНИЕ КАМЕРЫ ---
# ИЗМЕНЕНИЕ №1: Твой IP адрес. Добавляем /video в конце!
video_url = "http://10.0.0.100:8080/video"
cap = cv2.VideoCapture(video_url)

# Проверка подключения
if not cap.isOpened():
    print("ОШИБКА: Не вижу камеру! Проверь Wi-Fi и адрес в приложении.")
    exit()

last_speak_time = 0

print("СИСТЕМА АКТИВИРОВАНА. Нажми 'q' для выхода.")

while True:
    # ИЗМЕНЕНИЕ №2: Очистка буфера (чтобы видео не отставало от реальности)
    # Мы читаем 5 кадров, но обрабатываем только последний
    for _ in range(5):
        cap.grab()

    success, frame = cap.retrieve()
    if not success:
        print("Потеряна связь с камерой...")
        break

    # ИЗМЕНЕНИЕ №3: Использование track вместо predict для плавности
    results = model.track(frame, persist=True, stream=True, imgsz=IMG_SIZE, verbose=False)

    for r in results:
        # ИЗМЕНЕНИЕ №4: Отрисовка рамок для жюри (чтобы видели результат)
        frame = r.plot()

        boxes = r.boxes
        for box in boxes:
            conf = box.conf[0]
            if conf > CONF_LEVEL:
                cls = int(box.cls[0])
                name_en = model.names[cls]

                if name_en in NAMES_RU:
                    x_center = (box.xyxy[0][0] + box.xyxy[0][2]) / 2

                    # Логика зон
                    if x_center < 210:
                        direction = "слева"
                    elif x_center > 430:
                        direction = "справа"
                    else:
                        direction = "прямо"

                    # ИЗМЕНЕНИЕ №5: Проверка на близость объекта (Опасность)
                    # Если ширина рамки больше 350 пикселей - значит объект в упор
                    width = box.xyxy[0][2] - box.xyxy[0][0]
                    warning = "ОПАСНО, БЛИЗКО! " if width > 350 else ""

                    label = f"{warning}{NAMES_RU[name_en]} {direction}"

                    if time.time() - last_speak_time > 2.5:
                        print(f"Детекция: {label}")
                        speak(label)
                        last_speak_time = time.time()

    # Показываем результат в окне
   # cv2.imshow("TACTILE TRANSLATOR - DEMO", frame)

   # if cv2.waitKey(1) & 0xFF == ord('q'):
    #    break

cap.release()
cv2.destroyAllWindows()