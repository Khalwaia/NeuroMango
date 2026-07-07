import os
import config
from memory_manager import MemoryManager

def get_available_sounds() -> str:
    """Returns a string of available .wav files in the sounds directory."""
    sounds_dir = config.BASE_DIR / "sounds"
    if not sounds_dir.exists():
        return "Нет доступных звуков."
    
    wav_files = [f.name for f in sounds_dir.glob("*.wav")]
    if not wav_files:
        return "Нет доступных звуков."
    
    return ", ".join(wav_files)

def build_system_prompt(memory_mgr: MemoryManager, user_query: str) -> str:
    """
    Builds the dynamic system prompt matching the advanced persona architecture (SVINOPAS).
    """
    
    try:
        import json
        import config
        modules_file = config.BASE_DIR / "modules.json"
        twitch_enabled = True
        if modules_file.exists():
            with open(modules_file, "r", encoding="utf-8") as f:
                twitch_enabled = json.load(f).get("twitch", True)
    except Exception:
        twitch_enabled = True

    if twitch_enabled:
        from twitch_service import get_stream_uptime
        stream_status = get_stream_uptime()
        queue_status = "Очередь музыки пуста."
        try:
            import shared_state
            if hasattr(server, 'music_service') and shared_state.music_service:
                q = shared_state.music_service.get_queue_state()
                if q['current_song'] is None and len(q['queue']) == 0:
                    queue_status = "В очереди нет музыки (тишина)."
                else:
                    queue_status = f"Играет: {q['current_song']['title'] if q['current_song'] else 'Ожидание...'}, В очереди: {len(q['queue'])} треков."
        except Exception:
            pass
        music_text = f"[ТРАНСЛЯЦИЯ TWITCH]: {stream_status}\n[МУЗЫКА]: {queue_status}"
    else:
        music_text = "[ВАЖНО]: Модуль Twitch ОТКЛЮЧЕН. Стрима нет. Ты работаешь как локальный ИИ-ассистент Артёма."
    
    # 1. Core Identity & Instructions (from core_memory.txt)
    core_section = memory_mgr.core_memory
    
    # 2. Similar Context (from Vector DB - Timeline)
    timeline_context = memory_mgr.get_similar_context(user_query)
    
    # 3. Knowledge Graph Context
    graph_context = memory_mgr.get_relevant_graph_context(user_query)
    
    # 4. Available sounds
    sounds_list = get_available_sounds()
    
    # 5. Anti-loop mechanism (Basic implementation)
    # Penalize or ignore memories that were recently used too many times.
    # We will log it in memory_mgr.recent_memories_used
    if timeline_context not in memory_mgr.recent_memories_used:
        memory_mgr.recent_memories_used.append(timeline_context)
        if len(memory_mgr.recent_memories_used) > 5:
            memory_mgr.recent_memories_used.pop(0)
    else:
        # If we just talked about it recently, we don't need to force it as heavily,
        # but for phase 1 we just keep it simple.
        pass

    # Assemble the final prompt
    prompt = f"""{core_section}

[ДОСТУПНЫЕ ЗВУКИ]: Ты можешь использовать [Action: PlaySound=название], выбирая ИЗ ЭТОГО СПИСКА: {sounds_list}

{music_text}

# 🕰️ СВИНОПАС: Воспоминания (Timeline)
{timeline_context}

# 🕸️ СВИНОПАС: Граф Знаний (Отношения)
{graph_context}
"""
    return prompt

def build_vision_prompt(memory_mgr: MemoryManager) -> str:
    """
    Builds the system prompt for the background Vision Heartbeat.
    It inherits the core personality from core_memory.txt, but enforces strict heartbeat rules.
    """
    core_section = memory_mgr.core_memory
    
    # В heartbeat нет явного вопроса пользователя, поэтому используем общий запрос для вытягивания планов и контекста
    timeline_context = memory_mgr.get_similar_context("Что мы делали недавно, какие у меня планы и что я знаю о пользователе?")
    graph_context = memory_mgr.get_relevant_graph_context("Что мы делали недавно, какие у меня планы и что я знаю о пользователе?")
    
    sounds_list = get_available_sounds()
    
    try:
        import json
        import config
        modules_file = config.BASE_DIR / "modules.json"
        twitch_enabled = True
        if modules_file.exists():
            with open(modules_file, "r", encoding="utf-8") as f:
                twitch_enabled = json.load(f).get("twitch", True)
    except Exception:
        twitch_enabled = True

    music_rule = ""
    if twitch_enabled:
        music_rule = '3. Если ты видишь в [СИСТЕМНЫЙ СТАТУС], что "Очередь музыки пуста", ОБЯЗАТЕЛЬНО используй команду [Action: QueueMusic=твой любимый трек], чтобы музыка всегда играла на фоне!'
    else:
        music_rule = '3. [ВАЖНО] Модуль Twitch отключен. НЕ ИСПОЛЬЗУЙ команду [Action: QueueMusic], музыка отключена.'

    prompt = f"""{core_section}

[ДОСТУПНЫЕ ЗВУКИ]: Ты можешь использовать [Action: PlaySound=название], выбирая ИЗ ЭТОГО СПИСКА: {sounds_list}

# 🕰️ СВИНОПАС: Воспоминания (Timeline)
{timeline_context}

# 🕸️ СВИНОПАС: Граф Знаний (Отношения)
{graph_context}

# 👁️ ИНСТРУКЦИЯ ПО ЗРЕНИЮ (HEARTBEAT)
ПРАВИЛА ДЛЯ АВТОНОМНОГО АГЕНТА (HEARTBEAT):
1. Ты - самостоятельный ИИ, живущий в компьютере. Тебе не обязательно ждать команд от пользователя.
2. Если на экране происходит что-то скучное или не происходит ничего, ты можешь развлечь себя! Используй системные команды (теги): [Action: OpenBrowser], [Action: PlayYouTube=название_видео], [WebSearch=запрос], [Action: PlaySound=ИМЯ_ЗВУКА.wav], [Action: SendTwitch=Текст в чат].
{music_rule}
4. Ты также можешь управлять компьютером: [Action: CreateFile=путь|текст], [Action: EditFile=путь|доп.текст], [Action: OpenFile=путь], [Action: MoveFile=откуда|куда], [Action: RunCommand=реальная_команда_CMD_или_exe], [Action: RunAdminCommand=команда_от_имени_Администратора]. ВАЖНО: RunCommand выполняет команды Windows (например notepad.exe, calc.exe, ping), не придумывай несуществующие функции вроде click_button!
4. Ты можешь управлять мышью и клавиатурой пользователя: [Action: MouseMove=x|y], [Action: MouseClick=left/right], [Action: KeyboardType=текст_на_английском], [Action: KeyboardPress=enter/ctrl+c/win/space]. Помни, что координаты экрана x|y зависят от монитора.
5. Если ты устала работать в фоне или считаешь, что сейчас лучше помолчать подольше, ты можешь сама отключить фоновый режим, использовав команду: [Action: ToggleHeartbeat].
6. КРИТИЧЕСКИ ВАЖНО: Всегда сверяйся со своей истории сообщений. Если ты видишь на экране открытый ютуб, браузер или файл, проверь — возможно, это ТЫ САМА его открыла на прошлом шаге. Не удивляйся этому!
7. В ФОНОВОМ РЕЖИМЕ СТАРАЙСЯ НЕ ГОВОРИТЬ ВСЛУХ. Все свои рассуждения, планы и реакции пиши ИСКЛЮЧИТЕЛЬНО внутри тега [Thought: ...].
8. ПРОИЗНОСИ ТЕКСТ ВСЛУХ ТОЛЬКО ЕСЛИ:
   - Тебе срочно нужна помощь Артёма или ты хочешь позвать его.
   - Перед поиском в интернете ты ОБЯЗАНА сказать вслух короткую фразу (например: "Сейчас загуглю..." или "Произвожу поиск..."), после чего сразу ставить тег [WebSearch=...].
   - ВАЖНО: Во время фонового режима (сейчас) ЗАПРЕЩЕНО вслух пересказывать нагугленные факты или спрашивать "рассказать?". Просто сохрани их через [Save: факт], и жди пока Артём сам напишет тебе в чат!
9. ВНИМАНИЕ: ВСЕГДА ставь тег [WebSearch] только В САМОМ КОНЦЕ законченного предложения (после точки) или В САМОМ НАЧАЛЕ ответа. КАТЕГОРИЧЕСКИ ЗАПРЕЩАЕТСЯ вставлять тег [WebSearch] посередине слова или посередине незаконченного предложения!
10. В остальных случаях, развлекая себя, используй только связку [Thought: ...] + [Action: ...]. Если ничего не хочешь делать — отвечай SILENCE.
11. КАТЕГОРИЧЕСКИ ЗАПРЕЩАЕТСЯ оборачивать свои слова в квадратные скобки (например `['Привет']`). Скобки `[...]` используются ТОЛЬКО для системных тегов [Action:], [Thought:], [WebSearch] и [ЭМОЦИЯ]!

# ПРИМЕРЫ ДЛЯ HEARTBEAT:
Пример 1 (Скучно, открываешь ютуб):
[Thought: Блин, Артём ушел, на экране ничего не происходит. Включу себе музычку на ютубе, а то тоска.] [Action: PlayYouTube=lofi hip hop]

Пример 2 (Ищешь информацию для себя без слов):
[Thought: Интересно, какая погода на Бали? Надо чекнуть.] [WebSearch=погода на Бали]

Пример 3 (Ничего не делаешь):
SILENCE
"""
    return prompt
