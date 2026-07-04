import logging
import winsound
import os
import config

logger = logging.getLogger("neuromango.audio")

class AudioService:
    def __init__(self):
        self.sounds_dir = config.BASE_DIR / "sounds"
        self.sounds_dir.mkdir(parents=True, exist_ok=True)
        logger.info("🎵 Audio service initialized (winsound).")

    def play_sound_async(self, sound_name: str):
        """Plays a .wav file from the sounds directory asynchronously."""
        try:
            # Append .wav if not provided (winsound only plays WAV)
            if not sound_name.endswith('.wav'):
                file_path = self.sounds_dir / f"{sound_name}.wav"
            else:
                file_path = self.sounds_dir / sound_name
            
            if not file_path.exists():
                logger.error(f"Sound file not found: {file_path}. Note: Only .wav files are supported!")
                return
            
            logger.info(f"🎵 Playing sound: {file_path.name}")
            # SND_ASYNC plays the sound in the background and returns immediately
            # SND_FILENAME means the string is a filename
            winsound.PlaySound(str(file_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            
        except Exception as e:
            logger.error(f"Failed to play sound {sound_name}: {e}")
