import re
import logging
import asyncio
from openai import AsyncOpenAI
import config
from memory_manager import MemoryManager
from prompt_builder import build_system_prompt, build_vision_prompt
from memory_extractor import MemoryExtractor
from action_handler import execute_action
from search_tool import perform_search

logger = logging.getLogger("neuromango.llm")

class LLMEngine:
    def __init__(self, memory_manager: MemoryManager, vision_manager=None):
        self.memory = memory_manager
        self.vision = vision_manager
        self.extractor = MemoryExtractor()
        self.client = AsyncOpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL
        )

    async def check_heartbeat(self, frame_base64: str, heartbeat_context: str = "") -> str:
        sys_prompt = build_vision_prompt(self.memory, vision_context=self.vision.get_scene_context() if self.vision else "")
        
        messages = [{"role": "system", "content": sys_prompt}]
        
        # Обязательно передаем историю, чтобы она помнила, что уже говорила!
        history = self.memory.get_history()
        # Берем только последние 10 сообщений, чтобы не перегружать контекст
        messages.extend(history[-10:])
        
        # Сбор системного контекста для "осознания"
        import datetime
        from twitch_service import get_stream_uptime
        current_time = datetime.datetime.now().strftime("%H:%M")
        active_window = "Неизвестно"
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win:
                active_window = win.title
        except Exception:
            pass
            
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
            
        queue_status = "Очередь музыки пуста."
        if twitch_enabled:
            stream_status = get_stream_uptime()
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
                
            sys_status = f"\n[СИСТЕМНЫЙ СТАТУС]: Время - {current_time}. Активное окно на ПК Артёма - '{active_window}'.\n[ТРАНСЛЯЦИЯ TWITCH]: {stream_status}\n[МУЗЫКА]: {queue_status}"
        else:
            sys_status = f"\n[СИСТЕМНЫЙ СТАТУС]: Время - {current_time}. Активное окно на ПК Артёма - '{active_window}'.\n[ВАЖНО]: Модуль Twitch ОТКЛЮЧЕН. Стрима нет, зрителей нет. Ты работаешь как локальный ИИ-ассистент. Не пытайся включать музыку (она отключена)."
        
        # Inject subconscious context if provided
        subconscious_block = ""
        if heartbeat_context:
            subconscious_block = f"\n{heartbeat_context}\n[Инструкция подсознания]: Ты наедине со своими мыслями. Проанализируй контекст выше. Можешь: вспомнить что-то и подумать, погуглить интересное, поставить музыку, использовать звуки, или промолчать (SILENCE). Используй [Thought:] для размышлений. Говори вслух ТОЛЬКО если хочешь позвать Артёма или сообщить что-то срочное."
        
        if frame_base64:
            messages.append({
                "role": "user", 
                "content": [
                    {"type": "text", "text": f"[СИСТЕМНОЕ СООБЩЕНИЕ]: Вот текущий кадр с экрана/камеры пользователя. Ты работаешь в фоновом режиме.{sys_status}{subconscious_block}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_base64}"}}
                ]
            })
        else:
            messages.append({
                "role": "user",
                "content": f"[СИСТЕМНОЕ СООБЩЕНИЕ]: (Экран не виден). Ты работаешь в фоновом режиме. Хочешь ли ты сделать какое-то действие, поразмыслить или сказать что-то? Если нет, просто ответь SILENCE.{sys_status}{subconscious_block}"
            })
        
        try:
            response = await self.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            content = response.choices[0].message.content
            
            # Check for WebSearch tags
            search_matches = re.findall(r'\[WebSearch=(.*?)\]', content, re.IGNORECASE)
            if search_matches:
                query = search_matches[0].strip()
                logger.info(f"🔍 Heartbeat: Выполняю невидимый поиск: {query}")
                search_results = await asyncio.to_thread(perform_search, query)
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "system", "content": search_results})
                
                # Ask LLM again with search results
                response2 = await self.client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2048
                )
                content = content + "\n" + response2.choices[0].message.content
                
            if content and content.strip() != "SILENCE" and "SILENCE" not in content:
                # 1. Parse and execute Actions
                action_matches = re.findall(r'\[Action:\s*(.*?)\]', content, re.IGNORECASE)
                for action_cmd in action_matches:
                    from action_handler import execute_action
                    execute_action(action_cmd)
                    
                # 2. Add to history so she remembers her spontaneous thought/action
                self.memory.add_to_history("assistant", content.strip())
                
            return content
        except Exception as e:
            logger.error(f"Heartbeat Error: {e}")
            return "SILENCE"
        
    async def _run_svinopas_background(self, user_text: str, avatar_response: str):
        """Runs the SVINOPAS extraction in the background without blocking the TTS or chat."""
        try:
            data = await self.extractor.extract_memory(user_text, avatar_response)
            if data:
                self.memory.process_extracted_memory(data)
        except Exception as e:
            logger.error(f"SVINOPAS Background Task Failed: {e}")

    async def generate_response_stream(self, user_text: str, sender_name: str = "Артём", sender_role: str = "developer"):
        """
        Streams response from the LLM, yields (chunk_text, anim_trigger, is_final).
        Handles memory saving in the background and recursive WebSearch calls.
        """
        # Get vision context (textual scene descriptions)
        vision_ctx = ""
        if self.vision and self.vision.mode != "off":
            vision_ctx = self.vision.get_scene_context()
        
        system_prompt = build_system_prompt(self.memory, user_text, vision_context=vision_ctx)
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.memory.get_history())
        
        # Оборачиваем сообщение в теги ролей
        tagged_user_text = f"[Сообщение от: {sender_name} (Роль: {sender_role})]: {user_text}"
        messages.append({"role": "user", "content": tagged_user_text})
        
        full_reply = ""
        raw_reply = ""
        async for chunk, raw_chunk, anim_trigger, is_final in self._generate_internal(messages, user_text):
            full_reply += chunk
            raw_reply += raw_chunk
            yield chunk, anim_trigger, is_final
            
        # Post-process Memory Saves (Manual overrides from old system, still supported)
        save_matches = re.finditer(r'\[Save:\s*(.*?)\]', raw_reply, re.IGNORECASE)
        for match in save_matches:
            memory_fact = match.group(1).strip()
            self.memory.save_memory(memory_fact)
            
        # Update history with RAW text so she remembers her Thoughts and Actions!
        self.memory.add_to_history("user", tagged_user_text)
        self.memory.add_to_history("assistant", raw_reply.strip())
        
        # 🚀 Запуск СВИНОПАС в фоне (отдаем СЫРОЙ текст, включая мысли и действия)
        asyncio.create_task(self._run_svinopas_background(tagged_user_text, raw_reply.strip()))

    async def _generate_internal(self, messages: list, user_text: str):
        try:
            response = await self.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                temperature=0.6,
                max_tokens=2048,
                stream=True
            )
        except Exception as e:
            logger.error(f"LLM API Error: {e}")
            yield f"Ошибка: {e}", f"Ошибка: {e}", "Idle", True
            return

        buffer = ""
        raw_buffer = ""
        anim_trigger = ""
        # Умный паттерн: не разбиваем на предложения после 1- или 2-буквенных слов (рт., ст., А., ул.)
        sentence_endings = re.compile(r'(?<!\b[А-Яа-яЁё])(?<!\b[А-Яа-яЁё]{2})(?<!\b\d)([.!?]+[»"”’\']*(?:\s+|\n\n+|$))')
        
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                buffer += text
                raw_buffer += text
                
                # Parse Thought tags
                thought_matches = re.findall(r'\[Thought:\s*(.*?)\]', buffer, re.IGNORECASE)
                for thought_text in thought_matches:
                    logger.info("💭 Нейрона думает: %s", thought_text)
                    buffer = re.sub(r'\[Thought:\s*' + re.escape(thought_text) + r'\]', '', buffer, count=1, flags=re.IGNORECASE | re.DOTALL)
                
                # Parse Animation tags dynamically
                anim_matches = re.findall(r'\[([a-zA-Z0-9_]+)\]', buffer)
                for tag in anim_matches:
                    lower_tag = tag.lower()
                    if lower_tag != 'save' and not lower_tag.startswith('action') and not lower_tag.startswith('websearch'):
                        anim_trigger = tag
                        buffer = re.sub(r'\[' + re.escape(tag) + r'\]', '', buffer, count=1, flags=re.IGNORECASE | re.DOTALL)
                        
                # Parse Action tags
                action_matches = re.findall(r'\[Action:\s*(.*?)\]', buffer, re.IGNORECASE)
                for action_cmd in action_matches:
                    execute_action(action_cmd)
                    buffer = re.sub(r'\[Action:\s*' + re.escape(action_cmd) + r'\]', '', buffer, count=1, flags=re.IGNORECASE | re.DOTALL)
                    
                # Remove Save tags from buffer during stream so they don't break incomplete tag check
                save_matches = re.findall(r'\[Save:\s*(.*?)\]', buffer, re.IGNORECASE)
                for save_fact in save_matches:
                    buffer = re.sub(r'\[Save:\s*' + re.escape(save_fact) + r'\]', '', buffer, count=1, flags=re.IGNORECASE | re.DOTALL)
                    
                # Parse WebSearch tags (Two-Way Function Calling)
                search_matches = re.findall(r'\[WebSearch=(.*?)\]', buffer, re.IGNORECASE)
                if search_matches:
                    query = search_matches[0].strip()
                    logger.info(f"🔍 Перехватил тег поиска! Ищу: {query}")
                    
                    # 1. Выводим фразу-заполнитель, чтобы скрыть задержку
                    clean_buffer = re.sub(r'\[(?!КРИК|СМЕХ|ГРУСТЬ|SAD|LAUGH|SCREAM|SIGH).*?\]', '', buffer, flags=re.IGNORECASE | re.DOTALL).strip()
                    if clean_buffer:
                        yield clean_buffer, raw_buffer, anim_trigger, False
                        raw_buffer = ""
                        anim_trigger = "Think"
                        yield "", "", "Think", False # Переключаем анимацию в Think
                        
                    # 2. Выполняем поиск
                    search_results = await asyncio.to_thread(perform_search, query)
                    
                    # 3. Обновляем контекст
                    if clean_buffer:
                        messages.append({"role": "assistant", "content": clean_buffer})
                    messages.append({"role": "system", "content": search_results})
                    
                    # 4. Прерываем текущий стрим и запускаем новый рекурсивно!
                    try:
                        await response.close()
                    except Exception:
                        pass
                        
                    async for c, rc, a, f in self._generate_internal(messages, user_text):
                        yield c, rc, a, f
                        
                    return # Полностью выходим из текущего генератора
                
                # Если ИИ прямо сейчас печатает тег (есть открывающая скобка, но нет закрывающей),
                # мы ждем и не отправляем незаконченный тег в TTS!
                if '[' in buffer and ']' not in buffer:
                    continue
                
                # Начинаем цикл, чтобы вытащить все предложения из буфера, если их пришло сразу несколько
                while True:
                    clean_buffer = re.sub(r'\[(?!КРИК|СМЕХ|ГРУСТЬ|SAD|LAUGH|SCREAM|SIGH).*?\]', '', buffer, flags=re.IGNORECASE | re.DOTALL)
                    match = sentence_endings.search(clean_buffer)
                    
                    if not match and len(clean_buffer) > 250:
                        # Ищем запятую только во второй половине длинного предложения (после 150 символов)
                        emergency_endings = re.compile(r'^.{150,}?([,;]\s)')
                        match = emergency_endings.search(clean_buffer)
                        
                    if not match:
                        break
                        
                    end_pos = match.end()
                    sentence = clean_buffer[:end_pos].strip()
                    if sentence:
                        yield sentence, raw_buffer, anim_trigger, False
                        raw_buffer = ""
                        anim_trigger = "" # Reset animation
                    buffer = re.sub(r'\[(?!КРИК|СМЕХ|ГРУСТЬ|SAD|LAUGH|SCREAM|SIGH).*?\]', '', buffer, flags=re.IGNORECASE | re.DOTALL)[end_pos:].lstrip()

        # Yield any remaining text
        remaining = re.sub(r'\[(?!КРИК|СМЕХ|ГРУСТЬ|SAD|LAUGH|SCREAM|SIGH).*?\]', '', buffer, flags=re.IGNORECASE | re.DOTALL).strip()
        if remaining or raw_buffer:
            yield remaining, raw_buffer, anim_trigger, True
            
        else:
            yield "", "", "", True
