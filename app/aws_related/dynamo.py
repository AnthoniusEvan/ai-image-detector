

import os
import uuid
import time
import hashlib
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError



AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")
USERS_TABLE = os.getenv("DDB_TABLE_USERS", "ai_image_users")
IMAGES_TABLE = os.getenv("DDB_TABLE_IMAGES", "ai_image_images")
ACCURACY_TABLE = os.getenv("DDB_TABLE_ACCURACY", "ai_image_accuracy")


_session = boto3.session.Session(region_name=AWS_REGION)
_dynamodb = _session.resource("dynamodb")
_client = _session.client("dynamodb")


dynamo = _dynamodb

def _tbl(name: str):
    return _dynamodb.Table(name)


def _exists(name: str) -> bool:
    try:
        _client.describe_table(TableName=name)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("ResourceNotFoundException", "ValidationException"):
            return False
        raise


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


# --- Provisioning / bootstrap -------------------------------------------------

def ensure_all():
    if not _exists(USERS_TABLE):
        _client.create_table(
            TableName=USERS_TABLE,
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "username", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "username-index",
                    "KeySchema": [{"AttributeName": "username", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
                }
            ],
            BillingMode="PROVISIONED",
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )
        _tbl(USERS_TABLE).wait_until_exists()

    if not _exists(IMAGES_TABLE):
        _client.create_table(
            TableName=IMAGES_TABLE,
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            BillingMode="PROVISIONED",
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )
        _tbl(IMAGES_TABLE).wait_until_exists()

    if not _exists(ACCURACY_TABLE):
        _client.create_table(
            TableName=ACCURACY_TABLE,
            AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            BillingMode="PROVISIONED",
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )
        _tbl(ACCURACY_TABLE).wait_until_exists()


def bootstrap_default_users():
    try:
        if users_get_id_by_credentials("admin", "password") is None:
            users_insert("admin", 1, default_password="password")
        if users_get_id_by_credentials("user", "password") is None:
            users_insert("user", 0, default_password="password")
    except Exception:

        pass

def users_insert(username: str, is_admin: int, default_password: str = "password"):
    t = _tbl(USERS_TABLE)
    existing = _query_user_by_username(username)
    if existing:
        return {"id": existing["id"], "username": existing["username"], "is_admin": existing.get("is_admin", 0)}

    uid = str(uuid.uuid4())
    item = {
        "id": uid,
        "username": username,
        "password_hash": _hash(default_password),
        "is_admin": int(bool(is_admin)),
        "created_at": _now_iso(),
    }
    t.put_item(Item=item, ConditionExpression="attribute_not_exists(id)")
    return {"id": uid, "username": username, "is_admin": int(bool(is_admin))}


def users_get_id_by_credentials(username: str, password: str):
    u = _query_user_by_username(username)
    if not u:
        return None
    if u.get("password_hash") != _hash(password):
        return None
    return u["id"]


def users_get_username_by_id(user_id: str):
    t = _tbl(USERS_TABLE)
    res = t.get_item(Key={"id": user_id})
    return res.get("Item", {}).get("username")


def users_is_admin(user_id: str) -> bool:
    t = _tbl(USERS_TABLE)
    res = t.get_item(Key={"id": user_id})
    return bool(res.get("Item", {}).get("is_admin", 0))


def _query_user_by_username(username: str):
    t = _tbl(USERS_TABLE)
    res = t.query(
        IndexName="username-index",
        KeyConditionExpression=boto3.dynamodb.conditions.Key("username").eq(username),
    )
    items = res.get("Items", [])
    return items[0] if items else None


# --- Images -------------------------------------------------------------------

def images_insert(filename: str, s3_key: str, user_id: str, prediction: str, confidence: float):
    t = _tbl(IMAGES_TABLE)
    image_id = str(uuid.uuid4())
    item = {
        "id": image_id,
        "filename": filename or "",
        "s3_key": s3_key or "",
        "user_id": user_id,
        "prediction": prediction,
        "confidence": float(confidence) if confidence is not None else None,
        "user_prediction": None,
        "uploaded_at": _now_iso(),
    }
    t.put_item(Item=item, ConditionExpression="attribute_not_exists(id)")
    return {"id": image_id}


def images_update_user_prediction(image_id: str, prediction: str):
    t = _tbl(IMAGES_TABLE)
    res = t.update_item(
        Key={"id": image_id},
        UpdateExpression="SET user_prediction = :p",
        ExpressionAttributeValues={":p": prediction},
        ConditionExpression="attribute_exists(id)",
        ReturnValues="UPDATED_NEW",
    )
    return {"updated": "Attributes" in res}


def images_update_s3_key(image_id: str, s3_key: str):
    t = _tbl(IMAGES_TABLE)
    res = t.update_item(
        Key={"id": image_id},
        UpdateExpression="SET s3_key = :k",
        ExpressionAttributeValues={":k": s3_key},
        ConditionExpression="attribute_exists(id)",
        ReturnValues="UPDATED_NEW",
    )
    return {"updated": "Attributes" in res}


def images_get_by_id(image_id: str):
    t = _tbl(IMAGES_TABLE)
    res = t.get_item(Key={"id": image_id})
    return res.get("Item")


def images_list(limit: int, offset: int, sort_by: str, order: str, username: str | None, prediction: str | None):
    t = _tbl(IMAGES_TABLE)

    scan_kwargs = {}
    items = []
    start_key = None
    while True:
        if start_key:
            res = t.scan(ExclusiveStartKey=start_key, **scan_kwargs)
        else:
            res = t.scan(**scan_kwargs)
        items.extend(res.get("Items", []))
        start_key = res.get("LastEvaluatedKey")
        if not start_key:
            break
        if len(items) >= 2000:
            break
        time.sleep(0.05)

    if username:
        uid = None
        u = _query_user_by_username(username)
        if u:
            uid = u["id"]
        items = [i for i in items if i.get("user_id") == uid] if uid else []

    if prediction:
        items = [i for i in items if i.get("prediction") == prediction]

    allowed = {"uploaded_at", "id", "filename", "prediction", "image_id"}
    key = sort_by if sort_by in allowed else "uploaded_at"
    reverse = (order or "desc").lower() == "desc"
    items.sort(key=lambda x: x.get(key, ""), reverse=reverse)

    start = offset or 0
    end = start + (limit or 10)
    return items[start:end]


def images_delete(image_id: str):
    t = _tbl(IMAGES_TABLE)
    try:
        t.delete_item(Key={"id": image_id}, ConditionExpression="attribute_exists(id)")
        return {"deleted": True}
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {"deleted": False}
        raise




def put_accuracy(user_id: str, accuracy: float):
    t = _tbl(ACCURACY_TABLE)
    item = {"user_id": user_id, "accuracy": float(accuracy), "updated_at": _now_iso()}
    t.put_item(Item=item)
    return {"updated": True}



__all__ = [
    "dynamo",
    "ensure_all",
    "bootstrap_default_users",
    "users_insert",
    "users_get_id_by_credentials",
    "users_get_username_by_id",
    "users_is_admin",
    "images_insert",
    "images_update_user_prediction",
    "images_update_s3_key",
    "images_get_by_id",
    "images_list",
    "images_delete",
    "put_accuracy",
]