<<<<<<< Updated upstream
<<<<<<< Updated upstream:app/aws/cognito/signUp.py
# app/aws/cognito/signUp.py
import os
import hmac, hashlib, base64
import boto3
from typing import Optional

REGION = os.getenv("AWS_REGION", "ap-southeast-2")
=======
=======
>>>>>>> Stashed changes
import boto3
import os
import hmac, hashlib, base64 
from dotenv import load_dotenv
load_dotenv()

client_id = os.environ['AWS_COGNITO_CLIENT_ID']
client_secret = os.environ['AWS_COGNITO_CLIENT_SECRET']
<<<<<<< Updated upstream
>>>>>>> Stashed changes:app/aws_related/cognito/auth.py

def _secret_hash(client_id: str, client_secret: str, username: str) -> str:
    message = (username + client_id).encode("utf-8")
    key = client_secret.encode("utf-8")
    return base64.b64encode(hmac.new(key, message, hashlib.sha256).digest()).decode()

def signup(
    username: str,
    password: str,
    email: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    region: str = REGION,
):
    """
    CLI helper. Call this manually; do not import from the web app.
    Reads client_id/secret from args or environment if provided.
    """
    client_id = client_id or os.getenv("AWS_COGNITO_CLIENT_ID")
    client_secret = client_secret or os.getenv("AWS_COGNITO_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Set AWS_COGNITO_CLIENT_ID and AWS_COGNITO_CLIENT_SECRET to use signup()")

    client = boto3.client("cognito-idp", region_name=region)
    return client.sign_up(
        ClientId=client_id,
        Username=username,
        Password=password,
        SecretHash=_secret_hash(client_id, client_secret, username),
        UserAttributes=[{"Name": "email", "Value": email}],
    )

<<<<<<< Updated upstream:app/aws/cognito/signUp.py
if __name__ == "__main__":
    # Example usage; edit values before running this file directly.
    u = os.getenv("DEMO_USERNAME", "user")
    p = os.getenv("DEMO_PASSWORD", "MySuperSecret99!")
    e = os.getenv("DEMO_EMAIL", "someone@example.com")
    print(signup(u, p, e))
=======
=======

def secretHash(clientId, clientSecret, username):
    message = bytes(username + clientId,'utf-8') 
    key = bytes(clientSecret,'utf-8') 
    return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode() 

def signup(username, password, email):
    client = boto3.client("cognito-idp", region_name="ap-southeast-2")
    response = client.sign_up(
        ClientId=client_id,
        Username=username,
        Password=password,
        SecretHash=secretHash(client_id, client_secret, username),
        UserAttributes=[{"Name": "email", "Value": email}]
    )
    return response

>>>>>>> Stashed changes
def confirm(username, confirmation_code):
    client = boto3.client("cognito-idp", region_name="ap-southeast-2")
    response = client.confirm_sign_up(
        ClientId=client_id,
        Username=username,
        ConfirmationCode=confirmation_code,
        SecretHash=secretHash(client_id, client_secret, username)
    )
<<<<<<< Updated upstream
    return response
>>>>>>> Stashed changes:app/aws_related/cognito/auth.py
=======
    return response
>>>>>>> Stashed changes
