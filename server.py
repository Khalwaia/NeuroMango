"""NeuroMango — FastAPI Server.

Serves the web frontend, provides a WebSocket endpoint for real-time
lip-sync data, and exposes a REST API for triggering speech.
"""

import asyncio
import json
import shared_state
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import config
from tts_engine import TTSEngine
from memory_manager import MemoryManager
from llm_engine import LLMEngine
from vision_service import VisionManager

# ──────────────────────────────── Logging ──────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("neuromango")

# ──────────────────────────────── App ──────────────────────────────────
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(initialize_engines())
    asyncio.create_task(heartbeat_loop())
    yield

app = FastAPI(title="NeuroMango", version="0.2.0", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

# Mount temp folder for Unity audio downloads
app.mount("/temp", StaticFiles(directory=str(config.TEMP_DIR)), name="temp")

# Serve VRM models
app.mount("/models", StaticFiles(directory=str(config.MODELS_DIR)), name="models")

# ──────────────────────────────── Engines ──────────────────────────────




system_ready = False

# ──────────────────────────────── Modules ──────────────────────────────
MODULES_CONFIG_FILE = config.BASE_DIR / "modules.json"

def load_modules_state():
    if MODULES_CONFIG_FILE.exists():
        try:
            with open(MODULES_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"twitch": True, "da": True, "heartbeat": True}

def save_modules_state(state):
    with open(MODULES_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)

modules_state = load_modules_state()
heartbeat_enabled = modules_state.get("heartbeat", True)





async def on_twitch_message(username, text):
    logger.info(f"🧠 Forwarding Twitch message from {username} to LLM...")
    _schedule_speech(text, is_heartbeat=False, sender_name=username, sender_role="Twitch Зритель")

async def start_twitch():
    
    from twitch_service import TwitchService
    if shared_state.twitch_service is None:
        shared_state.twitch_service = TwitchService(on_twitch_message)
        if shared_state.twitch_service.message_callback:
            asyncio.create_task(shared_state.twitch_service.start())

async def stop_twitch():
    
    if shared_state.twitch_service:
        await shared_state.twitch_service.stop()
        

async def on_donation(username, amount, currency, message):
    logger.info("🧠 Forwarding Donation to LLM...")
    system_msg = f"[СИСТЕМНОЕ УВЕДОМЛЕНИЕ]: Пришел ДОНАТ от {username} на сумму {amount} {currency}! Сообщение: \"{message}\"."
    _schedule_speech(system_msg, is_heartbeat=False, sender_name="Система", sender_role="system")
    if message and len(message.strip()) > 2:
        import asyncio
        if shared_state.music_service:
            asyncio.create_task(shared_state.music_service.add_to_queue(message, requester=username))

async def start_da():
    
    from da_service import DonationAlertsService
    if shared_state.da_service is None:
        shared_state.da_service = DonationAlertsService(
            token=config.DA_WIDGET_TOKEN, 
            min_amount=config.DA_MUSIC_MIN_AMOUNT, 
            on_donation_callback=on_donation
        )
        asyncio.create_task(shared_state.da_service.start())

async def stop_da():
    
    if shared_state.da_service:
        await shared_state.da_service.stop()
        

async def initialize_engines():
    global system_ready
    
    # Wait briefly so frontend has time to connect its WebSocket
    await asyncio.sleep(1)
    logger.info("🚀 Starting async background initialization...")
    await manager.broadcast_json({"type": "system_log", "text": "System Online. Initializing AI Models (This takes 20-30s)..."})
    
    def _init():
        
        
        from memory_manager import MemoryManager
        from vision_service import VisionManager
        from tts_engine import TTSEngine
        from llm_engine import LLMEngine
        from audio_service import AudioService
        
        # Load sequentially or however they take time
        shared_state.memory_mgr = MemoryManager()
        shared_state.vision_manager = VisionManager()
        shared_state.tts = TTSEngine(voice_ref="voice_ref.wav")
        shared_state.llm = LLMEngine(shared_state.memory_mgr, shared_state.vision_manager)
        shared_state.audio_service = AudioService()
        
    # 1. Run heavy blocking models in a background thread
    await asyncio.to_thread(_init)
    
    # 2. Back in the main thread (with the running event loop), init async services
    
    from music_service import MusicService
    
    # Initialize Music Queue
    async def on_queue_update():
        if hasattr(shared_state, 'music_service') and shared_state.music_service:
            await manager.broadcast_json({"type": "queue_update", "data": shared_state.music_service.get_queue_state()})
            
    shared_state.music_service = MusicService(on_queue_update_callback=on_queue_update)
    
    # Initialize Twitch and DA if enabled
    if modules_state.get("twitch", True):
        await start_twitch()
        
    if modules_state.get("da", True):
        await start_da()
    
    system_ready = True
    logger.info("✅ Models loaded successfully. AI is ready.")
    await manager.broadcast_json({"type": "system_log", "text": "✅ Models loaded successfully. AI is ready."})

async def heartbeat_loop():
    logger.info("💓 Heartbeat (Subconscious) module started.")
    while True:
        await asyncio.sleep(10)
        global heartbeat_enabled
        if not heartbeat_enabled or not system_ready:
            continue
            
        import time
        import random
        import shared_state
        import config
        time_since_last = time.time() - shared_state.last_interaction_time
        
        # 120 seconds of absolute silence across everything
        if time_since_last > 120:
            if _current_speech_task and not _current_speech_task.done():
                continue
                
            logger.info("💓 Heartbeat: Subconscious activating after %.0f seconds of silence.", time_since_last)
            
            # --- Build subconscious context ---
            memory_mgr = shared_state.llm.memory
            
            # 1. Pull a random memory from vector DB (like a thought surfacing)
            random_memory = ""
            try:
                mem_count = memory_mgr.collection.count()
                if mem_count > 0:
                    # Pick a random "seed" word to query against for variety
                    seeds = ["Артём", "стрим", "музыка", "игра", "жизнь", "интересно", "смешно", "вспомнить", "скучно", "ночь", "утро", "донат", "чат"]
                    seed = random.choice(seeds)
                    results = memory_mgr.collection.query(
                        query_texts=[seed],
                        n_results=min(3, mem_count)
                    )
                    if results and results['documents'] and results['documents'][0]:
                        picked = random.choice(results['documents'][0])
                        random_memory = f"[Всплывшее воспоминание]: {picked}"
            except Exception as e:
                logger.warning("Heartbeat memory retrieval error: %s", e)
            
            # 2. Pull random graph knowledge (associations)
            graph_snippet = ""
            try:
                if memory_mgr.graph.number_of_edges() > 0:
                    edges = list(memory_mgr.graph.edges(data=True))
                    sample_edges = random.sample(edges, min(3, len(edges)))
                    facts = [f"  {u} → {d.get('relation', '?')} → {v}" for u, v, d in sample_edges]
                    graph_snippet = "[Ассоциации из памяти]:\n" + "\n".join(facts)
            except Exception as e:
                logger.warning("Heartbeat graph retrieval error: %s", e)
            
            # 3. Analyze recent history for context
            history_hint = ""
            try:
                recent = memory_mgr.history[-5:] if memory_mgr.history else []
                if recent:
                    last_msgs = [f"  {m['role']}: {m['content'][:80]}" for m in recent]
                    history_hint = "[Последние сообщения перед тишиной]:\n" + "\n".join(last_msgs)
                else:
                    history_hint = "[Контекст]: Сегодня ещё никто ничего не писал."
            except Exception:
                pass
            
            # 4. Environmental info
            minutes_silent = int(time_since_last // 60)
            env_info = f"[Окружение]: Тишина уже {minutes_silent} мин."
            if modules_state.get("twitch", False):
                env_info += " Режим: Стрим на Twitch."
            else:
                env_info += " Режим: Локальный (без стрима)."
            
            # 5. Assemble the subconscious prompt
            parts = [
                "[ПОДСОЗНАНИЕ АКТИВИРОВАНО]",
                env_info,
            ]
            if random_memory:
                parts.append(random_memory)
            if graph_snippet:
                parts.append(graph_snippet)
            if history_hint:
                parts.append(history_hint)
            parts.append("[Инструкция]: Ты сейчас наедине со своими мыслями. Проанализируй контекст. Можешь: вспомнить что-то и подумать об этом, погуглить то что тебя интересует, поставить музыку, использовать звуки, или просто помолчать (ответь SILENCE). Действуй как живое существо со своим внутренним миром. НЕ ПИШИ ДЛИННЫХ ТЕКСТОВ.")
            
            prompt = "\n".join(parts)
            logger.info("💓 Subconscious prompt:\n%s", prompt)
            
            _schedule_speech(prompt, is_heartbeat=True, sender_name="Подсознание", sender_role="system")
            shared_state.last_interaction_time = time.time()

@app.get("/api/modules")
async def get_modules():
    return modules_state

@app.post("/api/modules/toggle")
async def toggle_module(module: str, enabled: bool):
    global heartbeat_enabled
    modules_state[module] = enabled
    save_modules_state(modules_state)
    
    if module == "twitch":
        if enabled:
            await start_twitch()
        else:
            await stop_twitch()
    elif module == "da":
        if enabled:
            await start_da()
        else:
            await stop_da()
            
    return {"status": "ok", "modules": modules_state}


# ────────────────────────── Connection Manager ─────────────────────────
class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("🔗 WebSocket connected. Total: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("🔌 WebSocket disconnected. Total: %d", len(self.active_connections))

    async def broadcast_json(self, data: dict) -> None:
        """Send JSON to all connected clients."""
        for ws in self.active_connections:
            try:
                await ws.send_json(data)
            except Exception:
                pass

    async def broadcast_bytes(self, data: bytes) -> None:
        """Send binary data to all connected clients."""
        for ws in self.active_connections:
            try:
                await ws.send_bytes(data)
            except Exception:
                pass


manager = ConnectionManager()

# Track current speech task so we can cancel it
_current_speech_task: asyncio.Task | None = None


# ──────────────────────────────── Routes ───────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    index_path = config.STATIC_DIR / "index.html"
    return FileResponse(index_path)


@app.get("/api/model")
async def get_model_info():
    """Return info about the available VRM model."""
    if not system_ready:
        return {"error": "System initializing"}
    model_path = config.get_vrm_model_path()
    if model_path is None:
        return {"error": "No VRM model found in models/ directory"}
    return {
        "filename": model_path.name,
        "url": f"/models/{model_path.name}",
        "size_mb": round(model_path.stat().st_size / (1024 * 1024), 1),
    }


@app.get("/api/memory")
async def get_memory():
    """Return the core memory content."""
    try:
        with open(config.CORE_MEMORY_PATH, "r", encoding="utf-8") as f:
            return {"text": f.read()}
    except Exception as e:
        return {"error": str(e)}

class MemoryUpdateRequest(BaseModel):
    text: str

@app.post("/api/memory")
async def update_memory(req: MemoryUpdateRequest):
    """Update the core memory content."""
    try:
        with open(config.CORE_MEMORY_PATH, "w", encoding="utf-8") as f:
            f.write(req.text)
        # Force memory manager to reload the core memory
        shared_state.memory_mgr.load_core_memory()
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}

# ──────────────────────────── Speak Endpoint ───────────────────────────
class SpeakRequest(BaseModel):
    text: str
    sender_name: str = "Артём"
    sender_role: str = "developer"


@app.post("/api/vision/mode")
async def set_vision_mode(mode: str):
    """Set vision mode: off, screen, webcam"""
    if not system_ready or shared_state.vision_manager is None:
        return {"error": "System initializing"}
    if mode not in ["off", "screen", "webcam"]:
        return {"error": "Invalid mode"}
    shared_state.vision_manager.set_mode(mode)
    return {"status": "ok", "mode": mode}

@app.post("/api/speak")
async def speak(request: SpeakRequest):
    """Accept text and trigger LLM + TTS pipeline."""
    if not system_ready:
        return {"error": "System is still initializing. Please wait."}
        
    text = request.text.strip()
    if not text:
        return {"error": "Empty text"}

    logger.info("🗣️  Speak request (REST): %s", text[:80])
    _schedule_speech(text, is_heartbeat=False, sender_name=request.sender_name, sender_role=request.sender_role)
    return {"status": "ok", "text": text}


def _schedule_speech(text: str, is_heartbeat: bool = False, sender_name: str = "Артём", sender_role: str = "developer") -> None:
    """Schedule a speech task, cancelling any currently running one."""
    global _current_speech_task
    import time
    shared_state.last_interaction_time = time.time()

    if _current_speech_task and not _current_speech_task.done():
        # Do not interrupt ongoing speech for a heartbeat
        if is_heartbeat:
            logger.info("⏹️  Skipping heartbeat speech because AI is already speaking")
            return
            
        _current_speech_task.cancel()
        logger.info("⏹️  Cancelled previous speech task")

    _current_speech_task = asyncio.create_task(_send_speech(text, is_heartbeat, sender_name, sender_role))


async def _send_speech(text: str, is_heartbeat: bool = False, sender_name: str = "Артём", sender_role: str = "developer") -> None:
    """Pass text to LLM, then generate speech audio chunks and stream to clients."""
    try:
        await manager.broadcast_json({"type": "emotion", "animation_trigger": "Think"})
        chunk_index = 0
        
        logger.info("🧠 Sending to LLM: %s", text)
        await manager.broadcast_json({"type": "emotion", "animation_trigger": "Think"})
        chunk_index = 0
        
        async for chunk_text, anim_trigger, is_final in shared_state.llm.generate_response_stream(text, sender_name, sender_role):
            if not chunk_text and is_final:
                # Tell client we are done
                await manager.broadcast_json({"type": "speak_done"})
                break
                
            if chunk_text:
                logger.info("🔊 Generating speech for chunk %d: %s", chunk_index, chunk_text[:60])
                audio_base64 = await shared_state.tts.synthesize_chunk(chunk_text, chunk_index)
                
                if audio_base64:
                    await manager.broadcast_json({
                        "type": "speak_chunk",
                        "text": chunk_text,
                        "animation_trigger": anim_trigger,
                        "audio_base64": audio_base64,
                        "chunk_index": chunk_index,
                        "is_final": is_final
                    })
                    logger.info("📤 Sent chunk %d to clients (Anim: %s)", chunk_index, anim_trigger)
                    chunk_index += 1

    except asyncio.CancelledError:
        logger.info("⏹️  Speech task cancelled")
        await manager.broadcast_json({"type": "speak_cancel"})
    except Exception as e:
        logger.error("❌ Speech error: %s", e)
        await manager.broadcast_json({
            "type": "error",
            "message": f"TTS error: {e}",
        })
    finally:
        import time
        shared_state.last_interaction_time = time.time()


# ──────────────────────────── WebSocket ────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time communication."""
    await manager.connect(websocket)
    
    # Send current system status to the new client
    if system_ready:
        await websocket.send_json({"type": "system_log", "text": "✅ Models loaded successfully. AI is ready."})
    else:
        await websocket.send_json({"type": "system_log", "text": "System Online. Initializing AI Models (This takes 20-30s)..."})
        
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif message.get("type") == "get_queue":
                if hasattr(shared_state, 'music_service'):
                    await websocket.send_json({"type": "queue_update", "data": shared_state.music_service.get_queue_state()})
            elif message.get("type") == "song_ended":
                if hasattr(shared_state, 'music_service'):
                    await shared_state.music_service.pop_next()
            elif message.get("type") == "speak":
                # Client triggers speech via WebSocket
                text = message.get("text", "").strip()
                sender_name = message.get("sender_name", "Артём")
                sender_role = message.get("sender_role", "developer")
                if text:
                    logger.info("🗣️  Speak request (WS): %s", text[:80])
                    _schedule_speech(text, is_heartbeat=False, sender_name=sender_name, sender_role=sender_role)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        manager.disconnect(websocket)


# ──────────────────────────── Entry Point ──────────────────────────────
if __name__ == "__main__":
    import uvicorn

    logger.info("🥭 NeuroMango starting on http://%s:%d", config.HOST, config.PORT)
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level="info",
    )
