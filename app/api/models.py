from fastapi import Query
from db.db import get_connection

def insert_user(username, is_admin):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, is_admin) VALUES (?,?)", (username,is_admin))
    conn.commit()
    id = cursor.lastrowid
    conn.close()
    return {"id": id,"username": username,"is_admin": "true" if is_admin else "false"}

def get_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * from users WHERE username=? AND password=SHA2(?,512)", (username,password))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def get_username(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username from users WHERE id=?", (id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def is_user_admin(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin from users WHERE id=?", (id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def get_uploaded_images_adv(limit: int = Query(10, ge=1, le=100),offset: int = Query(0, ge=0), sort_by: str = Query("uploaded_at"), order: str = Query("desc", regex="^(asc|desc)$"),username: str | None = None, prediction: str | None = None):
    query = "SELECT * FROM uploaded_images"
    conditions = []
    params = []

    if username:
        conditions.append("user_id = (SELECT id FROM users WHERE username = ?)")
        params.append(username)

    if prediction:
        conditions.append("prediction = ?")
        params.append(prediction)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += f" ORDER BY {sort_by} {order.upper()}"
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def get_uploaded_images():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * from uploaded_images")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def get_image_by_id(image_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * from uploaded_images WHERE id=?", (image_id,))
    row = cursor.fetchone()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    if row:
        return dict(zip(columns, row))
    return None

def insert_image(filename, s3_key, user_id, prediction, confidence):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO uploaded_images (filename, s3_key, user_id, prediction, confidence) VALUES (?, ?, ?, ?, ?)",
        (filename, s3_key, user_id, prediction, confidence)
    )
    conn.commit()
    id = cursor.lastrowid
    conn.close()
    return {"id": id,"filename": filename,"s3_key": s3_key,"user_id": user_id,"prediction": prediction,"confidence": confidence}

def update_user_prediction(image_id, prediction):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE uploaded_images SET user_prediction = ? WHERE id = ?",
        (prediction, image_id)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return {"updated": updated}

def update_high_score(user_id, high_score):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET high_score = ? WHERE id = ?",
        (high_score, user_id)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return {"updated": updated}

def update_image_s3_key(image_id, s3_key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE uploaded_images SET s3_key = ? WHERE id = ?",
        (s3_key, image_id)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return {"updated": updated}

def delete_image(image_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM uploaded_images WHERE id = ?", (image_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return {"deleted": deleted}