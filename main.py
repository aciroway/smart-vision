import cv2
import time
import config
from modules.detector import SmartDetector
from modules.server import VoiceServer
from modules.geolocator import CityGuide

# Инициализация
detector = SmartDetector()
server = VoiceServer()
guide = CityGuide()

cap = cv2.VideoCapture(config.VIDEO_URL)
last_speak = 0
last_geo_check = 0

print(">>> Система запущена. Нажмите 'q' для выхода.")

frame_count = 0
while cap.isOpened():
    success, frame = cap.read()
    if not success: break

    frame_count += 1
    # Анализируем только каждый 5-й кадр
    if frame_count % 5 == 0:
        if time.time() - last_speak > config.SPEAK_COOLDOWN:
            command = detector.analyze(frame)
            if command:
                server.emit(command)
                last_speak = time.time()


    # 1. Зрение (каждые 3 секунды)
    if time.time() - last_speak > config.SPEAK_COOLDOWN:
        command = detector.analyze(frame)
        if command:
            server.emit(command)
            last_speak = time.time()

    # 2. Геолокация (раз в минуту)
    if time.time() - last_geo_check > config.GEO_INTERVAL:
        address = guide.get_current_location()
        if address:
            server.emit(address)
            print(f"ЛОКАЦИЯ: {address}")
        last_geo_check = time.time()

    # Визуализация
    cv2.imshow("Tactile Vision", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()