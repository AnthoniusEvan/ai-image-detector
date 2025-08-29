import requests
import time
from concurrent.futures import ThreadPoolExecutor

URL = "http://ec2-3-104-78-136.ap-southeast-2.compute.amazonaws.com:8080/detect"
IMAGE_PATH = "img.png" 
CONCURRENT = 10          # number of simultaneous requests
TOTAL_REQUESTS = 10     # how many total requests to send

def send_request(i):
    with open(IMAGE_PATH, "rb") as f:
        files = {"file": (IMAGE_PATH, f, "image/jpeg")}
        try:
            resp = requests.post(URL, files=files, timeout=30)
            print(f"[{i}] {resp.status_code} -> {resp.text[:80]}...")
        except Exception as e:
            print(f"[{i}] Error: {e}")

start = time.time()
with ThreadPoolExecutor(max_workers=CONCURRENT) as executor:
    executor.map(send_request, range(TOTAL_REQUESTS))

print(f"Completed {TOTAL_REQUESTS} requests in {time.time()-start:.2f} seconds")
