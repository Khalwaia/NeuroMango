import threading
import time
import cv2
import mss
import base64
import logging
import asyncio
import numpy as np
from PIL import Image
from collections import deque
from openai import AsyncOpenAI
import io
import config

logger = logging.getLogger("neuromango.vision")

# ──────────────────────────── Scene Description ────────────────────────────

DESCRIBE_PROMPT = (
    "Ты — глаза ИИ-аватара. Опиши ОДНИМ коротким предложением на русском, что сейчас видно на экране. "
    "Формат: '[Что на экране] — [что делает пользователь]'. Примеры:\n"
    "- 'Открыт VS Code с Python-кодом — пользователь программирует'\n"
    "- 'YouTube, играет клип MORGENSHTERN — пользователь смотрит видео'\n"
    "- 'Рабочий стол Windows, ничего не открыто — пользователь AFK'\n"
    "- 'Игра Minecraft, персонаж в пещере — пользователь играет'\n"
    "НЕ описывай интерфейс детально (кнопки, панели). Только суть — ЧТО открыто и ЧТО делает человек."
)


class VisionManager:
    def __init__(self):
        self.mode = "off"  # "off", "screen", "webcam"
        self.latest_frame_base64 = None
        self._lock = threading.Lock()
        
        self.camera = None
        self.sct = None
        
        # ── Continuous Vision ──
        self._scene_descriptions: deque = deque(maxlen=12)  # ~60 seconds at 5s interval
        self._last_describe_time: float = 0.0
        self._describe_interval: float = 5.0  # seconds between descriptions
        self._prev_frame_hash: int = 0
        self._scene_changed: bool = False
        self._describe_client = AsyncOpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL
        )
        self._describe_model = config.LLM_MODEL
        self._event_loop = None  # will be set from the async context
        
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        
    def set_mode(self, mode: str):
        if mode not in ["off", "screen", "webcam"]:
            return
            
        logger.info(f"👁️ Vision mode changed to: {mode}")
        with self._lock:
            self.mode = mode
            self.latest_frame_base64 = None
            self._scene_descriptions.clear()
            self._prev_frame_hash = 0
            
            # Release resources if switching
            if mode != "webcam" and self.camera is not None:
                self.camera.release()
                self.camera = None
            if mode != "screen" and self.sct is not None:
                self.sct.close()
                self.sct = None

    def get_latest_frame(self) -> str:
        with self._lock:
            return self.latest_frame_base64

    def get_scene_context(self) -> str:
        """Returns a textual summary of recent scene descriptions for injection into prompts."""
        with self._lock:
            if not self._scene_descriptions:
                return ""
            
            descriptions = list(self._scene_descriptions)
        
        if not descriptions:
            return ""
        
        # Deduplicate consecutive identical descriptions
        unique = [descriptions[0]]
        for d in descriptions[1:]:
            if d["text"] != unique[-1]["text"]:
                unique.append(d)
        
        if len(unique) == 1:
            return f"[ЗРЕНИЕ — Сейчас на экране]: {unique[0]['text']}"
        
        lines = ["[ЗРЕНИЕ — Что происходило на экране]:"]
        for entry in unique[-6:]:  # last 6 unique descriptions (~30 sec)
            marker = " 🔄" if entry.get("changed") else ""
            lines.append(f"  [{entry['time']}]{marker} {entry['text']}")
        
        return "\n".join(lines)

    def _compute_frame_hash(self, img: Image.Image) -> int:
        """Fast perceptual hash: resize to 16x16 grayscale, hash the pixels."""
        small = img.resize((16, 16)).convert("L")
        pixels = np.array(small)
        avg = pixels.mean()
        return int.from_bytes(
            bytes([1 if p > avg else 0 for p in pixels.flatten()[:32]]),
            byteorder='big'
        )

    def _detect_scene_change(self, img: Image.Image) -> bool:
        """Returns True if the scene has significantly changed from the previous frame."""
        current_hash = self._compute_frame_hash(img)
        if self._prev_frame_hash == 0:
            self._prev_frame_hash = current_hash
            return True  # first frame is always a "change"
        
        # XOR and count differing bits (hamming distance)
        diff = bin(current_hash ^ self._prev_frame_hash).count('1')
        self._prev_frame_hash = current_hash
        
        # If >25% of bits differ, scene changed significantly
        return diff > 8

    def _capture_loop(self):
        while True:
            time.sleep(1.0)  # 1 FPS capture for the base frame
            
            mode = self.mode
            if mode == "off":
                continue
                
            frame_base64 = None
            pil_img = None
            
            try:
                if mode == "screen":
                    if self.sct is None:
                        self.sct = mss.mss()
                    
                    # Capture the primary monitor
                    monitor = self.sct.monitors[1]
                    sct_img = self.sct.grab(monitor)
                    pil_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    
                    # Resize to save tokens/bandwidth
                    pil_img.thumbnail((1024, 1024))
                    
                    buffered = io.BytesIO()
                    pil_img.save(buffered, format="JPEG", quality=75)
                    frame_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                elif mode == "webcam":
                    if self.camera is None:
                        self.camera = cv2.VideoCapture(0)
                        
                    ret, frame = self.camera.read()
                    if ret:
                        # Convert to RGB (OpenCV uses BGR)
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(frame_rgb)
                        
                        pil_img.thumbnail((1024, 1024))
                        
                        buffered = io.BytesIO()
                        pil_img.save(buffered, format="JPEG", quality=75)
                        frame_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        
            except Exception as e:
                logger.error(f"Vision capture error ({mode}): {e}")
                
            if frame_base64 and pil_img:
                with self._lock:
                    # Update ONLY if mode hasn't changed during capture
                    if self.mode == mode:
                        self.latest_frame_base64 = frame_base64
                
                # Check for scene change
                scene_changed = self._detect_scene_change(pil_img)
                
                # Schedule description if enough time passed or scene changed
                now = time.time()
                should_describe = (
                    (now - self._last_describe_time >= self._describe_interval) or
                    (scene_changed and now - self._last_describe_time >= 2.0)  # min 2s between descriptions
                )
                
                if should_describe:
                    self._last_describe_time = now
                    self._scene_changed = scene_changed
                    # Schedule the async description on the event loop
                    if self._event_loop and not self._event_loop.is_closed():
                        asyncio.run_coroutine_threadsafe(
                            self._describe_frame(frame_base64, scene_changed),
                            self._event_loop
                        )

    async def _describe_frame(self, frame_b64: str, scene_changed: bool):
        """Send a compressed frame to Gemini Flash Lite and get a 1-sentence description."""
        try:
            import datetime
            response = await self._describe_client.chat.completions.create(
                model=self._describe_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": DESCRIBE_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}}
                    ]
                }],
                max_tokens=100,
                temperature=0.1
            )
            
            description = response.choices[0].message.content.strip()
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            
            with self._lock:
                self._scene_descriptions.append({
                    "text": description,
                    "time": now_str,
                    "changed": scene_changed
                })
            
            if scene_changed:
                logger.info(f"👁️ Scene CHANGED: {description}")
            else:
                logger.debug(f"👁️ Scene: {description}")
                
        except Exception as e:
            logger.warning(f"👁️ Vision describe error: {e}")
