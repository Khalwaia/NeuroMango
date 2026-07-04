import threading
import time
import cv2
import mss
import base64
import logging
from PIL import Image
import io

logger = logging.getLogger("neuromango.vision")

class VisionManager:
    def __init__(self):
        self.mode = "off"  # "off", "screen", "webcam"
        self.latest_frame_base64 = None
        self._lock = threading.Lock()
        
        self.camera = None
        self.sct = None
        
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        
    def set_mode(self, mode: str):
        if mode not in ["off", "screen", "webcam"]:
            return
            
        logger.info(f"👁️ Vision mode changed to: {mode}")
        with self._lock:
            self.mode = mode
            self.latest_frame_base64 = None
            
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

    def _capture_loop(self):
        while True:
            time.sleep(1.0) # 1 FPS is enough for context and heartbeat
            
            mode = self.mode
            if mode == "off":
                continue
                
            frame_base64 = None
            
            try:
                if mode == "screen":
                    if self.sct is None:
                        self.sct = mss.mss()
                    
                    # Capture the primary monitor
                    monitor = self.sct.monitors[1]
                    sct_img = self.sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    
                    # Resize to save tokens/bandwidth
                    img.thumbnail((1024, 1024))
                    
                    buffered = io.BytesIO()
                    img.save(buffered, format="JPEG", quality=75)
                    frame_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                elif mode == "webcam":
                    if self.camera is None:
                        self.camera = cv2.VideoCapture(0)
                        
                    ret, frame = self.camera.read()
                    if ret:
                        # Convert to RGB (OpenCV uses BGR)
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame_rgb)
                        
                        img.thumbnail((1024, 1024))
                        
                        buffered = io.BytesIO()
                        img.save(buffered, format="JPEG", quality=75)
                        frame_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        
            except Exception as e:
                logger.error(f"Vision capture error ({mode}): {e}")
                
            if frame_base64:
                with self._lock:
                    # Update ONLY if mode hasn't changed during capture
                    if self.mode == mode:
                        self.latest_frame_base64 = frame_base64
