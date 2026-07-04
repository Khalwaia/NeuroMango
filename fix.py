import os
with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('from shared_state.tts_engine', 'from tts_engine')
text = text.replace('from shared_state.llm_engine', 'from llm_engine')
text = text.replace('from shared_state.audio_service', 'from audio_service')
text = text.replace('from shared_state.music_service', 'from music_service')
text = text.replace("if 'shared_state.music_service' in globals()", "if hasattr(shared_state, 'music_service')")

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(text)
