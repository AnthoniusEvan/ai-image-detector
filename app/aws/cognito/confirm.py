import boto3
import os
import hmac, hashlib, base64 
from dotenv import load_dotenv
load_dotenv()

username= "user"
client_id = os.environ['AWS_COGNITO_CLIENT_ID']
client_secret = os.environ['AWS_COGNITO_CLIENT_SECRET']
confirmation_code = "886766" #Obtain from the verification email

def secretHash(clientId, clientSecret, username):
    message = bytes(username + clientId,'utf-8') 
    key = bytes(clientSecret,'utf-8') 
    return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode() 

def confirm(username, confirmation_code):
    client = boto3.client("cognito-idp", region_name="ap-southeast-2")
    response = client.confirm_sign_up(
        ClientId=client_id,
        Username=username,
        ConfirmationCode=confirmation_code,
        SecretHash=secretHash(client_id, client_secret, username)
    )
    return response

if __name__ == "__main__":
    confirm_response = confirm(username, confirmation_code)
    print("Confirmation successful:", confirm_response)