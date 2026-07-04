# shared_state.py
twitch_service = None
da_service = None
music_service = None
audio_service = None
tts = None
vision_manager = None
memory_mgr = None
llm = None

import time
last_interaction_time = time.time()
