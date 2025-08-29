from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
from api.models import *
from aws.s3 import delete_image_from_s3

router = APIRouter()


def get_images():
  try:
    return JSONResponse(content=get_uploaded_images())
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


async def create_user(request: Request):
  data = await request.json()
  username = data.get("username")
  if not username:
    raise HTTPException(status_code=400, detail="Username is required")
  try:
    is_admin = data.get("is_admin")
    return insert_user(username, 0 if not is_admin else is_admin)
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


async def upload_image(request: Request):
  data = await request.json()
  filename = data.get("filename")
  s3_url = data.get("s3_url")
  username = data.get("username")
  prediction = data.get("prediction")
  confidence = data.get("confidence")

  if not username and not filename and not s3_url:
    raise HTTPException(status_code=400, detail="Username, filename, and s3_url is required")
  try:
    return insert_image(filename, s3_url, username, prediction, confidence)
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


def delete_image(image_id: int):
  try:
    result = delete_image(image_id)
    if not result.get("deleted"):
      raise HTTPException(status_code=404, detail="Image not found")
    
    delete_image_from_s3()
    return {"message": "Image deleted"}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
  
def set_user_prediction(image_id: int, model_prediction: str, user_agrees: bool):
  try:
    if (user_agrees):
      user_prediction = model_prediction
    else:
      if (model_prediction == "Real"):
        user_prediction = "AI-generated"
      else:
        user_prediction = "Real"

    result = update_user_prediction(image_id, user_prediction)
    if not result.get("updated"):
      raise HTTPException(status_code=404, detail="Image not found")
    return {"status":"success", "message": "User prediction updated"}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
  
    
def set_high_score(user_id: int, high_score: int):
  try:
    result = update_high_score(user_id, high_score)
    if not result.get("updated"):
      raise HTTPException(status_code=404, detail="User not found")
    return {"status":"success", "message": "User high score updated"}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))