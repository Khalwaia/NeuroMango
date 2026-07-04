import os
with open('llm_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('import server', 'import shared_state')
text = text.replace('server.', 'shared_state.')

with open('llm_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
