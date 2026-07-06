import sys
import time
import urllib.request
import urllib.error
import json

def check_proxy(proxy_ip_port):
    print(f"Checking proxy: {proxy_ip_port} ...")
    
    # Proxy handler setup
    proxy_handler = urllib.request.ProxyHandler({
        'http': f'http://{proxy_ip_port}',
        'https': f'http://{proxy_ip_port}'
    })
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)
    
    start_time = time.time()
    try:
        # Requesting a URL to test
        req = urllib.request.Request("http://httpbin.org/ip")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            response_time = round(time.time() - start_time, 2)
            
            print(f"✅ Proxy is VALID and ALIVE! (Response time: {response_time}s)")
            print(f"Proxy Details: {data}")
    except urllib.error.URLError as e:
        print(f"❌ Proxy is DEAD or Invalid (Error: {e.reason})")
    except Exception as e:
        print(f"❌ Proxy is DEAD or Invalid (Error: {e})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_my_proxy.py <IP:PORT>")
        print("Example: python check_my_proxy.py 104.194.148.204:80")
    else:
        check_proxy(sys.argv[1])
