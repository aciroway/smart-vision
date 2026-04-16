from gtts import gTTS
import pygame
import os
import threading


class VoiceServer:
    def __init__(self):
        pygame.mixer.init()
        self.lock = threading.Lock()

    def start(self):
        print(">>> Голосовой гид (gTTS) активен")

    def emit(self, text):
        def target():
            with self.lock:
                try:
                    # Генерируем озвучку
                    tts = gTTS(text=text, lang='ru')
                    tts.save("voice.mp3")

                    # Воспроизводим
                    pygame.mixer.music.load("voice.mp3")
                    pygame.mixer.music.play()

                    while pygame.mixer.music.get_busy():
                        continue

                    pygame.mixer.music.unload()
                except Exception as e:
                    print(f"Ошибка звука: {e}")

        threading.Thread(target=target, daemon=True).start()