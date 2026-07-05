import os
import sys
import json
import asyncio
import traceback
import json
import asyncio
from pathlib import Path

# Добавляем корневую папку в путь, чтобы импортировать config
sys.path.append(str(Path(__file__).resolve().parent.parent))
import config
from openai import AsyncOpenAI

async def generate_dataset(num_batches=5, pairs_per_batch=10):
    """
    Генерирует синтетический датасет для обучения LoRA.
    """
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        
    print("🤖 Инициализация генератора датасета...")
    
    # Читаем характер
    core_memory_path = config.BASE_DIR / "core_memory.txt"
    if not core_memory_path.exists():
        print(f"❌ Файл {core_memory_path} не найден!")
        return
        
    with open(core_memory_path, "r", encoding="utf-8") as f:
        persona = f.read().strip()
        
    client = AsyncOpenAI(
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL
    )
    
    dataset_file = "dataset.jsonl"
    print(f"📝 Будет сгенерировано {num_batches * pairs_per_batch} примеров. Сохранение в {dataset_file}")
    
    # Сценарии для разнообразия
    scenarios = [
        "Зритель задает тупой вопрос про игры.",
        "Пользователь Артём опять ковыряется в коде и игнорирует стрим.",
        "Кто-то задонатил 500 рублей с просьбой включить странную песню.",
        "Зритель спрашивает совета по жизни.",
        "Зритель критикует внешность или голос аватара.",
        "Кто-то пишет в чат бессмысленный спам.",
        "Вопрос про популярность и ТикТок.",
        "Артём открыл IDE, и Неманго комментирует это в своих мыслях."
    ]

    total_generated = 0
    with open(dataset_file, "w", encoding="utf-8") as f:
        for i in range(num_batches):
            scenario = scenarios[i % len(scenarios)]
            print(f"⏳ Генерация батча {i+1}/{num_batches} (Сценарий: {scenario})...")
            
            prompt = f"""You are a dataset generator for fine-tuning an AI persona.
Here is the strict persona instruction for "NeuroMango":
<persona>
{persona}
</persona>

Your task is to generate {pairs_per_batch} realistic conversational exchanges between a user and NeuroMango, fitting the scenario: "{scenario}".
The assistant's response MUST STRICTLY follow the persona rules (including [Thought: ...], emotion tags like [Annoyed], and appropriate slang/toxicity).

Output the result as a raw JSON array of objects. Do not include markdown blocks (```json).
Format:
[
    {{"instruction": "user's message or action", "output": "assistant's exact response with all tags"}},
    ...
]
"""
            try:
                response = await client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.9
                )
                
                content = response.choices[0].message.content.strip()
                # Удаляем маркдаун если ИИ его все же добавил
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                
                pairs = json.loads(content)
                for pair in pairs:
                    if "instruction" in pair and "output" in pair:
                        # Записываем в формате JSONL (Alpaca format)
                        json_line = json.dumps({
                            "instruction": pair["instruction"],
                            "input": "",
                            "output": pair["output"]
                        }, ensure_ascii=False)
                        f.write(json_line + "\n")
                        total_generated += 1
                        
            except Exception as e:
                print(f"❌ Ошибка генерации батча {i+1}: {e}")
                traceback.print_exc()
                
    print(f"✅ Готово! Успешно сгенерировано {total_generated} пар для обучения. Файл: {dataset_file}")

if __name__ == "__main__":
    asyncio.run(generate_dataset())
