import os
import requests
import zipfile
import sys

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"
TARGET_DIR = "models/vosk-model-ru"
ZIP_PATH = "models/vosk-model-ru-0.42.zip"

def download_model():
    os.makedirs("models", exist_ok=True)
    if os.path.exists(TARGET_DIR):
        print(f"✅ Модель Vosk уже существует в {TARGET_DIR}")
        return

    print(f"📥 Скачивание тяжелой модели Vosk (1.8 ГБ). Это может занять время...")
    
    # Download
    response = requests.get(MODEL_URL, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 * 1024 # 1MB
    
    downloaded = 0
    with open(ZIP_PATH, 'wb') as f:
        for data in response.iter_content(block_size):
            downloaded += len(data)
            f.write(data)
            done = int(50 * downloaded / total_size)
            sys.stdout.write(f"\r[{'=' * done}{' ' * (50-done)}] {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB")
            sys.stdout.flush()
            
    print("\n📦 Распаковка архива...")
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall("models")
        
    os.rename("models/vosk-model-ru-0.42", TARGET_DIR)
    os.remove(ZIP_PATH)
    print("✅ Установка Vosk завершена!")

if __name__ == "__main__":
    download_model()
