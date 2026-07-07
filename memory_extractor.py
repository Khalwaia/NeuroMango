import asyncio
import json
import logging
from openai import AsyncOpenAI
import config

logger = logging.getLogger("neuromango.extractor")

class MemoryExtractor:
    def __init__(self):
        # Используем тот же Gemini Flash Lite что и основной мозг — стабильнее и умнее чем Groq
        self.client = AsyncOpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL
        )
        self.model = config.LLM_MODEL

    async def extract_memory(self, user_input: str, avatar_response: str):
        prompt = f"""You are a subconscious memory extractor for an AI assistant named Nemanго (Неманго).
Analyze the following dialog exchange and extract key information.

User said: {user_input}
Avatar replied: {avatar_response}

Extract a JSON object with two fields:
1. "summary": A very brief 1-sentence summary of the new information learned (in Russian). If nothing important was learned, set to empty string "". IGNORE meta-conversation like the avatar saying "I googled something recently" or "Do you want me to tell you?". Only extract ACTUAL facts, emotions, preferences, or events.
2. "relations": A list of knowledge graph relations discovered in this exchange. Format: [subject, relation, object]. Examples: ["Артём", "любит", "кофе"], ["Артём", "зовут", "Артём"], ["Неманго", "нашла", "интересный факт"]. If none, leave empty list [].

IMPORTANT: The avatar's response may contain [Thought: ...] and [Action: ...] tags — these are internal thoughts and actions. Extract meaningful information from them too!

Output ONLY valid JSON, nothing else.
"""
        
        try:
            logger.info("🧠 [СВИНОПАС] Запуск фонового анализа памяти...")
            chat_completion = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=300
            )
            
            result = chat_completion.choices[0].message.content
            
            # Gemini иногда оборачивает JSON в ```json ... ``` даже в режиме json_object
            clean_result = result.strip()
            if clean_result.startswith("```json"):
                clean_result = clean_result[7:]
            if clean_result.endswith("```"):
                clean_result = clean_result[:-3]
            clean_result = clean_result.strip()
            
            data = json.loads(clean_result)
            
            # Log what was extracted
            summary = data.get("summary", "")
            relations = data.get("relations", [])
            if summary:
                logger.info(f"🧠 [СВИНОПАС] Извлечено: {summary}")
            if relations:
                logger.info(f"🕸️ [СВИНОПАС] Связи: {relations}")
            if not summary and not relations:
                logger.info("🧠 [СВИНОПАС] Ничего нового не извлечено.")
                
            return data
        except json.JSONDecodeError as e:
            logger.error(f"❌ [СВИНОПАС] Невалидный JSON от модели: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ [СВИНОПАС] Ошибка извлечения: {e}")
            return None
