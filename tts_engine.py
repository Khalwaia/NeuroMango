import os
os.environ['COQUI_TOS_AGREED'] = '1'
import logging
import asyncio
import torch
import config
import time
import base64
import re

# Fix for PyTorch 2.6+ breaking older libraries with weights_only=True
_original_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = _patched_load

from TTS.api import TTS
from ruaccent import RUAccent

logger = logging.getLogger("neuromango.tts")

class TTSEngine:
    """XTTS-v2 Advanced Pipeline with Parametric Emotions and RUAccent."""

    def __init__(self, voice_ref: str = "voice_ref.wav"):
        logger.info("🔊 XTTS-v2 Advanced Engine initializing (this may take a minute)...")
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"🔊 Using device: {self.device}")
        
        model_dir = os.path.expanduser("~/AppData/Local/tts/tts_models--multilingual--multi-dataset--xtts_v2")
        self.tts = TTS(model_path=model_dir, config_path=os.path.join(model_dir, "config.json"), gpu=True)
        
        self.voice_ref = voice_ref
        if not os.path.exists(self.voice_ref):
            logger.warning(f"⚠️ Voice reference file '{self.voice_ref}' not found! Voice cloning will fail.")
        else:
            logger.info(f"🔊 Loaded voice reference: {self.voice_ref}")

    def _preprocess_text_and_params(self, text: str):
        """Parses emotion tags, cleans text, and returns (clean_text, temperature, speed)."""
        
        # Base parameters for XTTS
        temperature = 0.75
        speed = 1.05
        
        upper_text = text.upper()
        
        is_scream = False
        is_laugh = False
        is_sad = False
        
        if '[КРИК]' in upper_text or 'АХ ТЫ' in upper_text or 'БЛЯ' in upper_text or 'ПИЗДЕЦ' in upper_text:
            is_scream = True
        if '[СМЕХ]' in upper_text or 'АХАХ' in upper_text or 'ХАХА' in upper_text or 'ХЕХЕ' in upper_text:
            is_laugh = True
        if '[ГРУСТЬ]' in upper_text or 'ЭХ' in upper_text:
            is_sad = True
            
        # Clean up tags and markdown
        text = re.sub(r'\[.*?\]', '', text).strip()
        text = re.sub(r'[*_~`"\'()<>{}\\]', '', text)
        
        # VERY IMPORTANT: XTTS hallucination fix - kill all english characters ruthlessly
        text = re.sub(r'[a-zA-Z]', '', text)
        
        # Clean up weird punctuation, but allow dots and exclamation marks
        text = re.sub(r'[^А-Яа-яЁё0-9.,!?:\- ]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if not text:
            return "", temperature, speed
            
        # Parametric Emotion Application (done AFTER ruaccent so we don't accent phonetic laughs)
        if is_scream:
            # Scream needs fast speed, but keep temp safe to avoid noise
            speed = 1.15
            temperature = 0.75
            text = text.replace('.', '!!!').replace('?', '?!')
            if not text.endswith('!'):
                text += "!!!"
        elif is_laugh:
            # Safer phonetic laugh and safe temperature
            speed = 1.05
            temperature = 0.75
            text = "Ха-ха. " + text
        elif is_sad:
            # Sad needs slow speed, low temp
            speed = 0.90
            temperature = 0.65
            text = text.replace('!', '.')
            
        # Fix missing end punctuation (XTTS often cuts off without it)
        if text and text[-1] not in '.!?':
            text += '.'
            
        # VERY IMPORTANT: XTTS hates multiple dots (...) and generates white noise. 
        # We must collapse multiple dots into a single dot.
        text = re.sub(r'\.{2,}', '.', text)
        
        # VERY IMPORTANT: Prevent 'потайо' hallucination by ensuring text always ends with a space
        text += ' '
            
        return text, temperature, speed

    async def synthesize_to_file(self, text: str, output_path: str) -> str:
        clean_text, temp, speed = self._preprocess_text_and_params(text)
        if not clean_text:
            clean_text = "А?"
            
        logger.info(f"🔊 Generating XTTS speech for: {clean_text[:60]} (temp={temp}, speed={speed})")
        
        if not os.path.exists(self.voice_ref):
            raise FileNotFoundError(f"Missing {self.voice_ref}")

        start_time = time.time()
        
        try:
            def _generate():
                self.tts.tts_to_file(
                    text=clean_text,
                    speaker_wav=self.voice_ref,
                    language="ru",
                    file_path=output_path,
                    temperature=temp,
                    repetition_penalty=2.0,
                    speed=speed,
                    enable_text_splitting=False
                )
            await asyncio.to_thread(_generate)
            elapsed = time.time() - start_time
            logger.info(f"⏱️ XTTS generation took {elapsed:.2f} seconds")
            
        except Exception as e:
            logger.error(f"XTTS Generation failed: {e}")
            raise
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
            
        return output_path
        
    async def synthesize_chunk(self, text: str, chunk_index: int) -> str:
        clean_text, temp, speed = self._preprocess_text_and_params(text)
        if not clean_text:
            return ""
            
        output_path = config.TEMP_DIR / f"chunk_{chunk_index}.wav"
        
        try:
            def _generate():
                self.tts.tts_to_file(
                    text=clean_text,
                    speaker_wav=self.voice_ref,
                    language="ru",
                    file_path=str(output_path),
                    temperature=temp,           
                    repetition_penalty=2.0,
                    speed=speed,
                    enable_text_splitting=False
                )
            await asyncio.to_thread(_generate)
            
            with open(output_path, "rb") as f:
                audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            try:
                os.remove(output_path)
            except Exception:
                pass
                
            return audio_base64
        except Exception as e:
            logger.error(f"Chunk synthesis failed: {e}")
            return ""
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
