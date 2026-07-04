import asyncio
import logging
import requests
from twitchio.ext import commands
import config
from urllib.parse import quote

logger = logging.getLogger("neuromango.twitch")

class TwitchService(commands.Bot):
    def __init__(self, callback):
        # We start the bot only if token is provided and not the default
        if config.TWITCH_TOKEN.strip() and "ВАШ_ТОКЕН" not in config.TWITCH_TOKEN:
            super().__init__(token=config.TWITCH_TOKEN.strip(), prefix='!', initial_channels=[config.TWITCH_CHANNEL])
            self.message_callback = callback
            self.bot_name = config.TWITCH_BOT_NAME.lower()
        else:
            self.message_callback = None
            logger.warning("⚠️ Twitch token not configured. Chat integration disabled.")
            
    async def event_ready(self):
        logger.info(f"🎮 Twitch Bot Ready! Logged in as | {self.nick}")
        logger.info(f"🎮 Connected to channel | {config.TWITCH_CHANNEL}")

    async def event_message(self, message):
        # Ignore our own messages
        if message.echo:
            return

        # Check if the AI was mentioned
        content = message.content.lower()
        if self.bot_name in content or f"@{self.nick.lower()}" in content:
            user = message.author.name
            logger.info(f"💬 Twitch Mention from {user}: {message.content}")
            
            if self.message_callback:
                # Fire the callback with user and message
                await self.message_callback(user, message.content)
                
    async def stop(self):
        """Stops the Twitch bot."""
        logger.info("🛑 Stopping Twitch Bot...")
        try:
            await self.close()
        except Exception as e:
            logger.error(f"Error closing Twitch bot: {e}")
                
    async def send_chat_message(self, text: str):
        """Sends a message to the Twitch channel."""
        try:
            channel = self.get_channel(config.TWITCH_CHANNEL)
            if channel:
                # Add the prefix requested by the user
                await channel.send(f"НеМанго: {text}")
                logger.info(f"✉️ Sent to Twitch: НеМанго: {text}")
            else:
                logger.error("Twitch channel not joined yet.")
        except Exception as e:
            logger.error(f"Failed to send message to Twitch: {e}")

import time
_uptime_cache = {"time": 0, "status": "Стрим сейчас оффлайн"}

def get_stream_uptime() -> str:
    """Uses decapi.me to get stream uptime without needing complex OAuth tokens."""
    global _uptime_cache
    if getattr(config, 'FORCE_STREAM_ONLINE', False):
        return "Стрим идет уже: 1 hour, 30 minutes (РЕЖИМ ТЕСТА)"
        
    if not config.TWITCH_CHANNEL or "имя_вашего" in config.TWITCH_CHANNEL:
        return "Неизвестно (канал не настроен)"
        
    now = time.time()
    if now - _uptime_cache["time"] < 30:
        return _uptime_cache["status"]
        
    try:
        url = f"https://decapi.me/twitch/uptime/{quote(config.TWITCH_CHANNEL)}"
        res = requests.get(url, timeout=5)
        text = res.text.strip()
        if "offline" in text.lower():
            _uptime_cache["status"] = "Стрим сейчас оффлайн"
        elif "error" in text.lower() or "not found" in text.lower():
            _uptime_cache["status"] = "Не удалось получить статус стрима"
        else:
            _uptime_cache["status"] = f"Стрим идет уже: {text}"
    except Exception as e:
        logger.error(f"Failed to fetch stream uptime: {e}")
        _uptime_cache["status"] = "Ошибка проверки статуса стрима"
        
    _uptime_cache["time"] = now
    return _uptime_cache["status"]
