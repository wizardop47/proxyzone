import asyncio
import concurrent.futures
import time
import urllib.request
import os
import sys
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from proxybroker import Broker
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

# Config from .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
if ADMIN_CHAT_ID:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)

# Global variables
VALID_PROXIES = []
MAX_PROXIES = 20
IS_FETCHING = True  # Controlled by Telegram Bot

app = FastAPI(title="Live Proxy Generator API")

# Setup Telegram Bot (only if token is provided)
if BOT_TOKEN:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
else:
    bot = None
    dp = None

def test_proxy(proxy_str):
    """Test if a proxy is alive by requesting httpbin.org"""
    proxy_handler = urllib.request.ProxyHandler({
        'http': f'http://{proxy_str}',
        'https': f'http://{proxy_str}'
    })
    opener = urllib.request.build_opener(proxy_handler)
    
    try:
        req = urllib.request.Request("http://httpbin.org/ip")
        with opener.open(req, timeout=5) as response:
            if response.status == 200:
                return True, proxy_str
    except Exception:
        pass
    
    return False, proxy_str

async def proxy_fetcher_worker():
    """Background task to fetch and check proxies continuously."""
    global VALID_PROXIES, IS_FETCHING
    
    proxies_queue = asyncio.Queue()
    broker = Broker(proxies_queue)
    
    while True:
        if not IS_FETCHING:
            await asyncio.sleep(5)
            continue
            
        print("Starting new fetch cycle...")
        fetch_task = asyncio.create_task(broker.find(types=['HTTP', 'HTTPS'], limit=0))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            while IS_FETCHING:
                try:
                    # using wait_for so we can occasionally check IS_FETCHING status
                    proxy = await asyncio.wait_for(proxies_queue.get(), timeout=10.0)
                except asyncio.TimeoutError:
                    if fetch_task.done():
                        # sources exhausted
                        break
                    continue
                
                if proxy is None:
                    break
                
                proxy_str = f"{proxy.host}:{proxy.port}"
                
                future = executor.submit(test_proxy, proxy_str)
                is_valid, ip_port = future.result()
                
                if is_valid:
                    if ip_port not in VALID_PROXIES:
                        VALID_PROXIES.append(ip_port)
                    
                    if len(VALID_PROXIES) > MAX_PROXIES:
                        VALID_PROXIES.pop(0)
                        
        fetch_task.cancel()
        if IS_FETCHING:
            print("Proxy sources exhausted. Restarting fetcher in 30 seconds...")
            await asyncio.sleep(30)
        else:
            print("Fetcher stopped by Telegram Bot.")

@app.on_event("startup")
async def startup_event():
    """Start the background proxy fetcher and telegram bot when the server starts."""
    asyncio.create_task(proxy_fetcher_worker())
    
    if bot and dp:
        # Register bot handlers
        @dp.message(Command("start"))
        async def cmd_start(message: Message):
            global IS_FETCHING
            if ADMIN_CHAT_ID and message.chat.id != ADMIN_CHAT_ID:
                await message.answer("You are not authorized.")
                return
                
            IS_FETCHING = True
            await message.answer("✅ Proxy fetcher STARTED.")
            
        @dp.message(Command("stop"))
        async def cmd_stop(message: Message):
            global IS_FETCHING
            if ADMIN_CHAT_ID and message.chat.id != ADMIN_CHAT_ID:
                await message.answer("You are not authorized.")
                return
                
            IS_FETCHING = False
            await message.answer("🛑 Proxy fetcher STOPPED.")
            
        @dp.message(Command("status"))
        async def cmd_status(message: Message):
            status = "RUNNING" if IS_FETCHING else "STOPPED"
            await message.answer(f"Status: {status}\nValid Proxies in Queue: {len(VALID_PROXIES)}")
        
        print("Starting Telegram Bot Polling...")
        asyncio.create_task(dp.start_polling(bot))

@app.get("/")
def get_proxies_json():
    """Returns a simple JSON object for bots."""
    return {
        "proxies": VALID_PROXIES
    }

@app.get("/raw")
def get_proxies_raw():
    """Returns plain text (one proxy per line)."""
    return PlainTextResponse("\n".join(VALID_PROXIES))

if __name__ == "__main__":
    import uvicorn
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
