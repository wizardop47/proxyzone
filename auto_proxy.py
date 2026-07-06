import asyncio
from proxybroker import Broker
import urllib.request
import urllib.error
import time
import json
import concurrent.futures
import sys

# Kitni proxies aapko chahiye
TARGET_PROXIES = int(sys.argv[1]) if len(sys.argv) > 1 else 50
OUTPUT_FILE = "valid_proxies.txt"

def test_proxy(proxy_str):
    """
    Ek individual proxy ko test karta hai taaki 100% sure ho sakein
    ki yeh abhi chal rahi hai ya nahi.
    """
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

async def fetch_and_test_proxies():
    proxies = asyncio.Queue()
    broker = Broker(proxies)
    
    print(f"[*] Starting Auto-Proxy Fetcher...")
    print(f"[*] Target: {TARGET_PROXIES} 100% Valid Proxies")
    
    # Background me proxybroker proxies dhundhna shuru karega
    fetch_task = asyncio.create_task(broker.find(types=['HTTP', 'HTTPS'], limit=500))
    
    valid_count = 0
    
    # Purani file clear kar rahe hain
    with open(OUTPUT_FILE, "w") as f:
        f.write("")
        
    print(f"[*] Fetching & Testing Live...\n")
    
    with open(OUTPUT_FILE, "a") as f, concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        while valid_count < TARGET_PROXIES:
            proxy = await proxies.get()
            if proxy is None:
                print("All sources exhausted, no more proxies found.")
                break
            
            proxy_str = f"{proxy.host}:{proxy.port}"
            
            # Proxy ko background Thread me real-time test karein
            future = executor.submit(test_proxy, proxy_str)
            is_valid, ip_port = future.result() # Wait for test result
            
            if is_valid:
                valid_count += 1
                print(f"[ALIVE & ADDED] {ip_port} ({valid_count}/{TARGET_PROXIES})")
                f.write(f"{ip_port}\n")
                f.flush()
            else:
                print(f"[DEAD - DROPPED] {ip_port}")
                
    # Force cancel the fetcher when we have enough proxies
    fetch_task.cancel()
    print("\n" + "="*50)
    print(f"SUCCESS! {valid_count} working proxies saved to '{OUTPUT_FILE}'")
    print("="*50)

if __name__ == "__main__":
    # Windows me Asyncio Loop ka issue fix karne ke liye
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(fetch_and_test_proxies())
    except KeyboardInterrupt:
        print("\nProcess stopped by user.")
