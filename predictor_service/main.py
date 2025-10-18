from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from app.aws_related.memcached import predict_image  # reuse your existing logic
import httpx, os

load_dotenv()

IMAGE_PROCESSING_URL = os.environ.get("PREDICTOR_URL", "http://localhost:8001/preprocess-image/upload")

app = FastAPI(
    title="AI Image Detector - Predictor Service",
    description="Handles CPU-intensive image predictions",
    version="1.0.0"
)

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        if not file:
            raise HTTPException(status_code=400, detail="No file uploaded")

        if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
            raise HTTPException(status_code=400, detail="Invalid image format. Only PNG/JPEG allowed.")

        data = await file.read()
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")

        # Preprocess image
        async with httpx.AsyncClient() as client:
            files = {"file": (file.filename, data, file.content_type)}
            response = await client.post(IMAGE_PROCESSING_URL, files=files)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        result = response.json()
        tensor = result['tensor']

        # Perform prediction (CPU intensive)
        label, confidence = predict_image(tensor)

        return JSONResponse({
            "prediction": label,
            "confidence": confidence
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

@app.get("/health")
def health():
    return {"ok": True}
