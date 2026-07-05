"""NeuroMango — Project Configuration."""

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────── Paths ────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "static"
VOICE_SAMPLES_DIR = BASE_DIR / "voice_samples"
TEMP_DIR = BASE_DIR / "temp"

# Ensure directories exist
for _dir in [MODELS_DIR, STATIC_DIR, VOICE_SAMPLES_DIR, TEMP_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────── LLM (Brain) ──────────────────────────────
# Основная модель для общения (Gemini)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

# Подсознание (СВИНОПАС - Экстрактор памяти)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

# ──────────────────────────────── Memory (ChromaDB) ─────────────────────────
CHROMA_DB_DIR = BASE_DIR / "memory_db"
CORE_MEMORY_PATH = BASE_DIR / "core_memory.txt"

# ──────────────────────────────── Server ───────────────────────────────
HOST = "127.0.0.1"
PORT = 8766

# ──────────────────────────────── Twitch ───────────────────────────────
# Получить токен можно тут: https://twitchtokengenerator.com/ (нужен "Bot Chat Token", скопируйте Access Token и добавьте "oauth:" в начале, чтобы получилось oauth:ваш_токен)
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")
TWITCH_CHANNEL = "trigandonov"
# Имя, на которое ИИ будет реагировать в чате (без @)
TWITCH_BOT_NAME = "Неманго"

# Режим тестирования: установите True, чтобы ИИ всегда думал, что стрим запущен (полезно для тестов)
FORCE_STREAM_ONLINE = False

# ─────────────────────────── DonationAlerts ────────────────────────────
DA_WIDGET_TOKEN = os.getenv("DA_WIDGET_TOKEN")
DA_MUSIC_MIN_AMOUNT = 50.0

# ────────────────────────────── TTS (XTTS-v2) ─────────────────────────
TTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
TTS_LANGUAGE = "ru"  # Default language for speech synthesis
TTS_SAMPLE_RATE = 24000  # XTTS-v2 outputs 24kHz audio

# ────────────────────────────── Viseme ─────────────────────────────────
VISEME_CHUNK_DURATION_MS = 50  # Analyse audio in 50ms windows
VISEME_SMOOTHING = 0.35  # LERP factor for smooth transitions (0-1)

# ────────────────────────────── VRM Model ──────────────────────────────
def get_vrm_model_path() -> Path | None:
    """Return the first .vrm file found in MODELS_DIR."""
    if not MODELS_DIR.exists():
        return None
    vrm_files = list(MODELS_DIR.glob("*.vrm"))
    return vrm_files[0] if vrm_files else None
