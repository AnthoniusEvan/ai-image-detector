import os
import json
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")
SM_SECRET_APP_NAME = os.getenv("SM_SECRET_APP_NAME")

_session = boto3.session.Session(region_name=AWS_REGION)
_secrets = _session.client("secretsmanager")

def get_jwt_secret() -> str:
    if not SM_SECRET_APP_NAME:
        raise RuntimeError("SM_SECRET_APP_NAME not set in environment")
    try:
        resp = _secrets.get_secret_value(SecretId=SM_SECRET_APP_NAME)
        secret_str = resp.get("SecretString")
        if not secret_str:
            secret_str = resp.get("SecretBinary", b"").decode("utf-8", errors="ignore")
            
        try:
            data = json.loads(secret_str)
            sec = data.get("jwt_secret")
            if sec:
                return sec
        except Exception:
            pass

        if not secret_str:
            raise RuntimeError("SecretString empty")
        return secret_str
    except ClientError as e:
        raise RuntimeError(f"Failed to load JWT secret from Secrets Manager: {e}")