import logging
import os
import config
import asyncio

logger = logging.getLogger("neuromango.audio")

class AudioService:
    def __init__(self):
        self.sounds_dir = config.BASE_DIR / "sounds"
        self.sounds_dir.mkdir(parents=True, exist_ok=True)
        self.volume = 0.2  # 20% volume by default
        
        try:
            import pygame
            pygame.mixer.init()
            self.use_pygame = True
            logger.info(f"🎵 Audio service initialized (pygame, volume={self.volume*100}%).")
        except Exception as e:
            self.use_pygame = False
            logger.warning(f"⚠️ Pygame not available, falling back to winsound. Volume control disabled. Error: {e}")

    def play_sound_async(self, sound_name: str):
        """Plays a .wav file from the sounds directory asynchronously."""
        try:
            # Append .wav if not provided
            if not sound_name.endswith('.wav'):
                file_path = self.sounds_dir / f"{sound_name}.wav"
            else:
                file_path = self.sounds_dir / sound_name
            
            if not file_path.exists():
                logger.error(f"Sound file not found: {file_path}. Note: Only .wav files are supported!")
                return
            
            logger.info(f"🎵 Playing sound: {file_path.name}")
            
            if self.use_pygame:
                import pygame
                sound = pygame.mixer.Sound(str(file_path))
                sound.set_volume(self.volume)
                sound.play()
            else:
                import winsound
                winsound.PlaySound(str(file_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            
        except Exception as e:
            logger.error(f"Failed to play sound {sound_name}: {e}")
