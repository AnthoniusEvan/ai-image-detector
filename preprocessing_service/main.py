from fastapi import FastAPI, UploadFile, HTTPException
from PIL import Image
import io
import torch
from torchvision import transforms

app = FastAPI(title="Image Preprocessing Microservice")

preprocess_transform = transforms.Compose([
    transforms.Resize((448, 448)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

def preprocess_image_bytes(image_bytes: bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = preprocess_transform(image).unsqueeze(0) 
    return tensor

def serialize_tensor(tensor: torch.Tensor):
    return tensor.tolist()

@app.post("/upload")
async def preprocess_upload(file: UploadFile):
    try:
        contents = await file.read()
        tensor = preprocess_image_bytes(contents)
        return {"tensor": serialize_tensor(tensor)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process image: {e}")

@app.get("/health")
def health():
    return {"ok": True}