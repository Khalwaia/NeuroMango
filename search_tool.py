import logging
from duckduckgo_search import DDGS

logger = logging.getLogger("neuromango.search")

def perform_search(query: str, max_results: int = 3) -> str:
    """Performs a web search and returns a formatted string of results."""
    logger.info(f"🔎 Ищу в DuckDuckGo: '{query}'")
    try:
        # Use backend='lite' to avoid Bing timeouts
        results = DDGS().text(query, max_results=max_results, region='ru-ru', backend='lite')
        if not results:
            return "Поиск не дал результатов."
            
        import re
        formatted_results = "Вот что удалось найти в интернете (коротко перескажи это на русском, БЕЗ ССЫЛОК):\n\n"
        for i, res in enumerate(results):
            body = res.get('body', '')
            body = re.sub(r'https?://\S+', '', body) # Убираем ссылки
            formatted_results += f"[{i+1}] {res.get('title', '')}\n{body}\n\n"
            
        return formatted_results.strip()
    except Exception as e:
        logger.error(f"❌ Ошибка поиска: {e}")
        return f"Не удалось выполнить поиск из-за ошибки: {str(e)}"
