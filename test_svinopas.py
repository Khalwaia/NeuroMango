import asyncio
import logging
from memory_extractor import MemoryExtractor
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

async def run():
    load_dotenv()
    m = MemoryExtractor()
    res = await m.extract_memory('Привет, я люблю бананы', 'Отлично! [Thought: надо запомнить что он любит бананы]')
    print(res)

if __name__ == "__main__":
    asyncio.run(run())
