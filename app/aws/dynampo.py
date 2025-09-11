import os
import time
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
QUT_USERNAME = os.environ.get("QUT_USERNAME")
if not QUT_USERNAME:
    raise RuntimeError("QUT_USERNAME env var is required")
USERS_TABLE = os.environ.get("DDB_USERS_TABLE", f"{QUT_USERNAME}-users")
IMAGES_TABLE = os.environ.get("DDB_IMAGES_TABLE", f"{QUT_USERNAME}-images")
ACCURACY_TABLE = os.environ.get("DDB_TABLE", f"{QUT_USERNAME}-ai-accuracy")

dynamodb = boto3.client("dynamodb", region_name=REGION)

def _wait_active(name: str) -> None:
    while True:
        d = dynamodb.describe_table(TableName=name)
        if d["Table"]["TableStatus"] == "ACTIVE":
            break
        time.sleep(1)

def ensure_all() -> None:
    try:
        dynamodb.describe_table(TableName=USERS_TABLE)
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        dynamodb.create_table(
            TableName=USERS_TABLE,
            AttributeDefinitions=[{"AttributeName": "qut-username", "AttributeType": "S"},
                                  {"AttributeName": "username", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "qut-username", "KeyType": "HASH"},
                       {"AttributeName": "username", "KeyType": "RANGE"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )
        _wait_active(USERS_TABLE)
    try:
        dynamodb.describe_table(TableName=IMAGES_TABLE)
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        dynamodb.create_table(
            TableName=IMAGES_TABLE,
            AttributeDefinitions=[{"AttributeName": "qut-username", "AttributeType": "S"},
                                  {"AttributeName": "image_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "qut-username", "KeyType": "HASH"},
                       {"AttributeName": "image_id", "KeyType": "RANGE"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )
        _wait_active(IMAGES_TABLE)
    try:
        dynamodb.describe_table(TableName=ACCURACY_TABLE)
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        dynamodb.create_table(
            TableName=ACCURACY_TABLE,
            AttributeDefinitions=[{"AttributeName": "qut-username", "AttributeType": "S"},
                                  {"AttributeName": "user_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "qut-username", "KeyType": "HASH"},
                       {"AttributeName": "user_id", "KeyType": "RANGE"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )
        _wait_active(ACCURACY_TABLE)

def _sha512_hex(s: str) -> str:
    return hashlib.sha512(s.encode("utf-8")).hexdigest()

def bootstrap_default_users() -> None:
    for u, p, admin in [("admin", "admin", 1), ("user", "user", 0)]:
        try:
            dynamodb.put_item(
                TableName=USERS_TABLE,
                Item={
                    "qut-username": {"S": QUT_USERNAME},
                    "username": {"S": u},
                    "id": {"S": str(uuid.uuid4())},
                    "password": {"S": _sha512_hex(p)},
                    "is_admin": {"N": str(admin)},
                },
                ConditionExpression="attribute_not_exists(username)",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] not in ("ConditionalCheckFailedException",):
                raise

def users_insert(username: str, is_admin: int, password: Optional[str] = None) -> Dict[str, Any]:
    uid = str(uuid.uuid4())
    pw = _sha512_hex(password or username)
    dynamodb.put_item(
        TableName=USERS_TABLE,
        Item={
            "qut-username": {"S": QUT_USERNAME},
            "username": {"S": username},
            "id": {"S": uid},
            "password": {"S": pw},
            "is_admin": {"N": str(is_admin or 0)},
        },
        ConditionExpression="attribute_not_exists(username)",
    )
    return {"id": uid, "username": username, "is_admin": "true" if is_admin else "false"}

def users_get_id_by_credentials(username: str, password: str) -> Optional[str]:
    r = dynamodb.get_item(
        TableName=USERS_TABLE,
        Key={"qut-username": {"S": QUT_USERNAME}, "username": {"S": username}},
        ConsistentRead=True,
    )
    it = r.get("Item")
    if not it:
        return None
    if it.get("password", {}).get("S") != _sha512_hex(password):
        return None
    return it.get("id", {}).get("S")

def users_get_username_by_id(user_id: str) -> Optional[str]:
    ean = {"#pk": "qut-username"}
    eav = {":pk": {"S": QUT_USERNAME}}
    r = dynamodb.scan(
        TableName=USERS_TABLE,
        FilterExpression="#pk = :pk",
        ExpressionAttributeNames=ean,
        ExpressionAttributeValues=eav,
    )
    for it in r.get("Items", []):
        if it.get("id", {}).get("S") == user_id:
            return it.get("username", {}).get("S")
    return None

def users_is_admin(user_id: str) -> bool:
    ean = {"#pk": "qut-username"}
    eav = {":pk": {"S": QUT_USERNAME}}
    r = dynamodb.scan(
        TableName=USERS_TABLE,
        FilterExpression="#pk = :pk",
        ExpressionAttributeNames=ean,
        ExpressionAttributeValues=eav,
    )
    for it in r.get("Items", []):
        if it.get("id", {}).get("S") == user_id:
            return int(it.get("is_admin", {}).get("N", "0")) == 1
    return False

def images_insert(filename: str, s3_key: str, user_id: str, prediction: str, confidence: float) -> Dict[str, Any]:
    image_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    dynamodb.put_item(
        TableName=IMAGES_TABLE,
        Item={
            "qut-username": {"S": QUT_USERNAME},
            "image_id": {"S": image_id},
            "filename": {"S": filename},
            "s3_key": {"S": s3_key},
            "user_id": {"S": str(user_id)},
            "prediction": {"S": prediction} if prediction is not None else {"S": ""},
            "confidence": {"N": str(confidence if confidence is not None else 0)},
            "uploaded_at": {"S": now},
            "user_prediction": {"S": ""},
        },
    )
    return {"id": image_id, "filename": filename, "s3_key": s3_key, "user_id": user_id, "prediction": prediction, "confidence": confidence}

def images_update_user_prediction(image_id: str, prediction: str) -> Dict[str, Any]:
    dynamodb.update_item(
        TableName=IMAGES_TABLE,
        Key={"qut-username": {"S": QUT_USERNAME}, "image_id": {"S": image_id}},
        UpdateExpression="SET user_prediction = :p",
        ExpressionAttributeValues={":p": {"S": prediction}},
        ReturnValues="UPDATED_NEW",
    )
    return {"updated": True}

def images_update_s3_key(image_id: str, s3_key: str) -> Dict[str, Any]:
    dynamodb.update_item(
        TableName=IMAGES_TABLE,
        Key={"qut-username": {"S": QUT_USERNAME}, "image_id": {"S": image_id}},
        UpdateExpression="SET s3_key = :k",
        ExpressionAttributeValues={":k": {"S": s3_key}},
        ReturnValues="UPDATED_NEW",
    )
    return {"updated": True}

def images_delete(image_id: str) -> Dict[str, Any]:
    r = dynamodb.delete_item(
        TableName=IMAGES_TABLE,
        Key={"qut-username": {"S": QUT_USERNAME}, "image_id": {"S": image_id}},
        ReturnValues="ALL_OLD",
    )
    return {"deleted": "Attributes" in r}

def images_get_by_id(image_id: str) -> Optional[Dict[str, Any]]:
    r = dynamodb.get_item(
        TableName=IMAGES_TABLE,
        Key={"qut-username": {"S": QUT_USERNAME}, "image_id": {"S": image_id}},
        ConsistentRead=True,
    )
    it = r.get("Item")
    if not it:
        return None
    out = {k: list(v.values())[0] for k, v in it.items()}
    if "confidence" in out:
        out["confidence"] = float(out["confidence"])
    return out

def images_list(limit: int, offset: int, sort_by: str, order: str, username: Optional[str], prediction: Optional[str]) -> List[Dict[str, Any]]:
    ean = {"#pk": "qut-username"}
    eav = {":pk": {"S": QUT_USERNAME}}
    r = dynamodb.scan(
        TableName=IMAGES_TABLE,
        FilterExpression="#pk = :pk",
        ExpressionAttributeNames=ean,
        ExpressionAttributeValues=eav,
    )
    items = []
    for it in r.get("Items", []):
        obj = {k: list(v.values())[0] for k, v in it.items()}
        if "confidence" in obj:
            obj["confidence"] = float(obj["confidence"])
        items.append(obj)
    if username:
        uid = None
        ean2 = {"#pk": "qut-username"}
        eav2 = {":pk": {"S": QUT_USERNAME}}
        ru = dynamodb.scan(
            TableName=USERS_TABLE,
            FilterExpression="#pk = :pk",
            ExpressionAttributeNames=ean2,
            ExpressionAttributeValues=eav2,
        )
        for u in ru.get("Items", []):
            if u.get("username", {}).get("S") == username:
                uid = u.get("id", {}).get("S")
                break
        items = [i for i in items if i.get("user_id") == uid] if uid else []
    if prediction:
        items = [i for i in items if i.get("prediction") == prediction]
    allowed = {"uploaded_at", "id", "filename", "prediction", "image_id"}
    key = sort_by if sort_by in allowed else "uploaded_at"
    reverse = order.lower() == "desc"
    items.sort(key=lambda x: x.get(key) or "", reverse=reverse)
    start = max(0, offset)
    end = start + max(1, min(100, limit))
    return items[start:end]

def put_accuracy(user_id: str, accuracy: float) -> Dict[str, Any]:
    dynamodb.update_item(
        TableName=ACCURACY_TABLE,
        Key={"qut-username": {"S": QUT_USERNAME}, "user_id": {"S": str(user_id)}},
        UpdateExpression="SET accuracy = :v",
        ExpressionAttributeValues={":v": {"N": str(accuracy)}},
        ReturnValues="ALL_NEW",
    )
    return {"updated": True}

def get_accuracy(user_id: str) -> Optional[float]:
    r = dynamodb.get_item(
        TableName=ACCURACY_TABLE,
        Key={"qut-username": {"S": QUT_USERNAME}, "user_id": {"S": str(user_id)}},
        ConsistentRead=True,
    )
    it = r.get("Item")
    if not it:
        return None
    v = it.get("accuracy", {}).get("N")
    return float(v) if v is not None else None