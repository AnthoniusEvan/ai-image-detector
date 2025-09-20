# app/tools/check_cloud.py
import os
import json
import boto3
from botocore.exceptions import ClientError

# Use your app helpers so we test the same code paths
from app.aws_related.secret import get_jwt_secret
from app.aws_related.s3 import _get_model_key  # private helper, fine for diagnostics

REGION = os.getenv("AWS_REGION", "ap-southeast-2")
SSM_NAME = os.getenv("SSM_PARAM_MODEL_KEY")              # e.g. /n11671025/aipic/model_key
SM_NAME = os.getenv("SM_SECRET_APP_NAME") or os.getenv("JWT_SECRET_NAME")

def main():
    report = {
        "region": REGION,
        "ssm_param": SSM_NAME,
        "secret_name": SM_NAME,
    }

    # --- SSM Parameter Store check ---
    if SSM_NAME:
        ssm = boto3.client("ssm", region_name=REGION)
        try:
            resp = ssm.get_parameter(Name=SSM_NAME, WithDecryption=False)
            val = resp["Parameter"]["Value"]
            report["ssm_status"] = "ok"
            report["ssm_value_preview"] = (val[:60] + "…") if len(val) > 60 else val
        except ClientError as e:
            report["ssm_status"] = f"error: {e.response['Error'].get('Code','ClientError')}"
    else:
        report["ssm_status"] = "no SSM_PARAM_MODEL_KEY set"

    # What your app would actually use for the model key (SSM or env fallback)
    try:
        report["s3_model_key_effective"] = _get_model_key()
    except Exception as e:
        report["s3_model_key_effective"] = f"error: {e}"

    # --- Secrets Manager check (raw) ---
    if SM_NAME:
        sm = boto3.client("secretsmanager", region_name=REGION)
        try:
            resp = sm.get_secret_value(SecretId=SM_NAME)
            s = resp.get("SecretString") or ""
            # Don’t print the whole secret; just show a preview
            report["sm_status"] = "ok"
            report["sm_value_preview"] = (s[:60] + "…") if len(s) > 60 else s
        except ClientError as e:
            report["sm_status"] = f"error: {e.response['Error'].get('Code','ClientError')}"
    else:
        report["sm_status"] = "no SM secret name set"

    # --- Your app helper: get_jwt_secret() ---
    # NOTE: If APP_SECRET is set in env, your web app won’t call Secrets Manager at startup.
    # This call tests the SM path directly, regardless of APP_SECRET.
    try:
        sec = get_jwt_secret()
        report["app_get_jwt_secret"] = "ok"
        report["app_jwt_preview"] = (sec[:10] + "…") if isinstance(sec, str) else "non-string"
    except Exception as e:
        report["app_get_jwt_secret"] = f"error: {e}"

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()