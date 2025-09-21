import hashlib
from pymemcache.client.base import Client
from utils import preprocess_image
from model import detector

cache = Client('ai-image-detector-memcache.km2jzi.cfg.apse2.cache.amazonaws.com:11211')

def get_image_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()

def predict_image(image_bytes: bytes):
    image_hash = get_image_hash(image_bytes)

    cached_result = cache.get(image_hash)
    if cached_result:
        label, confidence = cached_result.decode().split("|")
        return label, float(confidence)
    
    tensor = preprocess_image(image_bytes)
    label, confidence = detector.predict(tensor)
    cache.set(image_hash, f"{label}|{confidence}", expire=86400)

    return label, confidence
