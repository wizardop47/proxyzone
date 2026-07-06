import asyncio
import concurrent.futures
import time
import urllib.request
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from proxybroker import Broker
import sys

app = FastAPI(title="Live Proxy Generator API")

# Global variables
VALID_PROXIES = []
MAX_PROXIES = 20

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
    global VALID_PROXIES
    
    proxies_queue = asyncio.Queue()
    broker = Broker(proxies_queue)
    
    # We run an infinite loop where we restart the broker whenever it runs out of sources
    while True:
        # Start the broker in the background
        fetch_task = asyncio.create_task(broker.find(types=['HTTP', 'HTTPS'], limit=0)) # limit=0 means fetch infinite until sources dry up
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            while True:
                proxy = await proxies_queue.get()
                if proxy is None:
                    # Sources exhausted, break the inner loop and restart the fetcher
                    break
                
                proxy_str = f"{proxy.host}:{proxy.port}"
                
                # Test proxy
                future = executor.submit(test_proxy, proxy_str)
                is_valid, ip_port = future.result()
                
                if is_valid:
                    # Append new proxy
                    if ip_port not in VALID_PROXIES:
                        VALID_PROXIES.append(ip_port)
                    
                    # Ensure max 20 length (delete oldest if limit reached)
                    if len(VALID_PROXIES) > MAX_PROXIES:
                        VALID_PROXIES.pop(0)
                        
        fetch_task.cancel()
        print("Proxy sources exhausted. Restarting fetcher in 60 seconds...")
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    """Start the background proxy fetcher when the server starts."""
    asyncio.create_task(proxy_fetcher_worker())

@app.get("/")
def get_proxies_json():
    """Returns a simple JSON array or object for bots."""
    # Ek simple format jo maximum bots support karte hain
    return {
        "proxies": VALID_PROXIES
    }

@app.get("/raw")
def get_proxies_raw():
    """Returns plain text (one proxy per line). Bots love this format!"""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("\n".join(VALID_PROXIES))

if __name__ == "__main__":
    import uvicorn
    # Required for Windows if running locally
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
