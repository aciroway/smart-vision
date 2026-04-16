import cv2
import time
from modules.detector import SmartDetector
from modules.server import VoiceServer

# Замени на свой IP из IP Webcam
VIDEO_URL = "http://10.14.240.61:8080/video"

detector = SmartDetector()
server = VoiceServer()

server.start()
cap = cv2.VideoCapture(VIDEO_URL)
last_speak = 0

print("Всё готово! Открой на телефоне http://10.14.240.61:5000")

while cap.isOpened():
    for _ in range(5): cap.grab()
    success, frame = cap.retrieve()
    if not success: break

    command = detector.analyze(frame)

    if command and (time.time() - last_speak > 3):
        server.emit(command)
        print(f"Голос: {command}")
        last_speak = time.time()

    cv2.imshow("Tactile System", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()