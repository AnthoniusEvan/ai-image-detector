from fastapi import Query
from aws import dynamo

def insert_user(username, is_admin):
    return dynamo.users_insert(username, is_admin)

def get_user(username, password):
    uid = dynamo.users_get_id_by_credentials(username, password)
    return uid

def get_username(id):
    return dynamo.users_get_username_by_id(str(id))

def is_user_admin(id):
    return dynamo.users_is_admin(str(id))

def get_uploaded_images_adv(limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0), sort_by: str = Query("uploaded_at"), order: str = Query("desc", regex="^(asc|desc)$"), username: str | None = None, prediction: str | None = None):
    return dynamo.images_list(limit, offset, sort_by, order, username, prediction)

def get_uploaded_images():
    return dynamo.images_list(1000, 0, "uploaded_at", "desc", None, None)

def get_image_by_id(image_id):
    return dynamo.images_get_by_id(str(image_id))

def insert_image(filename, s3_key, user_id, prediction, confidence):
    return dynamo.images_insert(filename, s3_key, str(user_id), prediction, confidence)

def update_user_prediction(image_id, prediction):
    return dynamo.images_update_user_prediction(str(image_id), prediction)

def update_image_s3_key(image_id, s3_key):
    return dynamo.images_update_s3_key(str(image_id), s3_key)

def delete_image(image_id):
    return dynamo.images_delete(str(image_id))

def update_high_score(user_id, high_score):
    return {"updated": False}