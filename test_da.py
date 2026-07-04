import asyncio
import socketio
import json

TOKEN = "WD7WKvBg1w894ib8Skkz"
sio = socketio.AsyncClient()

@sio.event
async def connect():
    print("Connected to DA!")
    await sio.emit('add-user', {"token": TOKEN, "type": "minor"})

@sio.event
async def donation(data):
    print("Donation!", data)
    
async def main():
    import ssl
    import aiohttp
    
    # Create an unverified SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    http_session = aiohttp.ClientSession(connector=connector)
    
    sio.http = http_session
    await sio.connect('wss://socket.donationalerts.ru:443', transports='websocket')
    print("Listening for 10 seconds...")
    await asyncio.sleep(10)
    await sio.disconnect()

if __name__ == "__main__":
    asyncio.run(main())

