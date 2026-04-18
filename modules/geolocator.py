import requests
import config
from geopy.geocoders import Nominatim


class CityGuide:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="tactile_helper_bishkek")

    def get_current_location(self):
        try:
            # Пытаемся взять реальный GPS с телефона
            # response = requests.get(config.GPS_URL, timeout=1)
            # data = response.json()
            # lat = data.get('gps', {}).get('lat', 42.8746) # Дефолт: Бишкек
            # lon = data.get('gps', {}).get('lon', 74.5919)

            # ДЛЯ ТЕСТА (центр Бишкека):
            lat, lon = 42.8746, 74.5919

            location = self.geolocator.reverse(f"{lat}, {lon}", language='ru')
            if location:
                # Обрезаем адрес, чтобы не был слишком длинным
                parts = location.address.split(',')
                return f"Вы находитесь: {parts[0]}, {parts[1]}"
            return None
        except:
            return "Не удалось определить адрес"