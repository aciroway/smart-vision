import cv2
from ultralytics import YOLO
import pyttsx3
import threading
import time

# 1. Инициализация "мозгов" и "голоса"
model = YOLO('yolov8n.pt')
engine = pyttsx3.init()

# Словарь для перевода (можешь дополнять)
names_ru = {
    'person': 'Человек',
    'car': 'Машина',
    'bus': 'Автобус',
    'door': 'Дверь'
}

# 2. Функция озвучки (в отдельном потоке, чтобы видео не фризило)
def speak(text):
    def target():
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=target, daemon=True).start()

# 3. Запуск камеры
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Ширина
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480) # Высота

print("Система запущена. Нажми 'q' для выхода.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Запускаем YOLO на кадре
    results = model(frame, stream=True, imgsz=320, conf=0.4)

    for r in results:
        boxes = r.boxes
        for box in boxes:
            cls = int(box.cls[0])
            name_en = model.names[cls]
            conf = box.conf[0]

            if conf > 0.5 and name_en in names_ru:
                name_ru = names_ru[name_en]
                print(f"Обнаружено: {name_ru}")
                speak(name_ru)
                # Пауза, чтобы не заспамить голосом (можно настроить)
                time.sleep(1)

    # Показываем окно с видео (для отладки)
    cv2.imshow("Smart Vision", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()