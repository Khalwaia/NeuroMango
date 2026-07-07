import logging
import yt_dlp
import asyncio
import threading

logger = logging.getLogger("neuromango.music")

class MusicService:
    def __init__(self, on_queue_update_callback=None):
        self.queue = []
        self.current_song = None
        self.on_queue_update = on_queue_update_callback
        
        # Configure yt-dlp to just extract metadata quickly without downloading video
        self.ytdl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'extract_flat': 'in_playlist' 
        }

    def _search_youtube(self, query: str):
        """Synchronous youtube search via yt-dlp"""
        try:
            with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                # Search for the query and get the first result
                search_query = f"ytsearch1:{query}"
                info = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info and len(info['entries']) > 0:
                    entry = info['entries'][0]
                    return {
                        'id': entry.get('id'),
                        'title': entry.get('title'),
                        'thumbnail': entry.get('thumbnail', f"https://img.youtube.com/vi/{entry.get('id')}/hqdefault.jpg")
                    }
        except Exception as e:
            logger.error(f"Error searching YouTube for '{query}': {e}")
        return None

    async def add_to_queue(self, query: str, requester: str = "НеМанго"):
        """Asynchronously searches and adds a song to the queue."""
        logger.info(f"🎵 Searching YouTube for: {query}")
        # Run the blocking yt-dlp network request in a background thread
        result = await asyncio.to_thread(self._search_youtube, query)
        
        if result:
            result['requested_by'] = requester
            self.queue.append(result)
            logger.info(f"✅ Added to queue: {result['title']}")
            
            # If nothing is playing, auto-play immediately by popping the queue
            if self.current_song is None and len(self.queue) > 0:
                self.current_song = self.queue.pop(0)

            if self.on_queue_update:
                await self.on_queue_update()
            return True
        else:
            logger.warning(f"❌ Could not find song: {query}")
            return False

    def get_queue_state(self):
        """Returns the current state of the queue for the frontend widget."""
        return {
            'current_song': self.current_song,
            'queue': self.queue
        }

    async def pop_next(self):
        """Removes and returns the next song from the queue. Sets it as current."""
        if len(self.queue) > 0:
            self.current_song = self.queue.pop(0)
        else:
            self.current_song = None
            
        if self.on_queue_update:
            await self.on_queue_update()
            
        return self.current_song
    
    def skip_current(self):
        # We don't actually pop here, we just tell the frontend to skip
        # The frontend will then ask for `pop_next`
        pass
