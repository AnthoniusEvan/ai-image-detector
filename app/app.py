# app.py

from io import BytesIO
import random
from fastapi import FastAPI, File, Response, UploadFile, HTTPException, Request, Depends, Cookie, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from urllib.parse import urlparse
from pydantic import BaseModel
from api.controllers import set_user_prediction
from utils import preprocess_image
from model import detector
from schemas import DetectionResponse
from api.models import *
from aws import s3
from aws import dynamo
import jwt
import datetime
import os
from datetime import timezone
import urllib.request
import json
from PIL import Image

app = FastAPI(
    title="AI Image Detector",
    description="API for detecting if an image is real or AI-generated ",
    version="0.0.1",
)
app.secret_key = 'e9aae26be08551392be664d620fb422350a30349899fc254a0f37bfa1b945e36ff20d25b12025e1067f9b69e8b8f2ef0f767f6fff6279e5755668bf4bae88588'

try:
    dynamo.ensure_table()
except Exception as e:
    print(f"[warn] DynamoDB ensure_table failed: {e}")

directory_path = os.path.join(os.path.dirname(__file__), 'public')
app.mount("/public", StaticFiles(directory=directory_path), name="public")
templates = Jinja2Templates(directory=directory_path)

def generate_access_token(id, username):
    payload = {
        'id': id,
        'username': username,
        'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(minutes=30)
    }
    token = jwt.encode(payload, app.secret_key, algorithm='HS256')
    return token

def browser_auth(authToken: str | None = Cookie(default=None)):
    if not authToken:
        raise HTTPException(
            status_code=307,
            detail="Redirect",
            headers={"Location": "/login"}
        )
    try:
        user = jwt.decode(authToken, app.secret_key, algorithms=["HS256"])
        return user
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=307,
            detail="Redirect",
            headers={"Location": "/login"}
        )

def authenticate_token(authToken: str | None = Cookie(default=None)):
    if not authToken:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        user = jwt.decode(authToken, app.secret_key, algorithms=["HS256"])
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.post('/login')
async def login(request: Request):
    data = await request.json()
    username = data.get('username')
    password = data.get('password')
    user_id = get_user(username, password)
    if not user_id:
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    token = generate_access_token(user_id, username)
    response = JSONResponse(content={"message": "Logged in"})
    response.set_cookie(
        key="authToken",
        value=token,
        httponly=True,
        max_age=1800,
        samesite="lax"
    )
    return response

class FeedbackRequest(BaseModel):
    image_id: int
    model_prediction: str
    user_agrees: bool

@app.post('/user/set_feedback')
async def set_user_feedback(feedback: FeedbackRequest, user=Depends(authenticate_token)):
    try:
        return set_user_prediction(feedback.image_id, feedback.model_prediction, feedback.user_agrees)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/detect")
async def detect_image(user=Depends(browser_auth)):
    return FileResponse(os.path.join(directory_path, 'index.html'))

@app.post("/detect", response_model=DetectionResponse)
async def detect_image(request: Request, user=Depends(authenticate_token), file: UploadFile = File(...)):
    try:
        if not file:
            raise HTTPException(status_code=401, detail="No image file attached")
        content_type = file.content_type
        if content_type not in ["image/png", "image/jpeg", "image/jpg"]:
            raise HTTPException(status_code=400, detail="Invalid image format. Only PNG/JPEG allowed.")
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB).")
        tensor = preprocess_image(file_content)
        label, confidence = detector.predict(tensor)
        image_id = insert_image(file.filename, "", user['id'], label, confidence).get('id')
        s3_key = s3.put_image_to_s3(file.filename, image_id, file_content)
        update_image_s3_key(image_id, s3_key)
        referer = request.headers.get("Referer", "")
        main_page_url = request.url_for("main_page")
        if referer.startswith(str(main_page_url)):
            return RedirectResponse(url=f"/result/{image_id}", status_code=303)
        return DetectionResponse(prediction=label, confidence=confidence)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/detect-image", response_model=DetectionResponse)
async def detect_image(request: Request, file: UploadFile = File(...)):
    try:
        if not file:
            raise HTTPException(status_code=401, detail="No image file attached")
        content_type = file.content_type
        if content_type not in ["image/png", "image/jpeg", "image/jpg"]:
            raise HTTPException(status_code=400, detail="Invalid image format. Only PNG/JPEG allowed.")
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB).")
        tensor = preprocess_image(file_content)
        label, confidence = detector.predict(tensor)
        return DetectionResponse(prediction=label, confidence=confidence)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def extract_s3_key(s3_url: str) -> str:
    return urlparse(s3_url).path.lstrip('/')

@app.get('/result/{image_id}', response_class=HTMLResponse)
async def result_page(image_id: int, request: Request, user=Depends(browser_auth)):
    image_data = get_image_by_id(image_id)
    s3_key = image_data['s3_key']
    presigned_url = s3.get_image_from_s3_presigned_url(s3_key)
    if not presigned_url:
        raise HTTPException(status_code=404, detail="Image not found")
    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "image_id": image_id,
            "image_url": presigned_url,
            "prediction": image_data['prediction'],
            "confidence": image_data['confidence'],
            "user_prediction": image_data['user_prediction']
        }
    )

@app.get('/login')
async def login_page():
    return FileResponse(os.path.join(directory_path, 'login.html'))

@app.get('/')
async def main_page(user=Depends(browser_auth)):
    return FileResponse(os.path.join(directory_path, 'index.html'))

@app.get('/admin')
async def admin_page(user=Depends(browser_auth)):
    is_admin = is_user_admin(user['id'])
    if not is_admin:
        raise HTTPException(status_code=403, detail='Unauthorised user requested admin content.')
    return FileResponse(os.path.join(directory_path, 'admin.html'))

@app.get('/admin/uploads')
async def admin_uploads(
    user=Depends(browser_auth),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("uploaded_at"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    username: str | None = None,
    prediction: str | None = None
):
    is_admin = is_user_admin(user['id'])
    if not is_admin:
        raise HTTPException(status_code=403, detail='Unauthorised user requested admin content.')
    allowed_sort_fields = ["uploaded_at", "id", "filename", "prediction"]
    if sort_by not in allowed_sort_fields:
        raise HTTPException(status_code=400, detail="Invalid sort field")
    images = get_uploaded_images_adv(limit, offset, sort_by, order, username, prediction)
    for img in images:
        img['image_url'] = s3.get_image_from_s3_presigned_url(img['s3_key'])
        img['username'] = get_username(img['user_id'])
    return images

@app.get("/game/image")
def get_game_image(user=Depends(browser_auth)):
    sources = [
        ("https://thispersondoesnotexist.com", "ai"),
        ("https://randomuser.me/api/?inc=picture", "real")
    ]
    url, answer = random.choice(sources)
    if answer == "real":
        with urllib.request.urlopen(url) as res:
            data = json.loads(res.read().decode())
            image_url = data["results"][0]["picture"]["large"]
            with urllib.request.urlopen(image_url) as img_res:
                data = img_res.read()
    else:
        with urllib.request.urlopen(url) as res:
            data = res.read()
    img = Image.open(BytesIO(data)).convert("RGB")
    img = img.resize((200, 200))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    response = StreamingResponse(buf, media_type="image/jpeg")
    response.headers["user_id"] = str(user["id"])
    response.headers["answer"] = answer
    return response

@app.get('/game')
async def main_page(user=Depends(browser_auth)):
    return FileResponse(os.path.join(directory_path, 'game.html'))

@app.post('/user/save_accuracy')
async def save_accuracy(request: Request, user=Depends(browser_auth)):
    data = await request.json()
    accuracy = float(data.get('accuracy', 0))
    try:
        result = dynamo.put_accuracy(user['id'], accuracy)
        return {"status": "updated" if result.get("updated") else "error"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DynamoDB error: {e}")

@app.get("/logout")
async def logout():
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie(key="authToken", path="/")
    return response