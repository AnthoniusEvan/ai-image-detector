import hashlib
from pymemcache.client.base import Client
from utils import preprocess_image
from model import detector

try:
    cache = Client(('ai-image-detector-memcache.km2jzi.cfg.apse2.cache.amazonaws.com',11211),connect_timeout=1,timeout=1)
    print("memcache success to initialize")
except Exception as e:
    print("memcache failed to initialize")
    cache = None

def get_image_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def predict_image(image_bytes: bytes):
    image_hash = get_image_hash(image_bytes)
    label, confidence = None, None
    if cache:
        try:
            cached_result = cache.get(image_hash)
            if cached_result:

                print('Found cache')    
                label, confidence = cached_result.decode().split("|")
                return label, float(confidence)
        except Exception:
            pass
        
    tensor = preprocess_image(image_bytes)
    label, confidence = detector.predict(tensor)
    if cache:
        try:
            print('setting cache')
            cache.set(image_hash, f"{label}|{confidence}", expire=86400)
        except Exception:
            pass

    return label, confidence