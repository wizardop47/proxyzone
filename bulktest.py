import urllib.request
import urllib.error
import time
import re
import json
import concurrent.futures

def check_proxy(proxy_ip_port):
    proxy_handler = urllib.request.ProxyHandler({
        'http': f'http://{proxy_ip_port}',
        'https': f'http://{proxy_ip_port}'
    })
    opener = urllib.request.build_opener(proxy_handler)
    
    start_time = time.time()
    try:
        req = urllib.request.Request("http://httpbin.org/ip")
        with opener.open(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            response_time = round(time.time() - start_time, 2)
            return True, proxy_ip_port, response_time, data
    except Exception as e:
        return False, proxy_ip_port, 0, str(e)

def main():
    file_path = "proxies.txt"
    proxy_list = []
    
    # Parse the proxies.txt file
    try:
        with open(file_path, "r") as f:
            for line in f:
                # Example line: <Proxy US 0.00s [] 38.7.195.53:999>
                match = re.search(r'\] ([0-9\.]+:[0-9]+)>', line)
                if match:
                    proxy_list.append(match.group(1))
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return

    print(f"Found {len(proxy_list)} proxies in {file_path}. Testing them now...\n")
    
    working_proxies = []
    
    # Check concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(check_proxy, proxy_list)
        
        for success, ip_port, resp_time, data in results:
            if success:
                print(f"[ALIVE] {ip_port} (Time: {resp_time}s)")
                working_proxies.append(ip_port)
            else:
                print(f"[DEAD]  {ip_port}")

    print("\n" + "="*40)
    print(f"Test Complete! {len(working_proxies)}/{len(proxy_list)} proxies are working.")
    print("="*40)

if __name__ == "__main__":
    main()
