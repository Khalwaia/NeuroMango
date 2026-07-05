import asyncio
import json
import logging
from openai import AsyncOpenAI
import config

logger = logging.getLogger("neuromango.extractor")

class MemoryExtractor:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=config.GROQ_API_KEY,
            base_url=config.GROQ_BASE_URL
        )
        self.model = config.GROQ_MODEL

    async def extract_memory(self, user_input: str, avatar_response: str):
        prompt = f"""You are a subconscious memory extractor for an AI assistant.
Analyze the following dialog exchange and extract key information.

User said: {user_input}
Avatar replied: {avatar_response}

Extract a JSON object with two fields:
1. "summary": A very brief 1-sentence summary of the new information learned. If nothing important was learned, leave empty. IGNORE meta-conversation like the avatar saying "I googled something recently" or "Do you want me to tell you?". Only extract ACTUAL facts.
2. "relations": A list of knowledge graph relations discovered in this exchange. Format: [subject, relation, object]. Example: ["User", "likes", "coffee"], ["User", "name is", "Artem"]. If none, leave empty list.

Output ONLY valid JSON.
"""
        
        try:
            logger.info("🧠 [СВИНОПАС] Запуск фонового анализа памяти...")
            chat_completion = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            result = chat_completion.choices[0].message.content
            data = json.loads(result)
            return data
        except Exception as e:
            logger.error(f"❌ [СВИНОПАС] Ошибка извлечения: {e}")
            return None
