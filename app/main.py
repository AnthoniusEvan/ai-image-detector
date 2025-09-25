# app/main.py
from io import BytesIO
import os
import random
import json
import urllib.request
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Depends, Cookie, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from urllib.parse import urlparse
from pydantic import BaseModel
from api.controllers import set_user_prediction
from app.aws_related.memcached import predict_image
from schemas import DetectionResponse
from api.models import *
from aws_related import s3
import os
import urllib.request
import json
from PIL import Image
from aws.cognito.signUp import signup
from aws.cognito.confirm import confirm
from dotenv import load_dotenv

load_dotenv()
COGNITO_CLIENT_ID = os.environ['AWS_COGNITO_CLIENT_ID']
COGNITO_CLIENT_SECRET = os.environ['AWS_COGNITO_CLIENT_SECRET']

from app.api.controllers import set_user_prediction
from app.aws_related import dynamo, s3
from app.aws_related.secret import get_jwt_secret
from app.utils import preprocess_image
from app.model import detector
from app.schemas import DetectionResponse

app = FastAPI(
    title="AI Image Detector",
    description="API for detecting if an image is real or AI-generated ",
    version="0.0.1",
)

SECRET_KEY = get_jwt_secret()
app.secret_key = SECRET_KEY
print("[config] JWT secret loaded from Secrets Manager")

try:
    dynamo.ensure_all()
    dynamo.bootstrap_default_users()
    print("[config] Dynamo tables ensured; default users bootstrapped")
except Exception as e:
    print((f"[warn] bootstrap failed: {e}"))

_base_dir = os.path.dirname(os.path.abspath(__file__))
_candidate_in_app = os.path.join(_base_dir, "public")
_candidate_root = os.path.normpath(os.path.join(_base_dir, "..", "public"))
directory_path = _candidate_in_app if os.path.isdir(_candidate_in_app) else _candidate_root
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
oauth = OAuth()

oauth.register(
  name='oidc',
  client_id=COGNITO_CLIENT_ID,
  client_secret=COGNITO_CLIENT_SECRET,
  server_metadata_url='https://cognito-idp.ap-southeast-2.amazonaws.com/ap-southeast-2_OJJPCGF1d/.well-known/openid-configuration',
  client_kwargs={'scope': 'email openid profile'}
)

app.mount("/public", StaticFiles(directory=directory_path), name="public")
templates = Jinja2Templates(directory=directory_path)

def authenticate_token(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

def browser_auth(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=307, detail="Redirect", headers={"Location": "/login"})
    return user

def is_user_admin(user):
    groups = user.get("cognito:groups", [])
    return "Admin" in groups

class FeedbackRequest(BaseModel):
    image_id: str
    model_prediction: str
    user_agrees: bool


@app.post("/user/set_feedback")
async def set_user_feedback(feedback: FeedbackRequest, user=Depends(authenticate_token)):
    try:
        return set_user_prediction(feedback.image_id, feedback.model_prediction, feedback.user_agrees)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/detect")
async def detect_page(user=Depends(browser_auth)):
    return FileResponse(os.path.join(directory_path, "index.html"))


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

        label, confidence = predict_image(file_content)

        image_id = dynamo.images_insert(file.filename, "", user["sub"], label, confidence).get("id")
        s3_key = s3.put_image_to_s3(file.filename, image_id, file_content)
        dynamo.images_update_s3_key(image_id, s3_key)

        return RedirectResponse(url=f"/result/{image_id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect-image", response_model=DetectionResponse)
async def detect_image_simple(request: Request, file: UploadFile = File(...)):
    try:
        if not file:
            raise HTTPException(status_code=401, detail="No image file attached")
        content_type = file.content_type
        if content_type not in ["image/png", "image/jpeg", "image/jpg"]:
            raise HTTPException(status_code=400, detail="Invalid image format. Only PNG/JPEG allowed.")
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB).")

        label, confidence = predict_image(file_content)
        return DetectionResponse(prediction=label, confidence=confidence)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def extract_s3_key(s3_url: str) -> str:
    return urlparse(s3_url).path.lstrip("/")


@app.get("/result/{image_id}", response_class=HTMLResponse)
async def result_page(image_id: str, request: Request, user=Depends(browser_auth)):
    image_data = dynamo.images_get_by_id(image_id)
    if not image_data:
        raise HTTPException(status_code=404, detail="Image not found")
    s3_key = image_data["s3_key"]
    presigned_url = s3.get_image_from_s3_presigned_url(s3_key)
    if not presigned_url:
        raise HTTPException(status_code=404, detail="Image not found")
    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "image_id": image_id,
            "image_url": presigned_url,
            "prediction": image_data["prediction"],
            "confidence": image_data["confidence"],
            "user_prediction": image_data.get("user_prediction"),
        },
    )

PUBLIC_DOMAIN = "https://ai-image-detector.cab432.com"
@app.get("/login")
async def login(request: Request):
    redirect_uri = f"{PUBLIC_DOMAIN}/authorize"
    return await oauth.oidc.authorize_redirect(request, redirect_uri)

@app.get("/authorize")
async def authorize(request: Request):
    token = await oauth.oidc.authorize_access_token(request) 
    user = token['userinfo']

    insert_user(user.get('sub'), user.get('cognito:username'), 0)
    request.session['user'] = user 
    return RedirectResponse(url="/")

@app.get("/logout")
async def logout(request: Request):
    request.session.pop('user', None)
    base_url = str(request.base_url) + "index"
    cognito_logout_url = (
        f"https://ap-southeast-2ojjpcgf1d.auth.ap-southeast-2.amazoncognito.com/logout"
        f"?client_id={COGNITO_CLIENT_ID}"
        f"&logout_uri={base_url}"
    )
    return RedirectResponse(url=cognito_logout_url)


@app.get('/')
async def main_page(request: Request):
    user = request.session.get('user')
    print(user)
    if user:
        return FileResponse(os.path.join(directory_path, 'index.html'))
    else:
        return RedirectResponse(url="/login")
    

@app.get('/index')
async def index_page(request: Request):
    user = request.session.get('user')
    if user:
        return FileResponse(os.path.join(directory_path, 'index.html'))
    else:
        return HTMLResponse("<h2>AI Image Detector</h2><p>To use this service please <a href='/login'>login</a></p><a href='/signup'>Sign up</a>")
    

@app.get('/signup')
async def index_page(request: Request):
    return FileResponse(os.path.join(directory_path, 'signUp.html'))
    
@app.post('/signup')
async def sign_up(request: Request):
    data = await request.json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
   
    try:
        result = signup(username, password, email)
        return {"detail": "Sign up successful. Please check your email for the confirmation code."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

 
@app.post('/confirm')
async def sign_up(request: Request):
    data = await request.json()
    username = data.get('username')
    code = data.get('code')
    try:
        result = confirm(username, code)
        return {"detail": "Confirmation successful. You can now log in."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    


@app.get("/")
async def main_page():
    return FileResponse(os.path.join(directory_path, "index.html"))


@app.get("/admin")
async def admin_page(user=Depends(browser_auth)):
    is_admin = is_user_admin(user)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Unauthorised user requested admin content.")
    return FileResponse(os.path.join(directory_path, "admin.html"))


@app.get("/admin/uploads")
async def admin_uploads(
    user=Depends(browser_auth),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("uploaded_at"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    username: str | None = None,
    prediction: str | None = None,
):
    is_admin = is_user_admin(user)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Unauthorised user requested admin content.")
    allowed_sort_fields = ["uploaded_at", "id", "filename", "prediction", "image_id"]
    if sort_by not in allowed_sort_fields:
        raise HTTPException(status_code=400, detail="Invalid sort field")

    images = dynamo.images_list(limit, offset, sort_by, order, username, prediction)
    for img in images:
        img["image_url"] = s3.get_image_from_s3_presigned_url(img["s3_key"])
        uid = img.get("user_id")
        img["username"] = dynamo.users_get_username_by_id(uid) if uid else None
    return images


@app.get("/game/image")
def get_game_image(user=Depends(browser_auth)):
    sources = [("https://thispersondoesnotexist.com", "ai"), ("https://randomuser.me/api/?inc=picture", "real")]
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
    response.headers["user_id"] = str(user["cognito:username"])
    response.headers["answer"] = answer
    return response


@app.get("/game")
async def game_page(user=Depends(browser_auth)):
    return FileResponse(os.path.join(directory_path, "game.html"))


@app.post("/user/save_accuracy")
async def save_accuracy(request: Request, user=Depends(browser_auth)):
    data = await request.json()
    accuracy = float(data.get("accuracy", 0))
    try:
        result = dynamo.put_accuracy(user["sub"], accuracy)
        return {"status": "updated" if result.get("updated") else "error"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DynamoDB error: {e}")


@app.get("/logout")
async def logout():
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie(key="authToken", path="/")
    return response
