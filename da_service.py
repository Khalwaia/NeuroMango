import asyncio
import logging
import socketio

logger = logging.getLogger("neuromango.da")

class DonationAlertsService:
    def __init__(self, token: str, min_amount: float, on_donation_callback):
        self.token = token
        self.min_amount = min_amount
        self.on_donation = on_donation_callback
        
        # Disable SSL verification due to DA's expired cert on their legacy socket server
        self.sio = socketio.AsyncClient(ssl_verify=False)
        self.server_url = "wss://socket.donationalerts.ru:443"

        @self.sio.event
        async def connect():
            logger.info("✅ DA WebSocket (Socket.IO) connected!")
            await self.sio.emit('add-user', {"token": self.token, "type": "minor"})

        @self.sio.event
        async def donation(data):
            try:
                # data is usually a JSON string in DA's socket
                import json
                if isinstance(data, str):
                    data = json.loads(data)
                    
                amount = float(data.get("amount", 0))
                currency = data.get("currency", "RUB")
                username = data.get("username", "Аноним")
                message = data.get("message", "")
                
                logger.info(f"💸 DONATION: {username} - {amount} {currency} - {message}")
                
                if amount >= self.min_amount:
                    if self.on_donation:
                        await self.on_donation(username, amount, currency, message)
            except Exception as e:
                logger.error(f"Error parsing DA donation: {e}")

        @self.sio.event
        async def disconnect():
            logger.warning("🔌 DA WebSocket disconnected.")
            
    async def stop(self):
        """Disconnects from DonationAlerts."""
        logger.info("🛑 Stopping DonationAlerts Service...")
        try:
            await self.sio.disconnect()
        except Exception as e:
            logger.error(f"Error stopping DA: {e}")

    async def start(self):
        logger.info("🔗 Connecting to DonationAlerts Socket.IO...")
        while True:
            try:
                await self.sio.connect(self.server_url, transports='websocket')
                await self.sio.wait()
            except Exception as e:
                logger.error(f"❌ DA WebSocket error: {e}")
                await asyncio.sleep(5)
