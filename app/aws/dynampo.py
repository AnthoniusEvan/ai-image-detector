# aws/dynamo.py

import os
import time
from typing import Optional
import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
QUT_USERNAME = os.environ.get("QUT_USERNAME")
if not QUT_USERNAME:
    raise RuntimeError("QUT_USERNAME env var is required for DynamoDB access")

TABLE_NAME = os.environ.get("DDB_TABLE", f"{QUT_USERNAME}-ai-accuracy")
PK_NAME = "qut-username"
SK_NAME = "user_id"

dynamodb = boto3.client("dynamodb", region_name=REGION)

def ensure_table() -> None:
    try:
        dynamodb.describe_table(TableName=TABLE_NAME)
        return
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
    try:
        dynamodb.create_table(
            TableName=TABLE_NAME,
            AttributeDefinitions=[
                {"AttributeName": PK_NAME, "AttributeType": "S"},
                {"AttributeName": SK_NAME, "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": PK_NAME, "KeyType": "HASH"},
                {"AttributeName": SK_NAME, "KeyType": "RANGE"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceInUseException":
            raise
    while True:
        desc = dynamodb.describe_table(TableName=TABLE_NAME)
        if desc["Table"]["TableStatus"] == "ACTIVE":
            break
        time.sleep(1)

def put_accuracy(user_id: int, accuracy: float) -> dict:
    ensure_table()
    try:
        dynamodb.update_item(
            TableName=TABLE_NAME,
            Key={
                PK_NAME: {"S": QUT_USERNAME},
                SK_NAME: {"S": str(user_id)},
            },
            UpdateExpression="SET accuracy = :val",
            ExpressionAttributeValues={":val": {"N": str(accuracy)}},
            ReturnValues="ALL_NEW",
        )
        return {"updated": True}
    except ClientError as e:
        raise

def get_accuracy(user_id: int) -> Optional[float]:
    ensure_table()
    try:
        res = dynamodb.get_item(
            TableName=TABLE_NAME,
            Key={
                PK_NAME: {"S": QUT_USERNAME},
                SK_NAME: {"S": str(user_id)},
            },
            ConsistentRead=True,
        )
        item = res.get("Item")
        if not item:
            return None
        val = item.get("accuracy", {}).get("N")
        return float(val) if val is not None else None
    except ClientError:
        raise