import os
import boto3
import torch
import io
from dotenv import load_dotenv

load_dotenv()

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    aws_session_token=os.environ["AWS_SESSION_TOKEN"],
    region_name=os.environ["AWS_REGION"]
)
REGION_NAME = os.environ["AWS_REGION"]
BUCKET_NAME = os.environ["AWS_S3_BUCKET"]

def getS3Key(filename:str, image_id):
    _, ext = os.path.splitext(filename)
    s3_key = f"images/{os.path.splitext(filename)[0]}-{image_id}{ext}"
    return s3_key

def put_image_to_s3(filename:str, image_id, file_content):
    s3_key = getS3Key(filename, image_id)
    s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_content)
    return s3_key


def delete_image_from_s3(filename: str, image_id):
    try:
        s3_key = getS3Key(filename, image_id)
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
        return {"message": f"{filename} deleted successfully from S3"}
    except Exception as e:
        return {"error": str(e)}

def get_image_from_s3_presigned_url(s3_key: str):
    try:
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=3600 
        )
        return presigned_url  
    except Exception as e:
        return None
    

MODEL_KEY = "model/model.pth"
LOCAL_MODEL_PATH = "/tmp/model.pth"


def download_model_from_s3():
    if not os.path.exists(LOCAL_MODEL_PATH):
        print(f"Downloading {MODEL_KEY} from S3...")
        s3_client.download_file(BUCKET_NAME, MODEL_KEY, LOCAL_MODEL_PATH)
    else:
        print("Model already cached locally.")
    return LOCAL_MODEL_PATH

def load_model():
    path = download_model_from_s3()
    model = torch.load(path, map_location="cpu")
    print("Model loaded successfully.")
    return model