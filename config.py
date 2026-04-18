# config.py
IP = "10.14.240.61"  # Твой актуальный IP из IP Webcam
PORT = "8080"

VIDEO_URL = f"http://{IP}:{PORT}/video"
GPS_URL = f"http://{IP}:{PORT}/gps.json"

# Настройки ИИ
MODEL_PATH = 'yolov8s.pt'
CONF_LEVEL = 0.7  # ИИ будет говорить только если уверен на 65% и выше
IMG_SIZE = 224



# Интервалы (в секундах)
GEO_INTERVAL = 60  # Как часто проверять адрес
SPEAK_COOLDOWN = 4 # Пауза между фразами детектора