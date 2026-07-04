import os
os.environ["COQUI_TOS_AGREED"] = "1"
print("Loading TTS API...")
import torch

_original_load = torch.load
def safe_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = safe_load
from TTS.api import TTS

print("Determining device...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")

print("Loading model...")
try:
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    print("Model loaded successfully!")
except Exception as e:
    print("CRASH:", e)
    import traceback
    traceback.print_exc()
