import asyncio
import websockets
import json
import threading
import queue
import sys
import os

try:
    import keyboard
    import sounddevice as sd
    from vosk import Model, KaldiRecognizer
except ImportError:
    print("[ERROR] Не установлены библиотеки. Запустите: pip install vosk sounddevice keyboard")
    sys.exit(1)

import os
VOSK_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "models", "vosk-model-ru"))

class ChatClient:
    def __init__(self):
        self.uri = "ws://127.0.0.1:8766/ws"
        self.websocket = None
        self.loop = None
        self.audio_queue = queue.Queue()
        self.is_recording = False
        
        # Загрузка модели Vosk
        if not os.path.exists(VOSK_MODEL_PATH):
            print(f"❌ Модель Vosk не найдена по пути {VOSK_MODEL_PATH}.")
            print("Запустите скрипт download_vosk.py для скачивания.")
            sys.exit(1)
            
        print("⏳ Загрузка большой модели Vosk (это может занять секунд 10-15)...")
        self.model = Model(VOSK_MODEL_PATH)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        print("✅ Vosk готов к работе!")

    async def connect_and_chat(self):
        self.loop = asyncio.get_running_loop()
        print("==================================================")
        print("🧠 Подключение к серверу Нейроны...")
        
        try:
            async with websockets.connect(self.uri) as ws:
                self.websocket = ws
                print("✅ Подключено!")
                print("🎤 Удерживайте клавишу 'M' (английскую), чтобы говорить, или пишите текст здесь.")
                print("==================================================")
                
                # Запускаем потоки для звука и распознавания
                threading.Thread(target=self._audio_processing_thread, daemon=True).start()
                
                with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                                    channels=1, callback=self._audio_callback):
                    
                    # Параллельно запускаем чтение сообщений с сервера и ввод с клавиатуры
                    receive_task = asyncio.create_task(self._receive_messages())
                    input_task = asyncio.create_task(self._handle_text_input())
                    
                    await asyncio.gather(receive_task, input_task)
                    
        except ConnectionRefusedError:
            print("❌ Ошибка подключения: Сервер недоступен.")
            print("Убедитесь, что вы сначала запустили start_server.bat!")
            input("Нажмите Enter для выхода...")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            input("Нажмите Enter для выхода...")

    async def _receive_messages(self):
        try:
            while True:
                if not self.websocket:
                    break
                msg = await self.websocket.recv()
                data = json.loads(msg)
                if data.get("type") == "speak_chunk" and data.get("text"):
                    anim = data.get("animation_trigger", "")
                    anim_text = f" [{anim}]" if anim else ""
                    print(f"\nНейрона{anim_text}: {data['text']}")
        except websockets.exceptions.ConnectionClosed:
            print("\n❌ Соединение разорвано.")
        except Exception as e:
            print(f"Ошибка получения: {e}")

    async def _handle_text_input(self):
        while True:
            # Блокирующий ввод в отдельном потоке
            user_text = await asyncio.to_thread(input, "")
            if user_text.strip():
                if self.websocket:
                    await self.websocket.send(json.dumps({
                        "type": "speak",
                        "text": user_text.strip()
                    }))

    def _audio_callback(self, indata, frames, time, status):
        """Вызывается звуковой картой для каждого чанка аудио."""
        if status:
            print(status, file=sys.stderr)
            
        # Захватываем звук только если зажата 'v'
        if keyboard.is_pressed('v'):
            if not self.is_recording:
                print("\n🎙️ Слушаю...", end="", flush=True)
                self.is_recording = True
            self.audio_queue.put(bytes(indata))
        else:
            if self.is_recording:
                # Кнопка отпущена, отправляем сигнал завершения
                self.audio_queue.put(None)
                self.is_recording = False

    def _audio_processing_thread(self):
        """Воркер, который обрабатывает звук через Vosk."""
        full_text = ""
        while True:
            data = self.audio_queue.get()
            
            if data is None:
                # Конец записи (кнопка отпущена)
                res = json.loads(self.recognizer.FinalResult())
                text = res.get("text", "")
                full_text += " " + text
                final_phrase = full_text.strip()
                
                if final_phrase:
                    print(f"\n🗣️ Вы сказали: {final_phrase}")
                    # Отправляем на сервер через event loop
                    if self.websocket and self.loop:
                        asyncio.run_coroutine_threadsafe(
                            self.websocket.send(json.dumps({
                                "type": "speak",
                                "text": final_phrase
                            })),
                            self.loop
                        )
                
                # Сброс состояния
                full_text = ""
                self.recognizer.Reset()
                continue

            if self.recognizer.AcceptWaveform(data):
                res = json.loads(self.recognizer.Result())
                text = res.get("text", "")
                if text:
                    full_text += text + " "

if __name__ == "__main__":
    client = ChatClient()
    try:
        asyncio.run(client.connect_and_chat())
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
