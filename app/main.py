from fastapi import FastAPI, File, UploadFile, HTTPException
from app.utils import preprocess_image
from app.model import detector
from app.schemas import DetectionResponse

app = FastAPI(title="AI Image Detector")

@app.post("/detect", response_model=DetectionResponse)
async def detect_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        tensor = preprocess_image(image_bytes)
        label, confidence = detector.predict(tensor)
        return DetectionResponse(prediction=label, confidence=confidence)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
      <head>
        <title>AI Image Detector</title>
      </head>
      <body>
        <h2>Upload an image to detect AI-generated or Real</h2>
        <form action="/detect" enctype="multipart/form-data" method="post">
          <input name="file" type="file" accept="image/*" required>
          <input type="submit" value="Detect">
        </form>
      </body>
    </html>
    """